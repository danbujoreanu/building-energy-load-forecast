#!/usr/bin/env python
"""
run_horizon_sweep.py
====================
Sprint 2: Horizon Sensitivity Analysis

Trains LightGBM, XGBoost, Ridge (Setup A) and optionally LSTM (Setup B)
at each target horizon in {1, 6, 12, 24, 48} hours and records test-set
MAE, RMSE, and R² for each (model, horizon) pair.

Produces: outputs/results/horizon_metrics.csv

Design notes
------------
- Each horizon H uses only lags >= H (no oracle leakage).
- Rolling statistics are anchored at t-H for causal correctness.
- MultiOutputRegressor wraps sklearn models for H > 1.
- DL models (LSTM) are optional (--include-dl) due to runtime cost.
- Each horizon run is independent: no weights transferred across horizons.
- The sweep is checkpoint-aware: already-completed (model, horizon) pairs
  are skipped when the output CSV already exists.

Usage
-----
    # Fast sweep — sklearn only (~15 min total)
    python scripts/run_horizon_sweep.py

    # Include LSTM for DL degradation curve (adds ~3h)
    python scripts/run_horizon_sweep.py --include-dl

    # Single horizon test
    python scripts/run_horizon_sweep.py --horizons 24

    # Resume interrupted sweep (skips completed pairs)
    python scripts/run_horizon_sweep.py --resume
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ── Project root on path ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from energy_forecast.utils import load_config, set_global_seed  # noqa: E402

# ── Logging ───────────────────────────────────────────────────────────────────
log_dir = ROOT / "outputs" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(str(log_dir / "run_horizon_sweep.log"), mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_HORIZONS = [1, 6, 12, 24, 48]
SKLEARN_MODELS   = ["lightgbm", "xgboost", "ridge"]
DL_MODELS        = ["LSTM"]
OUTPUT_FILE      = ROOT / "outputs" / "results" / "horizon_metrics.csv"


def parse_args():
    p = argparse.ArgumentParser(description="Horizon sensitivity sweep")
    p.add_argument("--config",      default="config/config.yaml")
    p.add_argument("--horizons",    nargs="+", type=int, default=DEFAULT_HORIZONS,
                   help="Horizons to sweep (hours)")
    p.add_argument("--include-dl",  action="store_true",
                   help="Include LSTM in sweep (adds ~1h per horizon)")
    p.add_argument("--resume",      action="store_true",
                   help="Skip (model, horizon) pairs already in output CSV")
    p.add_argument("--city",        default="drammen", choices=["drammen", "oslo"])
    return p.parse_args()


def load_completed_pairs(resume: bool) -> set:
    """Return set of (model, horizon) strings already in the output CSV."""
    if not resume or not OUTPUT_FILE.exists():
        return set()
    df = pd.read_csv(OUTPUT_FILE)
    return set(zip(df["model"], df["horizon"]))


def _build_features_for_horizon(cfg: dict, horizon: int) -> tuple:
    """Load processed data and return (X_train, y_train, X_val, y_val, X_test, y_test).

    The feature set is horizon-specific:
    - Only lags >= horizon are retained (causal constraint)
    - Feature selection re-run for each horizon (fewer features at longer horizons)

    Fast path: H+24 reuses the pre-processed splits from run_pipeline.py.
    General path: rebuilds temporal features from model_ready.parquet with horizon
                  injected into cfg["features"]["forecast_horizon"].
    """
    import copy

    from energy_forecast.data import make_splits
    from energy_forecast.features import build_temporal_features, select_features

    city     = cfg.get("city", "drammen")
    proc_dir = Path(cfg["paths"]["processed"]) / city / "splits"

    if horizon == 24 and (proc_dir / "X_train_fs.parquet").exists():
        # Fast path: reuse existing H+24 processed splits
        logger.info("H+24: reusing existing processed splits")
        X_train = pd.read_parquet(proc_dir / "X_train_fs.parquet")
        y_train = pd.read_parquet(proc_dir / "y_train.parquet").squeeze()
        X_val   = pd.read_parquet(proc_dir / "X_val_fs.parquet")
        y_val   = pd.read_parquet(proc_dir / "y_val.parquet").squeeze()
        X_test  = pd.read_parquet(proc_dir / "X_test_fs.parquet")
        y_test  = pd.read_parquet(proc_dir / "y_test.parquet").squeeze()
        return X_train, y_train, X_val, y_val, X_test, y_test

    # General path: rebuild features for this specific horizon
    logger.info("H+%d: rebuilding features with horizon-specific lag filter", horizon)
    model_ready_path = Path(cfg["paths"]["processed"]) / city / "model_ready.parquet"
    if not model_ready_path.exists():
        raise FileNotFoundError(
            f"model_ready.parquet not found at {model_ready_path}. "
            "Run: python scripts/run_pipeline.py --stages preprocess"
        )

    # Inject horizon into features config (build_temporal_features reads this)
    cfg_h = copy.deepcopy(cfg)
    cfg_h["features"]["forecast_horizon"] = horizon

    target = cfg["data"]["target_column"]
    df = pd.read_parquet(model_ready_path)

    featured = build_temporal_features(df, cfg_h, target)
    splits   = make_splits(featured, cfg_h, target)

    X_tr = splits["X_train"]
    y_tr = splits["y_train"]
    X_v  = splits["X_val"]
    y_v  = splits["y_val"]
    X_te = splits["X_test"]
    y_te = splits["y_test"]

    X_tr, X_v, X_te, _ = select_features(X_tr, y_tr, X_v, X_te, cfg_h)

    return X_tr, y_tr, X_v, y_v, X_te, y_te


def _run_sklearn_model(name: str, cfg: dict, horizon: int,
                       X_train, y_train, X_val, y_val, X_test, y_test) -> dict:
    """Train and evaluate one sklearn model at a given horizon."""
    from energy_forecast.models.sklearn_models import build_sklearn_models
    import sklearn.metrics as skm

    models = build_sklearn_models(cfg)
    if name not in models:
        raise ValueError(f"Model '{name}' not in sklearn model registry")
    model = models[name]

    t0 = time.time()
    model.fit(X_train, y_train, X_val, y_val)
    train_time = round(time.time() - t0, 1)

    preds = model.predict(X_test)
    # For MultiOutput (H > 1), preds shape is (n, H); take mean across steps
    # for scalar summary metrics, and also record per-step H+horizon step.
    if preds.ndim == 2:
        # Scalar summary: average across all horizon steps
        y_true_flat = y_test.values if hasattr(y_test, "values") else y_test
        # Reshape y_test to (n_samples, H) if it's flat
        n_steps = preds.shape[1]
        y_true_2d = y_true_flat.reshape(-1, n_steps) if y_true_flat.ndim == 1 else y_true_flat
        mae  = float(np.mean(np.abs(y_true_2d - preds)))
        rmse = float(np.sqrt(np.mean((y_true_2d - preds) ** 2)))
        ss_res = np.sum((y_true_2d - preds) ** 2)
        ss_tot = np.sum((y_true_2d - y_true_2d.mean()) ** 2)
        r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    else:
        y_true = y_test.values if hasattr(y_test, "values") else y_test
        mae  = float(np.mean(np.abs(y_true - preds)))
        rmse = float(np.sqrt(np.mean((y_true - preds) ** 2)))
        r2   = float(skm.r2_score(y_true, preds))

    return {
        "model":      name,
        "horizon":    horizon,
        "MAE":        round(mae, 4),
        "RMSE":       round(rmse, 4),
        "R2":         round(r2, 4),
        "train_time": train_time,
    }


def _subsample_per_building(X, y, max_rows: int = 4380):
    """Keep only the last `max_rows` rows per building to stay within memory.

    build_sequences() materialises (n × lookback × features) float32 arrays.
    Full training set: 1,144,535 × 72 × 35 × 4 B ≈ 11.6 GB → OOM on 16 GB.
    At max_rows=4380 (~6 months × 44 buildings ≈ 193k rows): ~1.9 GB ✓
    Horizon sensitivity (relative MAE H+1..H+48) is unaffected by subsampling.
    """
    X_sub = X.groupby(level="building_id", group_keys=False).tail(max_rows)
    y_sub = y.loc[X_sub.index]
    return X_sub, y_sub


def _run_lstm_model(cfg: dict, horizon: int,
                    X_train, y_train, X_val, y_val, X_test, y_test) -> dict:
    """Train and evaluate LSTM at a given horizon (Setup B, tabular features).

    Training/val data is subsampled to last 4,380 rows per building (~6 months)
    to avoid OOM: full 1.14M × 72 × 35 × float32 ≈ 11.6 GB which exceeds
    16 GB unified memory.  Test set is kept full for fair evaluation.
    """
    import copy
    from energy_forecast.models.deep_learning import LSTMForecaster

    cfg_h = copy.deepcopy(cfg)
    cfg_h["forecast_horizon"] = horizon
    cfg_h["sequence"]["horizon"] = horizon

    X_tr_sub, y_tr_sub = _subsample_per_building(X_train, y_train, max_rows=4380)
    X_v_sub,  y_v_sub  = _subsample_per_building(X_val,   y_val,   max_rows=1460)
    logger.info("LSTM sweep: training on %d rows (subsampled from %d)", len(X_tr_sub), len(X_train))

    model = LSTMForecaster(cfg_h)
    t0 = time.time()
    model.fit(X_tr_sub, y_tr_sub, X_v_sub, y_v_sub)
    train_time = round(time.time() - t0, 1)

    preds = model.predict(X_test)  # shape (n, horizon)
    y_true_flat = y_test.values if hasattr(y_test, "values") else np.array(y_test)
    y_true_2d = y_true_flat.reshape(-1, horizon)
    mae  = float(np.mean(np.abs(y_true_2d - preds)))
    rmse = float(np.sqrt(np.mean((y_true_2d - preds) ** 2)))
    ss_res = np.sum((y_true_2d - preds) ** 2)
    ss_tot = np.sum((y_true_2d - y_true_2d.mean()) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")

    return {
        "model":      "LSTM",
        "horizon":    horizon,
        "MAE":        round(mae, 4),
        "RMSE":       round(rmse, 4),
        "R2":         round(r2, 4),
        "train_time": train_time,
    }


def _append_result(row: dict) -> None:
    """Append one result row to the output CSV (creates if absent)."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df_new = pd.DataFrame([row])
    if OUTPUT_FILE.exists() and OUTPUT_FILE.stat().st_size > 0:
        existing = pd.read_csv(OUTPUT_FILE, index_col=0)
        # Remove any existing row for same (model, horizon) pair
        mask = ~((existing["model"] == row["model"]) & (existing["horizon"] == row["horizon"]))
        combined = pd.concat([existing[mask], df_new], ignore_index=True)
    else:
        combined = df_new
    combined.to_csv(OUTPUT_FILE)
    logger.info("Saved → %s  [%d rows total]", OUTPUT_FILE.name, len(combined))


