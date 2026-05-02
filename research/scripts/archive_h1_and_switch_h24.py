#!/usr/bin/env python
"""
archive_h1_and_switch_h24.py
=============================
Run this script AFTER run_tft_only.py finishes and TFT has appended its
results to outputs/results/final_metrics.csv.

What it does
------------
1. Archives H+1 results:
     outputs/results/final_metrics.csv        → outputs/results/h1_metrics.csv
     outputs/results/per_building_metrics.csv → outputs/results/h1_per_building_metrics.csv
     outputs/figures/                          → outputs/figures/h1/ (copies all PNGs + NPZs)
     outputs/models/  (TFT .ckpt)             → outputs/models/h1/ (copies checkpoint)

2. Flips config/config.yaml to H+24 mode:
     features.forecast_horizon: 1  →  features.forecast_horizon: 24
     sequence.horizon:           1  →  sequence.horizon:           24

3. Prints the command to run the full H+24 pipeline.

Usage
-----
    python scripts/archive_h1_and_switch_h24.py [--dry-run] [--no-config-flip]

Flags
-----
    --dry-run        Print what would happen without making any changes.
    --no-config-flip Archive results but do NOT flip config.yaml.  Use this
                     if you want to review the H+1 results before committing
                     to the H+24 run.
"""

import argparse
import logging
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Archive H+1 results and switch to H+24 mode")
    p.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    p.add_argument("--no-config-flip", action="store_true", help="Skip config.yaml H+24 flip")
    return p.parse_args()


def _copy(src: Path, dst: Path, dry_run: bool) -> bool:
    """Copy src → dst, creating parent dir if needed.  Returns True on success."""
    if not src.exists():
        logger.warning("SKIP (not found): %s", src)
        return False
    if dry_run:
        logger.info("DRY-RUN  copy  %s  →  %s", src, dst)
        return True
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    logger.info("Copied  %s  →  %s", src.name, dst)
    return True


def _move(src: Path, dst: Path, dry_run: bool) -> bool:
    """Move (rename) src → dst, creating parent dir if needed.  Returns True on success."""
    if not src.exists():
        logger.warning("SKIP (not found): %s", src)
        return False
    if dry_run:
        logger.info("DRY-RUN  move  %s  →  %s", src, dst)
        return True
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    logger.info("Moved   %s  →  %s", src.name, dst)
    return True


def archive_results(dry_run: bool) -> None:
    """Step 1: archive H+1 results CSVs."""
    res_dir = ROOT / "outputs" / "results"
    logger.info("── Archiving results CSVs ──────────────────────────────────────")

    _move(res_dir / "final_metrics.csv", res_dir / "h1_metrics.csv", dry_run)
    _move(res_dir / "per_building_metrics.csv", res_dir / "h1_per_building_metrics.csv", dry_run)


def archive_figures(dry_run: bool) -> None:
    """Step 2: copy all plots from outputs/figures/ to outputs/figures/h1/."""
    fig_dir = ROOT / "outputs" / "figures"
    h1_dir = fig_dir / "h1"
    logger.info("── Archiving figures → %s ─────────────────────────────────────", h1_dir)

    # Top-level PNGs (building_profiles, model_comparison_*, etc.)
    for png in fig_dir.glob("*.png"):
        _copy(png, h1_dir / png.name, dry_run)

    # Sub-directories: results/, shap/, eda/
    for sub in ["results", "shap", "eda"]:
        subdir = fig_dir / sub
        if subdir.exists():
            h1_sub = h1_dir / sub
            for f in subdir.iterdir():
                if f.suffix in {".png", ".npz", ".svg", ".pdf"}:
                    _copy(f, h1_sub / f.name, dry_run)


def archive_model_checkpoints(dry_run: bool) -> None:
    """Step 3: copy TFT checkpoint(s) to outputs/models/h1/."""
    model_dir = ROOT / "outputs" / "models"
    h1_dir = model_dir / "h1"
    logger.info("── Archiving model checkpoints → %s ───────────────────────────", h1_dir)

    found = list(model_dir.glob("*.ckpt"))
    if not found:
        logger.warning("No TFT .ckpt found in %s — TFT may still be running.", model_dir)
        return
    for ckpt in sorted(found):
        _copy(ckpt, h1_dir / ckpt.name, dry_run)

    # Also copy any sklearn / DL artefacts from today's run
    for f in model_dir.glob("*.joblib"):
        _copy(f, h1_dir / f.name, dry_run)
    for f in model_dir.glob("*.keras"):
        _copy(f, h1_dir / f.name, dry_run)


