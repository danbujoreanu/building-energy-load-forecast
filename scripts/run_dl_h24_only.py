#!/usr/bin/env python
"""
run_dl_h24_only.py
==================
Quiet, robust recovery script to train missing DL models (CNN-LSTM, GRU, TFT)
for Setup B. Adheres to Computing Stewardship policy:
1. Sequential execution.
2. Explicit ml_lab1 environment usage.
3. Clean logging.
4. METADATA TRACKING: Records activation types and training times.
"""

import logging
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# Calculate project root for CWD independence
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.append(str(PROJECT_ROOT / "src"))

# --- ENVIRONMENT STEWARDSHIP ---
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf  # noqa: E402

tf.get_logger().setLevel('ERROR')

from energy_forecast.data.splits import make_splits  # noqa: E402
from energy_forecast.evaluation import evaluate  # noqa: E402
from energy_forecast.models.deep_learning import CNNLSTMForecaster, GRUForecaster  # noqa: E402
from energy_forecast.models.tft import TFTForecaster  # noqa: E402
from energy_forecast.utils import load_config, set_global_seed  # noqa: E402

# Setup logging - USER FACING & CLEAN
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

def _build_y_true_matrix(y, lookback: int, horizon: int) -> np.ndarray:
    parts = []
    # y is a pd.Series with MultiIndex (building_id, timestamp)
    for bid in y.index.get_level_values("building_id").unique():
        y_b = y.xs(bid, level="building_id").values
        n = len(y_b)
        for i in range(lookback, n - horizon + 1):
            parts.append(y_b[i: i + horizon])
    return np.array(parts, dtype=np.float32)

def main():
    cfg = load_config(PROJECT_ROOT / "config/config.yaml")
    # Force absolute paths in cfg
    cfg["paths"]["processed"] = str(PROJECT_ROOT / "data/processed")

    set_global_seed(cfg.get("seed", 42))

    city = cfg.get("city", "drammen")  # noqa: F841
    lookback = cfg["sequence"]["lookback"]
    horizon = cfg["sequence"]["horizon"]
    target_col = cfg["data"]["target_column"]

    # Paths
    proc_dir = PROJECT_ROOT / "data/processed"
    model_ready_path = proc_dir / "model_ready.parquet"
    model_dir = PROJECT_ROOT / "outputs/models"
    results_dir = PROJECT_ROOT / "outputs/results"

    logger.info("=" * 60)
    logger.info("  SEQUENTIAL DL RECOVERY: SETUP B (H+24 PARADIGM)")
    logger.info("=" * 60)
    logger.info(f"Project Root: {PROJECT_ROOT}")
    logger.info("-" * 60)

    if not model_ready_path.exists():
        logger.error(f"Data not found at {model_ready_path}. Run pipeline first.")
        return

    # Load and split
    df = pd.read_parquet(model_ready_path)
    splits = make_splits(df, cfg, target_col)
    y_test = splits["y_test"]

    logger.info("Building evaluation matrix...")
    y_true_2d = _build_y_true_matrix(y_test, lookback, horizon)

    # Metadata for the user: Activation Types
    activations = {
        "CNN-LSTM_SetupB": "ReLU (Conv), Tanh (Recurrent), ReLU (Dense)",
        "GRU_SetupB": "Tanh (Recurrent), ReLU (Dense)",
        "TFT_SetupB": "GLU (Gated Linear Unit), ReLU"
    }

    models_to_run = [
        ("CNN-LSTM_SetupB", CNNLSTMForecaster),
        ("GRU_SetupB", GRUForecaster),
        ("TFT_SetupB", TFTForecaster)
    ]

    for name, ModelCls in models_to_run:  # noqa: N806
        logger.info(f"🚀 STARTING: {name}")
        try:
            # TFT uses PyTorch/Lightning — tf.keras.clear_session() is a no-op
            # for it and confusingly suggests we're clearing a TF graph state.
            # Only clear Keras session for TF-based models (LSTM, CNN-LSTM, GRU).
            is_tf_model = ModelCls not in (TFTForecaster,)
            if is_tf_model:
                tf.keras.backend.clear_session()

            # cfg.copy() is a shallow copy: modifying nested keys mutates the
            # original cfg dict.  Use a proper deep copy so each model gets a
            # clean config.  Only override deep_learning.epochs for TF models;
            # TFT uses cfg["training"]["tft"]["max_epochs"] independently.
            import copy
            model_cfg = copy.deepcopy(cfg)
            if is_tf_model:
                model_cfg["training"]["deep_learning"]["epochs"] = 10

            t0 = time.time()
            model = ModelCls(model_cfg)
            model.fit(splits["X_train"], splits["y_train"], splits["X_val"], splits["y_val"])
            train_t = round(time.time() - t0, 1)

            # Predict
            preds = model.predict(splits["X_test"])

            if preds.shape == y_true_2d.shape:
                res = evaluate(y_true_2d, preds, model_name=name)
                res["train_time_s"] = train_t
                res["activation"] = activations.get(name, "N/A")

                # Save results to central table
                metrics_file = results_dir / "final_metrics.csv"
                df_res = pd.DataFrame([res])
                if metrics_file.exists():
                    existing = pd.read_csv(metrics_file, index_col=0)
                    existing = existing[existing["model"] != name]
                    combined = pd.concat([existing, df_res], ignore_index=True)
                    combined.to_csv(metrics_file)
                else:
                    df_res.to_csv(metrics_file)

                # Save Model correctly
                if hasattr(model, "model_") and hasattr(model.model_, "save"):
                    model.model_.save(str(model_dir / f"{name}.keras"))

                logger.info(f" ✅ FINISHED: {name} | MAE: {res['MAE']:.3f} | Time: {train_t}s")
            else:
                logger.error(f" ❌ SHAPE MISMATCH: {name} (preds {preds.shape} vs true {y_true_2d.shape})")

        except Exception as e:
            logger.error(f" ❌ FAILED: {name} | Error: {str(e)}")

        logger.info("-" * 60)

    logger.info("🎉 Setup B recovery complete!")

if __name__ == "__main__":
    main()