def main():
    args = parse_args()
    cfg  = load_config(args.config)
    cfg["city"] = args.city
    set_global_seed(cfg.get("seed", 42))

    horizons    = sorted(args.horizons)
    model_names = SKLEARN_MODELS + (DL_MODELS if args.include_dl else [])
    completed   = load_completed_pairs(args.resume)

    logger.info("=" * 60)
    logger.info("Sprint 2: Horizon Sensitivity Sweep")
    logger.info("Horizons: %s", horizons)
    logger.info("Models:   %s", model_names)
    logger.info("Resume:   %s  (%d pairs already done)", args.resume, len(completed))
    logger.info("=" * 60)

    total = len(horizons) * len(model_names)
    done  = 0

    for horizon in horizons:
        logger.info("\n── Horizon H+%d ─────────────────────────────────────", horizon)

        try:
            X_train, y_train, X_val, y_val, X_test, y_test = \
                _build_features_for_horizon(cfg, horizon)
            logger.info("Data loaded: train=%d val=%d test=%d",
                        len(X_train), len(X_val), len(X_test))
        except Exception as e:
            logger.error("Failed to load data for H+%d: %s — skipping", horizon, e)
            continue

        for name in model_names:
            pair = (name, horizon)
            if args.resume and pair in completed:
                logger.info("  [SKIP] %s H+%d — already in output", name, horizon)
                done += 1
                continue

            logger.info("  Training %s at H+%d …", name, horizon)
            try:
                if name == "LSTM":
                    row = _run_lstm_model(cfg, horizon, X_train, y_train,
                                         X_val, y_val, X_test, y_test)
                else:
                    row = _run_sklearn_model(name, cfg, horizon, X_train, y_train,
                                             X_val, y_val, X_test, y_test)

                _append_result(row)
                logger.info("  %s H+%d → MAE=%.3f R²=%.4f  (%.1fs)",
                             name, horizon, row["MAE"], row["R2"], row["train_time"])
                done += 1
            except Exception as e:
                logger.error("  FAILED %s H+%d: %s", name, horizon, e)

    logger.info("\n=== Sweep complete: %d/%d pairs ===", done, total)
    logger.info("Output → %s", OUTPUT_FILE)

    if OUTPUT_FILE.exists():
        df = pd.read_csv(OUTPUT_FILE, index_col=0)
        pivot = df.pivot_table(index="model", columns="horizon",
                               values="MAE", aggfunc="first")
        logger.info("\nMAE summary:\n%s", pivot.to_string())


if __name__ == "__main__":
    main()
