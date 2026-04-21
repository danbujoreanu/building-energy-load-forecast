#!/usr/bin/env python3
"""
scripts/career_watch.py
=======================
Watches the Obsidian Applications folder for new or modified job spec .md files
and automatically ingests them into the career intel tier.

Usage
-----
    python scripts/career_watch.py
    # Leave running in the background — ingests new job specs within 2 seconds of save

    # Override the watched directory
    python scripts/career_watch.py --dir ~/Obsidian/Career/Applications

Run this on Mac Mini startup (add to Login Items or launchd).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_DIR = Path.home() / "Personal Projects" / "Career" / "Applications"
_SKIP_NAMES = {"readme", "index", "_index", "template", "00_template"}


def _ingest_file(fp: Path) -> None:
    from intel.career import _enrich_with_inferred_metadata, ingest_job_spec

    try:
        _enrich_with_inferred_metadata(fp)
        result = ingest_job_spec(fp, copy_to_intel=True)
        if result:
            print(f"  ✅ Auto-ingested: {fp.name}")
        else:
            logger.debug("Skipped (already indexed): %s", fp.name)
    except Exception as exc:
        logger.error("Failed to ingest %s: %s", fp.name, exc)


def watch(watch_dir: Path) -> None:
    """Simple polling watcher using file mtime — no additional dependencies."""
    print(f"👁  Watching for new job specs in: {watch_dir}")
    print("    (press Ctrl+C to stop)\n")

    seen_mtimes: dict[Path, float] = {}

    while True:
        for fp in watch_dir.rglob("*.md"):
            if fp.stem.lower() in _SKIP_NAMES:
                continue
            try:
                mtime = fp.stat().st_mtime
            except OSError:
                continue

            if fp not in seen_mtimes or seen_mtimes[fp] < mtime:
                seen_mtimes[fp] = mtime
                if fp in seen_mtimes:  # new modification (not first scan)
                    _ingest_file(fp)
                else:
                    seen_mtimes[fp] = mtime  # record on first scan without ingesting

        time.sleep(2)


def main():
    parser = argparse.ArgumentParser(
        description="Watch Obsidian Applications folder and auto-ingest job specs"
    )
    parser.add_argument(
        "--dir", type=str, default=None, help=f"Directory to watch (default: {_DEFAULT_DIR})"
    )
    args = parser.parse_args()

    watch_dir = Path(args.dir).expanduser().resolve() if args.dir else _DEFAULT_DIR.resolve()
    if not watch_dir.exists():
        print(f"❌ Directory not found: {watch_dir}")
        sys.exit(1)

    try:
        watch(watch_dir)
    except KeyboardInterrupt:
        print("\n\nWatcher stopped.")


if __name__ == "__main__":
    main()
