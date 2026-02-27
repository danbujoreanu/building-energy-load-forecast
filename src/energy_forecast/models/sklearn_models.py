"""
models.sklearn_models
=====================
Wraps scikit-learn and LightGBM regressors in the common BaseForecaster
interface, with cross-validated evaluation built in.

Supported models (all configured via config.yaml)
--------------------------------------------------
    ridge         Ridge regression
    lasso         Lasso regression
    random_forest RandomForestRegressor
    lightgbm      LGBMRegressor
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Lasso, Ridge
from sklearn.ensemble import RandomForestRegressor

from .base import BaseForecaster

logger = logging.getLogger(__name__)


def build_sklearn_models(cfg: dict[str, Any]) -> dict[str, "SklearnForecaster"]:
    """Instantiate all sklearn models from config and return as a dict."""
    t = cfg["training"]
    seed = cfg.get("seed", 42)

    models = {
        "ridge": SklearnForecaster(
            Ridge(alpha=t["ridge"]["alpha"]),
            name="Ridge",
        ),
        "lasso": SklearnForecaster(
            Lasso(alpha=t["lasso"]["alpha"], max_iter=t["lasso"]["max_iter"]),
            name="Lasso",
        ),
        "random_forest": SklearnForecaster(
            RandomForestRegressor(
                n_estimators=t["random_forest"]["n_estimators"],
                max_depth=t["random_forest"]["max_depth"],
                min_samples_leaf=t["random_forest"]["min_samples_leaf"],
                random_state=seed,
                n_jobs=t["random_forest"]["n_jobs"],
            ),
            name="RandomForest",
        ),
        "lightgbm": _build_lgbm(t["lightgbm"], seed),
    }
    return models


def _build_lgbm(lgbm_cfg: dict, seed: int) -> "SklearnForecaster":
    try:
        import lightgbm as lgb
    except ImportError as e:
        raise ImportError("lightgbm is required: pip install lightgbm") from e

    model = lgb.LGBMRegressor(
        n_estimators=lgbm_cfg["n_estimators"],
        learning_rate=lgbm_cfg["learning_rate"],
        max_depth=lgbm_cfg["max_depth"],
        num_leaves=lgbm_cfg["num_leaves"],
        min_child_samples=lgbm_cfg["min_child_samples"],
        subsample=lgbm_cfg["subsample"],
        colsample_bytree=lgbm_cfg["colsample_bytree"],
        n_jobs=lgbm_cfg["n_jobs"],
        random_state=seed,
        verbosity=-1,
    )
    return SklearnForecaster(model, name="LightGBM")


class SklearnForecaster(BaseForecaster):
    """Generic wrapper around any sklearn-compatible regressor."""

    def __init__(self, estimator: Any, name: str = "SklearnModel") -> None:
        self.estimator = estimator
        self.name = name

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | None = None,
        **kwargs: Any,
    ) -> "SklearnForecaster":
        logger.info("Training %s ...", self.name)
        fit_params: dict = {}

        # LightGBM supports early stopping via eval_set
        if X_val is not None and hasattr(self.estimator, "fit"):
            try:
                import lightgbm as lgb
                if isinstance(self.estimator, lgb.LGBMRegressor):
                    fit_params = {
                        "eval_set": [(X_val.values, y_val.values)],
                        "callbacks": [lgb.early_stopping(50, verbose=False)],
                    }
            except ImportError:
                pass

        self.estimator.fit(X_train.values, y_train.values, **fit_params)
        logger.info("%s training complete.", self.name)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.estimator.predict(X.values)

    @property
    def feature_importances_(self) -> np.ndarray | None:
        return getattr(self.estimator, "feature_importances_", None)
