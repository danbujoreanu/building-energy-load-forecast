"""
generate_eda_charts.py
======================
Standalone script that generates all comprehensive EDA charts for the
Drammen dataset, mirroring the original MSc thesis Jupyter notebooks.

Charts produced
---------------
outputs/figures/eda/
  metadata_overview.png          — 4-panel building metadata (category, year, area, label)
  column_availability.png        — Sensor heatmap per building
  missing_data_analysis.png      — Per-column and per-building missing %
  temperature_vs_electricity.png — Scatter + regression by category (75k sample)
  acf_pacf.png                   — ACF/PACF for a representative building
  seasonal_decomposition.png     — Additive decomposition (trend/seasonal/residual)
  building_profiles/             — Per-building daily + seasonal hourly profiles

outputs/figures/results/
  model_comparison_4panel.png    — MAE/RMSE/R²/MAPE 4-panel comparison
  model_comparison_mae_bar.png   — Standalone MAE bar chart
  thesis_vs_pipeline.png         — Side-by-side thesis vs new pipeline comparison

Usage
-----
    # From project root with ml_lab1 activated:
    python scripts/generate_eda_charts.py --city drammen

    # To also generate per-building profiles (slow, 43 buildings):
    python scripts/generate_eda_charts.py --city drammen --profiles

    # Skip heavy charts for quick iteration:
    python scripts/generate_eda_charts.py --city drammen --quick
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from energy_forecast.data.loader import load_city_data
from energy_forecast.visualization.eda_charts import (
    plot_building_metadata_overview,
    plot_column_availability_heatmap,
    plot_missing_data_analysis,
    plot_all_building_energy_profiles,
    plot_temperature_vs_electricity_by_category,
    plot_acf_pacf,
    plot_seasonal_decomposition,
    plot_model_results_comparison,
    plot_thesis_vs_pipeline_comparison,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Known thesis results (from results/final_metrics.csv in New Coding 14.05)
THESIS_METRICS = pd.DataFrame([
    {"Model": "Random Forest",              "MAE": 3.300, "RMSE": 6.403,  "R²": 0.9819},
    {"Model": "XGBoost",                    "MAE": 3.419, "RMSE": 6.443,  "R²": 0.9817},
    {"Model": "LightGBM",                   "MAE": 3.578, "RMSE": 6.679,  "R²": 0.9803},
    {"Model": "Stacking Ensemble (LGBM)",   "MAE": 3.582, "RMSE": 7.030,  "R²": 0.9782},
    {"Model": "Stacking Ensemble",          "MAE": 3.698, "RMSE": 7.051,  "R²": 0.9781},
    {"Model": "Weighted Avg Ensemble",      "MAE": 4.081, "RMSE": 7.841,  "R²": 0.9729},
    {"Model": "Lasso Regression",           "MAE": 4.201, "RMSE": 7.880,  "R²": 0.9726},
    {"Model": "Ridge Regression",           "MAE": 4.215, "RMSE": 7.767,  "R²": 0.9733},
    {"Model": "Persistence (Lag 1h)",       "MAE": 4.561, "RMSE": 9.587,  "R²": 0.9594},
    {"Model": "TFT (Comprehensive)",        "MAE": 5.114, "RMSE": 10.424, "R²": 0.9520},
    {"Model": "Seasonal Naive (24h)",       "MAE": 8.762, "RMSE": 19.383, "R²": 0.8340},
    {"Model": "LSTM",                       "MAE": 10.132,"RMSE": 17.686, "R²": 0.8623},
    {"Model": "CNN-LSTM",                   "MAE": 12.435,"RMSE": 20.930, "R²": 0.8071},
])


def _load_pipeline_metrics(results_dir: Path) -> pd.DataFrame | None:
    """Load current pipeline metrics from CSV if available."""
    csv = results_dir / "final_metrics.csv"
    if not csv.exists():
        logger.warning("Pipeline metrics not found at %s — skipping comparison chart", csv)
        return None
    df = pd.read_csv(csv)
    # Normalise column names
    col_map = {c: c.replace("MAE", "MAE").replace("RMSE", "RMSE")
               .replace("R2", "R²").replace("R²", "R²")
               for c in df.columns}
    df = df.rename(columns=col_map)
    if "Model" not in df.columns and df.columns[0] != "Model":
        df = df.rename(columns={df.columns[0]: "Model"})
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate all EDA charts.")
    parser.add_argument("--city", default="drammen", choices=["drammen", "oslo"])
    parser.add_argument("--profiles", action="store_true",
                        help="Also generate per-building energy profile plots (slow)")
    parser.add_argument("--quick", action="store_true",
                        help="Skip heavy charts (ACF, decomposition, profiles)")
    args = parser.parse_args()

    # ── Load config ───────────────────────────────────────────────────────
    cfg_path = ROOT / "config" / "config.yaml"
    with cfg_path.open() as f:
        cfg = yaml.safe_load(f)

    raw_dir = ROOT / cfg["paths"]["raw_data"][args.city]
    fig_dir = ROOT / cfg["paths"]["outputs"]["figures"] / "eda"
    results_dir = ROOT / cfg["paths"]["outputs"]["results"]
    fig_dir.mkdir(parents=True, exist_ok=True)

    # ── Load data ─────────────────────────────────────────────────────────
    logger.info("Loading %s data from %s …", args.city, raw_dir)
    metadata, timeseries = load_city_data(args.city, raw_dir, cfg)
    logger.info(
        "Loaded %d buildings | %d rows | columns: %s",
        len(metadata), len(timeseries), list(timeseries.columns[:6]),
    )

    # ── 1. Metadata overview ──────────────────────────────────────────────
    logger.info("[1/7] Building metadata overview …")
    plot_building_metadata_overview(
        metadata,
        save_path=fig_dir / "metadata_overview.png",
    )

    # ── 2. Column availability heatmap ────────────────────────────────────
    logger.info("[2/7] Column availability heatmap …")
    plot_column_availability_heatmap(
        metadata, timeseries,
        save_path=fig_dir / "column_availability.png",
    )

    # ── 3. Missing data analysis ──────────────────────────────────────────
    logger.info("[3/7] Missing data analysis …")
    plot_missing_data_analysis(
        timeseries, metadata,
        save_path=fig_dir / "missing_data_analysis.png",
    )

    # ── 4. Temperature vs electricity ─────────────────────────────────────
    logger.info("[4/7] Temperature vs electricity scatter …")
    plot_temperature_vs_electricity_by_category(
        timeseries, metadata,
        save_path=fig_dir / "temperature_vs_electricity.png",
    )

    if not args.quick:
        # ── 5. ACF / PACF ─────────────────────────────────────────────────
        logger.info("[5/7] ACF / PACF …")
        building_ids = timeseries.index.get_level_values("building_id").unique()
        plot_acf_pacf(
            timeseries,
            building_id=int(building_ids[0]),
            save_path=fig_dir / "acf_pacf.png",
        )

        # ── 6. Seasonal decomposition ──────────────────────────────────────
        logger.info("[6/7] Seasonal decomposition …")
        plot_seasonal_decomposition(
            timeseries,
            building_id=int(building_ids[0]),
            save_path=fig_dir / "seasonal_decomposition.png",
        )

    # ── 7. Per-building profiles ──────────────────────────────────────────
    if args.profiles:
        logger.info("[7/7] Per-building energy profiles (all buildings) …")
        plot_all_building_energy_profiles(
            timeseries, metadata,
            out_dir=fig_dir / "building_profiles",
        )
    else:
        logger.info("[7/7] Skipping per-building profiles (use --profiles to enable)")

    # ── 8. Model results comparison ───────────────────────────────────────
    pipeline_df = _load_pipeline_metrics(results_dir)
    results_fig_dir = ROOT / cfg["paths"]["outputs"]["figures"] / "results"
    results_fig_dir.mkdir(parents=True, exist_ok=True)

    logger.info("[8/8] Model comparison charts …")
    if pipeline_df is not None:
        plot_model_results_comparison(
            pipeline_df,
            save_path_prefix=results_fig_dir / "model_comparison",
        )
        # Thesis vs pipeline
        plot_thesis_vs_pipeline_comparison(
            THESIS_METRICS, pipeline_df,
            save_path=results_fig_dir / "thesis_vs_pipeline.png",
        )
    else:
        # Fall back to thesis metrics
        plot_model_results_comparison(
            THESIS_METRICS,
            save_path_prefix=results_fig_dir / "model_comparison",
        )

    logger.info("✓ All EDA charts saved to %s", fig_dir)
    logger.info("✓ Results charts saved to %s", results_fig_dir)


if __name__ == "__main__":
    main()
