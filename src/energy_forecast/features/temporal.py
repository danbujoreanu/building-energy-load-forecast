"""
features.temporal
=================
Generates all temporal features for the model-ready dataset:

    1. Cyclical (sin/cos) encoding of time periods
    2. Lag features for target and key predictors
    3. Rolling window statistics (mean, std)

All operations are applied *per building* to avoid leaking data across
buildings.  NaN rows introduced by lag/rolling are dropped at the end.

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
    """Add lag, rolling-window, and cyclical features to the dataset.

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

    logger.info("Building temporal features ...")
    df = df.copy()

    # ── 1. Cyclical encoding ──────────────────────────────────────────────────
    for col in feat_cfg.get("cyclical", []):
        if col in df.columns:
            period = _CYCLICAL_PERIODS.get(col, 24)
            df = _add_cyclical(df, col, period)

    # ── 2. Lag features (applied per building) ────────────────────────────────
    lag_windows: list[int] = feat_cfg.get("lag_windows", [1, 2, 3, 6, 12, 24])
    lag_sources = [target, "Temperature_Outdoor_C"]
    lag_sources = [c for c in lag_sources if c in df.columns]

    df = (
        df.groupby(level="building_id", group_keys=False)
        .apply(_add_lags, lag_sources=lag_sources, lags=lag_windows)
    )

    # ── 3. Rolling window statistics (per building) ───────────────────────────
    roll_windows: list[int] = feat_cfg.get("rolling_windows", [6, 12, 24, 48])
    roll_stats:   list[str] = feat_cfg.get("rolling_stats", ["mean", "std"])
    roll_sources = [target, "Temperature_Outdoor_C"]
    roll_sources = [c for c in roll_sources if c in df.columns]

    df = (
        df.groupby(level="building_id", group_keys=False)
        .apply(_add_rolling, sources=roll_sources, windows=roll_windows, stats=roll_stats)
    )

    # ── 4. Drop NaN rows introduced by lag/rolling ────────────────────────────
    before = len(df)
    df = df.dropna()
    logger.info(
        "Temporal features added. Dropped %d NaN rows (from lag/rolling). "
        "Total features: %d",
        before - len(df),
        df.shape[1],
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
    """Add rolling window statistics for a single building group."""
    for col in sources:
        for w in windows:
            roller = group[col].rolling(window=w, min_periods=1)
            if "mean" in stats:
                group[f"{col}_roll_{w}h_mean"] = roller.mean()
            if "std" in stats:
                group[f"{col}_roll_{w}h_std"] = roller.std()
    return group
