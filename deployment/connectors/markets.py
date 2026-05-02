"""
deployment.connectors.markets
==============================
MockPriceConnector — realistic Irish day-ahead price curve (demo mode).
SEMOConnector      — SEMO day-ahead prices [STUB — pending ENTSO-E token].
"""

from __future__ import annotations

import logging
import os
from datetime import date

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
