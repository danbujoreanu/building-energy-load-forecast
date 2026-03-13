"""
significance_test.py
====================
Statistical significance tests for the journal paper.

Two modes:

1. PER-BUILDING PAIRED TESTS (runs now, no re-run needed)
   -------------------------------------------------------
   Uses outputs/results/per_building_metrics.csv (44 Drammen buildings).
   Applies:
     - Wilcoxon signed-rank test (non-parametric, n=44 pairs)
     - Paired t-test (parametric, for reference)
     - Cohen's d effect size
   Compares: LightGBM vs XGBoost, RandomForest, Ridge, Lasso, MeanBaseline

2. DIEBOLD-MARIANO TEST (requires prediction saving — see NOTE below)
   ------------------------------------------------------------------
   Tests whether two forecast error series differ significantly.
   Requires: outputs/predictions/{model}_h24_test_errors.npy
             (error series e_t = y_true_t - y_pred_t, shape (n_test,))

   NOTE: To generate prediction files, re-run with:
         python scripts/run_pipeline.py --save-predictions
   This adds LightGBM vs PatchTST DM test, the key cross-paradigm comparison.
   Uses Harvey-Leybourne-Newbold (HLN) correction for autocorrelated errors.

Usage
-----
    python scripts/significance_test.py
    python scripts/significance_test.py --mode per_building
    python scripts/significance_test.py --mode dm

Output
------
    outputs/results/significance_results.csv
    Printed table suitable for copy-paste into LaTeX
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR  = PROJECT_ROOT / "outputs" / "results"
PREDS_DIR    = PROJECT_ROOT / "outputs" / "predictions"


# ---------------------------------------------------------------------------
# Mode 1: Per-Building Paired Tests
# ---------------------------------------------------------------------------

# LightGBM is the reference model — all comparisons are LightGBM vs X
_COMPARISONS = [
    ("LightGBM", "Ridge",        "LightGBM vs Ridge (linear baseline)"),
    ("LightGBM", "Lasso",        "LightGBM vs Lasso (linear baseline)"),
    ("LightGBM", "RandomForest", "LightGBM vs Random Forest"),
    ("LightGBM", "XGBoost",      "LightGBM vs XGBoost"),
    ("LightGBM", "Mean Baseline","LightGBM vs Mean Baseline"),
]


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Paired Cohen's d (difference / pooled std)."""
    diff = a - b
    return float(np.mean(diff) / (np.std(diff, ddof=1) + 1e-12))


def run_per_building_tests(output_path: Path) -> pd.DataFrame:
    """Wilcoxon + paired t-test on per-building MAEs across 44 Drammen buildings."""
    per_bldg_path = RESULTS_DIR / "per_building_metrics.csv"
    if not per_bldg_path.exists():
        raise FileNotFoundError(f"Not found: {per_bldg_path}")

    df = pd.read_csv(per_bldg_path)
    pivot = df.pivot_table(index="building_id", columns="model", values="MAE")

    rows: list[dict] = []
    logger.info("\n=== Per-Building Significance Tests (Wilcoxon + paired t) ===\n")

    for ref_model, cmp_model, label in _COMPARISONS:
        if ref_model not in pivot.columns or cmp_model not in pivot.columns:
            logger.warning("  Skipping '%s' — model not in per_building_metrics.csv", label)
            continue

        pair = pivot[[ref_model, cmp_model]].dropna()
        n = len(pair)
        a = pair[ref_model].values   # LightGBM MAEs
        b = pair[cmp_model].values   # Comparison model MAEs
        diff = a - b                  # negative = LightGBM is better (lower MAE)

        # Wilcoxon signed-rank (non-parametric, n=44)
        wilcoxon_stat, wilcoxon_p = stats.wilcoxon(a, b, alternative="less")

        # Paired t-test (parametric, for reference)
        t_stat, t_p = stats.ttest_rel(a, b)
        t_p_one = t_p / 2 if t_stat < 0 else 1.0 - t_p / 2  # one-sided (LightGBM < cmp)

        d = cohens_d(a, b)

        significance = (
            "***" if wilcoxon_p < 0.001
            else "**" if wilcoxon_p < 0.01
            else "*" if wilcoxon_p < 0.05
            else "ns"
        )

        row = {
            "comparison":         label,
            "n_buildings":        n,
            "lgbm_mean_mae":      round(float(np.mean(a)), 4),
            "cmp_mean_mae":       round(float(np.mean(b)), 4),
            "mean_diff":          round(float(np.mean(diff)), 4),
            "wilcoxon_stat":      round(float(wilcoxon_stat), 4),
            "wilcoxon_p":         round(float(wilcoxon_p), 6),
            "t_stat":             round(float(t_stat), 4),
            "t_p_one_sided":      round(float(t_p_one), 6),
            "cohens_d":           round(float(d), 4),
            "significance":       significance,
        }
        rows.append(row)

        logger.info(
            "%-45s | n=%2d | ΔMAE=%+.3f | Wilcoxon p=%.4f %s | d=%.2f",
            label, n, np.mean(diff), wilcoxon_p, significance, d
        )

    results_df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(output_path, index=False)
    logger.info("\nResults saved → %s", output_path)

    # LaTeX-ready table snippet
    logger.info("\n=== LaTeX Table Snippet ===")
    logger.info("\\begin{tabular}{lrrrl}")
    logger.info("Comparison & n & ΔMAE & Wilcoxon $p$ & \\\\")
    for r in rows:
        logger.info(
            "%-45s & %d & %+.3f & %.4f & %s \\\\",
            r["comparison"], r["n_buildings"], r["mean_diff"],
            r["wilcoxon_p"], r["significance"]
        )
    logger.info("\\end{tabular}")

    return results_df


