"""Tests for temporal feature engineering."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def mini_df() -> pd.DataFrame:
    n = 300
    rng = pd.date_range("2022-01-01", periods=n, freq="h", tz="Europe/Oslo")
    idx = pd.MultiIndex.from_arrays(
        [np.repeat([1, 2], n // 2), np.tile(rng[: n // 2], 2)],
        names=["building_id", "timestamp"],
    )
    return pd.DataFrame(
        {
            "Electricity_Imported_Total_kWh": np.random.rand(n) * 30 + 5,
            "Temperature_Outdoor_C": np.random.randn(n) * 8,
            "hour_of_day": np.tile(rng[: n // 2].hour, 2),
            "day_of_week": np.tile(rng[: n // 2].dayofweek, 2),
            "month": np.tile(rng[: n // 2].month, 2),
            "day_of_year": np.tile(rng[: n // 2].dayofyear, 2),
        },
        index=idx,
    )


@pytest.fixture
def mini_cfg() -> dict:
    return {
        "seed": 42,
        "data": {"target_column": "Electricity_Imported_Total_kWh"},
        "features": {
            "cyclical": ["hour_of_day", "day_of_week", "month"],
            "lag_windows": [1, 2, 24],
            "rolling_windows": [6, 24],
            "rolling_stats": ["mean", "std"],
            "selection": {
                "variance_threshold": 0.0,
                "correlation_threshold": 0.99,
                "n_features_lgbm": 10,
            },
        },
    }


class TestTemporalFeatures:
    def test_cyclical_columns_added(self, mini_df, mini_cfg):
        from energy_forecast.features.temporal import build_temporal_features

        result = build_temporal_features(mini_df, mini_cfg)
        assert "hour_of_day_sin" in result.columns
        assert "hour_of_day_cos" in result.columns
        assert "month_sin" in result.columns

    def test_lag_columns_added(self, mini_df, mini_cfg):
        from energy_forecast.features.temporal import build_temporal_features

        result = build_temporal_features(mini_df, mini_cfg)
        assert "Electricity_Imported_Total_kWh_lag_1h" in result.columns
        assert "Electricity_Imported_Total_kWh_lag_24h" in result.columns

    def test_rolling_columns_added(self, mini_df, mini_cfg):
        from energy_forecast.features.temporal import build_temporal_features

        result = build_temporal_features(mini_df, mini_cfg)
        assert "Electricity_Imported_Total_kWh_roll_6h_mean" in result.columns
        assert "Electricity_Imported_Total_kWh_roll_24h_std" in result.columns

    def test_no_nan_after_feature_building(self, mini_df, mini_cfg):
        from energy_forecast.features.temporal import build_temporal_features

        result = build_temporal_features(mini_df, mini_cfg)
        assert result.isna().sum().sum() == 0, "NaN values remain after feature building"

    def test_cyclical_range(self, mini_df, mini_cfg):
        from energy_forecast.features.temporal import build_temporal_features

        result = build_temporal_features(mini_df, mini_cfg)
        assert result["hour_of_day_sin"].between(-1, 1).all()
        assert result["hour_of_day_cos"].between(-1, 1).all()
