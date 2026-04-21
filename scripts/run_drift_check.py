"""
run_drift_check.py
==================
Standalone CLI for statistical drift detection on the load-forecast pipeline.

Loads processed splits from data/processed/{city}/splits/, runs KS + PSI
feature drift, target drift, and rolling MAE checks, then prints a Markdown
report and optionally saves JSON/Markdown artefacts.

Exit codes
----------
    0 — status is OK or WARNING (no immediate action required)
    1 — status is CRITICAL (retrain recommended; enables CI/CD gating)

Usage
-----
    python scripts/run_drift_check.py --city drammen
    python scripts/run_drift_check.py --city oslo --output-json outputs/results/drift_report.json
    python scripts/run_drift_check.py --city drammen --training-mae 4.029 --check-days 30
    python scripts/run_drift_check.py --city drammen --log-level DEBUG

Arguments
---------
    --city                  Required. "drammen" | "oslo"
    --training-mae          MAE of the reference model in kWh.  If omitted,
                            reads from outputs/results/final_metrics.csv
                            (or drammen_final_metrics.csv / oslo_final_metrics.csv)
                            looking for the LightGBM row.
    --check-days            How many recent days of the test split to treat as
                            the "check" set (default: 30).
    --output-json           If provided, save DriftReport JSON to this path.
    --output-md             If provided, save DriftReport Markdown to this path.
    --threshold-multiplier  MAE threshold multiplier (default: 1.5).
    --log-level             Python logging level: INFO | DEBUG | WARNING (default INFO).
"""

from __future__ import annotations

import argparse
import logging
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

# ── Project root on sys.path ─────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from energy_forecast.monitoring import DriftDetector, DriftSeverity  # noqa: E402

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
_DEFAULT_CHECK_DAYS = 30
_DEFAULT_MAE_MULTIPLIER = 1.5
_METRICS_CANDIDATES = [
    "drammen_final_metrics.csv",
    "oslo_final_metrics.csv",
    "final_metrics.csv",
]


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    """Load config/config.yaml from the repo root.

    Returns:
        Parsed YAML config dict.

    Raises:
        FileNotFoundError: If config/config.yaml does not exist.
    """
    cfg_path = REPO_ROOT / "config" / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config not found: {cfg_path}")
    with cfg_path.open() as f:
        return yaml.safe_load(f)


def _load_parquet(city: str) -> pd.DataFrame:
    """Load the model-ready parquet for ``city``.

    Args:
        city: City identifier ("drammen" | "oslo").

    Returns:
        DataFrame loaded from data/processed/{city}/model_ready.parquet.

    Raises:
        FileNotFoundError: If the parquet does not exist.
    """
    parquet_path = REPO_ROOT / "data" / "processed" / city / "model_ready.parquet"
    if not parquet_path.exists():
        raise FileNotFoundError(
            f"Model-ready parquet not found: {parquet_path}\n"
            f"  Run: python scripts/run_pipeline.py --city {city}"
        )
    df = pd.read_parquet(parquet_path)
    logger.info("Loaded parquet: %s  (%s rows)", parquet_path, f"{len(df):,}")
    return df


def _load_splits(city: str) -> dict[str, pd.DataFrame | np.ndarray]:
    """Load pre-computed splits from data/processed/{city}/splits/.

    Tries to load X_train/y_train/X_test/y_test from CSV files.  Falls back
    to the scaler.pkl if present.  Returns only the keys needed for drift
    detection (X_train, y_train, X_test, y_test).

    Args:
        city: City identifier.

    Returns:
        Dict with keys X_train, y_train, X_test, y_test (DataFrames/Series).

    Raises:
        FileNotFoundError: If split files are not found.
    """
    splits_dir = REPO_ROOT / "data" / "processed" / city / "splits"
    if not splits_dir.exists():
        raise FileNotFoundError(
            f"Splits directory not found: {splits_dir}\n"
            f"  Run: python scripts/run_pipeline.py --city {city}"
        )

    result: dict = {}
    for key in ("X_train", "y_train", "X_test", "y_test"):
        csv_path = splits_dir / f"{key}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(
                f"Split file not found: {csv_path}\n"
                f"  Run: python scripts/run_pipeline.py --city {city}"
            )
        df = pd.read_csv(csv_path, index_col=0)
        if key.startswith("y"):
            result[key] = df.iloc[:, 0]
        else:
            result[key] = df
        logger.info("Loaded %s: %s", key, df.shape)

    return result


