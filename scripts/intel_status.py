#!/usr/bin/env python
"""
scripts/intel_status.py
=======================
Print a quick status report of the intel corpus.

Usage
-----
    python scripts/intel_status.py
    python scripts/intel_status.py --json
"""

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from intel.ingest import get_status, VALID_TIERS, _PROJECT_ROOT as INTEL_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sparc Energy Intelligence — corpus status report")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (useful for CI / scripting).",
    )
    return parser.parse_args()


def _count_disk_files(tier: str) -> int:
    tier_dir = INTEL_ROOT / "intel" / "docs" / tier
    if not tier_dir.exists():
        return 0
    return len(list(tier_dir.glob("**/*.md"))) + len(list(tier_dir.glob("**/*.pdf")))


def main() -> None:
    args = parse_args()
    status = get_status()

    # Augment with disk file counts
    for tier in VALID_TIERS:
        status.setdefault(tier, {"docs": 0, "chunks": 0})
        status[tier]["disk_files"] = _count_disk_files(tier)

    if args.json:
        print(json.dumps(status, indent=2))
        return

    # Human-readable table
    print()
    print("Sparc Energy Intelligence — corpus status")
    print("=" * 58)
    print(f"  {'Tier':<15} {'On disk':>8} {'Ingested':>9} {'Chunks':>8}")
    print("  " + "-" * 54)
    total_disk = total_docs = total_chunks = 0
    for tier in sorted(VALID_TIERS):
        d = status[tier]["disk_files"]
        i = status[tier]["docs"]
        c = status[tier]["chunks"]
        pending = d - i
        flag = " ⚠ pending" if pending > 0 else ""
        print(f"  {tier:<15} {d:>8} {i:>9} {c:>8}{flag}")
        total_disk += d
        total_docs += i
        total_chunks += c
    print("  " + "-" * 54)
    print(f"  {'TOTAL':<15} {total_disk:>8} {total_docs:>9} {total_chunks:>8}")
    print()
    chroma_path = INTEL_ROOT / "data" / "chromadb"
    print(f"  ChromaDB path : {chroma_path}")
    print()


if __name__ == "__main__":
    main()
