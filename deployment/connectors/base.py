"""
deployment.connectors.base
==========================
Shared retry helper and abstract base classes for all connector families.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import date
from typing import Callable, TypeVar

import pandas as pd

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


def _retry_http(
    func: Callable[[], _T],
    max_attempts: int = 3,
    backoff_base: float = 2.0,
) -> _T:
    """Call *func* up to *max_attempts* times with exponential backoff.

    Backoff schedule: 2s, 4s, 8s (with backoff_base=2.0).

    Args:
        func: A zero-argument callable that performs the HTTP request and
              returns a result on success, or raises on failure.
        max_attempts: Total number of attempts before re-raising last exception.
        backoff_base: Base for exponential backoff (seconds before attempt 2).

    Returns:
        The value returned by *func* on its first successful call.

    Raises:
        The last exception raised by *func* if all attempts fail.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < max_attempts:
                wait = backoff_base ** (attempt - 1)
                logger.warning(
                    "_retry_http: attempt %d/%d failed (%s) — retrying in %.1fs",
                    attempt, max_attempts, exc, wait,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "_retry_http: all %d attempts failed. Last error: %s",
                    max_attempts, exc,
                )
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Abstract base classes
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
