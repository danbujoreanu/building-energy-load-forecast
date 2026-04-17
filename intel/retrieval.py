"""
intel/retrieval.py
==================
Query ChromaDB collections and return ranked answers with source citations.

Follows the spec in docs/ENERGY_INTELLIGENCE_MODULE_BRIEF.md §7 "Key Code Patterns".

LLM strategy:
  - If GEMINI_API_KEY env var is set: uses Gemini Flash for answer synthesis
    (requires: pip install llama-index-llms-gemini)
  - Otherwise: ResponseMode.CONTEXT_ONLY — top retrieved chunks are
    concatenated as the answer. No API call. Zero cost.

Confidence scoring:
  - ChromaDB cosine similarity scores are in [0, 1].
  - If the top chunk score < LOW_CONFIDENCE_THRESHOLD (0.60), the answer is
    prefixed with "[Low confidence — no strong match found in corpus]".
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.core.response_synthesizers import ResponseMode, get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
LOW_CONFIDENCE_THRESHOLD = 0.60
VALID_TIERS = {"operational", "strategic", "research", "market"}

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHROMA_PATH = str(_PROJECT_ROOT / "data" / "chromadb")

# Lazy singletons
_embed_model: Optional[HuggingFaceEmbedding] = None
_chroma_client: Optional[chromadb.PersistentClient] = None
_llm = None
_llm_checked = False


def _get_embed_model() -> HuggingFaceEmbedding:
    global _embed_model
    if _embed_model is None:
        logger.debug("Loading embedding model: %s", EMBED_MODEL_NAME)
        _embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)
    return _embed_model


def _get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _chroma_client


def _get_llm():
    """Return a Gemini LLM instance if GEMINI_API_KEY is set, else None."""
    global _llm, _llm_checked
    if _llm_checked:
        return _llm
    _llm_checked = True

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.debug("GEMINI_API_KEY not set — retrieval-only mode (no LLM synthesis)")
        return None

    try:
        from llama_index.llms.gemini import Gemini  # type: ignore
        _llm = Gemini(model="models/gemini-2.0-flash", api_key=api_key)
        logger.info("Gemini Flash LLM loaded for answer synthesis")
    except ImportError:
        logger.warning(
            "GEMINI_API_KEY is set but llama-index-llms-gemini is not installed. "
            "Falling back to context-only mode. "
            "Install with: pip install llama-index-llms-gemini"
        )
    return _llm


# ── Core query function ───────────────────────────────────────────────────────

def query_tier(tier: str, question: str, top_k: int = 5) -> dict:
    """Query a tier and return answer + source citations + confidence flag.

    Parameters
    ----------
    tier : str
        One of: operational | strategic | research | market.
    question : str
        Natural language question.
    top_k : int
        Number of chunks to retrieve (default: 5).

    Returns
    -------
    dict with keys:
        answer    : str   — answer text (or low-confidence prefix + context)
        sources   : list  — [{file, score, excerpt}, ...]
        tier      : str
        top_score : float — cosine similarity of the best chunk (0–1)
        llm_used  : bool  — whether LLM synthesis was applied
    """
    if tier not in VALID_TIERS:
        raise ValueError(f"Unknown tier '{tier}'. Valid: {sorted(VALID_TIERS)}")

    chroma_client = _get_chroma_client()
    collection_name = f"intel_{tier}"

    # Get or create collection (empty collection = graceful empty response)
    try:
        collection = chroma_client.get_collection(collection_name)
    except Exception:
        logger.info("Collection '%s' not found — returning empty result", collection_name)
        return {
            "answer": "[Low confidence — no strong match found in corpus]\n\nNo documents have been ingested into this tier yet.",
            "sources": [],
            "tier": tier,
            "top_score": 0.0,
            "llm_used": False,
        }

    embed_model = _get_embed_model()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)

    llm = _get_llm()
    llm_used = llm is not None

    if llm_used:
        # LLM synthesis path (Gemini Flash)
        query_engine = index.as_query_engine(
            similarity_top_k=top_k,
            llm=llm,
        )
        response = query_engine.query(question)
        source_nodes = response.source_nodes
        answer = str(response)
    else:
        # Retrieval-only path — no LLM needed
        retriever = index.as_retriever(similarity_top_k=top_k)
        source_nodes = retriever.retrieve(question)

        # Build answer by concatenating top chunks
        if source_nodes:
            answer_parts = []
            for i, node in enumerate(source_nodes, 1):
                src = node.metadata.get("source_file", "unknown")
                answer_parts.append(f"[Source {i}: {src}]\n{node.text.strip()}")
            answer = "\n\n---\n\n".join(answer_parts)
        else:
            answer = ""

    # ── Build sources list ────────────────────────────────────────────────────
    sources = []
    for node in source_nodes:
        score = getattr(node, "score", None) or 0.0
        sources.append({
            "file": node.metadata.get("source_file", "unknown"),
            "score": round(float(score), 3),
            "excerpt": node.text[:200],
            "tier": node.metadata.get("tier", tier),
            "title": node.metadata.get("title", ""),
        })

    top_score = sources[0]["score"] if sources else 0.0

    # ── Confidence flag ───────────────────────────────────────────────────────
    if top_score < LOW_CONFIDENCE_THRESHOLD:
        answer = f"[Low confidence — no strong match found in corpus]\n\n{answer}"

    return {
        "answer": answer,
        "sources": sources,
        "tier": tier,
        "top_score": top_score,
        "llm_used": llm_used,
    }


def query_all_tiers(question: str, top_k: int = 3) -> dict:
    """Query all tiers and return merged results sorted by score.

    Parameters
    ----------
    question : str
        Natural language question.
    top_k : int
        Chunks per tier (default: 3).

    Returns
    -------
    dict with keys:
        answer      : str   — best answer (from highest-scoring tier)
        sources     : list  — all sources merged, sorted by score
        top_score   : float
        tier        : str   — tier of the best match
        llm_used    : bool
    """
    all_sources: list[dict] = []
    best_result: dict = {}
    best_score = -1.0

    for tier in sorted(VALID_TIERS):
        try:
            result = query_tier(tier, question, top_k=top_k)
        except Exception as exc:
            logger.warning("Error querying tier '%s': %s", tier, exc)
            continue

        all_sources.extend(result["sources"])
        if result["top_score"] > best_score:
            best_score = result["top_score"]
            best_result = result

    all_sources.sort(key=lambda s: s["score"], reverse=True)

    if not best_result:
        return {
            "answer": "[Low confidence — no strong match found in corpus]\n\nNo documents have been ingested yet.",
            "sources": [],
            "top_score": 0.0,
            "tier": "none",
            "llm_used": False,
        }

    return {
        "answer": best_result["answer"],
        "sources": all_sources[:top_k * len(VALID_TIERS)],
        "top_score": best_score,
        "tier": best_result["tier"],
        "llm_used": best_result["llm_used"],
    }
