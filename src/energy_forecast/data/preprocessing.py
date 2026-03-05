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

from energy_forecast.data.imputation import impute_missing_weather, impute_missing_metadata

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

    # ── 4b. Impute remaining weather & metadata gaps via MICE ─────────────────
    df = impute_missing_weather(df, weather_cols)
    df = impute_missing_metadata(df)

    # ── 5. Drop rows where target is NaN ──────────────────────────────────────
    before = len(df)
    df = df.dropna(subset=[target])
    dropped = before - len(df)
    if dropped:
        logger.info("Dropped %d rows with missing target '%s'", dropped, target)

    # ── 5b. Drop sparse columns (not measured at most buildings) ──────────────
    col_min_coverage = cfg["data"].get("column_min_coverage", 0.50)
    before_cols = df.shape[1]
    coverage = df.notna().mean()
    keep_cols = coverage[coverage >= col_min_coverage].index.tolist()
    dropped_cols = before_cols - len(keep_cols)
    if dropped_cols:
        sparse = sorted(c for c in df.columns if c not in keep_cols)
        logger.info(
            "Dropped %d sparse columns (< %.0f%% coverage): %s",
            dropped_cols, col_min_coverage * 100, sparse,
        )
    df = df[keep_cols]

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
    """Left-join building metadata onto time-series rows.

    Applies intelligent imputation for ``number_of_users`` before joining:
      - Uses category-specific median users-per-sqm density (matching the
        MSc thesis EDA notebook approach).
      - Buildings: 6411 (Off), 6413 (Sch), 6441 (Off) had missing values
        in the original dataset.
      - If no same-category reference exists (e.g. both Offices missing),
        falls back to the global median users-per-sqm.
    """
    meta_cols = [
        "building_id", "building_category", "floor_area",
        "year_of_construction", "number_of_users", "energy_label",
        "sh_heat_source", "dhw_heat_source",
    ]
    available = [c for c in meta_cols if c in metadata.columns]
    meta = metadata[available].copy()

    # ── Intelligent number_of_users imputation ────────────────────────────────
    if "number_of_users" in meta.columns and "floor_area" in meta.columns and \
       "building_category" in meta.columns:
        meta = _impute_number_of_users(meta)

    # ── Derive central_heating_system (matches thesis feature set) ────────────
    # Binary indicator: 1 = centralised system (boiler, heat pump, district
    # heating); 0 = distributed electric heating (EH / EFH).
    # Rule: primary heat source (first token before comma) is EH or EFH → 0.
    # Derived from sh_heat_source column; matches consolidated_building_metadata.csv.
    if "sh_heat_source" in meta.columns:
        def _to_central(val: str | float) -> int:
            if pd.isna(val):
                return 0
            primary = str(val).split(",")[0].strip()
            return 0 if primary in ("EH", "EFH") else 1
        meta["central_heating_system"] = meta["sh_heat_source"].apply(_to_central)
        logger.info(
            "Derived central_heating_system: %d centralised, %d distributed",
            meta["central_heating_system"].sum(),
            (meta["central_heating_system"] == 0).sum(),
        )

    meta_sub = meta.set_index("building_id")
    df = df.join(meta_sub, on="building_id", how="left")
    return df


def _impute_number_of_users(meta: pd.DataFrame) -> pd.DataFrame:
    """Impute missing number_of_users using category-specific user density.

    Method (matches MSc thesis EDA notebook):
    1. Compute median users/m² for each building_category from complete rows.
    2. For missing buildings: imputed_users = category_density × floor_area.
    3. If the category has NO complete reference rows (e.g. all Offices missing),
       fall back to the global median density.

    Buildings with missing values in the Drammen dataset:
        6411 (Off, 8424 m²) — no other Office reference → global fallback
        6413 (Sch, 5086 m²) — median School density = 0.079 users/m² → ~402
        6441 (Off, 1510 m²) — no other Office reference → global fallback
    """
    missing_mask = meta["number_of_users"].isna()
    if not missing_mask.any():
        return meta

    # Compute users-per-sqm from buildings with complete data
    complete = meta.dropna(subset=["number_of_users", "floor_area"])
    complete = complete[complete["floor_area"] > 0]

    # Category-level median density
    cat_density = (
        complete
        .assign(density=complete["number_of_users"] / complete["floor_area"])
        .groupby("building_category")["density"]
        .median()
    )
    global_density = (
        complete["number_of_users"] / complete["floor_area"]
    ).median()

    meta = meta.copy()
    imputed_info = []
    for idx, row in meta[missing_mask].iterrows():
        cat = row.get("building_category")
        area = row.get("floor_area", np.nan)
        if pd.isna(area) or area <= 0:
            continue
        density = cat_density.get(cat, global_density)
        source = "category" if cat in cat_density.index else "global"
        imputed_val = round(density * area)
        meta.at[idx, "number_of_users"] = imputed_val
        imputed_info.append(
            f"building {row['building_id']} ({cat}, {area:.0f} m²) → "
            f"{imputed_val:.0f} users  [{source} density={density:.4f}]"
        )

    if imputed_info:
        logger.info(
            "Imputed number_of_users for %d buildings (thesis-style category density):\n  %s",
            len(imputed_info), "\n  ".join(imputed_info),
        )

    return meta


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
