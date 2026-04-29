"""
energy_forecast.api.esb_parser
================================
Parse ESB Networks HDF CSV files into meter_readings rows.

Supported formats (auto-detected by Read Type column):
  - kW  files: "Active Import/Export Interval (kW)"  → multiply × 0.5 → kWh
  - kWh files: "Active Import/Export Interval (kWh)" → use directly

Expected CSV columns (ESB Networks standard export):
  MPRN | Meter Serial Number | Read Value | Read Type | Read Date and End Time

Date format: DD-MM-YYYY HH:MM (local Irish time, treated as UTC for simplicity —
ESB HDF timestamps are already end-of-interval in Irish Standard Time but the
difference is small relative to 30-min resolution; an IST→UTC offset can be
added in Phase 2 when multi-timezone support is required).
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)

_REQUIRED_COLUMNS = {
    "MPRN",
    "Read Value",
    "Read Type",
    "Read Date and End Time",
}

_IMPORT_PATTERNS = ("Active Import Interval (kW)", "Active Import Interval (kWh)")
_EXPORT_PATTERNS = ("Active Export Interval (kW)", "Active Export Interval (kWh)")


class ESBParseError(ValueError):
    """Raised when the uploaded file doesn't match the expected ESB format."""


def parse_esb_csv(contents: bytes) -> tuple[str, list[dict]]:
    """Parse raw bytes of an ESB HDF CSV file.

    Returns:
        (mprn, rows) where rows is a list of dicts ready for upsert_meter_readings.
        Each row: {recorded_at: datetime (UTC), import_kwh: float, export_kwh: float}

    Raises:
        ESBParseError on format mismatch.
    """
    try:
        df = pd.read_csv(io.BytesIO(contents), dtype=str)
    except Exception as exc:
        raise ESBParseError(f"Could not parse file as CSV: {exc}") from exc

    df.columns = df.columns.str.strip()
    missing = _REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ESBParseError(
            f"Missing required columns: {sorted(missing)}. "
            f"Expected ESB HDF format with columns: {sorted(_REQUIRED_COLUMNS)}."
        )

    df["Read Type"] = df["Read Type"].str.strip()
    df["Read Value"] = pd.to_numeric(df["Read Value"], errors="coerce")
    df["MPRN"] = df["MPRN"].str.strip()

    mprns = df["MPRN"].dropna().unique()
    if len(mprns) == 0:
        raise ESBParseError("No valid MPRN found in file.")
    mprn = str(mprns[0])

    import_mask = df["Read Type"].str.startswith("Active Import Interval")
    export_mask = df["Read Type"].str.startswith("Active Export Interval")

    if not import_mask.any():
        raise ESBParseError(
            "No import readings found. "
            "File must contain 'Active Import Interval (kW)' or '(kWh)' rows."
        )

    def _is_kw(read_type_series: pd.Series) -> bool:
        sample = read_type_series.dropna().iloc[0] if not read_type_series.dropna().empty else ""
        return sample.endswith("(kW)")

    imports = df[import_mask].copy()
    exports = df[export_mask].copy()

    imports["recorded_at"] = pd.to_datetime(
        imports["Read Date and End Time"].str.strip(),
        format="%d-%m-%Y %H:%M",
        utc=True,
    )
    imports["import_kwh"] = imports["Read Value"] * (0.5 if _is_kw(imports["Read Type"]) else 1.0)

    if not exports.empty:
        exports["recorded_at"] = pd.to_datetime(
            exports["Read Date and End Time"].str.strip(),
            format="%d-%m-%Y %H:%M",
            utc=True,
        )
        exports["export_kwh"] = exports["Read Value"] * (0.5 if _is_kw(exports["Read Type"]) else 1.0)
        merged = imports[["recorded_at", "import_kwh"]].merge(
            exports[["recorded_at", "export_kwh"]],
            on="recorded_at",
            how="left",
        )
        merged["export_kwh"] = merged["export_kwh"].fillna(0.0)
    else:
        merged = imports[["recorded_at", "import_kwh"]].copy()
        merged["export_kwh"] = 0.0

    merged = merged.dropna(subset=["recorded_at", "import_kwh"])
    merged = merged.drop_duplicates(subset=["recorded_at"])

    rows = merged.to_dict(orient="records")
    logger.info("Parsed %d readings for MPRN %s", len(rows), mprn)
    return mprn, rows