# ---------------------------------------------------------------------------
# Mode 2: Diebold-Mariano Test (requires saved prediction error files)
# ---------------------------------------------------------------------------

def _dm_test_hln(e1: np.ndarray, e2: np.ndarray, h: int = 24) -> tuple[float, float]:
    """Harvey-Leybourne-Newbold (1997) corrected Diebold-Mariano test.

    Tests H0: E[d_t] = 0 where d_t = |e1_t|² - |e2_t|²  (squared error difference).
    Alternative: E[d_t] < 0 (model 1 has lower squared error).

    h: forecast horizon (used for HAC variance estimation, default 24 for H+24).

    Returns (dm_stat, p_value_one_sided)
    """
    d = e1 ** 2 - e2 ** 2          # loss differential (squared error)
    T = len(d)  # noqa: N806
    d_mean = np.mean(d)

    # HAC variance estimate (Newey-West with h-1 lags)
    gamma_0 = np.var(d, ddof=1)
    hac_var = gamma_0
    for k in range(1, h):
        gamma_k = np.mean((d[k:] - d_mean) * (d[:-k] - d_mean))
        hac_var += 2 * (1 - k / h) * gamma_k

    dm_stat = d_mean / np.sqrt(hac_var / T)

    # HLN correction (small-sample adjustment)
    # HLN-corrected: scale DM by sqrt((T+1-2h+h(h-1)/T)/T)
    correction = np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    dm_stat_hln = dm_stat * correction

    # Student-t p-value (one-sided: model1 better than model2)
    p_val = float(stats.t.cdf(dm_stat_hln, df=T - 1))
    return float(dm_stat_hln), p_val


_DM_COMPARISONS = [
    # Cross-paradigm (key journal paper comparison)
    # LightGBM errors: generated by run_pipeline.py --save-predictions
    # CNN-LSTM (Setup B, tabular features): also from run_pipeline.py --save-predictions
    # CNN-LSTM (Setup C, raw sequences): from scripts/run_raw_dl.py --save-predictions (if implemented)
    ("LightGBM", "CNN-LSTM", "LightGBM (Setup A) vs CNN-LSTM (Setup B, tabular DL)"),

    # Within-paradigm (tree models only)
    ("LightGBM", "Ridge",    "LightGBM (Setup A) vs Ridge (Setup A)"),
    ("LightGBM", "XGBoost",  "LightGBM (Setup A) vs XGBoost (Setup A)"),
]


def run_dm_tests(output_path: Path) -> pd.DataFrame:
    """Diebold-Mariano tests on saved test prediction error files.

    Expects: outputs/predictions/{model_name}_h24_test_errors.npy
             Files contain e_t = y_true_t - y_pred_t arrays, shape (n_test,)

    To generate these files:
        python scripts/run_pipeline.py --save-predictions
    """
    rows: list[dict] = []
    logger.info("\n=== Diebold-Mariano Tests (HLN-corrected, H+24) ===\n")

    for model1_key, model2_key, label in _DM_COMPARISONS:
        f1 = PREDS_DIR / f"{model1_key}_h24_test_errors.npy"
        f2 = PREDS_DIR / f"{model2_key}_h24_test_errors.npy"

        if not f1.exists() or not f2.exists():
            missing = [str(p) for p in [f1, f2] if not p.exists()]
            logger.warning(
                "  Skipping '%s' — missing prediction files:\n    %s\n"
                "  Run: python scripts/run_pipeline.py --save-predictions",
                label, "\n    ".join(missing)
            )
            rows.append({
                "comparison": label, "dm_stat": None, "p_value": None,
                "significance": "NOT RUN — missing prediction files",
            })
            continue

        e1 = np.load(f1).flatten()
        e2 = np.load(f2).flatten()
        n = min(len(e1), len(e2))
        e1, e2 = e1[:n], e2[:n]

        dm_stat, p_val = _dm_test_hln(e1, e2, h=24)
        significance = (
            "***" if p_val < 0.001
            else "**" if p_val < 0.01
            else "*" if p_val < 0.05
            else "ns"
        )

        logger.info(
            "%-55s | DM=%.4f | p=%.4f %s",
            label, dm_stat, p_val, significance
        )
        rows.append({
            "comparison": label,
            "dm_stat":    round(dm_stat, 4),
            "p_value":    round(p_val, 6),
            "significance": significance,
        })

    dm_df = pd.DataFrame(rows)
    dm_path = output_path.parent / "dm_test_results.csv"
    dm_df.to_csv(dm_path, index=False)
    logger.info("\nDM results saved → %s", dm_path)
    return dm_df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Statistical significance tests")
    parser.add_argument(
        "--mode",
        choices=["per_building", "dm", "both"],
        default="both",
        help="Which tests to run (default: both)",
    )
    args = parser.parse_args()

    if args.mode in ("per_building", "both"):
        run_per_building_tests(RESULTS_DIR / "significance_results.csv")

    if args.mode in ("dm", "both"):
        run_dm_tests(RESULTS_DIR / "dm_test_results.csv")


if __name__ == "__main__":
    main()
