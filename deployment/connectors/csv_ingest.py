"""
deployment.connectors.csv_ingest
=================================
CSVConnector — reads historical data from committed parquet files.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .base import DataConnector

logger = logging.getLogger(__name__)


class CSVConnector(DataConnector):
    """Read historical data from committed parquet files.

    This is the default connector for testing and demo purposes.  It uses
    the ``model_ready.parquet`` file produced by the pipeline's Stage 2.

    Parameters
    ----------
    data_dir:
        Path to ``data/processed/``.  Defaults to ``data/processed/`` relative
        to the repository root.
    """

    # Columns that must be present after loading the parquet file
    _REQUIRED_COLUMNS: frozenset[str] = frozenset({
        "Electricity_Imported_Total_kWh",
        "Temperature_Outdoor_C",
        "Global_Solar_Horizontal_Radiation_W_m2",
    })

    @classmethod
    def _validate_schema(cls, df: pd.DataFrame) -> None:
        """Validate that the loaded DataFrame has the expected schema.

        Checks:
        1. Required columns are present (raises ValueError with missing list).
        2. Warns about unexpected extra columns (lenient — does not raise).
        3. The DataFrame index is a tz-aware DatetimeIndex (raises ValueError if not).

        Args:
            df: The DataFrame returned after loading the parquet file
                (with building_id level already dropped).

        Raises:
            ValueError: If required columns are missing or the index is not
                a tz-aware DatetimeIndex.
        """
        # 1. Required columns check
        missing = cls._REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(
                f"[CSVConnector._validate_schema] Required columns missing: "
                f"{sorted(missing)}. "
                f"Available columns: {sorted(df.columns.tolist())}"
            )
        print(f"[CSVConnector._validate_schema] Required columns OK: {sorted(cls._REQUIRED_COLUMNS)}")

        # 2. Unexpected extra columns (warn only)
        known_columns = cls._REQUIRED_COLUMNS | {
            "Wind_Speed_m_s", "Wind_Direction_deg", "Relative_Humidity_pct",
            "hour_of_day", "day_of_week", "month", "day_of_year", "is_weekend",
        }
        extra = set(df.columns) - known_columns
        if extra:
            print(
                f"[CSVConnector._validate_schema] WARNING: unexpected extra columns "
                f"(ignored): {sorted(extra)}"
            )

        # 3. Index must be a tz-aware DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError(
                f"[CSVConnector._validate_schema] Index must be a DatetimeIndex, "
                f"got {type(df.index).__name__}."
            )
        if df.index.tz is None:
            raise ValueError(
                "[CSVConnector._validate_schema] DatetimeIndex must be tz-aware "
                "(expected UTC or local timezone). Call df.index = df.index.tz_localize('UTC') "
                "or ensure the parquet file was written with tz-aware timestamps."
            )
        print(
            f"[CSVConnector._validate_schema] DatetimeIndex OK: tz={df.index.tz}, "
            f"n_rows={len(df)}"
        )

    def __init__(self, data_dir: str | Path = "data/processed") -> None:
        self.data_dir = Path(data_dir)

    def fetch_last_n_hours(
        self,
        building_id: str,
        n_hours: int = 72,
        city: str = "drammen",
    ) -> pd.DataFrame:
        parquet_path = self.data_dir / "model_ready.parquet"
        if not parquet_path.exists():
            raise FileNotFoundError(
                f"Processed parquet not found at {parquet_path}. "
                "Run the pipeline first: python scripts/run_pipeline.py --city drammen --stages features"
            )

        df = pd.read_parquet(parquet_path)

        # Filter to requested building
        if "building_id" in df.index.names:
            building_mask = df.index.get_level_values("building_id") == building_id
            df = df[building_mask]
            if df.empty:
                raise ValueError(
                    f"Building '{building_id}' not found in {parquet_path}. "
                    f"Available: {df.index.get_level_values('building_id').unique().tolist()[:5]}"
                )
            df = df.droplevel("building_id")

        df.index = pd.to_datetime(df.index, utc=True)
        df = df.sort_index()
        result = df.iloc[-n_hours:]

        # Validate schema on the returned slice
        self._validate_schema(result)

        logger.info(
            "CSVConnector: loaded %d rows for building=%s from %s",
            len(result), building_id, parquet_path,
        )
        return result
