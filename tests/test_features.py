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


# ---------------------------------------------------------------------------
# LoadDisaggregator tests — DAN-164 Stream 1
# ---------------------------------------------------------------------------

class TestLoadDisaggregator:
    def test_happy_path(self):
        from energy_forecast.features.load_disaggregation import LoadDisaggregator
        df = pd.DataFrame({"import_kwh": [1.2, 0.8, 0.5], "eddi_kwh": [0.3, 0.0, 0.6]})
        result = LoadDisaggregator.separate_eddi_load(df)
        assert "base_load_kwh" in result.columns
        assert result["base_load_kwh"].round(4).tolist() == [0.9, 0.8, 0.0]  # 0.5-0.6 clipped to 0

    def test_no_negative_base_load(self):
        from energy_forecast.features.load_disaggregation import LoadDisaggregator
        df = pd.DataFrame({"import_kwh": [0.2], "eddi_kwh": [1.0]})
        result = LoadDisaggregator.separate_eddi_load(df)
        assert result["base_load_kwh"].iloc[0] == 0.0

    def test_missing_eddi_treated_as_zero(self):
        from energy_forecast.features.load_disaggregation import LoadDisaggregator
        df = pd.DataFrame({"import_kwh": [1.0], "eddi_kwh": [float("nan")]})
        result = LoadDisaggregator.separate_eddi_load(df)
        assert result["base_load_kwh"].iloc[0] == 1.0

    def test_missing_column_raises(self):
        from energy_forecast.features.load_disaggregation import LoadDisaggregator
        df = pd.DataFrame({"import_kwh": [1.0]})
        with pytest.raises(ValueError, match="eddi_kwh"):
            LoadDisaggregator.separate_eddi_load(df)


# ---------------------------------------------------------------------------
# SolarBaselineModel tests — DAN-164 Stream 2
# ---------------------------------------------------------------------------

class TestSolarBaselineModel:
    def test_zero_pv_returns_zeros(self):
        from energy_forecast.features.solar_baseline import SolarBaselineModel
        model = SolarBaselineModel(pv_peak_power_kw=0.0)
        result = model.predict(hours_ahead=24, cloud_coverage=[50.0] * 24)
        assert result == [0.0] * 24

    def test_daytime_positive_nighttime_zero(self):
        from energy_forecast.features.solar_baseline import SolarBaselineModel
        from datetime import datetime
        model = SolarBaselineModel(pv_peak_power_kw=4.0)
        # Summer noon in Dublin — should produce positive output
        noon = datetime(2026, 6, 21, 12, 0)
        result = model.predict(hours_ahead=1, cloud_coverage=[0.0], start_time=noon)
        assert result[0] > 0.0, "Expected positive PV output at noon"

    def test_midnight_output_zero(self):
        from energy_forecast.features.solar_baseline import SolarBaselineModel
        from datetime import datetime
        model = SolarBaselineModel(pv_peak_power_kw=4.0)
        midnight = datetime(2026, 6, 21, 0, 0)
        result = model.predict(hours_ahead=1, cloud_coverage=[0.0], start_time=midnight)
        assert result[0] == 0.0, "Expected zero PV output at midnight"

    def test_full_cloud_reduces_output(self):
        from energy_forecast.features.solar_baseline import SolarBaselineModel
        from datetime import datetime
        model = SolarBaselineModel(pv_peak_power_kw=4.0)
        noon = datetime(2026, 6, 21, 12, 0)
        clear = model.predict(1, [0.0], noon)[0]
        overcast = model.predict(1, [100.0], noon)[0]
        assert overcast < clear, "Overcast should reduce output vs clear sky"
