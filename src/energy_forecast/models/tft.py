"""
models.tft
==========
Temporal Fusion Transformer (TFT) wrapper using PyTorch Forecasting.

TFT is the most powerful model in this project and the most computationally
expensive (flagged as "slow" in config.yaml).  It provides:
- Variable selection networks (automatic feature importance)
- Multi-head self-attention for long-range dependencies
- Interpretable attention weights for each building

Computational note
------------------
TFT attention: O(n · T² · H) — quadratic in sequence length T.
For lookback=72, this is ~5184 operations per sample per head.
The accuracy gain over GRU justifies this cost in the full-run scenario.

Usage
-----
    from energy_forecast.models.tft import TFTForecaster
    model = TFTForecaster(cfg)
    model.fit(X_train, y_train, X_val, y_val)
    preds = model.predict(X_test)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from .base import BaseForecaster

logger = logging.getLogger(__name__)


class TFTForecaster(BaseForecaster):
    """Temporal Fusion Transformer via pytorch-forecasting."""

    name = "TFT"

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        self.model_ = None
        self.trainer_ = None
        self._dataset_params: dict = {}

    def fit(
        self,
        X_train: pd.DataFrame,  # noqa: N803
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,  # noqa: N803
        y_val: pd.Series | None = None,
        **kwargs: Any,
    ) -> TFTForecaster:
        """Train the TFT model.

        Note: TFT requires the full time-series (not pre-sliced windows) so
        it builds its own TimeSeriesDataSet internally.
        """
        try:
            # pytorch-forecasting 1.3+ uses lightning.pytorch internally.
            # Using pytorch_lightning (the legacy wrapper) causes an isinstance
            # check failure in Trainer.fit() even though both expose LightningModule
            # by the same name — they are different class objects.
            # Using lightning.pytorch directly ensures the same LightningModule
            # that TemporalFusionTransformer inherits from is the one Trainer checks.
            import lightning.pytorch as pl
            import torch  # noqa: F401
            from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
            from pytorch_forecasting.data import GroupNormalizer
            from pytorch_forecasting.metrics import MAE as TFT_MAE
        except ImportError as e:
            raise ImportError(
                "PyTorch Forecasting is required for TFT.\n"
                "Install: pip install pytorch-forecasting lightning"
            ) from e

        tft_cfg  = self.cfg["training"]["tft"]
        seq_cfg  = self.cfg["sequence"]
        seed     = self.cfg.get("seed", 42)
        pl.seed_everything(seed)

        # Combine splits into a single DataFrame for TimeSeriesDataSet
        df_train = self._prepare_df(X_train, y_train, "train")
        df_val   = self._prepare_df(X_val, y_val, "val") if X_val is not None else df_train.iloc[:0]

        df_full = pd.concat([df_train, df_val]).reset_index(drop=True)
        # Sort by building + time before assigning time_idx.
        # pd.concat preserves the within-split order but does NOT globally sort,
        # so cumcount() without sorting produces scrambled time indices which
        # causes TimeSeriesDataSet to fail validation.
        df_full = df_full.sort_values(by=["building_id", "timestamp"]).reset_index(drop=True)
        df_full["time_idx"] = df_full.groupby("building_id").cumcount()

        target_col = self.cfg["data"]["target_column"]
        # BUG-C3: "timestamp" must be excluded from time_varying_known_reals.
        # It is a non-stationary monotonically increasing value — StandardScaler
        # (or GroupNormalizer) fits to the training range, so test-set timestamps
        # fall outside the training distribution causing OOD saturation in TFT
        # activations.  time_idx already provides positional encoding; cyclical
        # features (hour_sin, day_of_week_sin, …) already handle seasonality.
        _EXCLUDE = {"building_id", "time_idx", target_col, "split", "timestamp"}  # noqa: N806
        time_varying_known = [c for c in df_full.columns if c not in _EXCLUDE]

        training_dataset = TimeSeriesDataSet(
            df_full[df_full["split"] == "train"],
            time_idx="time_idx",
            target=target_col,
            group_ids=["building_id"],
            # min_encoder_length == max_encoder_length (= lookback) so TFT produces
            # exactly the same number of windows as build_sequences() and
            # _build_y_true_matrix().  If min < max, TimeSeriesDataSet creates
            # (max - min) extra short-encoder windows per building, causing a shape
            # mismatch in the H+24 evaluation loop.
            min_encoder_length=seq_cfg["lookback"],
            max_encoder_length=seq_cfg["lookback"],
            min_prediction_length=1,
            max_prediction_length=seq_cfg["horizon"],
            time_varying_known_reals=time_varying_known,
            time_varying_unknown_reals=[target_col],
            target_normalizer=GroupNormalizer(
                groups=["building_id"],
                transformation="softplus",  # Thesis value: prevents NaN gradients when
                center=True,                # target values are near zero (StandardScaler
            ),                              # default causes loss errors on low-load periods)
            add_relative_time_idx=True,
            add_target_scales=True,
        )

        val_dataset = TimeSeriesDataSet.from_dataset(
            training_dataset,
            df_full[df_full["split"] == "val"],
            predict=True,
            stop_randomization=True,
        )

        train_loader = training_dataset.to_dataloader(
            train=True, batch_size=tft_cfg["batch_size"],
            num_workers=0,   # macOS "spawn" multiprocessing adds IPC overhead that
                             # hurts in-memory datasets — synchronous is faster here.
                             # Linux/CUDA users can safely raise this to 4+.
        )
        val_loader = val_dataset.to_dataloader(
            train=False, batch_size=tft_cfg["batch_size"] * 2,
            num_workers=0,
        )

        # Store for test-time prediction (predict() must continue time_idx)
        self._training_dataset_ = training_dataset
        self._max_time_idx_: dict[str, int] = (
            df_full.groupby("building_id")["time_idx"].max().to_dict()
        )
        self._target_col_ = target_col
        self._tft_cfg_ = tft_cfg
        self._seq_cfg_ = seq_cfg   # needed in predict() for horizon

        tft = TemporalFusionTransformer.from_dataset(
            training_dataset,
            learning_rate=tft_cfg["learning_rate"],
            hidden_size=tft_cfg["hidden_size"],
            attention_head_size=tft_cfg["attention_head_size"],
            dropout=tft_cfg["dropout"],
            hidden_continuous_size=tft_cfg["hidden_continuous_size"],
            loss=TFT_MAE(),
            log_interval=10,
            reduce_on_plateau_patience=4,
        )
        logger.info(
            "TFT parameters: %d  (this is the most complex model — patience!)",
            sum(p.numel() for p in tft.parameters()),
        )

        class _BatchProgressLogger(pl.Callback):
            """Heartbeat every N batches — prevents radio silence during long epochs.

            With enable_progress_bar=False the log is completely silent between
            epoch-end callbacks.  A single epoch can take 20-45 min, giving the
            operator no signal that the GPU is making progress.  This callback
            writes a line every `log_every_n_batches` batches with:
              - epoch / batch counters and % complete
              - live training loss
            so the operator can confirm forward progress and estimate time remaining.
            """
            def __init__(self, log_every_n_batches: int = 50):
                self.n = log_every_n_batches

            def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
                if (batch_idx + 1) % self.n != 0:
                    return
                total    = trainer.num_training_batches
                pct      = 100.0 * (batch_idx + 1) / total if total else 0.0
                # Loss function is TFT_MAE() so train_loss IS train_MAE.
                train_mae = (
                    outputs["loss"].item()
                    if isinstance(outputs, dict) and "loss" in outputs
                    else float("nan")
                )
                # Best val_MAE seen so far (populated after each validation epoch).
                # Falls back to sanity-check value until epoch 1 validation completes.
                cb = trainer.callback_metrics
                val_mae = (
                    cb.get("val_MAE", cb.get("sanity_check_MAE", None))
                )
                val_str = f" | val_MAE {val_mae:.4f}" if val_mae is not None else ""
                logger.info(
                    "TFT | epoch %d | batch %d/%d (%.0f%%) | train_MAE %.4f%s",
                    trainer.current_epoch + 1,
                    batch_idx + 1,
                    total,
                    pct,
                    train_mae,
                    val_str,
                )

        class _EpochLogger(pl.Callback):
            """Write one clean summary line at the end of each validation epoch."""
            def on_validation_epoch_end(self, trainer, pl_module):  # noqa: N802
                ep      = trainer.current_epoch
                metrics = {k: f"{v:.4f}" for k, v in trainer.callback_metrics.items()}
                logger.info("TFT epoch %d complete | %s", ep, metrics)

        # ModelCheckpoint: save the best val_loss epoch, not just the last.
        # Without this, Lightning auto-saves only the final epoch — if EarlyStopping
        # triggers or training ends with a late degradation, the best weights are lost.
        ckpt_cb = pl.callbacks.ModelCheckpoint(
            monitor="val_loss",
            mode="min",
            save_top_k=1,
            filename="tft-best-{epoch:02d}-{val_loss:.4f}",
            verbose=True,
        )

        callbacks = [
            pl.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=10,
                mode="min",
                verbose=True,  # prints "Metric val_loss improved..." to stdout
            ),
            ckpt_cb,
            # NOTE: LearningRateMonitor was removed — it requires logger != False.
            # LR reduction still occurs via reduce_on_plateau_patience inside TFT's
            # configure_optimizers (set via TemporalFusionTransformer.from_dataset()).
            _BatchProgressLogger(log_every_n_batches=50),  # heartbeat every 50 batches
            _EpochLogger(),
        ]
        trainer = pl.Trainer(
            max_epochs=tft_cfg["max_epochs"],
            gradient_clip_val=tft_cfg["gradient_clip_val"],
            callbacks=callbacks,
            enable_progress_bar=False,  # avoids \r-per-batch flood in log files
            logger=True,               # MUST be True: enables EarlyStopping verbose
                                       # messages ("Metric val_loss improved ...").
                                       # With logger=False those messages are suppressed.
            accelerator="auto",        # explicitly request auto-detect: MPS on Apple
            devices=1,                 # Silicon, CUDA on NVIDIA, CPU as fallback.
                                       # Without this, PL sometimes silently falls back
                                       # to CPU, making each epoch take hours.
        )

        logger.info("Training TFT (slow model — use --skip-slow during development) ...")
        trainer.fit(tft, train_dataloaders=train_loader, val_dataloaders=val_loader)

        self.model_   = tft
        self.trainer_ = trainer
        self._val_loader = val_loader
        self.best_checkpoint_path_ = ckpt_cb.best_model_path
        logger.info("Best checkpoint → %s", self.best_checkpoint_path_)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        """Predict on test data.

        Builds a TimeSeriesDataSet from X by continuing the time_idx from
        where training+validation ended, then creates a test dataloader and
        runs inference.  Returns one prediction per test timestep (after
        the initial lookback window per building).
        """
        if self.model_ is None:
            raise RuntimeError("Call .fit() before .predict()")

        try:
            from pytorch_forecasting import TimeSeriesDataSet
        except ImportError as e:
            raise ImportError("pytorch-forecasting required for TFT.") from e

        # Build test DataFrame in the same format as fit()
        y_placeholder = pd.Series(
            np.zeros(len(X)),
            index=X.index,
            name=self._target_col_,
        )
        df_test = self._prepare_df(X, y_placeholder, "test")

        # Assign time_idx continuing from training+val per building
        def _continuing_time_idx(g: pd.DataFrame) -> pd.Series:
            bid = g["building_id"].iloc[0]
            offset = int(self._max_time_idx_.get(bid, -1)) + 1
            return pd.Series(range(offset, offset + len(g)), index=g.index)

        df_test["time_idx"] = (
            df_test
            .groupby("building_id", group_keys=False)
            .apply(_continuing_time_idx)
        )

        # predict=False creates ALL valid sliding encoder/decoder windows through
        # the test set.  With H+1: (N_test - max_encoder_length) windows per
        # building — matches _trim_dl_targets(y_test, lookback).
        # predict=True would return only ONE window per building (last position),
        # giving just num_buildings predictions total — wrong for evaluation.
        test_dataset = TimeSeriesDataSet.from_dataset(
            self._training_dataset_,
            df_test,
            predict=False,
            stop_randomization=True,
        )
        test_loader = test_dataset.to_dataloader(
            train=False,
            batch_size=self._tft_cfg_["batch_size"] * 2,
            num_workers=0,
        )

        # BUG-FIX (2026-03-02): trainer_.predict() returns raw Lightning output
        # dicts, not tensors — calling .numpy() on a dict crashes immediately.
        # The correct API is pytorch-forecasting's model_.predict(), which:
        #   1. Handles GroupNormalizer denormalisation internally → output in kWh
        #   2. Returns a tensor of shape (n_samples, max_prediction_length)
        #   3. Moves output to CPU automatically
        # trainer_kwargs passes accelerator config so MPS/CUDA is used if available.
        raw_preds = self.model_.predict(
            test_loader,
            return_y=False,
            trainer_kwargs={
                "accelerator": "auto",
                "devices": 1,
                "enable_progress_bar": False,
                "logger": False,
            },
        )  # tensor: (n_samples, horizon), already denormalised to kWh
        preds = raw_preds.cpu().numpy()
        horizon = self._seq_cfg_.get("horizon", 1)
        from energy_forecast.models.deep_learning import reshape_dl_predictions
        return reshape_dl_predictions(preds, horizon)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    @staticmethod
    def _prepare_df(X: pd.DataFrame, y: pd.Series, split: str) -> pd.DataFrame:  # noqa: N803
        df = X.copy()
        df[y.name or "target"] = y.values
        df["split"] = split
        df = df.reset_index()
        return df
