"""
tests.test_validation
=====================
Unit tests for energy_forecast.validation (DataValidator, DataValidationError)
and energy_forecast.models.deep_learning.reshape_dl_predictions.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import pytest

from energy_forecast.validation import DataValidationError, DataValidator
from energy_forecast.models.deep_learning import reshape_dl_predictions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_X(n: int = 100, cols: int = 5) -> pd.DataFrame:
    """Return a clean float DataFrame with a MultiIndex."""
    idx = pd.MultiIndex.from_tuples(
        [(1, i) for i in range(n)],
        names=["building_id", "timestamp"],
    )
    return pd.DataFrame(
        np.random.default_rng(0).random((n, cols)),
        index=idx,
        columns=[f"feat_{i}" for i in range(cols)],
    )


def _make_y(n: int = 100) -> pd.Series:
    return pd.Series(np.random.default_rng(1).random(n) * 10, name="target")


# ---------------------------------------------------------------------------
# validate_features
# ---------------------------------------------------------------------------

def test_validate_features_passes_clean_data():
    X = _make_X()
    DataValidator.validate_features(X, name="X_train")  # must not raise


def test_validate_features_raises_on_empty():
    X = _make_X(n=0)
    with pytest.raises(DataValidationError, match="empty"):
        DataValidator.validate_features(X, name="X_empty")


def test_validate_features_raises_on_nan():
    X = _make_X()
    X.iloc[5, 2] = np.nan
    with pytest.raises(DataValidationError, match="NaN after imputation"):
        DataValidator.validate_features(X, name="X_nan")


def test_validate_features_raises_on_inf():
    X = _make_X()
    X.iloc[10, 1] = np.inf
    with pytest.raises(DataValidationError, match="infinite values"):
        DataValidator.validate_features(X, name="X_inf")


def test_validate_features_allow_nan_flag():
    X = _make_X()
    X.iloc[5, 2] = np.nan
    # With allow_nan=True the NaN check is skipped — should not raise
    DataValidator.validate_features(X, name="X_nan_allowed", allow_nan=True)


# ---------------------------------------------------------------------------
# validate_target
# ---------------------------------------------------------------------------

def test_validate_target_passes_clean():
    y = _make_y()
    DataValidator.validate_target(y, name="y_train")  # must not raise


def test_validate_target_raises_on_empty():
    with pytest.raises(DataValidationError, match="empty"):
        DataValidator.validate_target(np.array([]), name="y_empty")


def test_validate_target_warns_on_negatives(caplog):
    """More than 1% negative values should log a WARNING."""
    y = np.full(100, -1.0)  # 100% negative — well above threshold
    with caplog.at_level(logging.WARNING, logger="energy_forecast.validation"):
        DataValidator.validate_target(y, name="y_neg", allow_negative=False)
    assert any("negative" in rec.message for rec in caplog.records)


def test_validate_target_no_warning_below_threshold(caplog):
    """Fewer than 1% negatives should NOT log a WARNING."""
    y = np.ones(1000)
    y[0] = -0.001  # only 0.1% — below the 1% threshold
    with caplog.at_level(logging.WARNING, logger="energy_forecast.validation"):
        DataValidator.validate_target(y, name="y_mostly_pos", allow_negative=False)
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) == 0


# ---------------------------------------------------------------------------
# validate_shapes
# ---------------------------------------------------------------------------

def test_validate_shapes_raises_on_mismatch():
    X = _make_X(n=100)
    y = _make_y(n=50)
    with pytest.raises(DataValidationError, match="Shape mismatch"):
        DataValidator.validate_shapes(X, y, name="train")


def test_validate_shapes_passes_matching():
    X = _make_X(n=80)
    y = _make_y(n=80)
    DataValidator.validate_shapes(X, y, name="train")  # must not raise


# ---------------------------------------------------------------------------
# validate_training_data
# ---------------------------------------------------------------------------

def test_validate_training_data_full_call():
    X_train = _make_X(n=100)
    y_train = _make_y(n=100)
    X_val = _make_X(n=20)
    y_val = _make_y(n=20)
    DataValidator.validate_training_data(
        X_train, y_train, X_val, y_val, split_name="LightGBM"
    )  # must not raise


def test_validate_training_data_val_optional():
    X_train = _make_X(n=100)
    y_train = _make_y(n=100)
    # No val data — must still pass
    DataValidator.validate_training_data(X_train, y_train, split_name="Ridge")


def test_validate_training_data_raises_on_bad_train():
    X_train = _make_X(n=100)
    X_train.iloc[0, 0] = np.nan
    y_train = _make_y(n=100)
    with pytest.raises(DataValidationError, match="NaN after imputation"):
        DataValidator.validate_training_data(X_train, y_train, split_name="XGBoost")


# ---------------------------------------------------------------------------
# reshape_dl_predictions
# ---------------------------------------------------------------------------

def test_reshape_dl_predictions_h1_flattens():
    raw = np.ones((50, 1))
    out = reshape_dl_predictions(raw, horizon=1)
    assert out.shape == (50,)


def test_reshape_dl_predictions_h1_already_1d():
    raw = np.ones(50)
    out = reshape_dl_predictions(raw, horizon=1)
    assert out.shape == (50,)


def test_reshape_dl_predictions_hn_returns_matrix():
    raw = np.ones((50, 24))
    out = reshape_dl_predictions(raw, horizon=24)
    assert out.shape == (50, 24)


def test_reshape_dl_predictions_raises_on_1d_hn():
    raw = np.ones(50)  # 1-D — wrong for horizon=24
    with pytest.raises(ValueError, match="BUG-C5"):
        reshape_dl_predictions(raw, horizon=24)


def test_reshape_dl_predictions_raises_on_wrong_horizon():
    raw = np.ones((50, 12))  # last dim=12, but horizon=24
    with pytest.raises(ValueError, match="BUG-C5"):
        reshape_dl_predictions(raw, horizon=24)
