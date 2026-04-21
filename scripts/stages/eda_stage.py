"""
eda_stage.py
============
Stage 1: Load raw data, preprocess, and save model-ready parquet.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run(cfg: dict) -> None:
    """Stage 1: Load raw data, preprocess, and save model-ready parquet."""
    from energy_forecast.data import build_model_ready_data, load_city_data

    city = cfg["city"]
    raw_dir = Path(cfg["paths"]["raw_data"][city])
    # City-specific processed dir prevents cross-city data clobbering
    proc_dir = Path(cfg["paths"]["processed"]) / city

    logger.info("── Stage 1: EDA (%s) ──────────────────────────", city.upper())
    metadata, timeseries = load_city_data(city, raw_dir, cfg)

    # Save metadata
    meta_path = proc_dir / "metadata.parquet"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    metadata.to_parquet(meta_path)
    logger.info("Metadata saved → %s", meta_path)

    model_ready = build_model_ready_data(timeseries, metadata, cfg, proc_dir)

    # Generate EDA figures
    from energy_forecast.visualization import (
        plot_building_profiles,
        plot_missing_data,
        plot_seasonal_patterns,
        plot_temperature_sensitivity,
    )

    fig_dir = Path(cfg["paths"]["outputs"]["figures"])
    plot_building_profiles(timeseries, save_path=fig_dir / "building_profiles.png")
    plot_temperature_sensitivity(timeseries, save_path=fig_dir / "temperature_sensitivity.png")
    plot_seasonal_patterns(timeseries, save_path=fig_dir / "seasonal_patterns.png")
    plot_missing_data(timeseries, save_path=fig_dir / "missing_data.png")

    logger.info("Stage 1 complete. Model-ready dataset: %d rows, %d cols", *model_ready.shape)
