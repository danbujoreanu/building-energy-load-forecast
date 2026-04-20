#!/usr/bin/env python
"""
scripts/intel_ingest.py
=======================
CLI wrapper for intel/ingest.py.

Usage
-----
    # Ingest a single file
    python scripts/intel_ingest.py --file intel/docs/operational/CRU202517_APPENDIX_A_DRAFT.md

    # Ingest all files in a tier
    python scripts/intel_ingest.py --tier operational

    # Ingest all tiers
    python scripts/intel_ingest.py --all

    # Dry-run: list files that would be ingested (no write)
    python scripts/intel_ingest.py --tier operational --dry-run
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from intel.ingest import (
    VALID_TIERS,
    ingest_all,
    ingest_file,
    ingest_tier,
    get_status,
    _PROJECT_ROOT as INTEL_ROOT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sparc Energy Intelligence — document ingest CLI"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file", metavar="PATH",
        help="Ingest a single file. Tier is inferred from the directory name.",
    )
    group.add_argument(
        "--tier", choices=sorted(VALID_TIERS),
        help="Ingest all .md/.pdf files in intel/docs/{tier}/ (or --dir if provided).",
    )
    group.add_argument(
        "--all", action="store_true",
        help="Ingest all tiers.",
    )
    group.add_argument(
        "--status", action="store_true",
        help="Print document/chunk counts per tier and exit.",
    )
    parser.add_argument(
        "--dir", metavar="PATH",
        help="External directory to ingest from (use with --tier). "
             "Overrides the default intel/docs/{tier}/ path. "
             "Useful for ingesting MBA/UCD docs from ~/UCD/.",
    )
    parser.add_argument(
        "--force-tier", choices=sorted(VALID_TIERS),
        help="Override tier inference for --file (useful if file is outside intel/docs/).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be ingested without writing to ChromaDB.",
    )
    return parser.parse_args()


def _infer_tier(file_path: Path) -> str:
    """Infer tier from file path: .../intel/docs/{tier}/... → tier."""
    parts = file_path.parts
    try:
        docs_idx = next(
            i for i, p in enumerate(parts)
            if p == "docs" and i + 1 < len(parts) and parts[i + 1] in VALID_TIERS
        )
        return parts[docs_idx + 1]
    except StopIteration:
        return ""


def main() -> None:
    args = parse_args()

    # ── Status ────────────────────────────────────────────────────────────────
    if args.status:
        status = get_status()
        print("\nIntel corpus status")
        print("=" * 40)
        total_docs = total_chunks = 0
        for tier, counts in sorted(status.items()):
            d, c = counts["docs"], counts["chunks"]
            print(f"  {tier:<15} {d:>3} docs  /  {c:>5} chunks")
            total_docs += d
            total_chunks += c
        print("-" * 40)
        print(f"  {'TOTAL':<15} {total_docs:>3} docs  /  {total_chunks:>5} chunks")
        print()
        return

    # ── Single file ───────────────────────────────────────────────────────────
    if args.file:
        file_path = Path(args.file).resolve()

        # Determine tier
        tier = args.force_tier or _infer_tier(file_path)
        if not tier:
            print(
                f"ERROR: Could not infer tier from path '{file_path}'. "
                f"Use --force-tier {{{'|'.join(sorted(VALID_TIERS))}}}.",
                file=sys.stderr,
            )
            sys.exit(1)

        if args.dry_run:
            print(f"[dry-run] Would ingest: {file_path.name} → tier '{tier}'")
            return

        ingest_file(file_path, tier)
        return

    # ── Single tier ───────────────────────────────────────────────────────────
    if args.tier:
        # Use --dir if provided, otherwise fall back to intel/docs/{tier}/
        if args.dir:
            tier_dir = Path(args.dir).expanduser().resolve()
            if not tier_dir.exists():
                print(f"ERROR: --dir path does not exist: {tier_dir}", file=sys.stderr)
                sys.exit(1)
        else:
            tier_dir = INTEL_ROOT / "intel" / "docs" / args.tier

        if args.dry_run:
            files = sorted(tier_dir.glob("**/*.md")) + sorted(tier_dir.glob("**/*.pdf"))
            print(f"[dry-run] Would ingest {len(files)} file(s) from tier '{args.tier}':")
            for f in files:
                print(f"  {f.name}")
            return

        if args.dir:
            # External directory path — iterate and ingest file-by-file
            files = sorted(tier_dir.glob("**/*.md")) + sorted(tier_dir.glob("**/*.pdf"))
            if not files:
                print(f"No .md or .pdf files found in {tier_dir}")
                return
            ingested = skipped = 0
            errors: list = []
            for fp in files:
                try:
                    result = ingest_file(fp, args.tier)
                    if result:
                        ingested += 1
                    else:
                        skipped += 1
                except Exception as exc:
                    logger.error("Error ingesting %s: %s", fp.name, exc)
                    errors.append(f"{fp.name}: {exc}")
            _print_summary({args.tier: {"ingested": ingested, "skipped": skipped, "errors": errors}})
        else:
            result = ingest_tier(args.tier)
            _print_summary({args.tier: result})
        return

    # ── All tiers ─────────────────────────────────────────────────────────────
    if args.all:
        if args.dry_run:
            for tier in sorted(VALID_TIERS):
                tier_dir = INTEL_ROOT / "intel" / "docs" / tier
                if not tier_dir.exists():
                    print(f"[dry-run] Tier '{tier}': directory missing — skip")
                    continue
                files = sorted(tier_dir.glob("**/*.md")) + sorted(tier_dir.glob("**/*.pdf"))
                print(f"[dry-run] Tier '{tier}': {len(files)} file(s)")
                for f in files:
                    print(f"  {f.name}")
            return

        results = ingest_all()
        _print_summary(results)


def _print_summary(results: dict) -> None:
    print("\nIngest summary")
    print("=" * 50)
    total_i = total_s = total_e = 0
    for tier, r in sorted(results.items()):
        i, s, e = r["ingested"], r["skipped"], len(r["errors"])
        print(f"  {tier:<15}  ingested: {i}  skipped: {s}  errors: {e}")
        total_i += i
        total_s += s
        total_e += e
        for err in r["errors"]:
            print(f"    ✗ {err}")
    print("-" * 50)
    print(f"  {'TOTAL':<15}  ingested: {total_i}  skipped: {total_s}  errors: {total_e}")
    print()


if __name__ == "__main__":
    main()
