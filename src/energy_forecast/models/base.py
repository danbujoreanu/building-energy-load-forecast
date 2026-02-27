"""
models.base
===========
Abstract base class that every forecaster in this project implements.

By defining a common interface (fit / predict / evaluate), we can swap models
in the pipeline without touching orchestration code — **Low Coupling** from
the MSc Distributed Systems lecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import pandas as pd


class BaseForecaster(ABC):
    """Minimal interface every model must satisfy."""

    name: str = "BaseForecaster"

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    @abstractmethod
    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | None = None,
        **kwargs: Any,
    ) -> "BaseForecaster":
        """Fit the model. Returns self for chaining."""

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Return predictions as a 1-D numpy array aligned with X."""

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def fit_predict(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        **kwargs: Any,
    ) -> np.ndarray:
        """Fit then predict in one call."""
        return self.fit(X_train, y_train, **kwargs).predict(X_test)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
