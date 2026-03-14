#!/usr/bin/env python
"""
run_stacking_only.py
====================
Runs the OOF stacking ensemble (Setup A only) on pre-computed Drammen splits.

What it does:
  1. Loads saved feature-selected splits from data/processed/splits/
  2. Trains Ridge, LightGBM, XGBoost, RandomForest on full X_train
  3. Runs OOF (5 time-aware folds) to build meta-features for Ridge meta-learner
  4. Evaluates Stacking Ensemble on test set
  5. Appends "Stacking Ensemble (Ridge meta)" row to outputs/results/final_metrics.csv

Why run this separately?
  run_pipeline.py --stages training trains ALL DL models (LSTM/GRU/CNN-LSTM) before
  reaching the stacking step, which takes 2-4 hours.  This script skips all DL models
  and goes straight to stacking — total runtime ~30 min (dominated by RF OOF folds).

Usage
-----
    python scripts/run_stacking_only.py

Notes
-----
  - Safe to run alongside eval_tft_from_checkpoint.py (both only write to final_metrics.csv
    and each removes its own model row before appending — no race condition if they run
    on different model names).
  - Requires data/processed/splits/ to exist (run run_pipeline.py --stages features first
    if missing).
"""

import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import datetime

from energy_forecast.utils import load_config, set_global_seed, setup_logging  # noqa: E402

log_dir = ROOT / "outputs" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
_today = datetime.date.today().isoformat()
setup_logging(log_file=log_dir / f"stacking_only_{_today}.log")
logger = logging.getLogger(__name__)

MODEL_NAME = "Stacking Ensemble (Ridge meta)"


def main() -> None:
    cfg = load_config()
    set_global_seed(cfg.get("seed", 42))

    import pandas as pd

    from energy_forecast.evaluation import evaluate
    from energy_forecast.models.ensemble import StackingEnsemble
    from energy_forecast.models.sklearn_models import build_sklearn_models

    proc_dir = ROOT / "data" / "processed" / "splits"
    res_dir  = ROOT / "outputs" / "results"
    res_dir.mkdir(parents=True, exist_ok=True)

    # ── Load pre-computed splits ───────────────────────────────────────────────
    logger.info("Loading feature-selected splits from %s …", proc_dir)
    X_train = pd.read_parquet(proc_dir / "X_train_fs.parquet")
    y_train = pd.read_parquet(proc_dir / "y_train.parquet").squeeze()
    X_val   = pd.read_parquet(proc_dir / "X_val_fs.parquet")   # noqa: N806
    y_val   = pd.read_parquet(proc_dir / "y_val.parquet").squeeze()
    X_test  = pd.read_parquet(proc_dir / "X_test_fs.parquet")  # noqa: N806
    y_test  = pd.read_parquet(proc_dir / "y_test.parquet").squeeze()
    logger.info(
        "Splits loaded — train: %d | val: %d | test: %d rows, %d features",
        len(X_train), len(X_val), len(X_test), X_train.shape[1],
    )

    # ── Instantiate base models ───────────────────────────────────────────────
    # Only sklearn models — DL models are excluded from stacking because their
    # trimmed-length OOF predictions are incompatible with X_val for meta-features.
    # Build all sklearn models from config, then select the stacking base set.
    _STACKING_BASE = {"ridge", "lightgbm", "xgboost", "random_forest"}
    _all_models = build_sklearn_models(cfg)
    base_models = {v.name: v for k, v in _all_models.items() if k in _STACKING_BASE}
    logger.info("Base models: %s", list(base_models.keys()))

    # ── Pre-fit base models on full training set ──────────────────────────────
    # StackingEnsemble._oof_meta_features() trains fold *clones* only; the
    # original self.base_models instances remain unfitted.  predict() calls
    # the originals, so they must be fitted before the ensemble is created.
    # (run_pipeline.py avoids this by passing already-trained model objects.)
    logger.info("Pre-fitting base models on full training set …")
    for mname, model in base_models.items():
        t_fit = time.time()
        model.fit(X_train, y_train)
        logger.info("  %s fitted in %.1fs", mname, time.time() - t_fit)
    logger.info("All base models pre-fitted. Starting OOF stacking …")

    # ── Stacking ensemble ─────────────────────────────────────────────────────
    ensemble = StackingEnsemble(base_models, cfg)
    logger.info("Starting OOF stacking (oof_folds=%d) …", cfg["training"]["ensemble"]["oof_folds"])
    logger.info("Expected runtime: ~25–35 min (RF OOF dominates)")

    t0 = time.time()
    ensemble.fit(X_train, y_train, X_val, y_val)
    train_time_s = round(time.time() - t0, 1)
    logger.info("Stacking ensemble trained in %.1fs (%.1f min)", train_time_s, train_time_s / 60)

    # ── Evaluate on test set ───────────────────────────────────────────────────
    preds = ensemble.predict(X_test)
    test_bids = y_test.index.get_level_values("building_id")
    test_ts   = y_test.index.get_level_values("timestamp")
    res = evaluate(y_test, preds, ensemble.name,
                   building_ids=test_bids, timestamps=test_ts)
    res["train_time_s"] = train_time_s
    logger.info(
        "%s | MAE=%.3f kWh | RMSE=%.3f | R²=%.4f | n=%d",
        ensemble.name, res["MAE"], res["RMSE"], res["R2"], len(y_test),
    )

    # ── Append to final_metrics.csv ───────────────────────────────────────────
    csv_path = res_dir / "final_metrics.csv"
    res["model"] = ensemble.name
    res["n_samples"] = len(y_test)
    df_res = pd.DataFrame([res])

    if csv_path.exists():
        existing = pd.read_csv(csv_path, index_col=0)
        # Remove any stale stacking row
        existing = existing[~existing["model"].str.contains("Stacking", na=False)]
        combined = pd.concat([existing, df_res], ignore_index=True)
        combined.to_csv(csv_path)
        logger.info("Stacking row upserted in %s", csv_path)
    else:
        df_res.to_csv(csv_path)
        logger.info("Created %s with stacking row.", csv_path)

    logger.info("Done.\n%s", df_res[["model", "MAE", "RMSE", "R2"]].to_string(index=False))


if __name__ == "__main__":
    main()
