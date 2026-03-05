"""
data.loader
===========
Parses raw building files for both Drammen and Oslo datasets into clean
pandas DataFrames.  All downstream code receives the same schema regardless
of city, implementing the **Pipe-and-Filter** pattern from the MSc module.

Drammen format
--------------
Semi-colon-delimited .txt files with a metadata header section followed by
hourly time-series data.  The header line index is stored in ``Header_line``.

Oslo format
-----------
CSV files with the same metadata header convention as Drammen.

Public API
----------
    load_city_data(city, raw_dir, cfg) -> tuple[pd.DataFrame, pd.DataFrame]
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column-name mapping: raw codes → human-readable names
# ---------------------------------------------------------------------------
_COLUMN_MAP: dict[str, str] = {
    "Tout":       "Temperature_Outdoor_C",
    "SolGlob":    "Global_Solar_Horizontal_Radiation_W_m2",
    "WindSpd":    "Wind_Speed_m_s",
    "WindDir":    "Wind_Direction_deg",
    "RH":         "Relative_Humidity_pct",
    "ElImp":      "Electricity_Imported_Total_kWh",
    "ElPV":       "Electricity_Production_PV_kWh",
    "ElLight":    "Electricity_Lighting_kWh",
    "ElBoil":     "Electricity_Electric_Boiler_kWh",
    "ElHP":       "Electricity_Heat_Pump_kWh",
    "ElEV":       "Electricity_EV_Charging_kWh",
    "ElTech":     "Electricity_Technical_Rooms_kWh",
    "ElPump":     "Electricity_Pumps_kWh",
    "ElSnow":     "Electricity_Snow_Melt_kWh",
    "HtTot":      "Heat_Total_kWh",
    "HtSpace":    "Heat_Space_Heating_kWh",
    "HtDHW":      "Heat_DHW_kWh",
    "HtVent":     "Heat_Ventilation_kWh",
    "HtHP":       "Heat_Heat_Pump_kWh",
    "HtDH":       "Heat_District_Heating_kWh",
    "HtSC":       "Heat_Solar_Collector_kWh",
    "HtSnow":     "Heat_Snow_Melt_kWh",
}

# Metadata keys written as-is from the file header
_META_KEYS = [
    "Header_line", "location", "year_of_construction", "floor_area",
    "number_of_users", "number_of_buildings", "building_category",
    "energy_label", "notes", "central_heating_system", "dhw_heat_source",
    "sh_heat_source", "ventilation_heat_source", "ventilation_types",
    "night_setback", "lighting_control", "pv", "timestamp_format",
    "time_zone", "building_id",
]

_NUMERIC_META = [
    "year_of_construction", "floor_area", "number_of_users",
    "number_of_buildings", "Header_line",
]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def load_city_data(
    city: str,
    raw_dir: str | Path,
    cfg: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load all building files for a city and return metadata + time-series.

    Parameters
    ----------
    city:
        ``"drammen"`` or ``"oslo"``.
    raw_dir:
        Directory containing the raw building files.
    cfg:
        Full config dict (loaded from config.yaml).

    Returns
    -------
    metadata : pd.DataFrame
        One row per building with building characteristics.
    timeseries : pd.DataFrame
        MultiIndex (building_id, timestamp) DataFrame with hourly readings.
    """
    raw_dir = Path(raw_dir)
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw data directory not found: {raw_dir}")

    # Both datasets are now provided as .txt files
    files = sorted(list(raw_dir.glob("*.txt")) + list(raw_dir.glob("*.csv")))
    if not files:
        raise FileNotFoundError(f"No building files (.txt or .csv) found in {raw_dir}")

    logger.info("Loading %d %s building files from %s", len(files), city, raw_dir)

    meta_rows: list[dict] = []
    ts_frames: list[pd.DataFrame] = []

    for fp in files:
        try:
            meta, ts = _parse_building_file(fp, cfg)
            meta_rows.append(meta)
            ts_frames.append(ts)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping %s — %s", fp.name, exc)

    metadata = pd.DataFrame(meta_rows)
    metadata = _coerce_metadata_types(metadata)

    timeseries = pd.concat(ts_frames, axis=0)
    timeseries = timeseries.sort_index()

    logger.info(
        "Loaded %d buildings | %d hourly rows | date range: %s → %s",
        len(metadata),
        len(timeseries),
        timeseries.index.get_level_values("timestamp").min().date(),
        timeseries.index.get_level_values("timestamp").max().date(),
    )
    return metadata, timeseries


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_building_file(
    filepath: Path,
    cfg: dict[str, Any],
) -> tuple[dict, pd.DataFrame]:
    """Parse a single building file into (metadata dict, timeseries DataFrame).

    Handles both Drammen .txt and Oslo .csv formats — they share the same
    header convention (key;value rows above the data table).
    """
    with filepath.open(encoding="utf-8", errors="replace") as fh:
        raw_lines = fh.readlines()

    # ── Step 1: extract metadata from header ─────────────────────────────────
    meta = _extract_metadata(raw_lines, filepath)

    # ── Step 2: find where the data table starts ──────────────────────────────
    # Header_line;22 means the column-header row is at 1-indexed line 22
    # (0-indexed: 21).  Data begins at the NEXT row (0-indexed: 22).
    header_line_idx = int(meta.get("Header_line", 22))  # 0-indexed first data row

    # ── Step 3: parse the abbreviated column names (1 row above data) ─────────
    abbrev_line_idx = header_line_idx - 1
    abbrev_line = raw_lines[abbrev_line_idx].strip().split(";")
    # First element is the timestamp column
    raw_col_names = ["TimeStamp"] + abbrev_line[1:]

    # ── Step 4: read the data section ─────────────────────────────────────────
    data_lines = raw_lines[header_line_idx:]
    rows = []
    for line in data_lines:
        parts = line.strip().split(";")
        if len(parts) < 2 or not parts[0]:
            continue
        rows.append(parts)

    df = pd.DataFrame(rows, columns=raw_col_names[: len(rows[0])] if rows else raw_col_names)

    # ── Step 5: parse timestamp ───────────────────────────────────────────────
    # Use per-building format if stored in metadata, else fall back to config,
    # then fall back to ISO8601 inference (handles non-standard formats).
    ts_fmt = meta.get("timestamp_format") or cfg["data"].get(
        "timestamp_format", "%Y-%m-%dT%H:%M:%S%z"
    )
    try:
        df["TimeStamp"] = pd.to_datetime(df["TimeStamp"], format=ts_fmt, utc=True)
    except (ValueError, TypeError):
        logger.debug(
            "Timestamp format '%s' failed for %s — falling back to ISO8601 inference",
            ts_fmt, filepath.name,
        )
        # BUG-C4: infer_datetime_format was deprecated in pandas 2.2 and removed
        # in pandas 3.0.  Pandas infers the format by default without the flag.
        df["TimeStamp"] = pd.to_datetime(df["TimeStamp"], utc=True)
    df["TimeStamp"] = df["TimeStamp"].dt.tz_convert("Europe/Oslo")

    # ── Step 6: rename columns & coerce numeric ───────────────────────────────
    rename_map = {k: v for k, v in _COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    numeric_cols = [c for c in df.columns if c != "TimeStamp"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    # ── Step 7: Wh → kWh conversion (energy columns stored as Wh in source) ──
    if cfg["data"].get("wh_to_kwh", True):
        kwh_cols = [c for c in df.columns if c.endswith("_kWh")]
        df[kwh_cols] = df[kwh_cols] / 1000.0

    # ── Step 8: add building_id and set MultiIndex ────────────────────────────
    building_id = int(meta["building_id"])
    df["building_id"] = building_id
    df = df.set_index(["building_id", "TimeStamp"])
    df.index.names = ["building_id", "timestamp"]

    # ── Step 9: drop duplicate timestamps ─────────────────────────────────────
    df = df[~df.index.duplicated(keep="first")]

    return meta, df


def _extract_metadata(lines: list[str], filepath: Path) -> dict:
    """Extract key-value metadata from the header section of a building file.

    Robustness fixes:
    - BOM (\\ufeff) is stripped from the first line (building_6412.txt).
    - Extra trailing semicolons on values are stripped (building_6417.txt,
      e.g. ``Header_line;24;;;;;;`` → stored value is ``"24"``).
    """
    meta: dict[str, str] = {}
    for line in lines:
        # Strip BOM (U+FEFF) that some editors prepend on Windows/Excel exports
        stripped = line.strip().lstrip("\ufeff")
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(";", 1)
        if len(parts) < 2:
            continue
        key = parts[0].strip()
        # Take only the first non-empty segment of the value (handles
        # lines like "Header_line;24;;;;;;" or "lighting_control;0;")
        raw_val = parts[1].strip()
        value = raw_val.split(";")[0].strip()
        if key in _META_KEYS:
            meta[key] = value

    # Fallback: derive building_id from filename if not in header
    if "building_id" not in meta:
        match = re.search(r"(\d+)", filepath.stem)
        meta["building_id"] = match.group(1) if match else filepath.stem

    return meta


def _coerce_metadata_types(df: pd.DataFrame) -> pd.DataFrame:
    """Convert numeric metadata columns from str to appropriate types."""
    for col in _NUMERIC_META:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "building_id" in df.columns:
        df["building_id"] = df["building_id"].astype(int)
    return df
