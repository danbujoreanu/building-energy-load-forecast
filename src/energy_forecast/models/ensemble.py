"""
models.ensemble
===============
Stacking ensemble that combines predictions from multiple base learners
through a meta-learner (Ridge or LightGBM).

Architecture (from MSc thesis)
-------------------------------
    Base learners  → predictions on validation set  → meta-features
    Meta-learner   trained on meta-features
    Final prediction  = meta-learner(base_preds on test)

This implements the Task Orchestration pattern: the StackingEnsemble
coordinates independent base models without them knowing about each other.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from .base import BaseForecaster

logger = logging.getLogger(__name__)


class StackingEnsemble(BaseForecaster):
    """Stacking ensemble with a configurable meta-learner."""

    name = "Stacking Ensemble"

    def __init__(
        self,
        base_models: dict[str, BaseForecaster],
        cfg: dict[str, Any],
    ) -> None:
        """
        Parameters
        ----------
        base_models:
            Dict of {model_name: fitted BaseForecaster}.  Models must already
            be fitted before passing to the ensemble.
        cfg:
            Full config dict.
        """
        self.base_models = base_models
        self.cfg = cfg
        self.meta_learner_: Any = None
        self._base_names: list[str] = []

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | None = None,
        **kwargs: Any,
    ) -> "StackingEnsemble":
        """Train the meta-learner on validation-set predictions."""
        if X_val is None or y_val is None:
            raise ValueError("StackingEnsemble requires X_val and y_val to train the meta-learner.")

        # ── Generate meta-features (base model predictions on val set) ─────────
        meta_features = self._generate_meta_features(X_val)
        logger.info(
            "Meta-features shape: %s | training meta-learner on %d samples",
            meta_features.shape, len(y_val),
        )

        # ── Fit meta-learner ──────────────────────────────────────────────────
        ens_cfg = self.cfg["training"]["ensemble"]
        if ens_cfg["meta_learner"] == "lightgbm":
            self.meta_learner_ = _build_lgbm_meta(ens_cfg, self.cfg.get("seed", 42))
        else:
            self.meta_learner_ = Ridge(alpha=ens_cfg["ridge_alpha"])

        self.meta_learner_.fit(meta_features, y_val.values)
        logger.info("Stacking ensemble trained with %s meta-learner.", ens_cfg["meta_learner"])
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        meta_features = self._generate_meta_features(X)
        return self.meta_learner_.predict(meta_features)

    def _generate_meta_features(self, X: pd.DataFrame) -> np.ndarray:
        """Stack base model predictions as columns."""
        preds = {}
        for name, model in self.base_models.items():
            try:
                preds[name] = model.predict(X)
                self._base_names = list(preds.keys())
            except Exception as exc:  # noqa: BLE001
                logger.warning("Base model '%s' failed to predict: %s", name, exc)
        return np.column_stack(list(preds.values()))


def _build_lgbm_meta(ens_cfg: dict, seed: int) -> Any:
    try:
        import lightgbm as lgb
        return lgb.LGBMRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=4,
            random_state=seed,
            verbosity=-1,
        )
    except ImportError as e:
        raise ImportError("lightgbm required for LightGBM meta-learner.") from e
