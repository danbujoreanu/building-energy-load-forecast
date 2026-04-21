#!/usr/bin/env python3
"""
scripts/career_ingest.py
========================
CLI for the career intelligence module.

Ingests job specs from Obsidian, analyses fit, and evaluates which technologies
from job specs should be implemented in Sparc Energy.

Usage
-----
    # Ingest all job specs from Obsidian Applications folder
    python scripts/career_ingest.py --all-obsidian

    # Ingest a single job spec
    python scripts/career_ingest.py --file ~/Personal\ Projects/Career/Applications/Active/PartnerRe/Senior\ AI\ Architect.md

    # Analyse fit against a job spec
    python scripts/career_ingest.py --match "PartnerRe Senior AI Architect"

    # Evaluate tech stack gaps across all job specs
    python scripts/career_ingest.py --tech-eval

    # List all ingested job specs
    python scripts/career_ingest.py --list

    # Full workflow: ingest all + tech eval
    python scripts/career_ingest.py --all-obsidian --tech-eval
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_OBSIDIAN_DIR = Path.home() / "Personal Projects" / "Career" / "Applications"


def cmd_ingest_all_obsidian(args):
    from intel.career import ingest_obsidian_jobs, ingest_career_profile

    obsidian_dir = Path(args.obsidian_dir) if args.obsidian_dir else _DEFAULT_OBSIDIAN_DIR

    print(f"\n🔍 Scanning Obsidian Applications folder: {obsidian_dir}")
    result = ingest_obsidian_jobs(obsidian_dir)
    print(f"\n✅ Done: {result['ingested']} ingested, {result['skipped']} skipped")
    if result["errors"]:
        print(f"⚠️  Errors ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"   {e}")

    # Also (re-)ingest the profile
    print("\n📋 Ingesting career profile...")
    try:
        ok = ingest_career_profile()
        print("  ✓ Profile ingested" if ok else "  ↩ Profile already up to date")
    except FileNotFoundError:
        print("  ⚠️  Profile not found — create intel/docs/career/profile/DAN_BUJOREANU_PROFILE.md")


def cmd_ingest_file(args):
    from intel.career import ingest_job_spec

    file_path = Path(args.file).expanduser().resolve()
    print(f"\n📄 Ingesting: {file_path.name}")
    ok = ingest_job_spec(file_path, copy_to_intel=True)
    if ok:
        print(f"✅ Ingested: {file_path.name}")
    else:
        print(f"↩  Already ingested (deduplicated): {file_path.name}")


def cmd_match(args):
    from intel.career import match_job_spec

    query = args.match
    print(f"\n🔎 Analysing fit for: {query}")
    print("   (loading models — first run may take 30s...)\n")

    result = match_job_spec(query)

    print("─" * 70)
    print("FIT SUMMARY")
    print("─" * 70)
    print(result["fit_summary"])

    if result["strengths"]:
        print("\n✅ STRENGTHS")
        for s in result["strengths"]:
            print(f"  • {s}")

    if result["gaps"]:
        print("\n🔴 GAPS TO ADDRESS")
        for g in result["gaps"]:
            print(f"  • {g}")

    if result["resume_notes"]:
        print("\n📝 RESUME TAILORING NOTES")
        print(result["resume_notes"])

    print(
        f"\n[Top retrieval score: {result['top_score']:.3f} | LLM: {'Gemini' if result['llm_used'] else 'retrieval-only'}]"
    )


def cmd_tech_eval(args):
    from intel.career import evaluate_tech_stack

    print("\n🔧 Tech stack evaluation across all ingested job specs...")
    report = evaluate_tech_stack(top_n=25)

    if "error" in report:
        print(f"⚠️  {report['error']}")
        return

    print("\n📊 TOP TECHNOLOGIES in job specs:")
    for tech, count in list(report["tech_counts"].items())[:15]:
        in_stack = "✅" if tech in report["in_stack"] else "🔴"
        print(f"  {in_stack} {tech:30s} ×{count}")

    print(f"\n✅ Already in Sparc stack ({len(report['in_stack'])}):")
    print("  " + ", ".join(report["in_stack"][:10]))

    print(f"\n🔴 Gaps worth considering ({len(report['gaps'])}):")
    for tech in report["gaps"][:10]:
        print(f"  • {tech}")


def cmd_list(args):
    from intel.career import list_jobs

    jobs = list_jobs()
    if not jobs:
        print("\n📋 No job specs ingested yet. Run --all-obsidian or --file first.")
        return

    print(f"\n📋 Ingested job specs ({len(jobs)}):")
    print(f"  {'Company':20s} {'Role':35s} {'Status':15s} {'Added':12s}")
    print("  " + "-" * 85)
    for j in jobs:
        print(f"  {j['company']:20s} {j['role_title']:35s} {j['status']:15s} {j['date_added']}")


def main():
    parser = argparse.ArgumentParser(
        description="Career Intelligence CLI — job spec analysis and tech evaluation"
    )
    parser.add_argument(
        "--all-obsidian",
        action="store_true",
        help="Ingest all job specs from Obsidian Applications folder",
    )
    parser.add_argument(
        "--obsidian-dir", type=str, default=None, help="Override default Obsidian Applications path"
    )
    parser.add_argument("--file", type=str, default=None, help="Ingest a single job spec file")
    parser.add_argument(
        "--match",
        type=str,
        default=None,
        help="Analyse fit for a job spec (by company/title query)",
    )
    parser.add_argument(
        "--tech-eval", action="store_true", help="Evaluate tech stack gaps across all job specs"
    )
    parser.add_argument("--list", action="store_true", help="List all ingested job specs")

    args = parser.parse_args()

    if args.all_obsidian:
        cmd_ingest_all_obsidian(args)

    if args.file:
        cmd_ingest_file(args)

    if args.match:
        cmd_match(args)

    if args.tech_eval:
        cmd_tech_eval(args)

    if args.list:
        cmd_list(args)

    if not any([args.all_obsidian, args.file, args.match, args.tech_eval, args.list]):
        parser.print_help()


if __name__ == "__main__":
    main()
