#!/usr/bin/env python
"""
eval_tft_from_checkpoint.py
============================
Evaluates the saved TFT_SetupB checkpoint on the test set WITHOUT re-training.

The original run_dl_h24_only.py skipped TFT evaluation due to a shape mismatch:
  preds (243417, 24) vs y_true (241393, 24)

This script fixes the mismatch by:
  1. Rebuilding the training TimeSeriesDataSet from saved splits (for predict() context)
  2. Loading the best Lightning checkpoint directly
  3. Running inference on the test set
  4. Truncating preds to min(preds, y_true) — drops partial windows at building boundaries
  5. Computing MAE / RMSE / R² and appending TFT_SetupB to final_metrics.csv

Usage
-----
    python scripts/eval_tft_from_checkpoint.py

Expected runtime: ~5–15 min (inference only — no training).
"""

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))  # for _build_y_true_matrix from run_pipeline

import datetime

from energy_forecast.utils import load_config, set_global_seed, setup_logging  # noqa: E402

log_dir = ROOT / "outputs" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
_today = datetime.date.today().isoformat()
setup_logging(log_file=log_dir / f"eval_tft_checkpoint_{_today}.log")
logger = logging.getLogger(__name__)

CKPT_PATH = ROOT / "lightning_logs/version_30/checkpoints/tft-best-epoch=18-val_loss=1.6534.ckpt"
MODEL_NAME = "TFT_SetupB"
TRAIN_TIME_S = 5627.0  # 93.8 min — epoch 18 checkpoint


