"""
models.sklearn_models
=====================
Wraps scikit-learn, LightGBM, and XGBoost regressors in the common
BaseForecaster interface, with cross-validated evaluation built in.

Supported models (all configured via config.yaml)
--------------------------------------------------
    ridge         Ridge regression
    lasso         Lasso regression
    random_forest RandomForestRegressor
    lightgbm      LGBMRegressor
    xgboost       XGBRegressor  (MSc thesis rank 2 — 3.42 kWh MAE)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Lasso, Ridge

from .base import BaseForecaster

logger = logging.getLogger(__name__)


def build_sklearn_models(cfg: dict[str, Any]) -> dict[str, SklearnForecaster]:
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
        "lightgbm_quantile": _build_lgbm_quantile(t["lightgbm"], seed),
        "xgboost": _build_xgboost(t["xgboost"], seed),
    }
    return models


def _build_lgbm(lgbm_cfg: dict, seed: int) -> SklearnForecaster:
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


def _build_lgbm_quantile(lgbm_cfg: dict, seed: int) -> LightGBMQuantileForecaster:
    """Build the specialised probabilistic forecaster outputting P10/P50/P90 quantiles."""
    return LightGBMQuantileForecaster(lgbm_cfg, seed, name="LightGBM_Quantile")


def _build_xgboost(xgb_cfg: dict, seed: int) -> SklearnForecaster:
    """Build XGBoost regressor — MSc thesis rank 2 (MAE 3.42 kWh, ~3s train time)."""
    try:
        from xgboost import XGBRegressor
    except ImportError as e:
        raise ImportError("xgboost is required: pip install xgboost") from e

    model = XGBRegressor(
        n_estimators=xgb_cfg["n_estimators"],
        learning_rate=xgb_cfg["learning_rate"],
        max_depth=xgb_cfg["max_depth"],
        min_child_weight=xgb_cfg["min_child_weight"],
        subsample=xgb_cfg["subsample"],
        colsample_bytree=xgb_cfg["colsample_bytree"],
        reg_alpha=xgb_cfg["reg_alpha"],
        reg_lambda=xgb_cfg["reg_lambda"],
        n_jobs=xgb_cfg["n_jobs"],
        random_state=seed,
        verbosity=0,
    )
    return SklearnForecaster(model, name="XGBoost")


class SklearnForecaster(BaseForecaster):
    """Generic wrapper around any sklearn-compatible regressor."""

    def __init__(self, estimator: Any, name: str = "SklearnModel") -> None:
        self.estimator = estimator
        self.name = name

    def fit(
        self,
        X_train: pd.DataFrame,  # noqa: N803
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,  # noqa: N803
        y_val: pd.Series | None = None,
        **kwargs: Any,
    ) -> SklearnForecaster:
        from energy_forecast.validation import DataValidator

        DataValidator.validate_training_data(X_train, y_train, X_val, y_val, split_name=self.name)
        logger.info("Training %s ...", self.name)
        fit_params: dict = {}

        # LightGBM supports early stopping via eval_set.
        # Pass DataFrames (not .values) so column names are preserved in
        # feature_name_ — this allows the /predict API to validate semantic
        # names (lag_24h, hour_of_day, ...) instead of generic Column_0..N.
        # NOTE: existing saved models (pre-2026-04-20) still have Column_N
        # names; re-run scripts/run_pipeline.py to retrain with named features.
        if X_val is not None and hasattr(self.estimator, "fit"):
            try:
                import lightgbm as lgb

                if isinstance(self.estimator, lgb.LGBMRegressor):
                    fit_params = {
                        "eval_set": [(X_val, y_val.values)],
                        "callbacks": [lgb.early_stopping(50, verbose=False)],
                    }
            except ImportError:
                pass

        # XGBoost also supports early stopping via eval_set
        if X_val is not None and not fit_params:
            try:
                from xgboost import XGBRegressor

                if isinstance(self.estimator, XGBRegressor):
                    fit_params = {
                        "eval_set": [(X_val, y_val.values)],
                        "verbose": False,
                    }
            except ImportError:
                pass

        self.estimator.fit(X_train, y_train.values, **fit_params)
        logger.info("%s training complete.", self.name)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        # Pass DataFrame so sklearn/LightGBM/XGBoost can validate feature names.
        # Using X.values (numpy) silences the check but causes silent mismatch bugs.
        return self.estimator.predict(X)

    @property
    def feature_importances_(self) -> np.ndarray | None:
        return getattr(self.estimator, "feature_importances_", None)


class LightGBMQuantileForecaster(BaseForecaster):
    """Specialised wrapper to train three LightGBM models for P10, P50, and P90 quantiles."""

    def __init__(
        self,
        lgbm_cfg: dict,
        seed: int,
        name: str = "LightGBM_Quantile",
        quantiles: list[float] = [0.1, 0.5, 0.9],
    ) -> None:
        self.name = name
        self.lgbm_cfg = lgbm_cfg.copy()
        self.seed = seed
        self.quantiles = quantiles
        self.models: dict[float, Any] = {}

    def fit(
        self,
        X_train: pd.DataFrame,  # noqa: N803
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,  # noqa: N803
        y_val: pd.Series | None = None,
        **kwargs: Any,
    ) -> LightGBMQuantileForecaster:
        from energy_forecast.validation import DataValidator

        DataValidator.validate_training_data(X_train, y_train, X_val, y_val, split_name=self.name)
        try:
            import lightgbm as lgb
        except ImportError as e:
            raise ImportError("lightgbm is required: pip install lightgbm") from e

        for alpha in self.quantiles:
            logger.info("Training %s for alpha=%s", self.name, alpha)
            model = lgb.LGBMRegressor(
                objective="quantile",
                alpha=alpha,
                n_estimators=self.lgbm_cfg["n_estimators"],
                learning_rate=self.lgbm_cfg["learning_rate"],
                max_depth=self.lgbm_cfg["max_depth"],
                num_leaves=self.lgbm_cfg["num_leaves"],
                min_child_samples=self.lgbm_cfg["min_child_samples"],
                subsample=self.lgbm_cfg["subsample"],
                colsample_bytree=self.lgbm_cfg["colsample_bytree"],
                n_jobs=self.lgbm_cfg["n_jobs"],
                random_state=self.seed,
                verbosity=-1,
            )
            fit_params: dict = {}
            if X_val is not None:
                fit_params = {
                    "eval_set": [(X_val, y_val.values)],  # DataFrame preserves names
                    "callbacks": [lgb.early_stopping(50, verbose=False)],
                }
            model.fit(X_train, y_train.values, **fit_params)  # DataFrame preserves names
            self.models[alpha] = model

        logger.info("%s training complete.", self.name)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        """Returns the median prediction (P50) to satisfy standard evaluation frameworks."""
        if 0.5 not in self.models:
            raise ValueError("Median model (alpha=0.5) was not trained.")
        return self.models[0.5].predict(X.values)

    def predict_quantiles(self, X: pd.DataFrame) -> pd.DataFrame:  # noqa: N803
        """Return a DataFrame with specific quantile bound predictions."""
        preds = {}
        for alpha, model in self.models.items():
            label = f"P{int(alpha * 100)}"
            preds[label] = model.predict(X.values)
        return pd.DataFrame(preds, index=X.index)

    @property
    def feature_importances_(self) -> np.ndarray | None:
        """Returns importances from the median model."""
        if 0.5 in self.models:
            return getattr(self.models[0.5], "feature_importances_", None)
        return None
