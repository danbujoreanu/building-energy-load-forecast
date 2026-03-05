"""
features.temporal
=================
Generates all temporal features for the model-ready dataset:

    1. Cyclical (sin/cos) encoding of time periods
    2. Temperature × hour interaction features
    3. Lag features for target and key predictors
    4. Rolling window statistics (mean, std, min, max)

All operations are applied *per building* to avoid leaking data across
buildings.  NaN rows introduced by lag/rolling are dropped at the end.

The ``forecast_horizon`` config parameter controls which lags are permitted:
  - horizon=1  : all lags usable (single-step-ahead, H+1 evaluation)
  - horizon=24 : only lags ≥ 24h included (honest 24h-ahead evaluation)

Public API
----------
    build_temporal_features(df, cfg, target) -> pd.DataFrame
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Periods for each cyclical feature
_CYCLICAL_PERIODS: dict[str, int] = {
    "hour_of_day": 24,
    "day_of_week": 7,
    "month":       12,
    "day_of_year": 365,
}


def build_temporal_features(
    df: pd.DataFrame,
    cfg: dict[str, Any],
    target: str | None = None,
) -> pd.DataFrame:
    """Add lag, rolling-window, cyclical, and interaction features to the dataset.

    Parameters
    ----------
    df:
        MultiIndex (building_id, timestamp) model-ready DataFrame.
    cfg:
        Full config dict.
    target:
        Target column name.  Defaults to ``cfg["data"]["target_column"]``.

    Returns
    -------
    pd.DataFrame
        Extended DataFrame with new feature columns. NaN rows dropped.
    """
    target = target or cfg["data"]["target_column"]
    feat_cfg = cfg["features"]

    # ── Forecast horizon enforcement ──────────────────────────────────────────
    horizon: int = int(feat_cfg.get("forecast_horizon", 1))
    logger.info("Building temporal features (forecast_horizon=%dh) …", horizon)
    if horizon > 1:
        logger.info(
            "  horizon=%dh: removing lag/rolling features shorter than "
            "%dh to prevent oracle leakage.",
            horizon, horizon,
        )

    df = df.copy()

    # ── 1. Cyclical encoding ──────────────────────────────────────────────────
    for col in feat_cfg.get("cyclical", []):
        if col in df.columns:
            period = _CYCLICAL_PERIODS.get(col, 24)
            df = _add_cyclical(df, col, period)

    # ── 2. Interaction features ───────────────────────────────────────────────
    # Temperature × time-of-day: captures morning warm-up amplified by cold.
    if "Temperature_Outdoor_C" in df.columns and "hour_of_day_sin" in df.columns:
        df["temp_x_hour_sin"] = df["Temperature_Outdoor_C"] * df["hour_of_day_sin"]
    if "Temperature_Outdoor_C" in df.columns and "hour_of_day_cos" in df.columns:
        df["temp_x_hour_cos"] = df["Temperature_Outdoor_C"] * df["hour_of_day_cos"]
    # Is_Weekend + temperature × weekend: captures lower weekday/weekend occupancy.
    # Both features are in the thesis notebook and selected by LightGBM importance.
    if "day_of_week" in df.columns:
        df["Is_Weekend"] = (df["day_of_week"] >= 5).astype(int)
        if "Temperature_Outdoor_C" in df.columns:
            df["temp_x_is_weekend"] = df["Temperature_Outdoor_C"] * df["Is_Weekend"]

    # ── 3. Lag features (applied per building, horizon-aware) ─────────────────
    all_lag_windows: list[int] = feat_cfg.get("lag_windows", [1, 2, 3, 24, 25, 26, 48, 168])
    # Enforce minimum lag = forecast_horizon (no oracle leakage)
    lag_windows = [w for w in all_lag_windows if w >= horizon]
    if not lag_windows:
        lag_windows = [horizon]   # always include at least the horizon lag
    if len(lag_windows) < len(all_lag_windows):
        removed = sorted(set(all_lag_windows) - set(lag_windows))
        logger.info("  Removed oracle lags (< %dh): %s", horizon, removed)

    lag_sources = [target, "Temperature_Outdoor_C"]
    lag_sources = [c for c in lag_sources if c in df.columns]

    df = (
        df.groupby(level="building_id", group_keys=False)
        .apply(_add_lags, lag_sources=lag_sources, lags=lag_windows)
    )

    # ── 4. Rolling window statistics (per building, horizon-aware) ────────────
    all_roll_windows: list[int] = feat_cfg.get("rolling_windows", [3, 6, 12, 24, 72, 168])
    # Rolling windows < horizon would include future timesteps at prediction time
    roll_windows = [w for w in all_roll_windows if w >= horizon]
    if not roll_windows:
        roll_windows = [horizon]
    if len(roll_windows) < len(all_roll_windows):
        removed_r = sorted(set(all_roll_windows) - set(roll_windows))
        logger.info("  Removed oracle rolling windows (< %dh): %s", horizon, removed_r)

    roll_stats: list[str] = feat_cfg.get("rolling_stats", ["mean", "std", "min", "max"])
    roll_sources = [target, "Temperature_Outdoor_C"]
    roll_sources = [c for c in roll_sources if c in df.columns]

    df = (
        df.groupby(level="building_id", group_keys=False)
        .apply(_add_rolling, sources=roll_sources, windows=roll_windows, stats=roll_stats)
    )

    # ── 5. Drop NaN rows introduced by lag/rolling (warmup rows only) ─────────
    # Only drop on lag columns (first max_lag hours per building are NaN).
    # Do NOT drop on optional energy sub-meter columns that are legitimately
    # absent for buildings without those meters.
    before = len(df)
    lag_cols = [c for c in df.columns if "_lag_" in c]
    drop_subset = lag_cols if lag_cols else None
    df = df.dropna(subset=drop_subset)
    logger.info(
        "Temporal features added. Dropped %d NaN rows (lag warmup). "
        "Total features: %d  (horizon=%dh)",
        before - len(df),
        df.shape[1],
        horizon,
    )
    return df


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _add_cyclical(df: pd.DataFrame, col: str, period: int) -> pd.DataFrame:
    """Encode a cyclic column as sin and cos components."""
    radians = 2 * np.pi * df[col] / period
    df[f"{col}_sin"] = np.sin(radians)
    df[f"{col}_cos"] = np.cos(radians)
    return df


def _add_lags(
    group: pd.DataFrame,
    lag_sources: list[str],
    lags: list[int],
) -> pd.DataFrame:
    """Add lag features for a single building group."""
    for col in lag_sources:
        for lag in lags:
            group[f"{col}_lag_{lag}h"] = group[col].shift(lag)
    return group


def _add_rolling(
    group: pd.DataFrame,
    sources: list[str],
    windows: list[int],
    stats: list[str],
) -> pd.DataFrame:
    """Add rolling window statistics for a single building group.

    shift(1) is applied before rolling so that the rolling window at time t
    covers [t-w, t-1] rather than [t-w+1, t].  Without the shift, the target
    column at t would be included in its own rolling mean — classic target
    leakage.  This matches the thesis notebook implementation.
    """
    for col in sources:
        for w in windows:
            # shift(1) excludes the current timestep from its own rolling window
            roller = group[col].shift(1).rolling(window=w, min_periods=1)
            if "mean" in stats:
                group[f"{col}_roll_{w}h_mean"] = roller.mean()
            if "std" in stats:
                group[f"{col}_roll_{w}h_std"] = roller.std()
            if "min" in stats:
                group[f"{col}_roll_{w}h_min"] = roller.min()
            if "max" in stats:
                group[f"{col}_roll_{w}h_max"] = roller.max()
    return group
