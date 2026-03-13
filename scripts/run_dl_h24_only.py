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

from energy_forecast.evaluation import evaluate  # noqa: E402
from energy_forecast.models.deep_learning import CNNLSTMForecaster, GRUForecaster  # noqa: E402, F401
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

    city = cfg.get("city", "drammen")
    lookback = cfg["sequence"]["lookback"]
    horizon = cfg["sequence"]["horizon"]

    # Paths
    splits_dir = PROJECT_ROOT / "data/processed/splits"
    model_dir = PROJECT_ROOT / "outputs/models"
    results_dir = PROJECT_ROOT / "outputs/results"

    logger.info("=" * 60)
    logger.info("  SEQUENTIAL DL RECOVERY: SETUP B (H+24 PARADIGM)")
    logger.info("=" * 60)
    logger.info(f"Project Root: {PROJECT_ROOT}")
    logger.info(f"City: {city}")
    logger.info("-" * 60)

    # Load the pre-saved city splits (feature-selected, 35 features, correct city data)
    # These are identical to the splits used by run_pipeline.py for the authoritative results.
    city_prefix = f"{city}_"
    split_keys = {
        "X_train": "X_train_fs", "y_train": "y_train",
        "X_val":   "X_val_fs",   "y_val":   "y_val",
        "X_test":  "X_test_fs",  "y_test":  "y_test",
    }
    splits = {}
    for local_key, file_stem in split_keys.items():
        fpath = splits_dir / f"{city_prefix}{file_stem}.parquet"
        if not fpath.exists():
            logger.error("Split file not found: %s", fpath)
            return
        arr = pd.read_parquet(fpath)
        splits[local_key] = arr.squeeze() if local_key.startswith("y_") else arr
    y_test = splits["y_test"]

    logger.info("Building evaluation matrix...")
    y_true_2d = _build_y_true_matrix(y_test, lookback, horizon)

    # Metadata for the user: Activation Types
    activations = {
        "CNN-LSTM_SetupB": "ReLU (Conv), Tanh (Recurrent), ReLU (Dense)",
        "GRU_SetupB": "Tanh (Recurrent), ReLU (Dense)",
        "TFT_SetupB": "GLU (Gated Linear Unit), ReLU"
    }

    # Only TFT_SetupB is needed here.
    # CNN-LSTM_SetupB and GRU_SetupB already have correct authoritative results
    # (MAE=9.375 R²=0.877; MAE=9.639 R²=0.867) from the original pipeline run.
    # Re-running them risks overwriting those results; TFT is new and has no result yet.
    models_to_run = [
        ("TFT_SetupB", TFTForecaster),
    ]

    for name, ModelCls in models_to_run:  # noqa: N806
        logger.info(f"🚀 STARTING: {name}")
        try:
            # TFT uses PyTorch/Lightning — no Keras session to clear.
            is_tf_model = ModelCls not in (TFTForecaster,)
            if is_tf_model:
                tf.keras.backend.clear_session()

            # Deep copy so config mutations don't bleed across models.
            # Do NOT override epochs for TF models here; the config default (20)
            # is correct for CNN-LSTM/GRU.  TFT uses cfg["training"]["tft"]["max_epochs"].
            import copy
            model_cfg = copy.deepcopy(cfg)

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
