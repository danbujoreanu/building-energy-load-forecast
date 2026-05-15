"""
Energy RAG — Manual Ingest (changed files only)
================================================
Iterates all tiers, finds .md files whose SHA-256 has changed or is not yet
in ChromaDB, and ingests them. Use this:

  - When the auto-ingest watcher (energy-ingest-watch.service) is down
  - For a full corpus resync after restoring ChromaDB from backup
  - With --dry-run to see what would be ingested without touching the DB
  - With --force to re-embed everything regardless of hash state

Usage (on NUC — inside sparc-api container):
    docker exec sparc-api python3 /app/scripts/ingest_changed.py
    docker exec sparc-api python3 /app/scripts/ingest_changed.py --dry-run
    docker exec sparc-api python3 /app/scripts/ingest_changed.py --tier operational
    docker exec sparc-api python3 /app/scripts/ingest_changed.py --force

Port from: Gardening scripts/ingest_changed.py (2026-05-13)
"""

import argparse
import hashlib
import logging
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, "/app")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ingest-changed")
logging.getLogger("chromadb").setLevel(logging.CRITICAL)

DOCS_ROOT = Path("/app/intel/docs")

TIER_MAP: dict[str, str] = {
    "operational": "operational",
    "strategic": "strategic",
    "research": "research",
    "market": "market",
    "career": "career",
    "mba": "mba",
    "garden": "garden",
    "engineering": "engineering",
    "regulatory": "regulatory",
}

# Extra source paths per tier — outside intel/docs/, resolved at runtime.
# Each entry is a list of (path, recursive) tuples. Paths that don't exist are
# silently skipped (safe on NUC where Mac-local Career paths are absent).
_CAREER_ROOT = Path.home() / "Personal Projects" / "Career"
EXTRA_PATHS: dict[str, list[tuple[Path, bool]]] = {
    "career": [
        (_CAREER_ROOT / "Applications" / "Pipeline", True),
        (_CAREER_ROOT / "Applications" / "Closed" / "2026", True),
        (_CAREER_ROOT / "00_Master_Resume", False),
        (_CAREER_ROOT, False),  # single root-level .md files (TARGET_ROLE_PROFILE etc.)
    ],
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _known_hashes(tier: str) -> dict[str, set[str]]:
    """
    Returns {filename: {hash1, hash2, ...}} for all chunks in the collection.

    We collect ALL hashes per filename as a set — not just the first one.
    Files ingested multiple times (before dedup was enforced) have old + new
    chunks in ChromaDB with different hashes. Using a set catches all of them.
    """
    try:
        import chromadb
        import os

        chroma_path = os.environ.get("CHROMA_PATH", "/app/outputs/chromadb")
        client = chromadb.PersistentClient(path=chroma_path)
        collection_name = f"intel_{tier}"
        try:
            collection = client.get_collection(collection_name)
        except Exception:
            return {}

        metadatas = collection.get(include=["metadatas"])["metadatas"]
        hashes: dict[str, set[str]] = {}
        for meta in metadatas:
            src = meta.get("file_name", "")
            h = meta.get("doc_hash", "")
            if src and h:
                hashes.setdefault(src, set()).add(h)
        return hashes
    except Exception as exc:
        logger.warning("Could not read ChromaDB hashes for tier %s: %s", tier, exc)
        return {}


# Flush logic promoted to intel.ingest.flush_tier() (2026-05-14).
# Canonical implementation lives there — same singleton constraint applies.


def run(tiers: list[str], dry_run: bool, force: bool) -> None:
    from intel.ingest import ingest_file, flush_tier

    total_ingested = 0
    total_skipped = 0
    total_errors = 0

    for tier in tiers:
        # Primary source: intel/docs/<tier>/
        tier_dir = DOCS_ROOT / tier
        md_files: list[Path] = []
        if tier_dir.exists():
            md_files.extend(sorted(tier_dir.glob("*.md")))

        # Extra sources: tier-specific paths outside intel/docs/ (e.g. Career project)
        for extra_root, recursive in EXTRA_PATHS.get(tier, []):
            if not extra_root.exists():
                continue
            pattern = "**/*.md" if recursive else "*.md"
            md_files.extend(sorted(extra_root.glob(pattern)))

        # Deduplicate (preserve order) in case paths overlap
        seen: set[Path] = set()
        md_files = [p for p in md_files if not (p in seen or seen.add(p))]  # type: ignore[func-returns-value]

        if not md_files:
            logger.debug("Tier dir does not exist or is empty, skipping: %s", tier)
            continue

        logger.info("── Tier: %s (%d files) ──", tier, len(md_files))

        known = {} if force else _known_hashes(tier)
        tier_ingested = 0

        for path in md_files:
            current_hash = _sha256(path)
            existing_hashes = known.get(path.name, set())

            if not force and current_hash in existing_hashes:
                logger.info("  skip  %s (hash unchanged)", path.name)
                total_skipped += 1
                continue

            if dry_run:
                logger.info("  would ingest  %s (hash=%s)", path.name, current_hash[:8])
                total_ingested += 1
                continue

            try:
                result = ingest_file(str(path), tier)
                # ingest_file returns bool: True = ingested/skipped, False = error
                if result is False:
                    raise RuntimeError("ingest_file returned False (see ingest.py logs)")
                logger.info("  ✓  %s ingested", path.name)
                total_ingested += 1
                tier_ingested += 1
                time.sleep(0.5)  # avoid UniVec API rate limit on large batches
            except Exception as exc:
                logger.error("  ✗  %s — %s", path.name, exc)
                total_errors += 1
                time.sleep(1.0)  # back off longer on error

        # Per-tier flush + count-check (raises RuntimeError if post-flush count == 0).
        # Must run in the same process as ingest_file() to access _curr_batch.
        if not dry_run and tier_ingested > 0:
            try:
                verified = flush_tier(tier)
                logger.info("  flush %s — %d chunks verified", tier, verified)
            except RuntimeError as exc:
                logger.error("  %s", exc)
                total_errors += 1

    label = "[DRY RUN] " if dry_run else ""
    logger.info(
        "%sDone — ingested: %d, skipped: %d, errors: %d",
        label,
        total_ingested,
        total_skipped,
        total_errors,
    )



def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest changed Energy RAG documents")
    parser.add_argument(
        "--tier",
        choices=list(TIER_MAP),
        help="Process a single tier only (default: all tiers)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be ingested without touching ChromaDB",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed all files regardless of hash state",
    )
    args = parser.parse_args()

    tiers = [args.tier] if args.tier else list(TIER_MAP)
    run(tiers=tiers, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
