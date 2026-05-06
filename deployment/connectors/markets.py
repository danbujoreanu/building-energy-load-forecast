"""
deployment.connectors.markets
==============================
MockPriceConnector — realistic Irish day-ahead price curve (demo mode).
SEMOConnector      — EirGrid Smart Grid Dashboard day-ahead SMP prices (free, no token).
                     Falls back to MockPriceConnector on API failure.
"""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from typing import Any

from .base import PriceConnector

logger = logging.getLogger(__name__)


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
    """Fetch Irish day-ahead SMP prices from EirGrid Smart Grid Dashboard.

    Uses the public EirGrid Smart Grid Dashboard REST API — no API key required.
    Prices are SMP (System Marginal Price) in EUR/MWh, converted to EUR/kWh.

    API endpoint:
        GET https://smartgriddashboard.com/DashboardService.svc/data
            ?area=DA&region=ROI&datefrom={dd-Mon-yyyy}&dateto={dd-Mon-yyyy}

    Response: JSON with ``Rows`` list, each row containing:
        - ``EffectiveTime``: "dd/mm/yyyy hh:mm:ss"
        - ``Value``: SMP in EUR/MWh (divide by 1000 for EUR/kWh)

    Falls back to MockPriceConnector if the API is unreachable or returns
    unexpected data — the LP dispatcher will still work on realistic mock prices.

    ENTSO-E alternative (requires free registration):
        https://transparency.entsoe.eu → Account → API Key → set ENTSOE_API_TOKEN.
        The IE_SEM bidding zone covers the Irish Single Electricity Market.
        Implementation can be swapped in via __init__(entsoe_token=...).
    """

    _EIRGRID_URL = (
        "https://smartgriddashboard.com/DashboardService.svc/data"
        "?area=DA&region=ROI&datefrom={date_from}&dateto={date_to}"
    )

    def __init__(self, entsoe_token: str | None = None) -> None:
        self.entsoe_token = entsoe_token or os.environ.get("ENTSOE_API_TOKEN", "")
        self._mock = MockPriceConnector()

    def get_day_ahead_prices(
        self,
        for_date: date | None = None,
        timezone: str = "Europe/Dublin",
    ) -> list[float]:
        """Return 24 hourly day-ahead SMP prices in EUR/kWh.

        Queries EirGrid for ``for_date`` (defaults to tomorrow).
        Falls back to MockPriceConnector on any API failure.

        Parameters
        ----------
        for_date:
            The delivery date (the day whose prices you want). Defaults to tomorrow.
        timezone:
            Unused — EirGrid returns Irish local time directly.

        Returns
        -------
        List of 24 floats (EUR/kWh), one per hour 00:00–23:00.
        """
        if for_date is None:
            from datetime import datetime, timezone as tz
            import pytz
            dublin = pytz.timezone("Europe/Dublin")
            for_date = (datetime.now(dublin) + timedelta(days=1)).date()

        date_str = for_date.strftime("%d-%b-%Y")  # e.g. "07-May-2026"
        url = self._EIRGRID_URL.format(date_from=date_str, date_to=date_str)

        try:
            import requests
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            rows = data.get("Rows", [])

            if not rows:
                logger.warning("SEMOConnector: empty Rows for %s — falling back to mock", for_date)
                return self._mock.get_day_ahead_prices(for_date)

            # Rows are half-hourly (48 per day) or hourly (24 per day).
            # EirGrid DA data is hourly. Extract Value (EUR/MWh) in time order.
            prices_eur_mwh: list[float] = []
            for row in rows:
                v = row.get("Value")
                if v is not None:
                    try:
                        prices_eur_mwh.append(float(v))
                    except (TypeError, ValueError):
                        pass

            if len(prices_eur_mwh) < 23:
                logger.warning(
                    "SEMOConnector: only %d price rows for %s (expected 24) — falling back to mock",
                    len(prices_eur_mwh), for_date,
                )
                return self._mock.get_day_ahead_prices(for_date)

            # Convert EUR/MWh → EUR/kWh, take first 24 hours
            prices_eur_kwh = [round(p / 1000.0, 6) for p in prices_eur_mwh[:24]]
            logger.info(
                "SEMOConnector: fetched %d prices for %s (min=%.4f, max=%.4f EUR/kWh)",
                len(prices_eur_kwh), for_date, min(prices_eur_kwh), max(prices_eur_kwh),
            )
            return prices_eur_kwh

        except Exception as exc:
            logger.warning(
                "SEMOConnector: API call failed (%s) — falling back to MockPriceConnector", exc
            )
            return self._mock.get_day_ahead_prices(for_date)
