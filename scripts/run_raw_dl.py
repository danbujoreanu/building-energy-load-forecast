#!/usr/bin/env python
"""
run_raw_dl.py
=============
Executes Setup C (Paradigm Parity) experiment.
Runs Deep Learning models (LSTM, CNN-LSTM, GRU, PatchTST placeholder) on 
raw sequence data (ignoring tabular feature engineering) to ensure a fair
benchmarking against sklearn trees natively processing tabular data.

Logs directly to outputs/logs/run_raw_dl.log.
"""

import argparse
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

from energy_forecast.utils import load_config, set_global_seed
from energy_forecast.evaluation import evaluate
from energy_forecast.data.raw_sequence import build_raw_sequences

# Setup distinct logger configuration
def setup_local_logging(log_level: str):
    log_dir = Path("outputs/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "run_raw_dl.log"
    
    # Remove existing handlers to avoid duplicate logs in case of reload
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(str(log_file), mode="w"),
            logging.StreamHandler()
        ]
    )

logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Run Setup C DL models")
    parser.add_argument("--city", default="drammen", choices=["drammen", "oslo"])
    parser.add_argument("--config", default="config/config.yaml", help="Config file path")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING"])
    return parser.parse_args()

def get_keras_model(name, input_shape, horizon, cfg):
    """Wrapper to build keras models dynamically from deep_learning configurations.
    Since deep_learning.py expects df in .fit(), we build raw models here for 3D numpy arrays.
    """
    import tensorflow as tf
    dl_cfg = cfg["training"]["deep_learning"]
    tf.keras.backend.clear_session()
    
    if name == "LSTM":
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(dl_cfg["lstm"]["units"][0], return_sequences=True, input_shape=input_shape),
            tf.keras.layers.Dropout(dl_cfg["dropout_rate"]),
            tf.keras.layers.LSTM(dl_cfg["lstm"]["units"][1]),
            tf.keras.layers.Dropout(dl_cfg["dropout_rate"]),
            tf.keras.layers.Dense(dl_cfg["lstm"]["dense_units"], activation="relu"),
            tf.keras.layers.Dense(horizon)
        ], name="LSTM_Raw")
        
    elif name == "CNN-LSTM":
        cnn_cfg = dl_cfg["cnn_lstm"]
        model = tf.keras.Sequential([
            tf.keras.layers.Conv1D(cnn_cfg["conv_filters"][0], cnn_cfg["kernel_size"], activation="relu", input_shape=input_shape),
            tf.keras.layers.MaxPooling1D(pool_size=2),
            tf.keras.layers.Conv1D(cnn_cfg["conv_filters"][1], cnn_cfg["kernel_size"], activation="relu"),
            tf.keras.layers.LSTM(cnn_cfg["lstm_units"]),
            tf.keras.layers.Dropout(dl_cfg["dropout_rate"]),
            tf.keras.layers.Dense(cnn_cfg["dense_units"], activation="relu"),
            tf.keras.layers.Dense(horizon)
        ], name="CNN_LSTM_Raw")
        
    elif name == "GRU":
        model = tf.keras.Sequential([
            tf.keras.layers.GRU(dl_cfg["gru"]["units"][0], return_sequences=True, input_shape=input_shape),
            tf.keras.layers.Dropout(dl_cfg["dropout_rate"]),
            tf.keras.layers.GRU(dl_cfg["gru"]["units"][1]),
            tf.keras.layers.Dropout(dl_cfg["dropout_rate"]),
            tf.keras.layers.Dense(dl_cfg["gru"]["dense_units"], activation="relu"),
            tf.keras.layers.Dense(horizon)
        ], name="GRU_Raw")
    else:
        raise ValueError(f"Unknown deep learning model mode: {name}")

    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model

def create_callbacks(dl_cfg):
    import tensorflow as tf
    return [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=dl_cfg["early_stopping_patience"],
            min_delta=dl_cfg.get("early_stopping_min_delta", 0.0),
            restore_best_weights=True, verbose=1
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=dl_cfg["reduce_lr_factor"],
            patience=dl_cfg["reduce_lr_patience"], min_lr=dl_cfg["min_lr"], verbose=0
        )
    ]

