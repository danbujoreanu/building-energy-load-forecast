"""
monitor_drift.py
================
MLOps drift monitoring for the Sparc Energy load forecasting system.

Loads the production LightGBM model, computes rolling weekly MAE/RMSE/R²
against recent actuals, and compares against the baseline metrics from
the held-out test set (Drammen R²=0.975, Oslo R²=0.963).

Outputs a structured JSON drift report to outputs/monitoring/.
Run weekly — schedulable via CCR once live prediction logging is active.

Usage
-----
    python scripts/monitor_drift.py                    # default: last 4 weeks
    python scripts/monitor_drift.py --weeks 8          # last 8 weeks
    python scripts/monitor_drift.py --city oslo        # oslo model only
    python scripts/monitor_drift.py --dry-run          # report without alerts

Prerequisites
-------------
    live_inference.py must log predictions to:
    outputs/monitoring/predictions_log.jsonl

    Format (one JSON object per line):
    {"timestamp": "2026-04-13T09:00:00", "building_id": 1,
     "y_pred": 42.1, "y_true": null}   ← y_true backfilled next day
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# ── Project root on sys.path ──────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from energy_forecast.evaluation.metrics import evaluate  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Baseline metrics from held-out test set (update after retraining) ─────────
BASELINE_METRICS: dict[str, dict[str, float]] = {
    "drammen": {"MAE": 2.14, "RMSE": 3.21, "R2": 0.975},
    "oslo": {"MAE": 2.89, "RMSE": 4.12, "R2": 0.963},
}

# ── Drift thresholds (see ADR-008) ────────────────────────────────────────────
WARN_THRESHOLD = 0.20  # +20% MAE / -0.05 R² → WARNING
CRIT_THRESHOLD = 0.40  # +40% MAE / -0.10 R² → CRITICAL

PREDICTIONS_LOG = REPO_ROOT / "outputs" / "monitoring" / "predictions_log.jsonl"
REPORTS_DIR = REPO_ROOT / "outputs" / "monitoring"


def load_predictions(city: str, weeks: int = 4) -> pd.DataFrame:
    """Load recent predictions from the JSONL log, filtered to city and time window."""
    if not PREDICTIONS_LOG.exists():
        logger.warning(
            "Predictions log not found: %s\n"
            "  → Ensure live_inference.py is logging predictions before running drift monitoring.\n"
            "  → See ADR-008 for the prerequisite.",
            PREDICTIONS_LOG,
        )
        return pd.DataFrame()

    cutoff = datetime.utcnow() - timedelta(weeks=weeks)
    rows = []
    with PREDICTIONS_LOG.open() as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                ts = datetime.fromisoformat(record["timestamp"])
                if ts >= cutoff and record.get("city", city) == city:
                    rows.append(record)
            except (json.JSONDecodeError, KeyError):
                continue

    if not rows:
        logger.warning("No predictions found for city=%s in the last %d weeks.", city, weeks)
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.dropna(subset=["y_pred", "y_true"])  # only rows with actuals
    logger.info("[load_predictions] city=%s | rows with actuals: %d", city, len(df))
    return df


def compute_weekly_metrics(df: pd.DataFrame) -> list[dict]:
    """Compute MAE/RMSE/R² for each calendar week in the DataFrame."""
    if df.empty:
        return []

    df = df.copy()
    df["week"] = df["timestamp"].dt.to_period("W")
    weekly = []

    for week, group in df.groupby("week"):
        if len(group) < 24:  # need at least 24 hourly observations
            continue
        result = evaluate(
            y_true=group["y_true"].values,
            y_pred=group["y_pred"].values,
            model_name=str(week),
        )
        weekly.append(
            {
                "week": str(week),
                "n_samples": result["n_samples"],
                "MAE": round(result["MAE"], 4),
                "RMSE": round(result["RMSE"], 4),
                "R2": round(result["R2"], 4),
            }
        )

    return weekly


def assess_drift(
    weekly_metrics: list[dict],
    baseline: dict[str, float],
) -> dict:
    """
    Compare recent weekly metrics against baseline.
    Returns drift status: OK / WARNING / CRITICAL and per-metric deltas.
    """
    if not weekly_metrics:
        return {"status": "NO_DATA", "detail": "No weekly metrics available."}

    # Use the most recent week with sufficient data
    latest = weekly_metrics[-1]
    mae_delta = (latest["MAE"] - baseline["MAE"]) / baseline["MAE"]
    rmse_delta = (latest["RMSE"] - baseline["RMSE"]) / baseline["RMSE"]
    r2_delta = latest["R2"] - baseline["R2"]  # absolute (not relative)

    status = "OK"
    flags = []

    if mae_delta > CRIT_THRESHOLD or r2_delta < -0.10:
        status = "CRITICAL"
    elif mae_delta > WARN_THRESHOLD or r2_delta < -0.05:
        status = "WARNING"

    if mae_delta > WARN_THRESHOLD:
        flags.append(
            f"MAE +{mae_delta:.1%} vs baseline ({latest['MAE']:.3f} vs {baseline['MAE']:.3f})"
        )
    if r2_delta < -0.05:
        flags.append(f"R² {r2_delta:+.4f} vs baseline ({latest['R2']:.4f} vs {baseline['R2']:.4f})")

    return {
        "status": status,
        "latest_week": latest["week"],
        "flags": flags,
        "deltas": {
            "MAE_relative": round(mae_delta, 4),
            "RMSE_relative": round(rmse_delta, 4),
            "R2_absolute": round(r2_delta, 4),
        },
        "latest_metrics": latest,
        "baseline_metrics": baseline,
    }


def write_report(report: dict, city: str) -> Path:
    """Write drift report to outputs/monitoring/ as JSON."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    path = REPORTS_DIR / f"drift_report_{city}_{date_str}.json"
    with path.open("w") as f:
        json.dump(report, f, indent=2)
    logger.info("Drift report written → %s", path)
    return path


