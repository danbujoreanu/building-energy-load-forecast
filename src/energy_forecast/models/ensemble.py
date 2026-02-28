"""
models.ensemble
===============
Ensemble methods that combine predictions from multiple base learners.

Two implementations (both from MSc thesis):

StackingEnsemble
    Base learners → predictions on validation set → meta-features
    Meta-learner (Ridge or LightGBM) trained on those meta-features.
    Final prediction = meta-learner(base_preds on test).
    Thesis results: Ridge MAE 3.698 kWh | LGBM MAE 3.582 kWh.

WeightedAverageEnsemble
    Weights = softmax(1 / val_MAE) per model, normalised to sum=1.
    Simple, interpretable, no additional training needed.
    Thesis result: MAE 4.081 kWh (Drammen test set, all 6 models).

This implements the Task Orchestration pattern: each ensemble coordinates
independent base models without them knowing about each other.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from .base import BaseForecaster

logger = logging.getLogger(__name__)


_META_LABELS: dict[str, str] = {
    "ridge":    "Ridge",
    "lightgbm": "LGBM",
}


class StackingEnsemble(BaseForecaster):
    """Stacking ensemble with a configurable meta-learner.

    The instance ``name`` attribute is set from config at construction time
    so it matches the thesis naming convention:
        - "Stacking Ensemble (Ridge meta)"
        - "Stacking Ensemble (LGBM meta)"
    """

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

        meta_key = cfg["training"]["ensemble"].get("meta_learner", "ridge")
        meta_label = _META_LABELS.get(meta_key, meta_key.capitalize())
        self.name: str = f"Stacking Ensemble ({meta_label} meta)"

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


class WeightedAverageEnsemble(BaseForecaster):
    """Inverse-MAE weighted average ensemble.

    Weights are computed from each base model's MAE on the validation set:
        weight_i  = (1 / MAE_i) / sum(1 / MAE_j  for all j)

    This replicates the ``Weighted Avg Ensemble`` from the MSc thesis
    (validation MAE 4.081 kWh on the Drammen test set).

    Parameters
    ----------
    base_models:
        Dict of {model_name: fitted BaseForecaster}.
    """

    name = "Weighted Avg Ensemble"

    def __init__(self, base_models: dict[str, BaseForecaster]) -> None:
        self.base_models = base_models
        self.weights_: dict[str, float] = {}

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | None = None,
        **kwargs: Any,
    ) -> "WeightedAverageEnsemble":
        """Compute inverse-MAE weights from the validation set."""
        if X_val is None or y_val is None:
            raise ValueError(
                "WeightedAverageEnsemble requires X_val and y_val to compute weights."
            )

        maes: dict[str, float] = {}
        for model_name, model in self.base_models.items():
            try:
                preds = model.predict(X_val)
                mae = float(np.mean(np.abs(preds - y_val.values)))
                maes[model_name] = mae
            except Exception as exc:  # noqa: BLE001
                logger.warning("Model '%s' failed on val set: %s", model_name, exc)

        if not maes:
            raise ValueError("No base models produced valid validation predictions.")

        inv_maes = {k: 1.0 / v for k, v in maes.items() if v > 0}
        total = sum(inv_maes.values())
        self.weights_ = {k: v / total for k, v in inv_maes.items()}

        for name, w in sorted(self.weights_.items(), key=lambda x: -x[1]):
            logger.info("  Weight %-35s = %.4f  (val MAE=%.4f kWh)", name, w, maes[name])

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Weighted average of base model predictions."""
        weighted_sum = np.zeros(len(X))
        for model_name, model in self.base_models.items():
            weight = self.weights_.get(model_name, 0.0)
            if weight == 0.0:
                continue
            try:
                weighted_sum += weight * model.predict(X)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Model '%s' failed at predict: %s", model_name, exc)
        return weighted_sum

    @property
    def weights_df(self) -> pd.DataFrame:
        """Return weights as a tidy DataFrame, sorted descending."""
        return pd.DataFrame(
            {"model": list(self.weights_.keys()), "weight": list(self.weights_.values())}
        ).sort_values("weight", ascending=False).reset_index(drop=True)


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