def run_patchtst_eval(cfg, df_train, df_test, target_col, feature_cols, scaler_X, scaler_y, horizon):
    import time
    try:
        from neuralforecast import NeuralForecast
        from neuralforecast.models import PatchTST
    except ImportError:
        logger.warning("neuralforecast is not installed. Skipping PatchTST.")
        return None

    logger.info("Preparing data for NeuralForecast PatchTST...")

    def _prep_nf(df):
        df_scaled = df.copy()
        df_scaled[feature_cols] = scaler_X.transform(df_scaled[feature_cols].values)
        df_nf = df_scaled.reset_index()
        df_nf = df_nf.rename(columns={"building_id": "unique_id", "timestamp": "ds", target_col: "y"})
        # We also need to sort it, just in case
        cols_to_keep = ["unique_id", "ds", "y"] + [c for c in feature_cols if c != target_col]
        return df_nf[cols_to_keep].sort_values(by=["unique_id", "ds"]).reset_index(drop=True)

    nf_train = _prep_nf(df_train)
    nf_test = _prep_nf(df_test)

    nf_full = pd.concat([nf_train, nf_test]).reset_index(drop=True)

    hist_exog = [c for c in feature_cols if c != target_col]
    lookback = cfg["sequence"]["lookback"]
    dl_cfg = cfg.get("training", {}).get("deep_learning", {})

    max_steps = 500 # Explicitly capping this for a relatively fast demonstration
    
    # Define NeuralForecast PatchTST
    # Note: NeuralForecast handles scaling; we inject pre-scaled data and pass identity.
    model = PatchTST(
        h=horizon,
        input_size=lookback,
        max_steps=max_steps,
        batch_size=dl_cfg.get("batch_size", 64),
        scaler_type="identity", 
    )
    
    # Must specify freq according to temporal data granularity
    nf = NeuralForecast(models=[model], freq="h")
    
    t0 = time.time()
    logger.info("Training PatchTST (Setup C) on Train data...")
    nf.fit(df=nf_train, val_size=24)
    logger.info(f"PatchTST trained in {time.time() - t0:.1f}s")
    
    logger.info("Evaluating PatchTST... (Cross validation rolling window)")
    
    # Calculate exactly how many windows the Keras loop natively spans: (N - horizon + 1)
    b_ids = df_test.index.get_level_values("building_id").unique()
    if len(b_ids) == 0:
        return None
        
    num_test_steps = len(df_test.xs(b_ids[0], level="building_id"))
    n_windows = num_test_steps - horizon + 1
    
    if n_windows < 1:
        logger.warning("Test set too short for rolling prediction.")
        return None
        
    cv_df = nf.cross_validation(df=nf_full, step_size=1, n_windows=n_windows, refit=0)
    
    # Inverse scaling the evaluation predictions
    preds_scaled = cv_df["PatchTST"].values
    y_scaled = cv_df["y"].values
    
    preds_inv = scaler_y.inverse_transform(preds_scaled.reshape(-1, 1)).flatten()
    y_inv = scaler_y.inverse_transform(y_scaled.reshape(-1, 1)).flatten()
    
    # Unpack 1D sequence evaluations back into pseudo-2D metrics evaluation (matching Keras)
    preds_inv_2d = preds_inv.reshape(-1, horizon) if horizon > 1 else preds_inv.reshape(-1, 1)
    y_inv_2d = y_inv.reshape(-1, horizon) if horizon > 1 else y_inv.reshape(-1, 1)
    
    res_metrics = evaluate(y_inv_2d, preds_inv_2d, model_name="PatchTST")
    return res_metrics

