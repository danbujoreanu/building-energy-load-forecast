#!/usr/bin/env python
"""
recover_tft_h1_prediction.py
==============================
One-off recovery script for the H+1 TFT run (2026-03-02).

Context
-------
run_tft_only.py trained TFT for 20 epochs (660 min) and stopped at max_epochs.
The process then crashed during predict() because trainer_.predict() returns raw
Lightning output dicts, not tensors — calling .numpy() on a dict raised AttributeError.

The crash happened silently (exception went to stderr, not the log file).

Available checkpoint
--------------------
Lightning auto-saved the last epoch (epoch=19, val_MAE=0.5905 on normalised scale)
at:  lightning_logs/version_4/checkpoints/epoch=19-step=44700.ckpt

NOTE: The BEST epoch was epoch=18 (val_MAE=0.4586) but no ModelCheckpoint callback
was configured, so only the last epoch was saved.  This has been fixed in tft.py for
all future runs.  We use the available checkpoint (epoch=19) for H+1 documentation.

What this script does
---------------------
1. Reconstructs the TFT internal state from scratch (same config as the original run)
2. Loads the model weights from epoch=19 checkpoint (no retraining)
3. Runs prediction on X_test using the fixed model_.predict() API
4. Evaluates and appends the TFT row to outputs/results/final_metrics.csv

Usage
-----
    python scripts/recover_tft_h1_prediction.py
"""

import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from energy_forecast.utils import load_config, set_global_seed, setup_logging  # noqa: E402

log_dir = ROOT / "outputs" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
setup_logging(log_file=log_dir / "recover_tft_h1_2026-03-02.log")
logger = logging.getLogger(__name__)

CHECKPOINT = ROOT / "lightning_logs" / "version_4" / "checkpoints" / "epoch=19-step=44700.ckpt"


