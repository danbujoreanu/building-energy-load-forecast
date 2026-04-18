#!/usr/bin/env python3
"""
scripts/intel_feeds.py
======================
RSS / Atom / Substack feed ingester for the Sparc Energy intel corpus.

Polls feeds defined in config/config.yaml → intel_feeds and ingests new
items into the appropriate ChromaDB tier. Deduplication by URL hash —
safe to re-run daily.

Usage
-----
    # Ingest all configured feeds
    python scripts/intel_feeds.py --ingest

    # Ingest a specific tier only
    python scripts/intel_feeds.py --ingest --tier strategic

    # Show feed status (last item count per feed)
    python scripts/intel_feeds.py --status

    # Add a new feed to config interactively
    python scripts/intel_feeds.py --add-feed

Schedule (Mac Mini, June 2026):
    Add to launchd or cron: run daily at 06:00
    python /path/to/scripts/intel_feeds.py --ingest >> /tmp/intel_feeds.log 2>&1

Substack example:
    Any Substack newsletter exposes RSS at: https://{name}.substack.com/feed
    Add to config.yaml under intel_feeds.market or intel_feeds.strategic.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_MAX_ITEMS = 20   # Per feed per run
_ITEM_CHAR_LIMIT   = 8_000  # Truncate very long articles


def _load_config() -> dict:
    import yaml
    cfg_path = _PROJECT_ROOT / "config" / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def _fetch_feed(url: str) -> list[dict]:
    """Fetch and parse an RSS/Atom feed. Returns list of entry dicts."""
    try:
        import feedparser
    except ImportError:
        logger.error("feedparser not installed. Run: pip install feedparser")
        return []

    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            logger.warning("Feed parse warning for %s: %s", url, feed.bozo_exception)
        return feed.entries
    except Exception as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return []


def _entry_to_markdown(entry: dict, feed_name: str) -> tuple[str, dict]:
    """Convert a feed entry to markdown text + metadata dict."""
    title = entry.get("title", "Untitled")
    link  = entry.get("link", "")
    published = entry.get("published", entry.get("updated", ""))

    # Build content: prefer summary > content > description
    content_raw = ""
    if hasattr(entry, "content") and entry.content:
        content_raw = entry.content[0].get("value", "")
    elif entry.get("summary"):
        content_raw = entry.summary
    elif entry.get("description"):
        content_raw = entry.description

    # Strip HTML tags simply
    import re
    content_clean = re.sub(r"<[^>]+>", " ", content_raw)
    content_clean = re.sub(r"\s+", " ", content_clean).strip()
    content_clean = content_clean[:_ITEM_CHAR_LIMIT]

    # Deduplication hash (stable on URL)
    url_hash = hashlib.sha256(link.encode()).hexdigest()[:16]

    markdown = textwrap.dedent(f"""
        # {title}

        **Source:** {feed_name}
        **URL:** {link}
        **Published:** {published}

        {content_clean}
    """).strip()

    metadata = {
        "source_url": link,
        "source_name": feed_name,
        "title": title,
        "published": published,
        "document_type": "feed_item",
        "url_hash": url_hash,
    }
    return markdown, metadata


def _is_already_ingested(url_hash: str, collection) -> bool:
    """Check if this URL hash already exists in the collection."""
    try:
        results = collection.get(where={"url_hash": url_hash}, limit=1, include=[])
        return len(results.get("ids", [])) > 0
    except Exception:
        return False


def ingest_feeds(tier_filter: str | None = None, max_items: int = _DEFAULT_MAX_ITEMS) -> dict:
    """Ingest all (or a specific tier's) configured feeds.

    Returns
    -------
    dict: {tier: {feed_name: {ingested: int, skipped: int, errors: int}}}
    """
    import chromadb
    from intel.ingest import CHROMA_PATH, VALID_TIERS

    cfg = _load_config()
    feed_config: dict = cfg.get("intel_feeds", {})

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    results: dict = {}

    for tier, feeds in feed_config.items():
        if tier_filter and tier != tier_filter:
            continue
        if not feeds:
            continue

        # Dynamically allow new tiers (mba, garden, etc.)
        collection_name = f"intel_{tier}"
        try:
            collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            logger.error("Could not open collection %s: %s", collection_name, exc)
            continue

        results[tier] = {}

        for feed_entry in feeds:
            if isinstance(feed_entry, str):
                url, name = feed_entry, feed_entry
            else:
                url  = feed_entry.get("url", "")
                name = feed_entry.get("name", url)

            if not url:
                continue

            ingested = skipped = errors = 0
            entries = _fetch_feed(url)

            for entry in entries[:max_items]:
                try:
                    link = entry.get("link", "")
                    if not link:
                        skipped += 1
                        continue

                    url_hash = hashlib.sha256(link.encode()).hexdigest()[:16]
                    if _is_already_ingested(url_hash, collection):
                        skipped += 1
                        continue

                    markdown, metadata = _entry_to_markdown(entry, name)
                    metadata["tier"] = tier

                    # Embed and store
                    from intel.ingest import _get_embedding_model
                    embed_model = _get_embedding_model()
                    embedding = embed_model.get_text_embedding(markdown)

                    doc_id = f"feed_{tier}_{url_hash}"
                    collection.add(
                        ids=[doc_id],
                        documents=[markdown],
                        embeddings=[embedding],
                        metadatas=[metadata],
                    )
                    ingested += 1

                except Exception as exc:
                    logger.error("Error ingesting entry from %s: %s", name, exc)
                    errors += 1

            results[tier][name] = {"ingested": ingested, "skipped": skipped, "errors": errors}
            status = f"+{ingested} new, {skipped} existing"
            print(f"  [{tier}] {name[:50]:50s} {status}")

    return results


def show_status() -> None:
    """Show item counts per tier from ChromaDB."""
    import chromadb
    from intel.ingest import CHROMA_PATH

    cfg = _load_config()
    feed_config = cfg.get("intel_feeds", {})
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    print("\n📊 Intel feed status:")
    print(f"  {'Tier':12s} {'Collection':25s} {'Items':>8s}")
    print("  " + "─" * 50)

    for tier in feed_config:
        collection_name = f"intel_{tier}"
        try:
            collection = client.get_collection(collection_name)
            count = collection.count()
        except Exception:
            count = 0
        print(f"  {tier:12s} {collection_name:25s} {count:>8,}")


def main():
    parser = argparse.ArgumentParser(
        description="Intel feed ingester — RSS/Atom/Substack → ChromaDB"
    )
    parser.add_argument("--ingest", action="store_true",
                        help="Ingest all configured feeds")
    parser.add_argument("--tier", type=str, default=None,
                        help="Ingest only this tier (e.g. strategic, research, market)")
    parser.add_argument("--max-items", type=int, default=_DEFAULT_MAX_ITEMS,
                        help=f"Max new items per feed per run (default: {_DEFAULT_MAX_ITEMS})")
    parser.add_argument("--status", action="store_true",
                        help="Show item counts per collection")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.ingest:
        print(f"\n🌐 Ingesting intel feeds" + (f" (tier: {args.tier})" if args.tier else "") + "...\n")
        results = ingest_feeds(tier_filter=args.tier, max_items=args.max_items)
        total_new = sum(v["ingested"] for tier in results.values() for v in tier.values())
        print(f"\n✅ Done — {total_new} new items ingested across {len(results)} tier(s)")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
