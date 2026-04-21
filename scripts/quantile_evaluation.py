"""
quantile_evaluation.py
======================
Evaluates the probabilistic forecasting quality of LightGBM_Quantile (P10/P50/P90).

Metrics
-------
  Winkler Score     Measures combined sharpness and coverage of the P10-P90 interval.
                    Lower is better. For a 80% PI: score = width when y ∈ [P10,P90],
                    score = width + 2(violation)/0.8 when y is outside.
                    (Winkler 1972; standard in probabilistic forecast evaluation)

  Coverage Rate     Fraction of test observations inside [P10, P90].
                    A well-calibrated 80% PI should achieve 0.80.

  Mean PI Width     Mean(P90 - P10). Sharpness: tighter intervals are more useful.

  P50 MAE           Median forecast MAE, for comparison with the point forecasts.

  CRPS              (continuous ranked probability score, optional — not implemented
                    here as it requires the full distribution, not just P10/P50/P90)

Works for any city with pre-computed splits in data/processed/splits/.
No pipeline re-run required — retrains LightGBM_Quantile (~15s) from saved parquets.

Usage
-----
    python scripts/quantile_evaluation.py                  # Drammen (default)
    python scripts/quantile_evaluation.py --city oslo      # Oslo
    python scripts/quantile_evaluation.py --city drammen oslo  # Both cities

Output
------
    outputs/results/quantile_results.csv
    Printed table suitable for copy-paste into LaTeX.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "outputs" / "results"
SPLITS_DIR = PROJECT_ROOT / "data" / "processed" / "splits"
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def winkler_score(
    y_true: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    alpha: float = 0.80,
) -> float:
    """Winkler score for a (1-alpha) × 100% prediction interval.

    Parameters
    ----------
    y_true : shape (n,) — observed values
    lower  : shape (n,) — P10 predictions (lower bound of 80% PI)
    upper  : shape (n,) — P90 predictions (upper bound of 80% PI)
    alpha  : significance level (0.20 for a 80% interval = P10-P90)

    Returns
    -------
    float — mean Winkler score over all test points (lower is better)

    Reference
    ---------
    Winkler, R.L. (1972). A Decision-Theoretic Approach to Interval Estimation.
    JASA. doi:10.1080/01621459.1972.10481224
    """
    width = upper - lower  # interval width at each point

    # Penalty for observations outside the interval
    below_penalty = np.where(y_true < lower, 2.0 * (lower - y_true) / alpha, 0.0)
    above_penalty = np.where(y_true > upper, 2.0 * (y_true - upper) / alpha, 0.0)

    scores = width + below_penalty + above_penalty
    return float(np.mean(scores))


def coverage_rate(
    y_true: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> float:
    """Fraction of observations inside [lower, upper]."""
    return float(np.mean((y_true >= lower) & (y_true <= upper)))


def mean_interval_width(lower: np.ndarray, upper: np.ndarray) -> float:
    """Mean (P90 - P10) across all test points."""
    return float(np.mean(upper - lower))


# ---------------------------------------------------------------------------
# Per-building breakdown
# ---------------------------------------------------------------------------


def per_building_quantile_metrics(
    y_true: pd.Series,
    q_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute Winkler score and coverage rate per building.

    Parameters
    ----------
    y_true : MultiIndex Series (building_id, timestamp)
    q_df   : DataFrame with columns P10, P50, P90 and same index as y_true
    """
    rows = []
    for bid in y_true.index.get_level_values("building_id").unique():
        y_b = y_true.xs(bid, level="building_id").values
        lo = q_df.xs(bid, level="building_id")["P10"].values
        hi = q_df.xs(bid, level="building_id")["P90"].values

        rows.append(
            {
                "building_id": bid,
                "n": len(y_b),
                "winkler_score": round(winkler_score(y_b, lo, hi), 4),
                "coverage_rate": round(coverage_rate(y_b, lo, hi), 4),
                "mean_pi_width": round(mean_interval_width(lo, hi), 4),
                "p50_mae": round(
                    float(np.mean(np.abs(y_b - q_df.xs(bid, level="building_id")["P50"].values))), 4
                ),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------


def evaluate_city(city: str) -> dict:
    """Retrain LightGBM_Quantile on saved splits and compute interval metrics.

    Returns a dict with all aggregate results for this city.
    """
    from energy_forecast.models.sklearn_models import LightGBMQuantileForecaster
    from energy_forecast.utils import load_config, set_global_seed

    logger.info("=" * 60)
    logger.info("Quantile evaluation — %s", city.upper())
    logger.info("=" * 60)

    # ── Load config ──────────────────────────────────────────────────────────
    cfg = load_config(str(CONFIG_PATH))
    cfg["city"] = city
    set_global_seed(cfg.get("seed", 42))

    # ── Load splits ──────────────────────────────────────────────────────────
    prefix = city  # file naming: {city}_X_train_fs.parquet

    def _load(name: str, as_series: bool = False) -> pd.DataFrame | pd.Series:
        path = SPLITS_DIR / f"{prefix}_{name}.parquet"
        if not path.exists():
            raise FileNotFoundError(
                f"Split file not found: {path}\n"
                f"Run: python scripts/run_pipeline.py --city {city}"
            )
        df = pd.read_parquet(path)
        return df.squeeze() if as_series else df

    X_train = _load("X_train_fs")  # noqa: N806
    y_train = _load("y_train", as_series=True)
    X_val = _load("X_val_fs")  # noqa: N806
    y_val = _load("y_val", as_series=True)
    X_test = _load("X_test_fs")  # noqa: N806
    y_test = _load("y_test", as_series=True)

    logger.info(
        "Splits loaded — train: %d, val: %d, test: %d, features: %d",
        len(X_train),
        len(X_val),
        len(X_test),
        X_train.shape[1],
    )

    # ── Retrain LightGBM_Quantile ────────────────────────────────────────────
    lgbm_cfg = cfg["training"]["lightgbm"]
    seed = cfg.get("seed", 42)
    model = LightGBMQuantileForecaster(lgbm_cfg, seed, quantiles=[0.1, 0.5, 0.9])

    logger.info("Training LightGBM_Quantile (P10 / P50 / P90) ...")
    model.fit(X_train, y_train, X_val, y_val)

    # ── Predict quantiles ────────────────────────────────────────────────────
    q_df = model.predict_quantiles(X_test)  # columns: P10, P50, P90
    # q_df has the same index as X_test (same as y_test)

    y_true = y_test.values
    lower = q_df["P10"].values
    median = q_df["P50"].values
    upper = q_df["P90"].values

    # ── Aggregate metrics ────────────────────────────────────────────────────
    ws = winkler_score(y_true, lower, upper, alpha=0.20)  # 80% PI → alpha=0.20
    cov = coverage_rate(y_true, lower, upper)
    pi_width = mean_interval_width(lower, upper)
    p50_mae = float(np.mean(np.abs(y_true - median)))
    n = len(y_true)

    logger.info("── Results ──────────────────────────────────────────────")
    logger.info("  City             : %s", city.upper())
    logger.info("  n_test           : %d", n)
    logger.info("  P50 MAE          : %.4f kWh", p50_mae)
    logger.info("  Winkler Score    : %.4f kWh  (lower is better)", ws)
    logger.info("  Coverage Rate    : %.4f      (target: 0.80 for 80%% PI)", cov)
    logger.info("  Mean PI Width    : %.4f kWh  (P90 - P10)", pi_width)
    logger.info("")

    calibration_note = (
        "well-calibrated"
        if abs(cov - 0.80) < 0.05
        else ("over-conservative" if cov > 0.85 else "under-covering")
    )
    logger.info("  Calibration: %s (coverage %.1f%% vs target 80.0%%)", calibration_note, cov * 100)

    result = {
        "city": city,
        "n_test": n,
        "p50_mae": round(p50_mae, 4),
        "winkler_score": round(ws, 4),
        "coverage_rate": round(cov, 4),
        "mean_pi_width": round(pi_width, 4),
        "calibration": calibration_note,
    }

    # ── Per-building breakdown ────────────────────────────────────────────────
    # Only available when y_test has a MultiIndex with building_id level
    if hasattr(y_test.index, "names") and "building_id" in y_test.index.names:
        logger.info("── Per-Building Breakdown ───────────────────────────────")
        pb_df = per_building_quantile_metrics(y_test, q_df)
        pb_path = RESULTS_DIR / f"{city}_quantile_per_building.csv"
        pb_path.parent.mkdir(parents=True, exist_ok=True)
        pb_df.to_csv(pb_path, index=False)
        logger.info("  Saved → %s", pb_path)

        # Coverage range across buildings
        cov_min = pb_df["coverage_rate"].min()
        cov_max = pb_df["coverage_rate"].max()
        cov_std = pb_df["coverage_rate"].std()
        logger.info(
            "  Coverage across buildings: min=%.3f  max=%.3f  std=%.3f",
            cov_min,
            cov_max,
            cov_std,
        )
        result["cov_building_min"] = round(float(cov_min), 4)
        result["cov_building_max"] = round(float(cov_max), 4)
        result["cov_building_std"] = round(float(cov_std), 4)

    # ── LaTeX snippet ─────────────────────────────────────────────────────────
    logger.info("")
    logger.info("── LaTeX Table Row ─────────────────────────────────────────")
    logger.info(
        "%s & %.3f & %.3f & %.1f%% & %.3f \\\\",
        city.capitalize(),
        p50_mae,
        ws,
        cov * 100,
        pi_width,
    )

    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Winkler Score + Coverage Rate for LightGBM_Quantile P10-P90 intervals"
    )
    parser.add_argument(
        "--city",
        nargs="+",
        choices=["drammen", "oslo"],
        default=["drammen"],
        help="City (or cities) to evaluate (default: drammen)",
    )
    args = parser.parse_args()

    all_results: list[dict] = []
    for city in args.city:
        try:
            row = evaluate_city(city)
            all_results.append(row)
        except FileNotFoundError as e:
            logger.error("Skipping %s: %s", city, e)

    if not all_results:
        logger.error("No results produced. Run pipeline first for each city.")
        return

    out_df = pd.DataFrame(all_results)
    out_path = RESULTS_DIR / "quantile_results.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    logger.info("\nQuantile results saved → %s", out_path)

    # Summary table
    logger.info("\n=== Quantile Evaluation Summary ===\n")
    cols = ["city", "n_test", "p50_mae", "winkler_score", "coverage_rate", "mean_pi_width"]
    logger.info(out_df[[c for c in cols if c in out_df.columns]].to_string(index=False))

    # Full LaTeX table
    logger.info("\n=== LaTeX Table (interval evaluation) ===")
    logger.info("\\begin{tabular}{lrrrr}")
    logger.info("City & P50 MAE (kWh) & Winkler Score & Coverage & Mean PI Width (kWh) \\\\")
    logger.info("\\hline")
    for r in all_results:
        logger.info(
            "%s & %.3f & %.3f & %.1f\\%% & %.3f \\\\",
            r["city"].capitalize(),
            r["p50_mae"],
            r["winkler_score"],
            r["coverage_rate"] * 100,
            r["mean_pi_width"],
        )
    logger.info("\\end{tabular}")


if __name__ == "__main__":
    main()
