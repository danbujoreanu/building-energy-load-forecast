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
        return True


class MyEnergiConnector(DeviceConnector):
    """Control a myenergi eddi hot-water diverter via the community API.

    The myenergi API is a reverse-engineered REST API documented at:
        https://github.com/twonk/MyEnergi-App-Api

    Authentication:
        HTTP Digest authentication:
          - Username: HUB serial number (e.g. "21509692")
          - Password: API key — myenergi app → Settings → Advanced → API Key
        Server is auto-discovered via director.myenergi.net on first call.

    Key endpoints used:
        GET  /cgi-jstatus-E                  — all eddi devices status
        GET  /cgi-jeddi{eddi_sno}-mode-Z{n}  — set mode (0=auto, 1=boost, 3=stop)
        GET  /cgi-jeddi{eddi_sno}-day-Y{y}-M{m}-W{d}  — hourly history for a day

    Eddi status codes (sta field):
        1=Paused  3=Diverting(solar)  5=Boost  6=MaxBoost  8=Boosting(grid)

    Setup:
        1. Open myenergi app → Settings → Advanced → API Key → copy key
        2. Set env vars: MYENERGI_SERIAL (hub serial), MYENERGI_API_KEY
        OR pass serial/api_key directly to constructor.

    Example:
        c = MyEnergiConnector(serial="21509692", api_key="your-key")
        status = c.get_status()
        print(status["today_kwh"], "kWh diverted to hot water today")
        c.send_command("DEFER_HEATING")
    """

    _ACTION_TO_MODE: dict[str, int] = {
        "HEAT_NOW":          1,  # Boost — draw from grid at full power
        "DEFER_HEATING":     3,  # Stop  — wait for solar surplus
        "PARTIAL_HEAT":      0,  # Normal — auto solar divert (no grid draw)
        "ALERT_HIGH_DEMAND": 3,  # Stop  — reduce grid load
    }

    _STATUS_NAMES: dict[int, str] = {
        1: "paused", 3: "diverting_solar", 5: "boost",
        6: "max_boost", 8: "boosting_grid",
    }

    def __init__(
        self,
        serial: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.serial = serial or os.environ.get("MYENERGI_SERIAL", "")
        self.api_key = api_key or os.environ.get("MYENERGI_API_KEY", "")
        self._server: str | None = None  # cached after first director lookup

    # ── internal helpers ────────────────────────────────────────────────────

    def _discover_server(self) -> str:
        """Determine the correct myenergi server for this hub.

        director.myenergi.net accepts authenticated requests and routes
        them correctly, so it can be used directly as the server for all
        API calls.  For commands that must go to a specific ASN server
        (e.g. mode changes), we extract the ASN from the CORS origin
        header of the unauthenticated 401 response.

        Returns the server base URL, cached after first call.
        """
        if self._server:
            return self._server
        import requests
        import re

        # Bare request to director — 401 response contains CORS origin
        # header revealing actual ASN server (e.g. s18.myenergi.net)
        try:
            r = requests.get(
                "https://director.myenergi.net/cgi-jstatus-*", timeout=10
            )
            cors = r.headers.get("Access-Control-Allow-Origin", "")
            # Extract sNN from e.g. "https://admin-ui.s18.myenergi.net"
            m = re.search(r"(s\d+\.myenergi\.net)", cors)
            if m:
                self._server = f"https://{m.group(1)}"
                logger.info("MyEnergiConnector: server = %s (from CORS header)", self._server)
                return self._server
        except Exception as exc:
            logger.warning("MyEnergiConnector: server discovery failed (%s)", exc)

        # director.myenergi.net itself routes authenticated requests correctly
        self._server = "https://director.myenergi.net"
        logger.info("MyEnergiConnector: using director as server")
        return self._server

    def _get(self, path: str) -> dict:
        """GET request against the myenergi server with Digest auth."""
        import requests
        from requests.auth import HTTPDigestAuth

        server = self._discover_server()
        url = f"{server}{path}"
        resp = requests.get(
            url, auth=HTTPDigestAuth(self.serial, self.api_key), timeout=10
        )
        resp.raise_for_status()
        return resp.json()

    # ── public API ──────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Return current eddi status as a plain dict.

        Returns
        -------
        dict with keys:
            eddi_serial   — serial number of the eddi device
            mode          — human-readable mode string
            diverted_w    — current diversion power (W)
            grid_w        — grid import (+) / export (-) in W
            today_kwh     — energy diverted to hot water today (kWh)
            tank_temp_c   — tank temperature °C (None if no sensor)
            solar_w       — current solar generation (W; None if no Harvi CT)
        """
        data = self._get("/cgi-jstatus-*")
        # Response: list of device-type dicts, e.g. [{"eddi":[...]}, {"harvi":[...]}, ...]
        eddi_list, harvi_list = [], []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    eddi_list.extend(item.get("eddi", []))
                    harvi_list.extend(item.get("harvi", []))
        else:
            eddi_list = data.get("eddi", [])
            harvi_list = data.get("harvi", [])

        if not eddi_list:
            raise RuntimeError("No eddi devices found on this hub.")
        e = eddi_list[0]
        sta = e.get("sta", 0)
        div = e.get("div", 0)

        # Grid CT from Harvi (if present and measuring "Grid") or Eddi grd field
        harvi_grid_w = None
        if harvi_list:
            h = harvi_list[0]
            if h.get("ectt1", "") in ("Grid", "Internal Load"):
                harvi_grid_w = h.get("ectp1", 0)

        grd = harvi_grid_w if harvi_grid_w is not None else e.get("grd", 0)

        # Solar estimation: house_solar = Eddi_div + grid_export - grid_import
        # grd > 0 → importing; grd < 0 → exporting
        # This gives a lower bound (house loads met by solar are not counted)
        solar_lower_bound = max(0, div - grd)

        return {
            "eddi_serial":     str(e.get("sno", "")),
            "mode":            self._STATUS_NAMES.get(sta, f"unknown({sta})"),
            "diverted_w":      div,
            "grid_w":          grd,        # positive = import, negative = export
            "today_kwh":       round(e.get("che", 0.0), 3),
            "tank_temp_c":     e.get("cht"),   # None if no probe wired
            "solar_w":         e.get("gen", 0),  # 0 if Harvi not in Generation mode
            "solar_lower_w":   solar_lower_bound,  # Eddi_div - grid_import (lower bound)
            "harvi_serial":    str(harvi_list[0].get("sno", "")) if harvi_list else None,
            "harvi_ct1":       harvi_list[0].get("ectt1", "") if harvi_list else None,
            "ct1_load":        e.get("ectt1", ""),
            "frequency_hz":    e.get("frq"),
        }

    def get_history_day(
        self, target_date: date | None = None
    ) -> list[dict]:
        """Return hourly diversion history for one day.

        Fetches from the myenergi cloud server using the Eddi device serial
        (NOT the hub serial).  The hub serial is used only for Digest auth;
        the path must contain the Eddi device serial.

        Two URL formats are tried:
          1. /cgi-jeddi{eddi_sno}-day-Y{year}-M{month}-W{day}   (primary)
          2. /cgi-jday-E{hub_serial}-{year}-{month:02d}-{day:02d} (fallback)

        Returns status -14 if the firmware doesn't support history retrieval
        (observed on some older hub firmware versions).

        Parameters
        ----------
        target_date:
            Date to retrieve.  Defaults to today.

        Returns
        -------
        list of dicts, one per hour (00–23), each with:
            hour         — 0–23
            diverted_kwh — kWh diverted to hot water in that hour
            imported_kwh — kWh imported from grid in that hour
        Empty list if the hub returns status -14 or no data.
        """
        d = target_date or date.today()

        # Confirmed working URL format (tested live 2026-03-15):
        #   /cgi-jday-E{hub_serial}-{year}-{month:02d}-{day:02d}
        # Response: {"U{serial}": [ {minute-level snapshots} ]}
        # Each entry: imp (cumulative Wh import since midnight),
        #             hsk (cumulative Wh to hot water since midnight),
        #             v1 (voltage ×10 mV), frq (frequency ×100 mHz),
        #             yr/mon/dom/dow — date, min — minute within hour (absent at midnight)
        path = f"/cgi-jday-E{self.serial}-{d.year}-{d.month:02d}-{d.day:02d}"
        try:
            data = self._get(path)
        except Exception as exc:
            logger.warning("get_history_day: API error (%s)", exc)
            return []

        if isinstance(data, dict) and data.get("status") == -14:
            logger.warning(
                "get_history_day: status -14 — firmware history unavailable. "
                "Use log_eddi.py --once via nightly cron as a workaround."
            )
            return []

        # Find the data key: "U{serial}" (e.g. "U21509692")
        data_key = next((k for k in data if k.startswith("U")), None)
        if not data_key:
            logger.warning("get_history_day: no U-key in response: %s", list(data.keys()))
            return []

        all_entries = data[data_key]  # 1441 entries for a full day

        # ── Response structure (confirmed live, 2026-03-15) ──────────────────
        # Total entries = 1 + 24 × 60 = 1441
        # Layout: [global_header, h0_start, h0_m1…m59,
        #                         h1_start, h1_m1…m59, …, h23_start, h23_m1…m59]
        # - Entries WITHOUT "min" key: global header (index 0) + 24 hour-start
        #   snapshots (minute 0 of each hour).
        # - Entries WITH "min" key (1–59): the remaining 59 minutes of each hour.
        # - "min" = minute within the hour (1–59).
        # - Hour index = (array_index - 1) // 60   for array_index ≥ 1.
        #
        # Field units (confirmed):
        #   imp  — instantaneous grid import power.  Unit ≈ centi-Watts (0.01 W).
        #          Confirmed: imp ≈ 19000 cW = 190 W at midnight (plausible standby).
        #          imp ≈ 90000 cW = 900 W during moderate daytime load.
        #   hsk  — instantaneous power to hot water (heater supplied).
        #          Same centi-Watt units.  0 when Eddi is idle.
        # Both fields are INSTANTANEOUS, not cumulative.
        # For daily total diversion use get_status()["today_kwh"] (the `che` field).
        # ─────────────────────────────────────────────────────────────────────

        CW_TO_KW = 1e-5  # centi-Watts → kW  (divide by 100 to get W, divide by 1000 for kW)

        hourly_imp_sum: dict[int, float] = {h: 0.0 for h in range(24)}
        hourly_hsk_sum: dict[int, float] = {h: 0.0 for h in range(24)}
        hourly_count:   dict[int, int]   = {h: 0   for h in range(24)}

        for idx, entry in enumerate(all_entries):
            if not isinstance(entry, dict):
                continue
            # Determine hour from array position (idx=0 is global header, idx≥1 → hour=(idx-1)//60)
            hour = (idx - 1) // 60 if idx >= 1 else 0
            if hour < 0 or hour > 23:
                continue
            hourly_imp_sum[hour] += entry.get("imp", 0)
            hourly_hsk_sum[hour] += entry.get("hsk", 0)
            hourly_count[hour]   += 1

        hours = []
        for h in range(24):
            n = hourly_count[h]
            if n == 0:
                continue
            avg_imp_kw = (hourly_imp_sum[h] / n) * CW_TO_KW  # mean instantaneous kW
            avg_hsk_kw = (hourly_hsk_sum[h] / n) * CW_TO_KW
            hours.append({
                "hour":          h,
                "diverted_kwh":  round(avg_hsk_kw * 1.0, 4),   # avg kW ≈ kWh/h
                "imported_kwh":  round(avg_imp_kw * 1.0, 4),
            })
        return hours

    def get_history_range(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """Return daily diversion totals for a date range.

        Calls get_history_day() for each date and aggregates to one row/day.
        If the hub doesn't support history, returns empty list immediately
        (no hammering the API with repeated -14 responses).

        Returns
        -------
        list of dicts, one per date:
            date         — ISO date string (YYYY-MM-DD)
            diverted_kwh — total kWh diverted that day
            imported_kwh — total kWh imported that day
        """
        from datetime import timedelta

        # Quick pre-check: try one day; if -14, abort early
        probe = self.get_history_day(start_date)
        if not probe and start_date != end_date:
            logger.warning("get_history_range: history unavailable, aborting range fetch")
            return []

        results = []
        current = start_date
        while current <= end_date:
            hours = self.get_history_day(current)
            if hours:
                results.append({
                    "date":          current.isoformat(),
                    "diverted_kwh":  round(sum(h["diverted_kwh"] for h in hours), 3),
                    "imported_kwh":  round(sum(h["imported_kwh"] for h in hours), 3),
                })
            current += timedelta(days=1)
        return results

    # Day-of-week positions in the myenergi `bdd` 8-char string.
    # Confirmed format (live API, 2026-03-15):
    #   bdd[0] = unused/special (always "0")
    #   bdd[1] = Monday, bdd[2] = Tuesday, …, bdd[5] = Friday
    #   bdd[6] = Saturday, bdd[7] = Sunday
    # "01111101" → Mon+Tue+Wed+Thu+Fri+Sun  (not Saturday)
    # "00000010" → Saturday only
    # "00000011" → Sat+Sun
    # "01111100" → Mon+Tue+Wed+Thu+Fri+Sat
    _BDD_DAYS = ["_", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    @staticmethod
    def _decode_bdd(bdd: str) -> list[str]:
        """Decode myenergi day-of-week bitmask string to list of day names.

        The bdd field is an 8-character '0'/'1' string where:
          position 0 = unused, positions 1-7 = Mon through Sun.
        """
        if not bdd or len(bdd) != 8:
            return []
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        return [day_names[i] for i in range(7) if bdd[i + 1] == "1"]

    def get_schedule(self) -> list[dict]:
        """Return the Eddi boost timer schedule configured in the myenergi app.

        Endpoint confirmed working (live API, 2026-03-15):
            GET /cgi-boost-time-E{hub_serial}

        Response format:
            {"boost_times": [{"slt": 11, "bsh": 7, "bsm": 0,
                               "bdh": 0, "bdm": 30, "bdd": "01111101"}, ...]}

        The ``bdd`` field is an 8-char string; positions 1–7 = Mon–Sun,
        position 0 is unused.  Confirmed day mapping:
            "01111101" → Mon+Tue+Wed+Thu+Fri+Sun  (slots 11, 12 — daily grid boost)
            "00000010" → Saturday only             (slots 13, 14 — free window)

        Slot number prefixes observed on this hub:
            1x = Heater 1 (Tank 1) — the active schedule
            2x, 5x, 6x = Heater 2 / additional program slots (may be inactive)

        Returns
        -------
        List of dicts, one per active slot (bdd all-zeros omitted), with keys:

            slot          int   Raw slot number (11, 12, 13, 14, …)
            start_hour    int   Hour (0–23)
            start_min     int   Minute (0, 15, 30, or 45)
            duration_h    int   Duration hours component
            duration_m    int   Duration minutes component
            duration_min  int   Total duration in minutes
            days          list  Day names active, e.g. ["Mon","Tue","Wed","Thu","Fri"]
            bdd           str   Raw 8-char day string from API
            label         str   Human-readable summary, e.g. "07:00 +30min Mon-Fri"

        Example (Dan's home, 2026-03-15):
        -------
        >>> timers = connector.get_schedule()
        >>> for t in timers: print(t["label"])
        07:00 +30min Mon+Tue+Wed+Thu+Fri+Sun    # slot 11 — night-rate grid boost
        09:15 +180min Sat                        # slot 13 — Saturday free window
        14:00 +180min Sat                        # slot 14 — Saturday free window
        19:45 +30min Mon+Tue+Wed+Thu+Fri+Sun    # slot 12 — evening grid boost
        """
        try:
            data = self._get(f"/cgi-boost-time-E{self.serial}")
        except Exception as exc:
            logger.warning("get_schedule: API error (%s) — returning empty schedule", exc)
            return []

        # Confirmed response key: "boost_times"
        slots_raw = data.get("boost_times") if isinstance(data, dict) else []
        if not slots_raw:
            logger.warning("get_schedule: no boost_times in response: %s", list(data.keys()) if isinstance(data, dict) else type(data))
            return []

        results = []
        for slot in slots_raw:
            if not isinstance(slot, dict):
                continue
            bdd = slot.get("bdd", "00000000")
            if bdd == "00000000":
                continue  # inactive slot

            days = self._decode_bdd(bdd)
            if not days:
                continue

            slt       = slot.get("slt", 0)
            bsh       = slot.get("bsh", 0)
            bsm       = slot.get("bsm", 0)
            bdh       = slot.get("bdh", 0)
            bdm_val   = slot.get("bdm", 0)
            total_min = bdh * 60 + bdm_val

            dur_str = f"{total_min}min" if total_min > 0 else "until-setpoint"
            if len(days) == 7:
                day_str = "daily"
            elif days == ["Mon", "Tue", "Wed", "Thu", "Fri"]:
                day_str = "Mon-Fri"
            elif days == ["Sat", "Sun"]:
                day_str = "Sat-Sun"
            elif days == ["Sat"]:
                day_str = "Sat"
            elif days == ["Sun"]:
                day_str = "Sun"
            else:
                day_str = "+".join(days)

            label = f"{bsh:02d}:{bsm:02d} +{dur_str} {day_str}"

            results.append({
                "slot":         slt,
                "start_hour":   bsh,
                "start_min":    bsm,
                "duration_h":   bdh,
                "duration_m":   bdm_val,
                "duration_min": total_min,
                "days":         days,
                "bdd":          bdd,
                "label":        label,
            })

        results.sort(key=lambda x: (x["start_hour"], x["start_min"]))
        return results

    def schedule_advice(
        self,
        timers: list[dict],
        solar_forecast_wh_m2: list[float],
        grid_price_eur_kwh: list[float],
        solar_threshold_wh_m2: float = 300.0,
        price_peak_threshold: float = 0.40,
    ) -> list[dict]:
        """Cross-reference boost timers with tomorrow's solar + price forecast.

        For each scheduled boost slot, decide whether to keep, defer, or advance.

        Parameters
        ----------
        timers:
            Output of ``get_schedule()``.
        solar_forecast_wh_m2:
            24 floats — hourly solar irradiance (Wh/m²) for tomorrow.
            Index 0 = midnight, index 6 = 06:00, etc.
        grid_price_eur_kwh:
            24 floats — hourly day-ahead electricity price (EUR/kWh) for tomorrow.
        solar_threshold_wh_m2:
            Irradiance above which solar diversion is likely sufficient
            (default 300 Wh/m² ≈ 0.3 kW/m² → ~1.5–2 kW on a typical Irish roof).
        price_peak_threshold:
            Grid price above which drawing from grid is considered expensive
            (default 0.40 EUR/kWh, between Bord Gáis day 0.40 and peak 0.49).

        Returns
        -------
        List of advice dicts — one per timer slot, each with:

            label          str   Original timer label
            slot           int   Slot number
            action         str   "KEEP" | "DEFER_TO_SOLAR" | "ADVANCE_TO_OFFPEAK"
            reason         str   One-line human-readable explanation
            suggested_hour int   Suggested start hour (same as original if KEEP)

        Example
        -------
        >>> solar = [0]*6 + [50,150,300,450,600,700,650,500,350,200,80,20] + [0]*6
        >>> prices = [0.30]*7 + [0.40]*2 + [0.35]*6 + [0.49]*2 + [0.38]*7 + [0.30]*2
        >>> timers = connector.get_schedule()
        >>> for a in connector.schedule_advice(timers, solar, prices):
        ...     print(a["action"], a["label"], "->", a["reason"])
        """
        advice = []
        for t in timers:
            h = t["start_hour"]
            price_at_slot = grid_price_eur_kwh[h] if h < len(grid_price_eur_kwh) else None
            solar_at_slot = solar_forecast_wh_m2[h] if h < len(solar_forecast_wh_m2) else None

            peak_solar_hours = [
                i for i, s in enumerate(solar_forecast_wh_m2)
                if s > solar_threshold_wh_m2
            ]

            if (solar_at_slot is not None
                    and solar_at_slot > solar_threshold_wh_m2
                    and price_at_slot is not None
                    and price_at_slot > price_peak_threshold):
                # Scheduled during high-solar + expensive-grid window
                action = "DEFER_TO_SOLAR"
                reason = (
                    f"Solar forecast {solar_at_slot:.0f} Wh/m² at {h:02d}:00 — "
                    f"Eddi will divert without drawing grid "
                    f"(grid price {price_at_slot:.2f} EUR/kWh)"
                )
                suggested = h
            elif (price_at_slot is not None
                  and price_at_slot > price_peak_threshold
                  and not peak_solar_hours):
                # Expensive slot, no solar expected — suggest cheapest hour
                cheapest_h = int(min(range(24), key=lambda i: grid_price_eur_kwh[i]))
                action = "ADVANCE_TO_OFFPEAK"
                reason = (
                    f"Grid price {price_at_slot:.2f} EUR/kWh at {h:02d}:00, "
                    f"no solar forecast today. "
                    f"Cheapest hour: {cheapest_h:02d}:00 "
                    f"({grid_price_eur_kwh[cheapest_h]:.2f} EUR/kWh)"
                )
                suggested = cheapest_h
            else:
                action = "KEEP"
                price_str = f"{price_at_slot:.2f} EUR/kWh" if price_at_slot is not None else "unknown"
                solar_str = f"{solar_at_slot:.0f} Wh/m²" if solar_at_slot is not None else "unknown"
                reason = (
                    f"Grid price {price_str}, solar {solar_str} — "
                    f"keep scheduled boost"
                )
                suggested = h

            advice.append({
                "label":          t["label"],
                "slot":           t["slot"],
                "action":         action,
                "reason":         reason,
                "suggested_hour": suggested,
            })

        return advice

    def send_command(self, action_type: str, building_id: str = "unknown") -> bool:
        """Send a mode command to the eddi.

        Parameters
        ----------
        action_type:
            One of: "HEAT_NOW", "DEFER_HEATING", "PARTIAL_HEAT", "ALERT_HIGH_DEMAND"
        building_id:
            For logging only.

        Returns
        -------
        bool — True if accepted (HTTP 200).
        """
        if not self.serial or not self.api_key:
            raise ValueError(
                "MyEnergiConnector: serial and api_key must both be set. "
                "Set env vars MYENERGI_SERIAL and MYENERGI_API_KEY."
            )
        mode = self._ACTION_TO_MODE.get(action_type, 0)
        # eddi serial is the first eddi on the hub — fetch it from status
        status = self.get_status()
        eddi_sno = status["eddi_serial"]
        path = f"/cgi-jeddi{eddi_sno}-mode-Z{mode}"
        try:
            result = self._get(path)
            ok = result.get("status", 0) == 0
            logger.info(
                "[MyEnergi] %s → mode=%d (%s) — %s",
                building_id, mode, action_type, "OK" if ok else f"error: {result}"
            )
            return ok
        except Exception as exc:
            logger.error("[MyEnergi] send_command failed: %s", exc)
            return False
