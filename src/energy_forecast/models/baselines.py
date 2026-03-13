"""
models.baselines
================
Simple reference models used to set a performance floor.  Every more
sophisticated model must beat these to be worth the added complexity
(see NP Problem lecture — complexity must be justified by accuracy gain).

Models
------
NaiveModel          Repeat the last observed value
SeasonalNaiveModel  Repeat the value from 24 hours ago (daily seasonality)
MeanModel           Predict the per-building training mean
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BaseForecaster


class NaiveModel(BaseForecaster):
    """Predict the last observed target value (persistence forecast)."""

    name = "Naive"

    def fit(self, X_train, y_train, X_val=None, y_val=None, **kwargs):  # noqa: N803
        self._last_value = float(y_train.iloc[-1])
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        return np.full(len(X), self._last_value)


class SeasonalNaiveModel(BaseForecaster):
    """Repeat the value from 24 hours ago — captures daily seasonality."""

    name = "Seasonal Naive (24 h)"

    def __init__(self, season_length: int = 24) -> None:
        self.season_length = season_length

    def fit(self, X_train, y_train, X_val=None, y_val=None, **kwargs):  # noqa: N803
        # Keep the tail of training series to handle the first season_length predictions
        self._tail = y_train.values[-self.season_length :]
        self._full_train = y_train.copy()
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        lag_col = f"Electricity_Imported_Total_kWh_lag_{self.season_length}h"
        if lag_col in X.columns:
            return X[lag_col].values
        # Fallback: repeat training tail cyclically
        n = len(X)
        repeats = int(np.ceil(n / self.season_length))
        return np.tile(self._tail, repeats)[:n]


class MeanModel(BaseForecaster):
    """Predict the per-building mean from training data."""

    name = "Mean Baseline"

    def fit(self, X_train, y_train, X_val=None, y_val=None, **kwargs):  # noqa: N803
        if "building_id" in y_train.index.names:
            self._building_means = (
                y_train.groupby(level="building_id").mean().to_dict()
            )
            self._global_mean = float(y_train.mean())
        else:
            self._building_means = {}
            self._global_mean = float(y_train.mean())
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        if self._building_means and "building_id" in X.index.names:
            building_ids = X.index.get_level_values("building_id")
            return np.array([
                self._building_means.get(bid, self._global_mean)
                for bid in building_ids
            ])
        return np.full(len(X), self._global_mean)
