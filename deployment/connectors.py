"""
deployment.connectors
======================
Abstract connector interfaces and concrete implementations for the
real-world data-ingestion and device-control layers of the
Building Energy Load Forecast system.

Three connector families
------------------------
DataConnector   — fetch recent historical load + weather time-series
PriceConnector  — fetch day-ahead electricity prices (EUR/kWh per hour)
DeviceConnector — send control commands to managed devices (eddi, HVAC)

Implementations
---------------
DataConnector
  CSVConnector         — reads from committed parquet/CSV files (test/demo)
  OpenMeteoConnector   — live weather + solar forecast (Open-Meteo free API)
  EcowittConnector     — Ecowitt cloud API [STUB — pending hardware]
  MQTTConnector        — MQTT topic subscriber [STUB — pending broker]

PriceConnector
  MockPriceConnector   — realistic Irish day-ahead price curve (demo mode)
  SEMOConnector        — SEMO day-ahead prices [STUB — pending scraper]

DeviceConnector
  MockDeviceConnector  — logs command to stdout (demo / CI mode)
  MyEnergiConnector    — myenergi eddi API [STUB — pending API key]
"""

from __future__ import annotations

import logging
import math
import os
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DATA CONNECTORS
# ---------------------------------------------------------------------------


class DataConnector(ABC):
    """Abstract base class for historical load + weather data ingestion.

    Implementations must return a DataFrame with (at minimum):
      - Index: DatetimeIndex (hourly, UTC)
      - ``Electricity_Imported_Total_kWh``  — target load column
      - ``Temperature_Outdoor_C``           — outdoor temperature
      - ``Global_Solar_Horizontal_Radiation_W_m2`` — solar irradiance (may be NaN)

    The DataFrame must contain at least ``n_hours`` rows so that the
    feature engineering pipeline can construct lag and rolling features.
    """

    @abstractmethod
    def fetch_last_n_hours(
        self,
        building_id: str,
        n_hours: int,
        city: str = "drammen",
    ) -> pd.DataFrame:
        """Return the last ``n_hours`` of observed data for ``building_id``.

        Parameters
        ----------
        building_id:
            Building identifier (e.g. "B001" or a numeric string).
        n_hours:
            Number of historical hours required (at least 72 for feature engineering).
        city:
            Dataset name ("drammen" or "oslo").

        Returns
        -------
        pd.DataFrame
            Hourly time-series with DatetimeIndex (UTC).
        """


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
        logger.info(
            "CSVConnector: loaded %d rows for building=%s from %s",
            len(result), building_id, parquet_path,
        )
        return result


class OpenMeteoConnector(DataConnector):
    """Fetch live weather and solar irradiance forecasts from Open-Meteo.

    Open-Meteo (https://open-meteo.com) is a free, no-API-key weather
    forecast service with global coverage including Ireland and Norway.

    This connector returns a *forecast* DataFrame for the next ``n_hours``
    hours, suitable for feeding into the ControlEngine alongside historical
    load data from a ``CSVConnector``.

    Supported variables
    -------------------
    - ``Temperature_Outdoor_C`` — 2m air temperature (°C)
    - ``Global_Solar_Horizontal_Radiation_W_m2`` — direct radiation (W/m²)

    Parameters
    ----------
    latitude, longitude:
        Location coordinates.  Defaults to Dublin, Ireland.
    city_coords:
        Convenience mapping — pass ``city="dublin"`` or ``city="oslo"``
        to use pre-defined coordinates.
    """

    _CITY_COORDS: dict[str, tuple[float, float]] = {
        "dublin":   (53.3498, -6.2603),
        "oslo":     (59.9139, 10.7522),
        "drammen":  (59.7440, 10.2045),
        "bergen":   (60.3929, 5.3241),
    }

    def __init__(
        self,
        latitude: float = 53.3498,
        longitude: float = -6.2603,
    ) -> None:
        self.latitude = latitude
        self.longitude = longitude

    @classmethod
    def for_city(cls, city: str) -> "OpenMeteoConnector":
        """Construct connector using a named city's coordinates."""
        city_lower = city.lower()
        if city_lower not in cls._CITY_COORDS:
            raise ValueError(
                f"Unknown city '{city}'. Known cities: {list(cls._CITY_COORDS.keys())}"
            )
        lat, lon = cls._CITY_COORDS[city_lower]
        return cls(latitude=lat, longitude=lon)

    def fetch_last_n_hours(
        self,
        building_id: str,
        n_hours: int = 48,
        city: str = "dublin",
    ) -> pd.DataFrame:
        """Fetch the next ``n_hours`` weather forecast from Open-Meteo.

        Note: this connector returns *future* forecast data (not historical).
        Combine with CSVConnector for the historical load tail.
        """
        try:
            import requests  # lightweight HTTP; in deployment/requirements.txt
        except ImportError as exc:
            raise ImportError("requests is required for OpenMeteoConnector. pip install requests") from exc

        hours = min(n_hours, 168)  # Open-Meteo free tier: up to 7 days
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={self.latitude}&longitude={self.longitude}"
            f"&hourly=temperature_2m,direct_radiation"
            f"&forecast_days={math.ceil(hours / 24)}"
            f"&timezone=UTC"
        )

        logger.info("OpenMeteoConnector: fetching %d hours from %s", hours, url)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        hourly = data.get("hourly", {})
        times = pd.to_datetime(hourly["time"], utc=True)
        temps = hourly["temperature_2m"]
        solar = hourly["direct_radiation"]

        df = pd.DataFrame(
            {
                "Temperature_Outdoor_C": temps[:hours],
                "Global_Solar_Horizontal_Radiation_W_m2": solar[:hours],
                "Electricity_Imported_Total_kWh": float("nan"),  # unknown future load
            },
            index=times[:hours],
        )
        logger.info(
            "OpenMeteoConnector: fetched %d rows (lat=%.4f, lon=%.4f)",
            len(df), self.latitude, self.longitude,
        )
        return df

    def get_solar_forecast(self, n_hours: int = 24) -> list[float]:
        """Return just the solar irradiance list (W/m²) for quick ControlEngine use."""
        df = self.fetch_last_n_hours("_", n_hours=n_hours)
        return df["Global_Solar_Horizontal_Radiation_W_m2"].tolist()


