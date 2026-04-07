"""Integration tests — full feature → split → train → evaluate pipeline.

These tests exercise the critical path end-to-end on synthetic data to catch:
  - Feature/label horizon misalignment
  - Temporal leakage (future data in training)
  - Silent config mismatches (forecast_horizon vs sequence.horizon)
  - Shape and NaN errors across pipeline stages
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

N_HOURS = 2000  # per building — enough lag warmup + meaningful test split
N_BUILDINGS = 2
TOTAL_ROWS = N_HOURS * N_BUILDINGS

START = pd.Timestamp("2022-01-01", tz="Europe/Oslo")
# 2000h window ≈ 83 days, ends ~2022-03-25.
# Splits: train=first 60% (~50 days), val=next 20% (~16 days), test=last 20%.
TRAIN_END = pd.Timestamp("2022-02-20", tz="Europe/Oslo")
VAL_END = pd.Timestamp("2022-03-08", tz="Europe/Oslo")


@pytest.fixture(scope="module")
def synthetic_df() -> pd.DataFrame:
    """Synthetic MultiIndex (building_id, timestamp) DataFrame.

    Matches the schema expected by build_temporal_features and make_splits.
    Uses a simple deterministic pattern so tests are reproducible.
    """
    rng_dt = pd.date_range(START, periods=N_HOURS, freq="h", tz="Europe/Oslo")
    hours = rng_dt.hour.to_numpy()
    rng = np.random.default_rng(0)

    # Realistic-ish load: morning + evening peaks + noise
    base = (
        10
        + 8 * np.exp(-((hours - 8) ** 2) / 10)
        + 12 * np.exp(-((hours - 18) ** 2) / 8)
        + rng.normal(0, 1, N_HOURS)
    )

    buildings = []
    for bid in range(1, N_BUILDINGS + 1):
        scale = 1.0 + 0.2 * bid
        df_b = pd.DataFrame(
            {
                "Electricity_Imported_Total_kWh": np.clip(base * scale, 1, 80),
                "Temperature_Outdoor_C": (
                    5 + 10 * np.sin(2 * np.pi * rng_dt.dayofyear / 365)
                    + rng.normal(0, 1, N_HOURS)
                ),
                "Global_Solar_Horizontal_Radiation_W_m2": np.clip(
                    300 * np.sin(np.pi * hours / 24).clip(min=0)
                    + rng.normal(0, 20, N_HOURS),
                    0, None,
                ),
                "hour_of_day": hours,
                "day_of_week": rng_dt.dayofweek,
                "month": rng_dt.month,
                "day_of_year": rng_dt.dayofyear,
            },
            index=pd.MultiIndex.from_arrays(
                [np.full(N_HOURS, bid), rng_dt],
                names=["building_id", "timestamp"],
            ),
        )
        buildings.append(df_b)

    return pd.concat(buildings)


@pytest.fixture(scope="module")
def cfg() -> dict:
    """Minimal config dict for H+24 evaluation (no sequence.horizon collision)."""
    return {
        "seed": 42,
        "data": {"target_column": "Electricity_Imported_Total_kWh"},
        "features": {
            "forecast_horizon": 24,
            "cyclical": ["hour_of_day", "day_of_week", "month"],
            "lag_windows": [24, 25, 48, 168],
            "rolling_windows": [24, 48, 168],
            "rolling_stats": ["mean", "std"],
        },
        "splits": {
            "train_end": TRAIN_END.isoformat(),
            "val_end": VAL_END.isoformat(),
        },
    }


# ---------------------------------------------------------------------------
# Test 1: Feature engineering produces valid output
# ---------------------------------------------------------------------------

class TestFeatureEngineering:
    def test_features_no_nan(self, synthetic_df, cfg):
        from energy_forecast.features.temporal import build_temporal_features

        result = build_temporal_features(synthetic_df, cfg)
        assert result.isna().sum().sum() == 0, "NaN values remain after feature building"

    def test_lag_horizon_enforced(self, synthetic_df, cfg):
        """Lags shorter than forecast_horizon must be absent — prevents oracle leakage."""
        from energy_forecast.features.temporal import build_temporal_features

        result = build_temporal_features(synthetic_df, cfg)
        lag_cols = [c for c in result.columns if "_lag_" in c]
        for col in lag_cols:
            lag_h = int(col.split("_lag_")[1].replace("h", ""))
            assert lag_h >= cfg["features"]["forecast_horizon"], (
                f"Oracle lag detected: {col} (lag={lag_h}h) < "
                f"horizon={cfg['features']['forecast_horizon']}h"
            )

    def test_rolling_horizon_enforced(self, synthetic_df, cfg):
        """Rolling windows shorter than horizon must be absent."""
        from energy_forecast.features.temporal import build_temporal_features

        result = build_temporal_features(synthetic_df, cfg)
        roll_cols = [c for c in result.columns if "_roll_" in c]
        for col in roll_cols:
            w = int(col.split("_roll_")[1].split("h_")[0])
            assert w >= cfg["features"]["forecast_horizon"], (
                f"Oracle rolling window detected: {col} (w={w}h) < "
                f"horizon={cfg['features']['forecast_horizon']}h"
            )

    def test_cyclical_features_in_range(self, synthetic_df, cfg):
        from energy_forecast.features.temporal import build_temporal_features

        result = build_temporal_features(synthetic_df, cfg)
        for col in ["hour_of_day_sin", "hour_of_day_cos", "day_of_week_sin", "month_sin"]:
            assert col in result.columns
            assert result[col].between(-1.0, 1.0).all(), f"{col} out of [-1, 1]"

    def test_row_count_reduced_by_warmup_only(self, synthetic_df, cfg):
        """After feature building, rows lost should be bounded by lag warmup (not more)."""
        from energy_forecast.features.temporal import build_temporal_features

        result = build_temporal_features(synthetic_df, cfg)
        max_lag = max(cfg["features"]["lag_windows"])
        # Each building loses max_lag warmup rows
        min_expected = TOTAL_ROWS - max_lag * N_BUILDINGS
        assert len(result) >= min_expected, (
            f"Too many rows dropped: {TOTAL_ROWS - len(result)} lost, "
            f"expected at most {max_lag * N_BUILDINGS} (lag warmup)"
        )


# ---------------------------------------------------------------------------
# Test 2: Temporal leakage guard
# ---------------------------------------------------------------------------

class TestNoTemporalLeakage:
    def test_test_timestamps_after_val_end(self, synthetic_df, cfg):
        """Test set must contain no rows from training or validation windows."""
        from energy_forecast.data.splits import make_splits
        from energy_forecast.features.temporal import build_temporal_features

        featured = build_temporal_features(synthetic_df, cfg)
        splits = make_splits(featured, cfg)

        test_ts = splits["X_test"].index.get_level_values("timestamp")
        assert (test_ts > VAL_END).all(), (
            "LEAKAGE DETECTED: test split contains rows from before val_end"
        )

    def test_val_timestamps_after_train_end(self, synthetic_df, cfg):
        """Validation set must not overlap with training window."""
        from energy_forecast.data.splits import make_splits
        from energy_forecast.features.temporal import build_temporal_features

        featured = build_temporal_features(synthetic_df, cfg)
        splits = make_splits(featured, cfg)

        val_ts = splits["X_val"].index.get_level_values("timestamp")
        assert (val_ts > TRAIN_END).all(), (
            "LEAKAGE DETECTED: val split contains rows from training window"
        )

    def test_splits_disjoint(self, synthetic_df, cfg):
        """Train, val, and test sets must be mutually exclusive in time."""
        from energy_forecast.data.splits import make_splits
        from energy_forecast.features.temporal import build_temporal_features

        featured = build_temporal_features(synthetic_df, cfg)
        splits = make_splits(featured, cfg)

        train_ts = set(splits["X_train"].index.get_level_values("timestamp"))
        val_ts   = set(splits["X_val"].index.get_level_values("timestamp"))
        test_ts  = set(splits["X_test"].index.get_level_values("timestamp"))

        assert train_ts.isdisjoint(val_ts),  "Train/val overlap detected"
        assert train_ts.isdisjoint(test_ts), "Train/test overlap detected"
        assert val_ts.isdisjoint(test_ts),   "Val/test overlap detected"


# ---------------------------------------------------------------------------
# Test 3: Config horizon mismatch guard
# ---------------------------------------------------------------------------

class TestHorizonAssertionGuard:
    def test_mismatched_horizons_raise(self, synthetic_df):
        """features.forecast_horizon != sequence.horizon must raise AssertionError."""
        from energy_forecast.features.temporal import build_temporal_features

        bad_cfg = {
            "data": {"target_column": "Electricity_Imported_Total_kWh"},
            "features": {
                "forecast_horizon": 24,
                "cyclical": [],
                "lag_windows": [24],
                "rolling_windows": [24],
                "rolling_stats": ["mean"],
            },
            "sequence": {"horizon": 12},  # deliberate mismatch
        }
        with pytest.raises(AssertionError, match="Config mismatch"):
            build_temporal_features(synthetic_df, bad_cfg)

    def test_matching_horizons_ok(self, synthetic_df):
        """features.forecast_horizon == sequence.horizon must not raise."""
        from energy_forecast.features.temporal import build_temporal_features

        good_cfg = {
            "data": {"target_column": "Electricity_Imported_Total_kWh"},
            "features": {
                "forecast_horizon": 24,
                "cyclical": [],
                "lag_windows": [24],
                "rolling_windows": [24],
                "rolling_stats": ["mean"],
            },
            "sequence": {"horizon": 24},  # consistent
        }
        # Should not raise
        build_temporal_features(synthetic_df, good_cfg)


# ---------------------------------------------------------------------------
# Test 4: Full pipeline — train LightGBM and check accuracy
# ---------------------------------------------------------------------------

class TestEndToEndLightGBM:
    def test_lgbm_trains_and_achieves_positive_r2(self, synthetic_df, cfg):
        """LightGBM trained on features must beat a naive mean baseline (R² > 0)."""
        from lightgbm import LGBMRegressor

        from energy_forecast.data.splits import make_splits
        from energy_forecast.features.temporal import build_temporal_features

        featured = build_temporal_features(synthetic_df, cfg)
        splits = make_splits(featured, cfg)

        model = LGBMRegressor(
            n_estimators=50, learning_rate=0.1, num_leaves=31, verbose=-1, random_state=42
        )
        model.fit(splits["X_train"], splits["y_train"])

        preds = model.predict(splits["X_test"])
        y_test = splits["y_test"].values

        ss_res = np.sum((y_test - preds) ** 2)
        ss_tot = np.sum((y_test - y_test.mean()) ** 2)
        r2 = 1.0 - ss_res / ss_tot

        assert r2 > 0, f"LightGBM R²={r2:.4f} — worse than mean baseline. Check for leakage or feature errors."

    def test_scaler_fitted_on_train_only(self, synthetic_df, cfg):
        """Scaler mean/scale must be derived from training data statistics."""
        from energy_forecast.data.splits import make_splits
        from energy_forecast.features.temporal import build_temporal_features

        featured = build_temporal_features(synthetic_df, cfg)
        splits = make_splits(featured, cfg)

        scaler = splits["scaler"]
        # Scaler was fit on X_train; its mean should be close to X_train unscaled mean
        # After scaling, X_train should have mean ≈ 0 and std ≈ 1
        x_train_scaled = splits["X_train"]
        col_means = x_train_scaled.mean()
        col_stds  = x_train_scaled.std()

        assert col_means.abs().max() < 1e-6, "Scaled X_train mean is not ≈ 0 — scaler may be fitted on wrong data"
        assert (col_stds - 1.0).abs().max() < 0.1, "Scaled X_train std is not ≈ 1 — check StandardScaler fit"
