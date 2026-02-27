"""
data.preprocessing
==================
Cleans and validates the merged time-series DataFrame, producing a
``model_ready`` dataset suitable for feature engineering.

Steps (in order)
----------------
1. Remove buildings below the minimum data-completeness threshold.
2. Clip obvious sensor outliers (negative electricity, extreme temperatures).
3. Fill short gaps in weather data (forward-fill up to 3 hours).
4. Drop rows where the target variable is missing.
5. Save intermediate artefacts as Parquet for fast subsequent loads.

Public API
----------
    build_model_ready_data(timeseries, metadata, cfg) -> pd.DataFrame
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def build_model_ready_data(
    timeseries: pd.DataFrame,
    metadata: pd.DataFrame,
    cfg: dict[str, Any],
    processed_dir: str | Path | None = None,
) -> pd.DataFrame:
    """Transform raw merged time-series into a clean model-ready dataset.

    Parameters
    ----------
    timeseries:
        MultiIndex (building_id, timestamp) DataFrame from ``loader``.
    metadata:
        Building characteristics DataFrame from ``loader``.
    cfg:
        Full config dict.
    processed_dir:
        If provided, saves the model-ready parquet here.

    Returns
    -------
    pd.DataFrame
        Cleaned MultiIndex DataFrame with target variable and weather features.
    """
    target = cfg["data"]["target_column"]
    weather_cols = cfg["data"]["weather_columns"]
    min_completeness = cfg["data"].get("min_completeness", 0.70)

    df = timeseries.copy()

    # ── 1. Filter buildings below completeness threshold ──────────────────────
    df = _filter_by_completeness(df, target, min_completeness)

    # ── 2. Merge building metadata as additional columns ──────────────────────
    df = _merge_metadata(df, metadata)

    # ── 3. Clip outliers ──────────────────────────────────────────────────────
    df = _clip_outliers(df, target, weather_cols)

    # ── 4. Fill short weather gaps ────────────────────────────────────────────
    df = _fill_weather_gaps(df, weather_cols, max_hours=3)

    # ── 5. Drop rows where target is NaN ──────────────────────────────────────
    before = len(df)
    df = df.dropna(subset=[target])
    dropped = before - len(df)
    if dropped:
        logger.info("Dropped %d rows with missing target '%s'", dropped, target)

    # ── 6. Derive time-based features (deterministic, no leakage) ─────────────
    df = _add_calendar_features(df)

    logger.info(
        "Model-ready dataset: %d buildings, %d rows, %d columns",
        df.index.get_level_values("building_id").nunique(),
        len(df),
        df.shape[1],
    )

    # ── 7. Persist ────────────────────────────────────────────────────────────
    if processed_dir is not None:
        path = Path(processed_dir) / "model_ready.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path)
        logger.info("Saved model-ready data → %s", path)

    return df


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _filter_by_completeness(
    df: pd.DataFrame,
    target: str,
    threshold: float,
) -> pd.DataFrame:
    """Remove buildings where target completeness is below ``threshold``."""
    completeness = (
        df[target]
        .groupby(level="building_id")
        .apply(lambda s: s.notna().mean())
    )
    keep = completeness[completeness >= threshold].index
    removed = set(df.index.get_level_values("building_id").unique()) - set(keep)
    if removed:
        logger.warning(
            "Removing %d buildings below %.0f%% completeness: %s",
            len(removed), threshold * 100, sorted(removed),
        )
    return df.loc[df.index.get_level_values("building_id").isin(keep)]


def _merge_metadata(df: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    """Left-join building metadata onto time-series rows."""
    meta_cols = [
        "building_id", "building_category", "floor_area",
        "year_of_construction", "number_of_users", "energy_label",
        "sh_heat_source", "dhw_heat_source",
    ]
    available = [c for c in meta_cols if c in metadata.columns]
    meta_sub = metadata[available].set_index("building_id")

    df = df.join(meta_sub, on="building_id", how="left")
    return df


def _clip_outliers(
    df: pd.DataFrame,
    target: str,
    weather_cols: list[str],
) -> pd.DataFrame:
    """Clip physically implausible sensor values."""
    # Electricity cannot be negative
    if target in df.columns:
        negative_mask = df[target] < 0
        if negative_mask.any():
            logger.info(
                "Clipping %d negative electricity readings to 0",
                negative_mask.sum(),
            )
            df.loc[negative_mask, target] = np.nan

    # Temperature: Norway — plausible range [-40, +40] °C
    temp_col = "Temperature_Outdoor_C"
    if temp_col in df.columns:
        df[temp_col] = df[temp_col].clip(-40, 40)

    # Solar radiation: cannot be negative
    solar_col = "Global_Solar_Horizontal_Radiation_W_m2"
    if solar_col in df.columns:
        df[solar_col] = df[solar_col].clip(lower=0)

    # Wind speed: cannot be negative
    wind_col = "Wind_Speed_m_s"
    if wind_col in df.columns:
        df[wind_col] = df[wind_col].clip(lower=0)

    return df


def _fill_weather_gaps(
    df: pd.DataFrame,
    weather_cols: list[str],
    max_hours: int = 3,
) -> pd.DataFrame:
    """Forward-fill short gaps in weather columns within each building."""
    cols = [c for c in weather_cols if c in df.columns]
    if not cols:
        return df

    df = df.copy()
    df[cols] = (
        df[cols]
        .groupby(level="building_id", group_keys=False)
        .apply(lambda g: g.ffill(limit=max_hours))
    )
    return df


def _add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add deterministic calendar columns (no future information used)."""
    ts = df.index.get_level_values("timestamp")
    df = df.copy()
    df["hour_of_day"]  = ts.hour
    df["day_of_week"]  = ts.dayofweek        # 0=Monday … 6=Sunday
    df["day_of_year"]  = ts.dayofyear
    df["month"]        = ts.month
    df["is_weekend"]   = (ts.dayofweek >= 5).astype(int)
    return df