class EcowittConnector(DataConnector):
    """[STUB] Fetch readings from an Ecowitt personal weather station.

    Ecowitt API documentation:
        https://doc.ecowitt.net/web/#/apiv3en

    Authentication:
        Obtain ``application_key`` and ``api_key`` from:
        https://www.ecowitt.net/user/index → API → Generate Key

    Setup (Ecowitt GW1100 gateway):
        1. Install the WS View Plus app (iOS/Android)
        2. Under "Weather Services" → "Customized" → enter your local
           endpoint OR use the Ecowitt cloud API
        3. Set push interval to 60 seconds

    This stub will be completed once the Ecowitt hardware is installed.
    """

    def __init__(
        self,
        application_key: str | None = None,
        api_key: str | None = None,
        mac: str | None = None,
    ) -> None:
        self.application_key = application_key or os.environ.get("ECOWITT_APP_KEY", "")
        self.api_key = api_key or os.environ.get("ECOWITT_API_KEY", "")
        self.mac = mac or os.environ.get("ECOWITT_MAC", "")

    def fetch_last_n_hours(
        self,
        building_id: str,
        n_hours: int = 72,
        city: str = "dublin",
    ) -> pd.DataFrame:
        """NOT YET IMPLEMENTED — pending Ecowitt hardware installation.

        When implemented, this will call:
            GET https://api.ecowitt.net/api/v3/device/history
                ?application_key={app_key}
                &api_key={api_key}
                &mac={mac}
                &temp_unitid=1&pressure_unitid=3&wind_speed_unitid=7
                &start_date={start}&end_date={now}
        """
        raise NotImplementedError(
            "EcowittConnector is a stub. Hardware (Ecowitt GW1100 + sensor array) "
            "must be installed and API keys configured before use. "
            "Set env vars: ECOWITT_APP_KEY, ECOWITT_API_KEY, ECOWITT_MAC"
        )


# ---------------------------------------------------------------------------
# PRICE CONNECTORS
# ---------------------------------------------------------------------------


class PriceConnector(ABC):
    """Abstract base class for electricity price signals."""

    @abstractmethod
    def get_day_ahead_prices(
        self,
        for_date: date | None = None,
        timezone: str = "Europe/Dublin",
    ) -> list[float]:
        """Return 24 day-ahead electricity prices (EUR/kWh) for ``for_date``.

        Parameters
        ----------
        for_date:
            The target date.  Defaults to tomorrow (next calendar day).
        timezone:
            Local timezone for hour alignment.  "Europe/Dublin" for Ireland.

        Returns
        -------
        list[float]
            24 prices, one per hour (00:00–23:00 local time).
        """


class MockPriceConnector(PriceConnector):
    """Return a realistic Irish residential electricity price curve.

    Based on Bord Gáis/Electric Ireland typical day-ahead structure (2025):
    - Night rate (00:00–08:00): ~0.15 EUR/kWh
    - Morning peak (08:00–11:00): ~0.35 EUR/kWh
    - Shoulder (11:00–17:00): ~0.24 EUR/kWh
    - Evening peak (17:00–20:00): ~0.40 EUR/kWh
    - Evening shoulder (20:00–24:00): ~0.26 EUR/kWh

    Used for testing, demos, and the AWS conference live demonstration.
    """

    _MOCK_CURVE: list[float] = [
        # 00–07: night rate
        0.150, 0.148, 0.145, 0.143, 0.142, 0.140, 0.145, 0.150,
        # 08–10: morning peak
        0.340, 0.360, 0.355,
        # 11–16: shoulder
        0.240, 0.235, 0.230, 0.228, 0.232, 0.238,
        # 17–19: evening peak
        0.400, 0.420, 0.410,
        # 20–23: evening shoulder
        0.265, 0.255, 0.250, 0.245,
    ]

    def get_day_ahead_prices(
        self,
        for_date: date | None = None,
        timezone: str = "Europe/Dublin",
    ) -> list[float]:
        logger.info("MockPriceConnector: returning mock Irish day-ahead curve for %s", for_date or "tomorrow")
        return self._MOCK_CURVE.copy()