def _read_training_mae(city: str) -> float | None:
    """Attempt to read the LightGBM MAE from stored metrics CSVs.

    Searches outputs/results/ for a CSV containing a LightGBM row and
    returns the MAE value.

    Args:
        city: City identifier (used to prefer city-specific metrics file).

    Returns:
        Training MAE as float, or None if not found.
    """
    results_dir = REPO_ROOT / "outputs" / "results"

    # Prefer city-specific file; fall back to generic
    candidates = [
        results_dir / f"{city}_final_metrics.csv",
        results_dir / "drammen_final_metrics.csv",
        results_dir / "final_metrics.csv",
    ]

    for csv_path in candidates:
        if not csv_path.exists():
            continue
        try:
            df = pd.read_csv(csv_path)
            # Normalise column names to lowercase
            df.columns = [c.lower().strip() for c in df.columns]
            if "model" not in df.columns or "mae" not in df.columns:
                continue

            # Filter to the target city if a city column exists
            if "city" in df.columns:
                df = df[df["city"].str.lower() == city.lower()]

            # Find LightGBM row (case-insensitive)
            lgbm_mask = df["model"].str.lower().str.contains("lightgbm")
            if lgbm_mask.any():
                mae = float(df.loc[lgbm_mask, "mae"].iloc[0])
                logger.info("Training MAE read from %s: %.4f kWh", csv_path.name, mae)
                return mae
        except (pd.errors.ParserError, KeyError, ValueError) as exc:
            logger.debug("Could not parse %s: %s", csv_path, exc)
            continue

    return None


