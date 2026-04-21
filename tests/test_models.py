"""Tests for model interfaces — fast, no GPU required."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def tabular_splits() -> dict:
    """Tiny train/val/test splits for testing sklearn & baseline models."""
    np.random.seed(42)
    n = 100
    rng = pd.date_range("2022-01-01", periods=n, freq="h", tz="Europe/Oslo")
    idx = pd.MultiIndex.from_arrays(
        [np.repeat([1, 2], n // 2), np.tile(rng[: n // 2], 2)],
        names=["building_id", "timestamp"],
    )
    X = pd.DataFrame(  # noqa: N806
        np.random.randn(n, 5),
        index=idx,
        columns=["f1", "f2", "f3", "f4", "f5"],
    )
    y = pd.Series(np.random.rand(n) * 50 + 10, index=idx, name="target")
    return {
        "X_train": X[:60],
        "y_train": y[:60],
        "X_val": X[60:80],
        "y_val": y[60:80],
        "X_test": X[80:],
        "y_test": y[80:],
    }


class TestBaselines:
    def test_naive_predict_shape(self, tabular_splits):
        from energy_forecast.models.baselines import NaiveModel

        model = NaiveModel()
        model.fit(tabular_splits["X_train"], tabular_splits["y_train"])
        preds = model.predict(tabular_splits["X_test"])
        assert len(preds) == len(tabular_splits["X_test"])

    def test_seasonal_naive_constant(self, tabular_splits):
        from energy_forecast.models.baselines import SeasonalNaiveModel

        model = SeasonalNaiveModel(season_length=24)
        model.fit(tabular_splits["X_train"], tabular_splits["y_train"])
        preds = model.predict(tabular_splits["X_test"])
        assert len(preds) == len(tabular_splits["X_test"])

    def test_mean_baseline(self, tabular_splits):
        from energy_forecast.models.baselines import MeanModel

        model = MeanModel()
        model.fit(tabular_splits["X_train"], tabular_splits["y_train"])
        preds = model.predict(tabular_splits["X_test"])
        assert len(preds) == len(tabular_splits["X_test"])
        assert np.all(np.isfinite(preds))


class TestSklearnModels:
    def test_ridge_fit_predict(self, tabular_splits):
        from sklearn.linear_model import Ridge

        from energy_forecast.models.sklearn_models import SklearnForecaster

        model = SklearnForecaster(Ridge(alpha=1.0), name="Ridge")
        model.fit(tabular_splits["X_train"], tabular_splits["y_train"])
        preds = model.predict(tabular_splits["X_test"])
        assert preds.shape == (len(tabular_splits["X_test"]),)

    def test_lgbm_fit_predict(self, tabular_splits):
        try:
            import lightgbm as lgb  # noqa: F401
        except (ImportError, OSError):
            pytest.skip("LightGBM not available — run: brew install libomp && pip install lightgbm")
        from energy_forecast.models.sklearn_models import build_sklearn_models

        cfg = {
            "seed": 42,
            "training": {
                "ridge": {"alpha": 1.0},
                "lasso": {"alpha": 0.01, "max_iter": 1000},
                "random_forest": {
                    "n_estimators": 10,
                    "max_depth": 3,
                    "min_samples_leaf": 1,
                    "n_jobs": 1,
                },
                "lightgbm": {
                    "n_estimators": 50,
                    "learning_rate": 0.1,
                    "max_depth": 3,
                    "num_leaves": 15,
                    "min_child_samples": 5,
                    "subsample": 0.8,
                    "colsample_bytree": 0.8,
                    "n_jobs": 1,
                },
                "xgboost": {
                    "n_estimators": 50,
                    "learning_rate": 0.1,
                    "max_depth": 3,
                    "min_child_weight": 1,
                    "subsample": 0.8,
                    "colsample_bytree": 0.8,
                    "reg_alpha": 0.0,
                    "reg_lambda": 1.0,
                    "n_jobs": 1,
                },
            },
        }
        models = build_sklearn_models(cfg)
        lgbm = models["lightgbm"]
        lgbm.fit(tabular_splits["X_train"], tabular_splits["y_train"])
        preds = lgbm.predict(tabular_splits["X_test"])
        assert len(preds) == len(tabular_splits["X_test"])


class TestMetrics:
    def test_evaluate_returns_all_keys(self):
        from energy_forecast.evaluation.metrics import evaluate

        y_true = np.array([10.0, 20.0, 30.0, 40.0])
        y_pred = np.array([11.0, 19.0, 31.0, 38.0])
        result = evaluate(y_true, y_pred, "TestModel")

        for key in ["model", "MAE", "RMSE", "MAPE", "R2"]:
            assert key in result, f"Missing key: {key}"

    def test_mae_perfect_prediction(self):
        from energy_forecast.evaluation.metrics import _mae

        y = np.array([5.0, 10.0, 15.0])
        assert _mae(y, y) == pytest.approx(0.0)

    def test_compare_models_sorted(self):
        from energy_forecast.evaluation.metrics import compare_models, evaluate

        results = [
            evaluate(np.ones(10) * 10, np.ones(10) * 12, "ModelA"),
            evaluate(np.ones(10) * 10, np.ones(10) * 11, "ModelB"),
        ]
        df = compare_models(results)
        assert df.iloc[0]["Model"] == "ModelB"  # lower MAE first