class SEMOConnector(PriceConnector):
    """[STUB] Fetch Irish day-ahead electricity prices from SEMO.

    SEMO (Single Electricity Market Operator) publishes day-ahead prices at:
        https://www.semo.ie/en/markets/market-data/day-ahead/

    The SMARTS portal exports are available as CSV but require session-based
    authentication.  A lightweight scraper or the ENTSO-E Transparency Platform
    (which covers the Irish bidding zone IE_SEM) is the recommended approach.

    ENTSO-E API:
        https://transparency.entsoe.eu/content/static_content/Static%20content/
        web%20api/Guide.html
        Token: register at https://transparency.entsoe.eu → Account → API Key

    This stub will be completed once an ENTSO-E API token is available.
    """

    def __init__(self, entsoe_token: str | None = None) -> None:
        self.token = entsoe_token or os.environ.get("ENTSOE_API_TOKEN", "")

    def get_day_ahead_prices(
        self,
        for_date: date | None = None,
        timezone: str = "Europe/Dublin",
    ) -> list[float]:
        """NOT YET IMPLEMENTED — pending ENTSO-E API token."""
        raise NotImplementedError(
            "SEMOConnector is a stub. Register at https://transparency.entsoe.eu "
            "to obtain an API token, then set env var: ENTSOE_API_TOKEN"
        )


# ---------------------------------------------------------------------------
# DEVICE CONNECTORS
# ---------------------------------------------------------------------------


class DeviceConnector(ABC):
    """Abstract base class for demand-response device control."""

    @abstractmethod
    def send_command(self, action_type: str, building_id: str = "unknown") -> bool:
        """Send a control command to a managed device.

        Parameters
        ----------
        action_type:
            ActionType string value (e.g. "DEFER_HEATING", "HEAT_NOW").
        building_id:
            Building or device identifier for audit logging.

        Returns
        -------
        bool
            True if command was accepted; False on failure.
        """


class MockDeviceConnector(DeviceConnector):
    """Log device commands to stdout — safe for demos, CI, and testing.

    No real device is contacted.  All commands are printed and recorded
    in ``self.command_log`` for inspection in tests.
    """

    def __init__(self) -> None:
        self.command_log: list[dict[str, Any]] = []

    def send_command(self, action_type: str, building_id: str = "unknown") -> bool:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "building_id": building_id,
            "action": action_type,
        }
        self.command_log.append(entry)
        logger.info("[MockDevice] %s → %s", building_id, action_type)
        print(f"[MOCK DEVICE] {entry['timestamp']}  building={building_id}  action={action_type}")
        return True


class MyEnergiConnector(DeviceConnector):
    """[STUB] Control a myenergi eddi hot-water diverter via the community API.

    The myenergi API is a reverse-engineered REST API documented at:
        https://github.com/twonk/MyEnergi-App-Api

    Authentication:
        HTTP Digest authentication using:
          - Username: eddi serial number (found on the device label)
          - Password: API key from myenergi app → Settings → Advanced → API Key
        The server is determined by the serial number:
          https://s{n}.myenergi.net  where n = serial[0]

    Key endpoints:
        GET  /cgi-jstatus-E           — current eddi status (power, mode, temp)
        GET  /cgi-jeddi-mode-Z{mode}  — set boost mode
             mode=0: Normal (auto solar divert)
             mode=1: Boost (draw from grid)
             mode=3: Stop (no heating)
        GET  /cgi-jeddi-boost-1-T{minutes}  — time-limited boost

    Example usage (once implemented):
        connector = MyEnergiConnector(serial="12345678", api_key="your-key")
        connector.send_command("DEFER_HEATING")  # sets mode=3 (stop)
        connector.send_command("HEAT_NOW")        # sets mode=1 (boost)

    Setup:
        1. Open myenergi app → Settings → Advanced → API
        2. Note your eddi serial number and generate API key
        3. Set env vars: MYENERGI_SERIAL, MYENERGI_API_KEY

    This stub will be completed once API credentials are available.
    """

    _ACTION_TO_MODE: dict[str, int] = {
        "HEAT_NOW":        1,  # Boost — draw from grid
        "DEFER_HEATING":   3,  # Stop — wait for solar
        "PARTIAL_HEAT":    0,  # Normal — auto solar divert
        "ALERT_HIGH_DEMAND": 3,  # Stop — reduce demand
    }

    def __init__(
        self,
        serial: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.serial = serial or os.environ.get("MYENERGI_SERIAL", "")
        self.api_key = api_key or os.environ.get("MYENERGI_API_KEY", "")

    def send_command(self, action_type: str, building_id: str = "unknown") -> bool:
        """NOT YET IMPLEMENTED — pending myenergi API credentials."""
        raise NotImplementedError(
            "MyEnergiConnector is a stub. "
            "Set env vars MYENERGI_SERIAL and MYENERGI_API_KEY, "
            "then implement HTTP Digest auth against "
            f"https://s{self.serial[0] if self.serial else 'N'}.myenergi.net"
        )
