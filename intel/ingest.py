"""
intel/ingest.py
===============
PDF/MD → chunk → embed → ChromaDB with deduplication.

Follows the spec in docs/ENERGY_INTELLIGENCE_MODULE_BRIEF.md §7 "Key Code Patterns".

Key design decisions:
  - SHA-256 hash of file content → stored as `doc_hash` in chunk metadata
  - Dedup check: skip if any chunk with matching doc_hash already exists
  - YAML frontmatter is parsed and ALL fields are attached as chunk metadata
  - SentenceSplitter(512 tokens, 50 overlap) per brief §5 diagram
  - Embedding: sentence-transformers/all-MiniLM-L6-v2 (local, zero cost)
  - One ChromaDB collection per tier: intel_operational, intel_strategic,
    intel_research, intel_market
  - ChromaDB persisted at ./data/chromadb/ (relative to project root)
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Optional

import chromadb
import yaml
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
VALID_TIERS = {"operational", "strategic", "research", "market"}

# Resolve ChromaDB path relative to this file's project root (two levels up from intel/)
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHROMA_PATH = str(_PROJECT_ROOT / "data" / "chromadb")

# Lazy-initialised singletons to avoid re-loading the model on every call
_embed_model: Optional[HuggingFaceEmbedding] = None
_chroma_client: Optional[chromadb.PersistentClient] = None


def _get_embed_model() -> HuggingFaceEmbedding:
    global _embed_model
    if _embed_model is None:
        logger.debug("Loading embedding model: %s", EMBED_MODEL_NAME)
        _embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)
    return _embed_model


def _get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _chroma_client


# ── YAML frontmatter parsing ──────────────────────────────────────────────────

def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from a markdown document.

    Returns (metadata_dict, body_text). If no frontmatter is found, returns
    ({}, original_content).
    """
    # Match --- ... --- at the very start of the document
    pattern = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = pattern.match(content)
    if not match:
        return {}, content

    try:
        metadata = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        logger.warning("Failed to parse YAML frontmatter: %s", exc)
        metadata = {}

    body = content[match.end():]
    return metadata, body


def _flatten_metadata(meta: dict) -> dict:
    """Flatten frontmatter for ChromaDB metadata storage.

    ChromaDB only accepts str/int/float/bool values — convert lists to
    comma-separated strings, drop None values.
    """
    flat: dict = {}
    for k, v in meta.items():
        if v is None:
            continue
        if isinstance(v, list):
            flat[k] = ", ".join(str(i) for i in v)
        elif isinstance(v, (str, int, float, bool)):
            flat[k] = v
        else:
            flat[k] = str(v)
    return flat


# ── Core ingest function ──────────────────────────────────────────────────────

def ingest_file(file_path: str | Path, tier: str) -> bool:
    """Ingest a single .md or .pdf file into ChromaDB.

    Parameters
    ----------
    file_path : str | Path
        Absolute or relative path to the document.
    tier : str
        One of: operational | strategic | research | market.

    Returns
    -------
    bool
        True if the file was ingested, False if it was skipped (already exists).

    Raises
    ------
    ValueError
        If ``tier`` is not a recognised value.
    FileNotFoundError
        If ``file_path`` does not exist.
    """
    file_path = Path(file_path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if tier not in VALID_TIERS:
        raise ValueError(f"Unknown tier '{tier}'. Valid: {sorted(VALID_TIERS)}")

    # ── Read content & compute hash ───────────────────────────────────────────
    content = file_path.read_text(encoding="utf-8")
    doc_hash = hashlib.sha256(content.encode()).hexdigest()

    # ── Open (or create) ChromaDB collection ─────────────────────────────────
    chroma_client = _get_chroma_client()
    collection_name = f"intel_{tier}"
    collection = chroma_client.get_or_create_collection(collection_name)

    # ── Deduplication check ───────────────────────────────────────────────────
    existing = collection.get(where={"doc_hash": doc_hash})
    if existing["ids"]:
        logger.info("Skipping — already ingested: %s", file_path.name)
        print(f"Skipping — already ingested: {file_path.name}")
        return False

    # ── Parse frontmatter ─────────────────────────────────────────────────────
    frontmatter, _body = _parse_frontmatter(content)
    flat_meta = _flatten_metadata(frontmatter)

    # ── Build LlamaIndex Document objects ─────────────────────────────────────
    documents = SimpleDirectoryReader(input_files=[str(file_path)]).load_data()

    # Attach all metadata to every document chunk
    for doc in documents:
        doc.metadata.update(flat_meta)
        doc.metadata["doc_hash"] = doc_hash
        doc.metadata["tier"] = tier
        doc.metadata["source_file"] = file_path.name
        doc.metadata["source_path"] = str(file_path)

    # ── Build index ───────────────────────────────────────────────────────────
    embed_model = _get_embed_model()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model,
        transformations=[splitter],
        show_progress=True,
    )

    title = frontmatter.get("title", file_path.name)
    logger.info("Ingested '%s' → collection '%s'", title, collection_name)
    print(f"✓ Ingested: {file_path.name} → tier '{tier}'  [{doc_hash[:8]}]")
    return True


# ── Tier-level helpers ────────────────────────────────────────────────────────

def ingest_tier(tier: str) -> dict:
    """Ingest all .md and .pdf files from intel/docs/{tier}/.

    Returns a summary dict: {ingested: int, skipped: int, errors: list[str]}.
    """
    if tier not in VALID_TIERS:
        raise ValueError(f"Unknown tier '{tier}'. Valid: {sorted(VALID_TIERS)}")

    tier_dir = _PROJECT_ROOT / "intel" / "docs" / tier
    if not tier_dir.exists():
        raise FileNotFoundError(f"Tier directory not found: {tier_dir}")

    files = sorted(tier_dir.glob("**/*.md")) + sorted(tier_dir.glob("**/*.pdf"))
    ingested = skipped = 0
    errors: list[str] = []

    for fp in files:
        try:
            result = ingest_file(fp, tier)
            if result:
                ingested += 1
            else:
                skipped += 1
        except Exception as exc:
            logger.error("Error ingesting %s: %s", fp.name, exc)
            errors.append(f"{fp.name}: {exc}")

    return {"tier": tier, "ingested": ingested, "skipped": skipped, "errors": errors}


def ingest_all() -> dict[str, dict]:
    """Ingest all tiers. Returns {tier: summary_dict}."""
    results = {}
    for tier in sorted(VALID_TIERS):
        tier_dir = _PROJECT_ROOT / "intel" / "docs" / tier
        if not tier_dir.exists():
            logger.debug("Tier directory missing (skipping): %s", tier_dir)
            continue
        results[tier] = ingest_tier(tier)
    return results


# ── Status helper ─────────────────────────────────────────────────────────────

def get_status() -> dict:
    """Return doc and chunk counts per tier.

    Example output::

        {
            "operational": {"docs": 2, "chunks": 123},
            "strategic":   {"docs": 0, "chunks": 0},
        }
    """
    client = _get_chroma_client()
    status: dict = {}

    for tier in sorted(VALID_TIERS):
        collection_name = f"intel_{tier}"
        try:
            col = client.get_collection(collection_name)
            all_meta = col.get(include=["metadatas"])
            hashes = {m.get("doc_hash") for m in all_meta["metadatas"] if m}
            status[tier] = {
                "docs": len(hashes),
                "chunks": col.count(),
            }
        except Exception:
            # Collection doesn't exist yet
            status[tier] = {"docs": 0, "chunks": 0}

    return status
