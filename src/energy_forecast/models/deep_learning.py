"""
models.deep_learning
====================
LSTM, CNN-LSTM and GRU sequence models implemented in TensorFlow/Keras.

All three follow the same interface:
    1. Call ``build_sequences()`` to convert the 2-D split DataFrames into
       3-D (samples, timesteps, features) arrays.
    2. Instantiate a model class (LSTMForecaster, CNNLSTMForecaster, GRUForecaster).
    3. Call ``.fit()`` with training and validation data.
    4. Call ``.predict()`` on test data.

Computational note (MSc NP lecture)
------------------------------------
LSTM / GRU: O(n · T · H²) where T = lookback, H = hidden units.
CNN-LSTM:   O(n · T · F · K) for the conv layers + O(n · H²) for LSTM.
These are the "slow" models flagged in config.yaml — skip with --skip-slow.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from .base import BaseForecaster

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sequence builder
# ---------------------------------------------------------------------------

def build_sequences(
    X: pd.DataFrame,
    y: pd.Series,
    lookback: int,
    horizon: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert 2-D tabular data into 3-D sliding windows.

    Respects building boundaries — windows never cross from one building
    into another.

    Parameters
    ----------
    X : shape (n_rows, n_features)
    y : shape (n_rows,)
    lookback : number of past hours used as input
    horizon : number of future hours to predict (currently 1-step, multi-step
              can be enabled by adjusting ``y`` construction)

    Returns
    -------
    X_seq : (n_samples, lookback, n_features)
    y_seq : (n_samples,)
    """
    X_seqs, y_seqs = [], []
    building_ids = X.index.get_level_values("building_id").unique()

    for bid in building_ids:
        X_b = X.xs(bid, level="building_id").values
        y_b = y.xs(bid, level="building_id").values
        n = len(X_b)

        for i in range(lookback, n - horizon + 1):
            X_seqs.append(X_b[i - lookback : i])
            y_seqs.append(y_b[i])   # next-step target

    return np.array(X_seqs, dtype=np.float32), np.array(y_seqs, dtype=np.float32)


# ---------------------------------------------------------------------------
# LSTM
# ---------------------------------------------------------------------------

class LSTMForecaster(BaseForecaster):
    """Stacked LSTM: 64 → 32 units with dropout, followed by Dense layers."""

    name = "LSTM"

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        self.model_ = None
        self.history_ = None

    def fit(self, X_train, y_train, X_val=None, y_val=None, **kwargs):
        tf = _import_tf()
        dl_cfg = self.cfg["training"]["deep_learning"]
        seq_cfg = self.cfg["sequence"]

        X_tr_seq, y_tr_seq = build_sequences(
            X_train, y_train, seq_cfg["lookback"], seq_cfg["horizon"]
        )
        n_features = X_tr_seq.shape[2]

        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(
                dl_cfg["lstm"]["units"][0], return_sequences=True,
                input_shape=(seq_cfg["lookback"], n_features)
            ),
            tf.keras.layers.Dropout(dl_cfg["dropout_rate"]),
            tf.keras.layers.LSTM(dl_cfg["lstm"]["units"][1]),
            tf.keras.layers.Dropout(dl_cfg["dropout_rate"]),
            tf.keras.layers.Dense(dl_cfg["lstm"]["dense_units"], activation="relu"),
            tf.keras.layers.Dense(1),
        ], name="LSTM")
        model.compile(optimizer="adam", loss="mse", metrics=["mae"])

        callbacks = _make_callbacks(dl_cfg)

        fit_kwargs: dict = {
            "epochs":     dl_cfg["epochs"],
            "batch_size": dl_cfg["batch_size"],
            "callbacks":  callbacks,
            "verbose":    0,
        }
        if X_val is not None and y_val is not None:
            X_v_seq, y_v_seq = build_sequences(
                X_val, y_val, seq_cfg["lookback"], seq_cfg["horizon"]
            )
            fit_kwargs["validation_data"] = (X_v_seq, y_v_seq)

        logger.info("Training LSTM ...")
        self.history_ = model.fit(X_tr_seq, y_tr_seq, **fit_kwargs)
        self.model_ = model
        self._seq_cfg = seq_cfg
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        # Build sequences from X; y is a placeholder (values not used)
        y_placeholder = pd.Series(np.zeros(len(X)), index=X.index)
        X_seq, _ = build_sequences(
            X, y_placeholder, self._seq_cfg["lookback"], self._seq_cfg["horizon"]
        )
        return self.model_.predict(X_seq, verbose=0).flatten()


# ---------------------------------------------------------------------------
# CNN-LSTM
# ---------------------------------------------------------------------------