def _slice_check_window(
    X: pd.DataFrame,
    y: pd.Series,
    check_days: int,
) -> tuple[pd.DataFrame, pd.Series]:
    """Return the last ``check_days`` calendar days from X and y.

    If the index is a DatetimeIndex or MultiIndex with a timestamp level,
    uses calendar-day slicing.  Otherwise uses the last N samples.

    Args:
        X: Feature DataFrame.
        y: Target Series.
        check_days: Number of days to include in the check window.

    Returns:
        Sliced (X_check, y_check) tuple.
    """
    idx = X.index

    # Extract timestamp level from MultiIndex if present
    if isinstance(idx, pd.MultiIndex):
        for level_idx in range(idx.nlevels):
            level = idx.get_level_values(level_idx)
            if isinstance(level, pd.DatetimeIndex):
                cutoff = level.max() - pd.Timedelta(days=check_days)
                mask = level >= cutoff
                return X.loc[mask], y.loc[mask]

    if isinstance(idx, pd.DatetimeIndex):
        cutoff = idx.max() - pd.Timedelta(days=check_days)
        mask = idx >= cutoff
        return X.loc[mask], y.loc[mask]

    # Fallback: use last check_days * 24 samples (assumes hourly)
    n = min(check_days * 24, len(X))
    return X.iloc[-n:], y.iloc[-n:]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse CLI arguments and run the drift check."""
    parser = argparse.ArgumentParser(
        description="Sparc Energy — Statistical drift detection for LightGBM pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--city",
        required=True,
        choices=["drammen", "oslo"],
        help='Dataset city: "drammen" or "oslo".',
    )
    parser.add_argument(
        "--training-mae",
        type=float,
        default=None,
        help=(
            "MAE of the reference model in kWh.  If omitted, reads from "
            "outputs/results/final_metrics.csv (LightGBM row)."
        ),
    )
    parser.add_argument(
        "--check-days",
        type=int,
        default=_DEFAULT_CHECK_DAYS,
        help=f"Days of recent test data to treat as check set (default: {_DEFAULT_CHECK_DAYS}).",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Path to save DriftReport JSON output (optional).",
    )
    parser.add_argument(
        "--output-md",
        type=str,
        default=None,
        help="Path to save DriftReport Markdown output (optional).",
    )
    parser.add_argument(
        "--threshold-multiplier",
        type=float,
        default=_DEFAULT_MAE_MULTIPLIER,
        help=f"MAE ratio threshold for retrain trigger (default: {_DEFAULT_MAE_MULTIPLIER}).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)-8s %(name)s | %(message)s",
    )

    # ------------------------------------------------------------------
    # 1. Config
    # ------------------------------------------------------------------
    try:
        cfg = _load_config()
    except FileNotFoundError as exc:
        logger.error("Config load failed: %s", exc)
        sys.exit(2)

    # Inject CLI override for threshold multiplier
    if "monitoring" not in cfg:
        cfg["monitoring"] = {}
    cfg["monitoring"]["mae_threshold_multiplier"] = args.threshold_multiplier

    # ------------------------------------------------------------------
    # 2. Training MAE
    # ------------------------------------------------------------------
    training_mae = args.training_mae
    if training_mae is None:
        training_mae = _read_training_mae(args.city)
    if training_mae is None:
        logger.error(
            "Could not determine training MAE.  "
            "Pass --training-mae <value> explicitly, or ensure "
            "outputs/results/{city}_final_metrics.csv exists."
        )
        sys.exit(2)
    logger.info("Training MAE: %.4f kWh", training_mae)

    # ------------------------------------------------------------------
    # 3. Load splits
    # ------------------------------------------------------------------
    try:
        splits = _load_splits(args.city)
    except FileNotFoundError as exc:
        logger.error("Splits not found: %s", exc)
        sys.exit(2)

    X_train: pd.DataFrame = splits["X_train"]
    y_train: pd.Series = splits["y_train"]
    X_test: pd.DataFrame = splits["X_test"]
    y_test: pd.Series = splits["y_test"]

    # ------------------------------------------------------------------
    # 4. Slice check window from test split
    # ------------------------------------------------------------------
    X_check, y_check = _slice_check_window(X_test, y_test, args.check_days)
    logger.info(
        "Reference: %s samples | Check window (%dd): %s samples",
        f"{len(X_train):,}",
        args.check_days,
        f"{len(X_check):,}",
    )

    if len(X_check) == 0:
        logger.error(
            "Check window is empty.  "
            "Try increasing --check-days or verify the test split covers recent data."
        )
        sys.exit(2)

    # ------------------------------------------------------------------
    # 5. Derive reference/check period strings
    # ------------------------------------------------------------------
    def _period_str(idx: pd.Index) -> tuple[str, str]:
        """Extract (start_str, end_str) from a DataFrame/Series index."""
        if isinstance(idx, pd.MultiIndex):
            for lv in range(idx.nlevels):
                level = idx.get_level_values(lv)
                if isinstance(level, pd.DatetimeIndex):
                    return (
                        str(level.min().date()),
                        str(level.max().date()),
                    )
        if isinstance(idx, pd.DatetimeIndex):
            return str(idx.min().date()), str(idx.max().date())
        return ("unknown", "unknown")

    reference_period = _period_str(X_train.index)
    check_period = _period_str(X_check.index)

    # ------------------------------------------------------------------
    # 6. Run drift detection
    # ------------------------------------------------------------------
    detector = DriftDetector(
        cfg,
        rolling_window_days=cfg["monitoring"].get("rolling_window_days", 7),
        mae_threshold_multiplier=args.threshold_multiplier,
    )

    report = detector.full_report(
        city=args.city,
        model_name="LightGBM",
        X_reference=X_train,
        X_check=X_check,
        y_reference=y_train,
        y_check=y_check,
        training_mae=training_mae,
        y_pred=None,  # No live predictions available at check time
        reference_period=reference_period,
        check_period=check_period,
    )

    # ------------------------------------------------------------------
    # 7. Output
    # ------------------------------------------------------------------
    md_output = report.to_markdown()
    print(md_output)

    if args.output_json:
        json_path = Path(args.output_json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(report.to_json())
        logger.info("JSON report saved: %s", json_path)

    if args.output_md:
        md_path = Path(args.output_md)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(md_output)
        logger.info("Markdown report saved: %s", md_path)

    # Default JSON output to the monitoring directory
    default_dir = REPO_ROOT / "outputs" / "results" / "drift_reports"
    default_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone as _tz

    ts = datetime.now(tz=_tz.utc).strftime("%Y-%m-%d")
    default_json = default_dir / f"drift_{args.city}_{ts}.json"
    default_json.write_text(report.to_json())
    logger.info("Default JSON report saved: %s", default_json)

    # ------------------------------------------------------------------
    # 8. Exit code
    # ------------------------------------------------------------------
    if report.overall_severity == DriftSeverity.CRITICAL:
        logger.warning("CRITICAL drift detected — exit code 1 (CI retrain trigger).")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