def flip_config_to_h24(dry_run: bool) -> None:
    """Step 4: change forecast_horizon and sequence.horizon to 24 in config.yaml."""
    cfg_path = ROOT / "config" / "config.yaml"
    logger.info("── Flipping config.yaml to H+24 mode ─────────────────────────")

    if not cfg_path.exists():
        logger.error("config.yaml not found at %s", cfg_path)
        return

    original = cfg_path.read_text(encoding="utf-8")

    # Replace `forecast_horizon: 1` → `forecast_horizon: 24`
    # The trailing group (\s*(?:#.*)?) captures optional inline comment so it
    # is preserved intact after the substitution.
    updated, n1 = re.subn(
        r"(^\s*forecast_horizon:\s*)1(\s*(?:#.*)?)$",
        r"\g<1>24\2",
        original,
        flags=re.MULTILINE,
    )
    # Replace `horizon:   1` (sequence section) → `horizon:   24`
    # config.yaml has trailing comment on this line:
    #   "horizon:   1     # Must match forecast_horizon. ..."
    # The regex preserves everything after the integer (spaces + comment).
    updated, n2 = re.subn(
        r"(^\s*horizon:\s*)1(\s*(?:#.*)?)$",
        r"\g<1>24\2",
        updated,
        flags=re.MULTILINE,
    )

    if n1 == 0:
        logger.warning("forecast_horizon: 1 not found — already flipped or pattern mismatch.")
    if n2 == 0:
        logger.warning("sequence.horizon: 1 not found — already flipped or pattern mismatch.")

    if dry_run:
        logger.info(
            "DRY-RUN  would write updated config.yaml (%d forecast_horizon + %d horizon replacements)",
            n1,
            n2,
        )
        # Show the changed lines
        for i, (orig_line, new_line) in enumerate(
            zip(original.splitlines(), updated.splitlines()), start=1
        ):
            if orig_line != new_line:
                logger.info("  Line %d:  %r  →  %r", i, orig_line.strip(), new_line.strip())
        return

    cfg_path.write_text(updated, encoding="utf-8")
    logger.info(
        "config.yaml updated: forecast_horizon → 24 (%d), sequence.horizon → 24 (%d)",
        n1,
        n2,
    )


def print_next_steps() -> None:
    logger.info("")
    logger.info("=" * 65)
    logger.info("H+1 archival complete.  Next steps:")
    logger.info("")
    logger.info("  1. Verify archived files:")
    logger.info("       outputs/results/h1_metrics.csv")
    logger.info("       outputs/results/h1_per_building_metrics.csv")
    logger.info("       outputs/figures/h1/")
    logger.info("       outputs/models/h1/")
    logger.info("")
    logger.info("  2. Run the full H+24 pipeline:")
    logger.info("       python scripts/run_pipeline.py --city drammen")
    logger.info("")
    logger.info("  3. Results will appear in:")
    logger.info("       outputs/results/final_metrics.csv        (H+24)")
    logger.info("       outputs/results/per_building_metrics.csv (H+24)")
    logger.info("=" * 65)


def main() -> None:
    args = parse_args()

    if args.dry_run:
        logger.info("DRY-RUN mode — no files will be modified.")

    # Step 1: check TFT is done by looking for final_metrics.csv with TFT row
    res_dir = ROOT / "outputs" / "results"
    csv_path = res_dir / "final_metrics.csv"
    if csv_path.exists():
        import pandas as pd

        df = pd.read_csv(csv_path)
        if "TFT" not in df.get("Model", pd.Series([])).values:
            logger.warning(
                "TFT row NOT found in final_metrics.csv — run_tft_only.py may still be running."
            )
            logger.warning("Continuing anyway (use --dry-run to preview without changes).")
    else:
        logger.warning("final_metrics.csv not found — pipeline has not produced results yet.")

    archive_results(args.dry_run)
    archive_figures(args.dry_run)
    archive_model_checkpoints(args.dry_run)

    if not args.no_config_flip:
        flip_config_to_h24(args.dry_run)
    else:
        logger.info("Config flip skipped (--no-config-flip).")

    print_next_steps()


if __name__ == "__main__":
    main()