def main():
    args = parse_args()
    setup_local_logging(args.log_level)
    
    logger.info("=" * 60)
    logger.info("Running Setup C (Paradigm Parity Raw DL)")
    logger.info("=" * 60)

    cfg = load_config(args.config)
    cfg["city"] = args.city
    set_global_seed(cfg.get("seed", 42))

    lookback = cfg["sequence"]["lookback"]
    horizon = cfg["sequence"]["horizon"]
    target_col = cfg["data"]["target_column"]
    
    # Define raw features for Setup C
    feature_cols = [
        "Temperature_Outdoor_C",
        "Global_Solar_Horizontal_Radiation_W_m2"
    ]
    # In some DL literature, the target is ALSO included in the raw sequence as input 
    # (autoregressive feature). We must explicitly pass both.
    feature_cols = [target_col] + feature_cols
    
    proc_dir = Path(cfg["paths"]["processed"])
    model_ready_path = proc_dir / "model_ready.parquet"
    
    logger.info(f"Loading {model_ready_path}...")
    df = pd.read_parquet(model_ready_path)
    
    # Replicate train/val/test splits (from src/energy_forecast/data/splits.py logic)
    train_end = pd.Timestamp(cfg["splits"]["train_end"], tz="Europe/Oslo")
    val_end   = pd.Timestamp(cfg["splits"]["val_end"],   tz="Europe/Oslo")
    ts = df.index.get_level_values("timestamp")
    
    df_train = df[ts <= train_end].copy()
    df_val   = df[(ts > train_end) & (ts <= val_end)].copy()
    df_test  = df[ts > val_end].copy()
    
    # Impute missing weather values using Train Median (no leakage)
    for col in feature_cols:
        med = df_train[col].median()
        df_train[col] = df_train[col].fillna(med)
        df_val[col]   = df_val[col].fillna(med)
        df_test[col]  = df_test[col].fillna(med)
    
    # Generate 3D sequences and scaled Targets
    res = build_raw_sequences(
        df_train, df_val, df_test, 
        target_col, feature_cols, 
        lookback, horizon
    )
    X_tr, y_tr, X_v, y_v, X_te, y_te, scaler_X, scaler_y = res
    
    models_to_run = []
    results = []
    
    input_shape = (lookback, len(feature_cols))
    dl_cfg = cfg["training"]["deep_learning"]
    callbacks = create_callbacks(dl_cfg)

    # Train Keras models
    for name in models_to_run:
        logger.info(f"--- Training Raw {name} (Setup C) ---")
        try:
            model = get_keras_model(name, input_shape, horizon, cfg)
            
            t0 = time.time()
            model.fit(
                X_tr, y_tr,
                epochs=dl_cfg["epochs"],
                batch_size=dl_cfg["batch_size"],
                validation_data=(X_v, y_v),
                callbacks=callbacks,
                verbose=2
            )
            logger.info(f"{name} Setup C trained in {time.time() - t0:.1f}s")
            
            logger.info(f"Evaluating {name} Setup C...")
            preds_scaled = model.predict(X_te, verbose=0)
            
            # INVERSE TRANSFORM (Un-scale predictions and test targets back to kWh)
            # StandardScaler was fit on (N, 1). We must reshape to inverse_transform, then revert shapes.
            preds_flat = preds_scaled.reshape(-1, 1)
            preds_inv = scaler_y.inverse_transform(preds_flat).reshape(preds_scaled.shape)
            
            y_te_2d = y_te.reshape(-1, horizon) if horizon > 1 else y_te.reshape(-1, 1)
            y_te_flat = y_te_2d.reshape(-1, 1)
            y_true_inv = scaler_y.inverse_transform(y_te_flat).reshape(y_te_2d.shape)
            
            # Run Evaluation over un-scaled data to get real kWh MAE/RMSE
            res_metrics = evaluate(y_true_inv, preds_inv, model_name=f"{name}_SetupC")
            
            # Save immediately
            df_res = pd.DataFrame([res_metrics])
            df_res["train_time_s"] = time.time() - t0
            metrics_file = Path(cfg["paths"]["outputs"]["results"]) / "final_metrics.csv"
            
            if metrics_file.exists():
                existing = pd.read_csv(metrics_file, index_col=0) if metrics_file.stat().st_size > 0 else pd.DataFrame()
                if not existing.empty:
                    existing = existing[existing["model"] != f"{name}_SetupC"]
                combined = pd.concat([existing, df_res], ignore_index=True)
                combined.to_csv(metrics_file)
            else:
                df_res.to_csv(metrics_file)

        except Exception as e:
            logger.error(f"Failed to process {name} Setup C: {e}")

    # PatchTST Model Implementation
    logger.info("--- Training Raw PatchTST (Setup C) ---")
    try:
        patchtst_res = run_patchtst_eval(
            cfg, df_train, df_test, target_col, feature_cols, scaler_X, scaler_y, horizon
        )
        if patchtst_res:
            df_res = pd.DataFrame([patchtst_res])
            metrics_file = Path(cfg["paths"]["outputs"]["results"]) / "final_metrics.csv"
            
            if metrics_file.exists():
                existing = pd.read_csv(metrics_file, index_col=0) if metrics_file.stat().st_size > 0 else pd.DataFrame()
                if not existing.empty:
                    existing = existing[existing["model"] != "PatchTST"]
                combined = pd.concat([existing, df_res], ignore_index=True)
                combined.to_csv(metrics_file)
            else:
                df_res.to_csv(metrics_file)
    except Exception as e:
        logger.error(f"Failed to process PatchTST: {e}")

    logger.info("Setup C Evaluation complete! Check outputs/results/final_metrics.csv")

if __name__ == "__main__":
    main()