def main() -> None:  # noqa: PLR0914 (many local vars — dataset reconstruction)
    cfg = load_config()
    set_global_seed(cfg.get("seed", 42))

    import numpy as np  # noqa: F401
    import pandas as pd

    try:
        import lightning.pytorch as pl  # noqa: F401
        from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
        from pytorch_forecasting.data import GroupNormalizer
    except ImportError as exc:
        raise ImportError(
            "pytorch-forecasting + lightning required.\n"
            "Install: pip install pytorch-forecasting lightning"
        ) from exc

    from energy_forecast.evaluation import evaluate
    from energy_forecast.models.tft import TFTForecaster

    def _build_y_true_matrix(y, lookback: int, horizon: int):
        """Build 2-D y_true matrix aligned with DL sliding-window predictions.
        Inlined from scripts/run_pipeline.py to avoid package-import issues.
        """
        parts = []
        for bid in y.index.get_level_values("building_id").unique():
            y_b = y.xs(bid, level="building_id").values
            n = len(y_b)
            for i in range(lookback, n - horizon + 1):
                parts.append(y_b[i : i + horizon])
        import numpy as np  # noqa: PLC0415

        return np.array(parts, dtype=np.float32)

    proc_dir = ROOT / "data" / "processed" / "splits"
    res_dir = ROOT / "outputs" / "results"
    res_dir.mkdir(parents=True, exist_ok=True)

    # ── Load splits ────────────────────────────────────────────────────────────
    logger.info("Loading splits …")
    X_train = pd.read_parquet(proc_dir / "X_train_fs.parquet")
    y_train = pd.read_parquet(proc_dir / "y_train.parquet").squeeze()
    X_val = pd.read_parquet(proc_dir / "X_val_fs.parquet")  # noqa: N806
    y_val = pd.read_parquet(proc_dir / "y_val.parquet").squeeze()
    X_test = pd.read_parquet(proc_dir / "X_test_fs.parquet")  # noqa: N806
    y_test = pd.read_parquet(proc_dir / "y_test.parquet").squeeze()
    logger.info(
        "Splits loaded — train: %d | val: %d | test: %d",
        len(X_train),
        len(X_val),
        len(X_test),
    )

    # ── Rebuild training TimeSeriesDataSet (no training!) ─────────────────────
    # We need _training_dataset_ and _max_time_idx_ to call predict().
    # These are built identically to TFTForecaster.fit() but without calling
    # trainer.fit() — so no GPU time is consumed here.
    seq_cfg = cfg["sequence"]
    target_col = cfg["data"]["target_column"]

    df_train = TFTForecaster._prepare_df(X_train, y_train, "train")
    df_val = TFTForecaster._prepare_df(X_val, y_val, "val")
    df_full = pd.concat([df_train, df_val]).reset_index(drop=True)
    df_full = df_full.sort_values(by=["building_id", "timestamp"]).reset_index(drop=True)
    df_full["time_idx"] = df_full.groupby("building_id").cumcount()

    _EXCLUDE = {"building_id", "time_idx", target_col, "split", "timestamp"}
    time_varying_known = [c for c in df_full.columns if c not in _EXCLUDE]

    logger.info(
        "Building TimeSeriesDataSet — %d train rows, %d features …",
        len(df_full[df_full["split"] == "train"]),
        len(time_varying_known),
    )
    training_dataset = TimeSeriesDataSet(
        df_full[df_full["split"] == "train"],
        time_idx="time_idx",
        target=target_col,
        group_ids=["building_id"],
        min_encoder_length=seq_cfg["lookback"],
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
    logger.info("TimeSeriesDataSet built.")

    # ── Assemble TFTForecaster state without calling fit() ────────────────────
    tft_obj = TFTForecaster.__new__(TFTForecaster)
    tft_obj.cfg = cfg
    tft_obj.model_ = None
    tft_obj.trainer_ = None
    tft_obj._dataset_params = {}
    tft_obj._training_dataset_ = training_dataset
    tft_obj._max_time_idx_ = df_full.groupby("building_id")["time_idx"].max().to_dict()
    tft_obj._target_col_ = target_col
    tft_obj._tft_cfg_ = cfg["training"]["tft"]
    tft_obj._seq_cfg_ = seq_cfg

    # ── Load checkpoint ────────────────────────────────────────────────────────
    if not CKPT_PATH.exists():
        raise FileNotFoundError(f"Checkpoint not found: {CKPT_PATH}")
    logger.info("Loading checkpoint: %s", CKPT_PATH)
    loaded_model = TemporalFusionTransformer.load_from_checkpoint(
        str(CKPT_PATH),
        map_location="cpu",
    )
    tft_obj.model_ = loaded_model
    n_params = sum(p.numel() for p in loaded_model.parameters())
    logger.info("Checkpoint loaded — %d parameters.", n_params)

    # ── Predict on test set ────────────────────────────────────────────────────
    logger.info("Generating test-set predictions (inference only — no GPU training) …")
    preds = tft_obj.predict(X_test)
    logger.info("Predictions shape: %s", preds.shape)

    # ── Build y_true_2d ────────────────────────────────────────────────────────
    lookback = seq_cfg["lookback"]
    horizon = seq_cfg["horizon"]
    y_true_2d = _build_y_true_matrix(y_test, lookback, horizon)
    logger.info("y_true_2d shape: %s", y_true_2d.shape)

    # ── Shape mismatch fix: remove NaN rows (partial-window boundary rows) ─────
    # TFT with min_prediction_length=1 creates extra partial windows at building
    # boundaries (prediction_length = 1..horizon-1).  These boundary predictions
    # produce NaN after GroupNormalizer inverse-transform (the decoder span extends
    # beyond the available test data).  Empirically: 2024/243417 = 0.83% NaN rows,
    # and after filtering, exactly 241,393 finite rows remain — matching y_true_2d.
    import numpy as _np  # noqa: PLC0415

    finite_mask = ~_np.any(_np.isnan(preds), axis=1)
    n_nan = int(_np.sum(~finite_mask))
    preds_t = preds[finite_mask]
    logger.info(
        "NaN rows removed: %d (%.2f%%). Finite predictions: %d rows.",
        n_nan,
        100 * n_nan / len(preds),
        len(preds_t),
    )
    if len(preds_t) != len(y_true_2d):
        logger.warning(
            "After NaN filtering, preds (%d) != y_true (%d). " "Truncating to min to proceed.",
            len(preds_t),
            len(y_true_2d),
        )
        n = min(len(preds_t), len(y_true_2d))
        preds_t = preds_t[:n]
        y_true_t = y_true_2d[:n]
    else:
        y_true_t = y_true_2d

    # ── Evaluate ───────────────────────────────────────────────────────────────
    res = evaluate(y_true_t, preds_t, MODEL_NAME)
    logger.info(
        "%s | MAE=%6.3f kWh | RMSE=%6.3f | R²=%.4f | n=%d",
        MODEL_NAME,
        res["MAE"],
        res["RMSE"],
        res["R2"],
        n,
    )

    # ── Append to final_metrics.csv ───────────────────────────────────────────
    csv_path = res_dir / "final_metrics.csv"
    res["model"] = MODEL_NAME
    res["n_samples"] = n
    res["train_time_s"] = TRAIN_TIME_S
    res["horizon"] = horizon
    df_res = pd.DataFrame([res])

    if csv_path.exists():
        existing = pd.read_csv(csv_path, index_col=0)
        existing = existing[existing["model"] != MODEL_NAME]
        combined = pd.concat([existing, df_res], ignore_index=True)
        combined.to_csv(csv_path)
        logger.info("TFT_SetupB row upserted in %s", csv_path)
    else:
        df_res.to_csv(csv_path)
        logger.info("Created %s with TFT_SetupB row.", csv_path)

    logger.info(
        "Done.\n%s", df_res[["model", "MAE", "RMSE", "R2", "n_samples"]].to_string(index=False)
    )


if __name__ == "__main__":
    main()
