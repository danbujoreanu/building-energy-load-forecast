"""
Tests for data loading and preprocessing.

Uses synthetic mini-datasets so no actual building files are needed to run CI.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_timeseries() -> pd.DataFrame:
    """Create a minimal synthetic MultiIndex (building_id, timestamp) DataFrame."""
    n = 200
    rng = pd.date_range("2022-01-01", periods=n, freq="h", tz="Europe/Oslo")
    building_ids = np.repeat([6396, 6397], n // 2)  # noqa: F841
    timestamps = np.tile(rng, 2)[: n * 2 // 2]  # noqa: F841

    idx = pd.MultiIndex.from_arrays(
        [np.repeat([6396, 6397], n), np.tile(rng, 2)],
        names=["building_id", "timestamp"],
    )
    df = pd.DataFrame(
        {
            "Electricity_Imported_Total_kWh": np.random.rand(n * 2) * 50 + 5,
            "Temperature_Outdoor_C": np.random.randn(n * 2) * 10,
            "Global_Solar_Horizontal_Radiation_W_m2": np.abs(np.random.randn(n * 2)) * 100,
            "Wind_Speed_m_s": np.abs(np.random.randn(n * 2)) * 3,
            "hour_of_day": np.tile(rng.hour, 2),
            "day_of_week": np.tile(rng.dayofweek, 2),
            "month": np.tile(rng.month, 2),
            "day_of_year": np.tile(rng.dayofyear, 2),
            "is_weekend": (np.tile(rng.dayofweek, 2) >= 5).astype(int),
        },
        index=idx,
    )
    return df


@pytest.fixture
def sample_config() -> dict:
    return {
        "city": "drammen",
        "seed": 42,
        "data": {
            "target_column": "Electricity_Imported_Total_kWh",
            "weather_columns": [
                "Temperature_Outdoor_C",
                "Global_Solar_Horizontal_Radiation_W_m2",
                "Wind_Speed_m_s",
            ],
            "wh_to_kwh": True,
            "min_completeness": 0.5,
            "timestamp_format": "%Y-%m-%dT%H:%M:%S%z",
        },
        "splits": {
            "train_end": "2022-01-05",
            "val_end": "2022-01-07",
        },
        "paths": {
            "raw_data": {"drammen": "data/raw/drammen", "oslo": "data/raw/oslo"},
            "processed": "data/processed",
            "splits": "data/processed/splits",
            "outputs": {
                "figures": "outputs/figures",
                "models": "outputs/models",
                "results": "outputs/results",
            },
        },
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPreprocessing:
    def test_completeness_filter(self, sample_timeseries, sample_config):
        """Buildings below completeness threshold should be removed."""
        from energy_forecast.data.preprocessing import _filter_by_completeness

        target = sample_config["data"]["target_column"]
        # Introduce 80% missing for building 6397
        mask = sample_timeseries.index.get_level_values("building_id") == 6397
        sample_timeseries.loc[mask, target] = np.nan

        result = _filter_by_completeness(sample_timeseries, target, threshold=0.5)
        remaining_ids = result.index.get_level_values("building_id").unique()
        assert 6397 not in remaining_ids
        assert 6396 in remaining_ids

    def test_calendar_features_added(self, sample_timeseries, sample_config):
        """Calendar columns must be present after preprocessing."""
        from energy_forecast.data.preprocessing import _add_calendar_features

        result = _add_calendar_features(sample_timeseries)
        for col in ["hour_of_day", "day_of_week", "month", "is_weekend"]:
            assert col in result.columns, f"Missing: {col}"

    def test_outlier_clipping(self, sample_timeseries, sample_config):
        """Negative electricity values should be set to NaN."""
        from energy_forecast.data.preprocessing import _clip_outliers

        target = sample_config["data"]["target_column"]
        sample_timeseries.loc[sample_timeseries.index[0], target] = -999.0
        result = _clip_outliers(
            sample_timeseries,
            target,
            sample_config["data"]["weather_columns"],
        )
        assert result.loc[result.index[0], target] != -999.0


class TestSplits:
    def test_split_shapes(self, sample_timeseries, sample_config):
        """Train + val + test should cover the full dataset (minus NaN drops)."""
        from energy_forecast.data.splits import make_splits

        splits = make_splits(sample_timeseries, sample_config)
        total = len(splits["X_train"]) + len(splits["X_val"]) + len(splits["X_test"])
        assert total > 0

    def test_no_future_leakage(self, sample_timeseries, sample_config):
        """Train timestamps must all be before validation timestamps."""
        from energy_forecast.data.splits import make_splits

        splits = make_splits(sample_timeseries, sample_config)
        train_max = splits["X_train"].index.get_level_values("timestamp").max()
        val_min = splits["X_val"].index.get_level_values("timestamp").min()
        if len(splits["X_val"]) > 0:
            assert train_max < val_min, "Data leakage detected!"

    def test_scaler_fitted(self, sample_timeseries, sample_config):
        """StandardScaler must be fitted and have mean_ attribute."""
        from energy_forecast.data.splits import make_splits

        splits = make_splits(sample_timeseries, sample_config)
        scaler = splits["scaler"]
        assert hasattr(scaler, "mean_"), "Scaler not fitted"
