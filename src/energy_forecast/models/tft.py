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
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | None = None,
        **kwargs: Any,
    ) -> "TFTForecaster":
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
            import torch
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
        df_full["time_idx"] = df_full.groupby("building_id").cumcount()

        target_col = self.cfg["data"]["target_column"]
        time_varying_known = [
            c for c in df_full.columns
            if c not in ["building_id", "time_idx", target_col, "split"]
        ]

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
            target_normalizer=GroupNormalizer(groups=["building_id"]),
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
            train=True, batch_size=tft_cfg["batch_size"], num_workers=0
        )
        val_loader = val_dataset.to_dataloader(
            train=False, batch_size=tft_cfg["batch_size"] * 2, num_workers=0
        )

        # Store for test-time prediction (predict() must continue time_idx)
        self._training_dataset_ = training_dataset
        self._max_time_idx_: dict[str, int] = (
            df_full.groupby("building_id")["time_idx"].max().to_dict()
        )
        self._target_col_ = target_col
        self._tft_cfg_ = tft_cfg

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

        callbacks = [
            pl.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=10,
                mode="min",
            ),
            pl.callbacks.LearningRateMonitor(),
        ]
        trainer = pl.Trainer(
            max_epochs=tft_cfg["max_epochs"],
            gradient_clip_val=tft_cfg["gradient_clip_val"],
            callbacks=callbacks,
            enable_progress_bar=True,
            logger=False,
        )

        logger.info("Training TFT (slow model — use --skip-slow during development) ...")
        trainer.fit(tft, train_dataloaders=train_loader, val_dataloaders=val_loader)

        self.model_   = tft
        self.trainer_ = trainer
        self._val_loader = val_loader
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
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

        test_dataset = TimeSeriesDataSet.from_dataset(
            self._training_dataset_,
            df_test,
            predict=True,
            stop_randomization=True,
        )
        test_loader = test_dataset.to_dataloader(
            train=False,
            batch_size=self._tft_cfg_["batch_size"] * 2,
            num_workers=0,
        )

        raw_preds = self.trainer_.predict(self.model_, test_loader)
        return np.concatenate([p.numpy().flatten() for p in raw_preds])

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    @staticmethod
    def _prepare_df(X: pd.DataFrame, y: pd.Series, split: str) -> pd.DataFrame:
        df = X.copy()
        df[y.name or "target"] = y.values
        df["split"] = split
        df = df.reset_index()
        return df