def run(city: str, weeks: int, dry_run: bool = False) -> dict:
    """Full drift monitoring run for a given city."""
    print(f"\n[monitor_drift] city={city} | window={weeks} weeks | dry_run={dry_run}")
    print(
        f"[monitor_drift] Baseline: MAE={BASELINE_METRICS[city]['MAE']:.3f} | "
        f"R²={BASELINE_METRICS[city]['R2']:.4f}"
    )

    df = load_predictions(city, weeks)
    weekly = compute_weekly_metrics(df)

    print(f"[monitor_drift] Weekly snapshots computed: {len(weekly)}")
    for w in weekly:
        print(
            f"  {w['week']}: MAE={w['MAE']:.3f} RMSE={w['RMSE']:.3f} R²={w['R2']:.4f} "
            f"(n={w['n_samples']})"
        )

    drift = assess_drift(weekly, BASELINE_METRICS[city])

    status_symbol = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "🚨", "NO_DATA": "📭"}.get(
        drift["status"], "?"
    )
    print(f"\n[monitor_drift] Status: {status_symbol} {drift['status']}")
    for flag in drift.get("flags", []):
        print(f"  ⚠️  {flag}")

    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "city": city,
        "window_weeks": weeks,
        "drift": drift,
        "weekly_metrics": weekly,
    }

    if not dry_run:
        write_report(report, city)
    else:
        print("[monitor_drift] dry_run=True — report not written.")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Sparc Energy — MLOps drift monitor")
    parser.add_argument("--city", choices=["drammen", "oslo", "all"], default="all")
    parser.add_argument("--weeks", type=int, default=4, help="Rolling window in weeks")
    parser.add_argument("--dry-run", action="store_true", help="Compute but don't write report")
    args = parser.parse_args()

    cities = ["drammen", "oslo"] if args.city == "all" else [args.city]
    reports = {}

    for city in cities:
        report = run(city=city, weeks=args.weeks, dry_run=args.dry_run)
        reports[city] = report

    # Summary
    print("\n── Drift Monitor Summary ─────────────────────────────────────────")
    any_alert = False
    for city, report in reports.items():
        status = report["drift"]["status"]
        symbol = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "🚨", "NO_DATA": "📭"}.get(status, "?")
        print(f"  {city:10s}: {symbol} {status}")
        if status in ("WARNING", "CRITICAL"):
            any_alert = True

    if any_alert:
        print("\n  Action required: review drift report in outputs/monitoring/")
        sys.exit(1)  # non-zero exit for CCR scheduled task alerting
    else:
        print("\n  All models within drift thresholds.")


if __name__ == "__main__":
    main()
