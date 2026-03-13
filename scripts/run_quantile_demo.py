#!/usr/bin/env python
"""
run_quantile_demo.py
====================
Standalone demonstration of the LightGBM Quantile Forecaster.
Trains the P10, P50, and P90 models, predicts on the test set,
and calculates the Prediction Interval Coverage Probability (PICP)
to verify the 80% theoretical confidence interval.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from energy_forecast.models.sklearn_models import _build_lgbm_quantile
from energy_forecast.utils import load_config, set_global_seed, setup_logging

logger = logging.getLogger(__name__)

def main():
    setup_logging("INFO")
    cfg = load_config()
    set_global_seed(cfg.get("seed", 42))

    logger.info("============================================================")
    logger.info("LightGBM Probabilistic Forecasting (Quantile Regression)")
    logger.info("============================================================")

    proc_dir = Path(cfg["paths"]["processed"]) / "splits"

    logger.info("Loading feature-selected data splits...")
    X_train = pd.read_parquet(proc_dir / "X_train_fs.parquet")  # noqa: N806
    y_train = pd.read_parquet(proc_dir / "y_train.parquet").squeeze()
    X_val   = pd.read_parquet(proc_dir / "X_val_fs.parquet")  # noqa: N806
    y_val   = pd.read_parquet(proc_dir / "y_val.parquet").squeeze()
    X_test  = pd.read_parquet(proc_dir / "X_test_fs.parquet")  # noqa: N806
    y_test  = pd.read_parquet(proc_dir / "y_test.parquet").squeeze()

    # Model Initialization
    logger.info("Initializing LightGBMQuantileForecaster...")
    model = _build_lgbm_quantile(cfg["training"]["lightgbm"], seed=cfg.get("seed", 42))

    # Training
    model.fit(X_train, y_train, X_val=X_val, y_val=y_val)

    # Predictions
    logger.info("Generating probabilistic confidence intervals (P10, P50, P90)...")
    quantiles_df = model.predict_quantiles(X_test)

    # Calculate Coverage Metrics
    # Nominal coverage for P10 to P90 is exactly 80% (0.90 - 0.10)
    y_true = y_test.values
    p10 = quantiles_df["P10"].values
    p50 = quantiles_df["P50"].values
    p90 = quantiles_df["P90"].values

    # PICP: Prediction Interval Coverage Probability
    hits = (y_true >= p10) & (y_true <= p90)
    picp = hits.mean() * 100.0

    # PINAW: Prediction Interval Normalized Average Width
    range_y = y_true.max() - y_true.min()
    pinaw = np.mean(p90 - p10) / range_y * 100.0

    logger.info("============================================================")
    logger.info("Probabilistic Evaluation Results (Test Set, N=%d)", len(y_true))
    logger.info("------------------------------------------------------------")
    logger.info("Target Nominal Coverage (P10 to P90): 80.00%")
    logger.info(f"Actual PICP (Coverage Probability)  : {picp:.2f}%")
    logger.info(f"PINAW (Normalized Average Width)    : {pinaw:.2f}%")
    logger.info("============================================================")

    # Print a tiny sample
    sample = pd.DataFrame({
        "Actual": y_true[:5],
        "P10": p10[:5],
        "P50": p50[:5],
        "P90": p90[:5]
    })
    logger.info("Sample Predictions:")
    logger.info("\n" + sample.to_string())

if __name__ == "__main__":
    main()
