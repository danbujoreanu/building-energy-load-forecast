"""
deployment.connectors.weather
==============================
OpenMeteoConnector — live weather + solar forecast (Open-Meteo free API).
EcowittConnector   — Ecowitt cloud API [STUB — pending hardware].
"""

from __future__ import annotations

import logging
import math
import os
import time
from typing import Any

import pandas as pd

from .base import DataConnector

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level weather cache — keyed by f"{building_id}:{n_hours}"
# Populated on successful OpenMeteo fetches; used as fallback on failure.
# ---------------------------------------------------------------------------
_weather_cache: dict[str, pd.DataFrame] = {}


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

        Retries up to 3 times with exponential backoff (2s, 4s, 8s).
        On total failure, falls back to the last successfully cached response.
        If no cache exists, re-raises the original exception.

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
            f"&hourly=temperature_2m,direct_radiation,cloud_cover,shortwave_radiation"
            f"&forecast_days={math.ceil(hours / 24)}"
            f"&timezone=UTC"
        )
        cache_key = f"{building_id}:{n_hours}"
        max_attempts = 3

        def _do_fetch() -> pd.DataFrame:
            for attempt in range(1, max_attempts + 1):
                print(f"[OpenMeteoConnector] attempt {attempt}/{max_attempts} for {url}")
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    data: dict[str, Any] = response.json()

                    hourly = data.get("hourly", {})
                    _required = {"time", "temperature_2m", "direct_radiation"}
                    _missing = _required - hourly.keys()
                    if _missing:
                        raise ValueError(
                            f"Open-Meteo response missing expected fields: {sorted(_missing)}"
                        )

                    times = pd.to_datetime(hourly["time"], utc=True)
                    temps = hourly["temperature_2m"]
                    solar = hourly["direct_radiation"]
                    cloud = hourly.get("cloud_cover", [None] * hours)
                    shortwave = hourly.get("shortwave_radiation", [None] * hours)

                    df = pd.DataFrame(
                        {
                            "Temperature_Outdoor_C": temps[:hours],
                            "Global_Solar_Horizontal_Radiation_W_m2": solar[:hours],
                            "cloud_cover_pct": cloud[:hours],
                            "shortwave_radiation_W_m2": shortwave[:hours],
                            "Electricity_Imported_Total_kWh": float("nan"),  # unknown future load
                        },
                        index=times[:hours],
                    )
                    logger.info(
                        "OpenMeteoConnector: fetched %d rows (lat=%.4f, lon=%.4f)",
                        len(df), self.latitude, self.longitude,
                    )
                    return df
                except Exception as exc:
                    if attempt < max_attempts:
                        wait = 2.0 ** (attempt - 1)  # 1s, 2s, 4s → 2s, 4s, 8s on attempts 1,2,3
                        # Corrected: attempt=1 → wait 2s, attempt=2 → wait 4s
                        wait = 2.0 * (2.0 ** (attempt - 1))
                        logger.warning(
                            "OpenMeteoConnector: attempt %d/%d failed (%s) — retrying in %.1fs",
                            attempt, max_attempts, exc, wait,
                        )
                        time.sleep(wait)
                    else:
                        raise

        logger.info("OpenMeteoConnector: fetching %d hours from %s", hours, url)
        try:
            df = _do_fetch()
            # Cache successful result
            _weather_cache[cache_key] = df
            return df
        except Exception as exc:
            # All retries exhausted — try cache fallback
            cached = _weather_cache.get(cache_key)
            if cached is not None:
                cache_ts = cached.index[0].isoformat() if len(cached) > 0 else "unknown"
                logger.warning(
                    "OpenMeteo unavailable — using cached weather from %s", cache_ts
                )
                return cached
            # No cache — re-raise original exception
            raise

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