def main() -> None:
    if not CHECKPOINT.exists():
        logger.error("Checkpoint not found: %s", CHECKPOINT)
        sys.exit(1)

    cfg = load_config()
    set_global_seed(cfg.get("seed", 42))

    import numpy as np
    import pandas as pd
    from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
    from pytorch_forecasting.data import GroupNormalizer

    proc_dir = ROOT / "data" / "processed" / "splits"
    res_dir = ROOT / "outputs" / "results"
    res_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading feature-selected splits …")
    X_train = pd.read_parquet(proc_dir / "X_train_fs.parquet")  # noqa: N806
    y_train = pd.read_parquet(proc_dir / "y_train.parquet").squeeze()
    X_val = pd.read_parquet(proc_dir / "X_val_fs.parquet")  # noqa: N806
    y_val = pd.read_parquet(proc_dir / "y_val.parquet").squeeze()
    X_test = pd.read_parquet(proc_dir / "X_test_fs.parquet")  # noqa: N806
    y_test = pd.read_parquet(proc_dir / "y_test.parquet").squeeze()

    tft_cfg = cfg["training"]["tft"]
    seq_cfg = cfg["sequence"]
    target_col = cfg["data"]["target_column"]

    # ── Rebuild the same TimeSeriesDataSet used in the original fit() ─────────
    # This is required to create the test dataset and load the model.
    # Must use IDENTICAL parameters to the original training run.
    logger.info("Reconstructing TimeSeriesDataSet (same params as original fit) …")

    def _prepare_df(X: pd.DataFrame, y: pd.Series, split: str) -> pd.DataFrame:  # noqa: N803
        df = X.copy()
        df[y.name or "target"] = y.values
        df["split"] = split
        return df.reset_index()

    df_train = _prepare_df(X_train, y_train, "train")
    df_val = _prepare_df(X_val, y_val, "val")
    df_full = (
        pd.concat([df_train, df_val])
        .sort_values(["building_id", "timestamp"])
        .reset_index(drop=True)
    )
    df_full["time_idx"] = df_full.groupby("building_id").cumcount()

    # NOTE: The original run_tft_only.py training did NOT exclude "timestamp" from
    # time_varying_known_reals (BUG-C3 was fixed in tft.py but not before this training).
    # The checkpoint (epoch=19) therefore expects 36 time_varying_known features including
    # "timestamp".  We intentionally retain timestamp here to match the checkpoint exactly.
    _EXCLUDE = {"building_id", "time_idx", target_col, "split"}  # noqa: N806
    time_varying_known = [c for c in df_full.columns if c not in _EXCLUDE]

    training_dataset = TimeSeriesDataSet(
        df_full[df_full["split"] == "train"],
        time_idx="time_idx",
        target=target_col,
        group_ids=["building_id"],
        min_encoder_length=seq_cfg["lookback"] // 2,
        max_encoder_length=seq_cfg["lookback"],
        min_prediction_length=1,
        max_prediction_length=seq_cfg["horizon"],
        time_varying_known_reals=time_varying_known,
        time_varying_unknown_reals=[target_col],
        target_normalizer=GroupNormalizer(
            groups=["building_id"],
            transformation="softplus",
            center=True,
        ),
        add_relative_time_idx=True,
        add_target_scales=True,
    )
    logger.info("TimeSeriesDataSet rebuilt — %d training samples", len(training_dataset))

    # ── Load model from checkpoint ────────────────────────────────────────────
    logger.info("Loading TFT from checkpoint: %s", CHECKPOINT)
    model = TemporalFusionTransformer.load_from_checkpoint(str(CHECKPOINT))
    model.eval()
    logger.info("Model loaded — %d parameters", sum(p.numel() for p in model.parameters()))

    # ── Build test dataset (continuing time_idx from train+val) ───────────────
    logger.info("Building test dataset …")
    max_time_idx = df_full.groupby("building_id")["time_idx"].max().to_dict()

    y_placeholder = pd.Series(np.zeros(len(X_test)), index=X_test.index, name=target_col)
    df_test = _prepare_df(X_test, y_placeholder, "test")

    def _continuing_idx(g: pd.DataFrame) -> pd.Series:
        bid = g["building_id"].iloc[0]
        offset = int(max_time_idx.get(bid, -1)) + 1
        return pd.Series(range(offset, offset + len(g)), index=g.index)

    df_test["time_idx"] = df_test.groupby("building_id", group_keys=False).apply(_continuing_idx)

    # predict=False (training-style windows) — creates ALL valid encoder/decoder
    # windows by sliding through the test set.  With H+1 this yields
    # (N_test - max_encoder_length) windows per building, matching
    # _trim_dl_targets(y_test, lookback).
    # predict=True returns only ONE window per building (the last), giving 44
    # predictions total — wrong for evaluation.
    test_dataset = TimeSeriesDataSet.from_dataset(
        training_dataset,
        df_test,
        predict=False,
        stop_randomization=True,
    )
    test_loader = test_dataset.to_dataloader(
        train=False,
        batch_size=tft_cfg["batch_size"] * 2,
        num_workers=0,
    )
    logger.info("Test dataloader ready — %d batches", len(test_loader))

    # ── Predict ───────────────────────────────────────────────────────────────
    logger.info("Running TFT inference on test set (this may take 10-20 min) …")
    t0 = time.time()
    raw_preds = model.predict(
        test_loader,
        return_y=False,
        trainer_kwargs={
            "accelerator": "auto",
            "devices": 1,
            "enable_progress_bar": False,
            "logger": False,
        },
    )
    infer_time = time.time() - t0
    logger.info("Inference complete in %.1f seconds", infer_time)

    preds = raw_preds.cpu().numpy()
    horizon = seq_cfg.get("horizon", 1)
    preds = preds.flatten() if horizon == 1 else preds

    # ── Align y_test (TFT may return fewer rows if encoder context is limited) ─
    def _trim_dl_targets(y, lookback: int):
        """Drop the first ``lookback`` rows per building from y_true."""
        parts = []
        for bid in y.index.get_level_values("building_id").unique():
            y_b = y.xs(bid, level="building_id")
            parts.append(y_b.iloc[lookback:])
        return pd.concat(parts)

    lookback = seq_cfg.get("lookback", 72)
    if len(preds) == len(y_test):
        y_tft = y_test
    else:
        y_tft = _trim_dl_targets(y_test, lookback)
        if len(preds) != len(y_tft):
            raise ValueError(
                f"Prediction length {len(preds)} ≠ y_test ({len(y_test)}) "
                f"or trimmed ({len(y_tft)})"
            )

    # ── Evaluate ──────────────────────────────────────────────────────────────
    from energy_forecast.evaluation import evaluate

    tft_bids = y_tft.index.get_level_values("building_id")
    tft_ts = y_tft.index.get_level_values("timestamp")
    result = evaluate(y_tft, preds, "TFT", building_ids=tft_bids, timestamps=tft_ts)

    logger.info(
        "TFT H+1 | MAE=%.4f kWh | RMSE=%.4f | MAPE=%.2f%% | R²=%.4f | n=%d",
        result["MAE"],
        result["RMSE"],
        result["MAPE"],
        result["R2"],
        len(y_tft),
    )
    logger.info(
        "NOTE: Checkpoint is epoch=19 (last epoch, val_MAE=0.5905 normalised). "
        "Best epoch was epoch=18 (val_MAE=0.4586) — not saved due to missing "
        "ModelCheckpoint callback (now fixed for future runs)."
    )

    # ── Append to final_metrics.csv ───────────────────────────────────────────
    csv_path = res_dir / "final_metrics.csv"
    train_time_s = 39648.6  # from run_tft_only log: "660.8 min"

    if csv_path.exists():
        existing = pd.read_csv(csv_path, index_col=0)
        existing = existing[existing["Model"] != "TFT"]
        tft_row = pd.DataFrame([{**result, "n_samples": len(y_tft), "train_time_s": train_time_s}])
        updated = (
            pd.concat([existing, tft_row], ignore_index=True)
            .sort_values("MAE")
            .reset_index(drop=True)
        )
        updated.to_csv(csv_path)
        logger.info("TFT result appended → %s", csv_path)
        logger.info(
            "\n%s", updated[["Model", "MAE", "RMSE", "MAPE", "R²", "n_samples"]].to_string()
        )
    else:
        tft_row = pd.DataFrame([{**result, "n_samples": len(y_tft), "train_time_s": train_time_s}])
        tft_row.to_csv(csv_path)
        logger.warning("final_metrics.csv not found — wrote TFT-only file.")

    # ── Save checkpoint copy to outputs/models/ ───────────────────────────────
    import datetime
    import shutil

    model_dir = ROOT / "outputs" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    dest = model_dir / f"drammen_TFT_h1_{datetime.date.today().isoformat()}_epoch19.ckpt"
    shutil.copy2(CHECKPOINT, dest)
    logger.info("Checkpoint copied → %s", dest)

    logger.info("Recovery complete.")


if __name__ == "__main__":
    main()