class CNNLSTMForecaster(BaseForecaster):
    """1-D Conv layers for local pattern detection, LSTM for temporal context."""

    name = "CNN-LSTM"

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        self.model_ = None
        self.history_ = None

    def fit(self, X_train, y_train, X_val=None, y_val=None, **kwargs):
        tf = _import_tf()
        dl_cfg = self.cfg["training"]["deep_learning"]
        cnn_cfg = dl_cfg["cnn_lstm"]
        seq_cfg = self.cfg["sequence"]

        X_tr_seq, y_tr_seq = build_sequences(
            X_train, y_train, seq_cfg["lookback"], seq_cfg["horizon"]
        )
        n_features = X_tr_seq.shape[2]

        model = tf.keras.Sequential([
            tf.keras.layers.Conv1D(
                cnn_cfg["conv_filters"][0], cnn_cfg["kernel_size"],
                activation="relu",
                input_shape=(seq_cfg["lookback"], n_features)
            ),
            tf.keras.layers.MaxPooling1D(pool_size=2),
            tf.keras.layers.Conv1D(
                cnn_cfg["conv_filters"][1], cnn_cfg["kernel_size"],
                activation="relu"
            ),
            tf.keras.layers.LSTM(cnn_cfg["lstm_units"]),
            tf.keras.layers.Dropout(dl_cfg["dropout_rate"]),
            tf.keras.layers.Dense(cnn_cfg["dense_units"], activation="relu"),
            tf.keras.layers.Dense(1),
        ], name="CNN_LSTM")
        model.compile(optimizer="adam", loss="mse", metrics=["mae"])

        callbacks = _make_callbacks(dl_cfg)
        fit_kwargs: dict = {
            "epochs":     dl_cfg["epochs"],
            "batch_size": dl_cfg["batch_size"],
            "callbacks":  callbacks,
            "verbose":    0,
        }
        if X_val is not None and y_val is not None:
            X_v_seq, y_v_seq = build_sequences(
                X_val, y_val, seq_cfg["lookback"], seq_cfg["horizon"]
            )
            fit_kwargs["validation_data"] = (X_v_seq, y_v_seq)

        logger.info("Training CNN-LSTM (this takes a while — go get a coffee ☕) ...")
        self.history_ = model.fit(X_tr_seq, y_tr_seq, **fit_kwargs)
        self.model_ = model
        self._seq_cfg = seq_cfg
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        y_placeholder = pd.Series(np.zeros(len(X)), index=X.index)
        X_seq, _ = build_sequences(
            X, y_placeholder, self._seq_cfg["lookback"], self._seq_cfg["horizon"]
        )
        return self.model_.predict(X_seq, verbose=0).flatten()


# ---------------------------------------------------------------------------
# GRU
# ---------------------------------------------------------------------------

class GRUForecaster(BaseForecaster):
    """Gated Recurrent Unit — lighter alternative to LSTM."""

    name = "GRU"

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        self.model_ = None
        self.history_ = None

    def fit(self, X_train, y_train, X_val=None, y_val=None, **kwargs):
        tf = _import_tf()
        dl_cfg = self.cfg["training"]["deep_learning"]
        seq_cfg = self.cfg["sequence"]

        X_tr_seq, y_tr_seq = build_sequences(
            X_train, y_train, seq_cfg["lookback"], seq_cfg["horizon"]
        )
        n_features = X_tr_seq.shape[2]

        model = tf.keras.Sequential([
            tf.keras.layers.GRU(
                dl_cfg["gru"]["units"][0], return_sequences=True,
                input_shape=(seq_cfg["lookback"], n_features)
            ),
            tf.keras.layers.Dropout(dl_cfg["dropout_rate"]),
            tf.keras.layers.GRU(dl_cfg["gru"]["units"][1]),
            tf.keras.layers.Dropout(dl_cfg["dropout_rate"]),
            tf.keras.layers.Dense(dl_cfg["gru"]["dense_units"], activation="relu"),
            tf.keras.layers.Dense(1),
        ], name="GRU")
        model.compile(optimizer="adam", loss="mse", metrics=["mae"])

        callbacks = _make_callbacks(dl_cfg)
        fit_kwargs: dict = {
            "epochs":     dl_cfg["epochs"],
            "batch_size": dl_cfg["batch_size"],
            "callbacks":  callbacks,
            "verbose":    0,
        }
        if X_val is not None and y_val is not None:
            X_v_seq, y_v_seq = build_sequences(
                X_val, y_val, seq_cfg["lookback"], seq_cfg["horizon"]
            )
            fit_kwargs["validation_data"] = (X_v_seq, y_v_seq)

        logger.info("Training GRU ...")
        self.history_ = model.fit(X_tr_seq, y_tr_seq, **fit_kwargs)
        self.model_ = model
        self._seq_cfg = seq_cfg
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        y_placeholder = pd.Series(np.zeros(len(X)), index=X.index)
        X_seq, _ = build_sequences(
            X, y_placeholder, self._seq_cfg["lookback"], self._seq_cfg["horizon"]
        )
        return self.model_.predict(X_seq, verbose=0).flatten()


# ---------------------------------------------------------------------------
# Private utilities
# ---------------------------------------------------------------------------

def _import_tf():
    try:
        import tensorflow as tf
        tf.get_logger().setLevel("ERROR")
        return tf
    except ImportError as e:
        raise ImportError(
            "TensorFlow is required for deep learning models.\n"
            "Install with: pip install tensorflow"
        ) from e


def _make_callbacks(dl_cfg: dict) -> list:
    tf = _import_tf()
    return [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=dl_cfg["early_stopping_patience"],
            restore_best_weights=True,
            verbose=1,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=dl_cfg["reduce_lr_factor"],
            patience=dl_cfg["reduce_lr_patience"],
            min_lr=dl_cfg["min_lr"],
            verbose=0,
        ),
    ]
