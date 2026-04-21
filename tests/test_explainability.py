"""
tests/test_explainability.py
============================
Unit tests for SHAP-based explainability.

All tests use a tiny synthetic dataset so they run in CI without the real
Drammen data or slow model training.  shap itself is imported with pytest.importorskip
so the tests are skipped gracefully if the package is not installed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestRegressor

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def small_dataset():
    """Return tiny X_train, X_test, y_train with 3 features."""
    rng = np.random.default_rng(42)
    n_train, n_test = 100, 30
    cols = ["lag_1h", "temperature", "hour_of_day_sin"]

    X_train = pd.DataFrame(rng.standard_normal((n_train, 3)), columns=cols)  # noqa: N806
    y_train = pd.Series(
        5 + 2 * X_train["lag_1h"] - 1.5 * X_train["temperature"] + rng.normal(0, 0.1, n_train)
    )
    X_test = pd.DataFrame(rng.standard_normal((n_test, 3)), columns=cols)  # noqa: N806
    return X_train, X_test, y_train


@pytest.fixture
def fitted_rf(small_dataset):
    """Return a fitted RandomForestRegressor wrapped in a mock SklearnForecaster."""
    X_train, _, y_train = small_dataset  # noqa: N806
    rf = RandomForestRegressor(n_estimators=5, max_depth=3, random_state=42)
    rf.fit(X_train.values, y_train.values)

    # Lightweight mock — just needs .estimator and .name attributes
    class MockForecaster:
        def __init__(self, est, name):
            self.estimator = est
            self.name = name

        def predict(self, X):  # noqa: N803
            return self.estimator.predict(X.values)

    return MockForecaster(rf, "RandomForest")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSHAPExplainer:
    """Tests for SHAPExplainer class."""

    def test_import_shap_or_skip(self):
        """Ensure shap is available — skip gracefully if not installed."""
        try:
            import shap  # noqa: F401
        except ImportError:
            pytest.skip("shap not installed — skipping SHAP tests")

    def test_explainer_builds(self, small_dataset, fitted_rf):
        """SHAPExplainer initialises without error on a tree model."""
        try:
            import shap  # noqa: F401
        except ImportError:
            pytest.skip("shap not installed")

        from energy_forecast.evaluation.explainability import SHAPExplainer

        X_train, _, _ = small_dataset  # noqa: N806
        explainer = SHAPExplainer(fitted_rf, X_train)
        assert explainer.model_name == "RandomForest"
        assert len(explainer.feature_names_) == 3

    def test_compute_returns_correct_shape(self, small_dataset, fitted_rf):
        """SHAP values have shape (n_samples, n_features)."""
        try:
            import shap  # noqa: F401
        except ImportError:
            pytest.skip("shap not installed")

        from energy_forecast.evaluation.explainability import SHAPExplainer

        X_train, X_test, _ = small_dataset  # noqa: N806
        explainer = SHAPExplainer(fitted_rf, X_train)
        sv = explainer.compute(X_test)
        assert sv.values.shape == (len(X_test), X_test.shape[1])

    def test_get_top_features_returns_dataframe(self, small_dataset, fitted_rf):
        """get_top_features() returns a correctly ordered DataFrame."""
        try:
            import shap  # noqa: F401
        except ImportError:
            pytest.skip("shap not installed")

        from energy_forecast.evaluation.explainability import SHAPExplainer

        X_train, X_test, _ = small_dataset  # noqa: N806
        explainer = SHAPExplainer(fitted_rf, X_train)
        explainer.compute(X_test)
        top = explainer.get_top_features(n=3)

        assert isinstance(top, pd.DataFrame)
        assert "feature" in top.columns
        assert "mean_abs_shap" in top.columns
        assert len(top) == 3
        # Must be sorted descending by mean |SHAP|
        assert top["mean_abs_shap"].is_monotonic_decreasing

    def test_explain_model_convenience_function(self, small_dataset, fitted_rf, tmp_path):
        """explain_model() saves plots and returns a SHAPExplainer."""
        try:
            import shap  # noqa: F401
        except ImportError:
            pytest.skip("shap not installed")

        from energy_forecast.evaluation.explainability import explain_model

        X_train, X_test, _ = small_dataset  # noqa: N806

        explainer = explain_model(
            fitted_rf,
            X_train,
            X_test,
            save_dir=tmp_path,
            n_samples=20,
        )
        assert explainer._shap_values is not None

        # At least one plot file should have been written
        shap_dir = tmp_path / "shap"
        png_files = list(shap_dir.glob("*.png"))
        npz_files = list(shap_dir.glob("*.npz"))
        assert len(png_files) >= 1, "Expected at least one SHAP plot"
        assert len(npz_files) == 1, "Expected one .npz file with SHAP values"
