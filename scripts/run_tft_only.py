#!/usr/bin/env python
"""
run_tft_only.py
===============
Standalone TFT training and evaluation script.

Loads pre-computed feature-selected splits from data/processed/splits/
(created by run_pipeline.py Stage 2) so we don't have to re-run EDA
or feature engineering.

Appends the TFT result to outputs/results/final_metrics.csv and prints
a full results table. Safe to run concurrently with other work — it does
not overwrite sklearn or DL results, only appends/updates the TFT row.

Usage
-----
    python scripts/run_tft_only.py

Estimated runtime: 2–6 hours (depends on early stopping, MPS GPU speeds up).
"""

import logging
import sys
import time
from pathlib import Path

# ── path setup ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import datetime
from energy_forecast.utils import load_config, setup_logging, set_global_seed

log_dir = ROOT / "outputs" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
_today = datetime.date.today().isoformat()
# Date-stamped log: run_tft_only_2026-03-02.log etc.
# NOTE: Do NOT also redirect stdout to this file at the shell — setup_logging
# already adds a FileHandler. Double-redirecting duplicates every log line.
setup_logging(log_file=log_dir / f"run_tft_only_{_today}.log")
logger = logging.getLogger(__name__)


def main() -> None:
    cfg = load_config()
    set_global_seed(cfg.get("seed", 42))

    import pandas as pd
    import numpy as np

    proc_dir = ROOT / "data" / "processed" / "splits"
    res_dir  = ROOT / "outputs" / "results"
    res_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading pre-computed feature-selected splits …")
    X_train = pd.read_parquet(proc_dir / "X_train_fs.parquet")
    y_train = pd.read_parquet(proc_dir / "y_train.parquet").squeeze()
    X_val   = pd.read_parquet(proc_dir / "X_val_fs.parquet")
    y_val   = pd.read_parquet(proc_dir / "y_val.parquet").squeeze()
    X_test  = pd.read_parquet(proc_dir / "X_test_fs.parquet")
    y_test  = pd.read_parquet(proc_dir / "y_test.parquet").squeeze()
    logger.info(
        "Splits loaded — train: %d rows | val: %d rows | test: %d rows",
        len(X_train), len(X_val), len(X_test),
    )

    # ── TFT training ─────────────────────────────────────────────────────────
    from energy_forecast.models.tft import TFTForecaster
    from energy_forecast.evaluation import evaluate, compare_models

    tft = TFTForecaster(cfg)
    logger.info("Starting TFT training — this will take 2–6 hours …")
    logger.info("Parameters: %s", sum(p.numel() for p in tft.model_.parameters()) if hasattr(tft, "model_") and tft.model_ is not None else "not yet built")

    t0 = time.time()
    tft.fit(X_train, y_train, X_val, y_val)
    train_time_s = round(time.time() - t0, 1)
    logger.info("TFT training complete in %.1f seconds (%.1f min)", train_time_s, train_time_s / 60)

    # ── Prediction & evaluation ───────────────────────────────────────────────
    from scripts.run_pipeline import _trim_dl_targets  # noqa: PLC0415

    lookback = cfg.get("sequence", {}).get("lookback", 72)
    logger.info("Generating TFT predictions on test set …")
    preds = tft.predict(X_test)

    # TFT may return full-length or trimmed predictions
    if len(preds) == len(y_test):
        y_tft = y_test
    else:
        y_tft = _trim_dl_targets(y_test, lookback)
        if len(preds) != len(y_tft):
            raise ValueError(
                f"TFT prediction length {len(preds)} does not match "
                f"y_test ({len(y_test)}) or trimmed y_test ({len(y_tft)})."
            )

    result = evaluate(y_tft, preds, "TFT")
    # evaluate() returns key "R2" (not "R²") — the Unicode key only appears in
    # compare_models() display formatting.  Using "R²" here causes a KeyError
    # after a 6-hour training run (BUG-C1 from pipeline audit 2026-03-02).
    logger.info(
        "TFT | MAE=%6.4f | RMSE=%6.4f | MAPE=%6.2f%% | R²=%6.4f | n=%d | train_time=%.0fs",
        result["MAE"], result["RMSE"], result["MAPE"], result["R2"],
        len(y_tft), train_time_s,
    )

    # ── Save model checkpoint ─────────────────────────────────────────────────
    # Lightning checkpoint preserves weights, optimizer state, and epoch number
    # so training can be resumed or predictions re-run without re-training.
    model_dir = ROOT / "outputs" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = model_dir / f"tft_{_today}.ckpt"
    tft.trainer_.save_checkpoint(str(checkpoint_path))
    logger.info("TFT model checkpoint saved → %s", checkpoint_path)

    # ── Append to final_metrics.csv ───────────────────────────────────────────
    csv_path = res_dir / "final_metrics.csv"
    if csv_path.exists():
        existing = pd.read_csv(csv_path, index_col=0)
        # Remove any stale TFT row before appending the new one
        existing = existing[existing["Model"] != "TFT"]
        tft_row = pd.DataFrame([{**result, "n_samples": len(y_tft), "train_time_s": train_time_s}])
        updated = pd.concat([existing, tft_row], ignore_index=True)
        # Re-sort by MAE ascending
        updated = updated.sort_values("MAE").reset_index(drop=True)
        updated.to_csv(csv_path)
        logger.info("TFT result appended to %s", csv_path)
        logger.info("\n%s", updated.to_string())
    else:
        logger.warning("final_metrics.csv not found — writing TFT-only file.")
        tft_row = pd.DataFrame([{**result, "n_samples": len(y_tft), "train_time_s": train_time_s}])
        tft_row.to_csv(csv_path)

    logger.info("Done.")


if __name__ == "__main__":
    main()
