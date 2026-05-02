"""
tests/connectors/test_markets.py
==================================
Smoke tests for MockPriceConnector (realistic Irish day-ahead price curve).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "deployment"))

from connectors import MockPriceConnector


class TestMockPriceConnector:
    """Smoke tests for MockPriceConnector (realistic Irish day-ahead curve)."""

    def test_returns_24_prices(self):
        """get_day_ahead_prices() returns exactly 24 values."""
        pc = MockPriceConnector()
        prices = pc.get_day_ahead_prices()
        assert len(prices) == 24

    def test_prices_are_floats(self):
        """All prices are floats."""
        for p in MockPriceConnector().get_day_ahead_prices():
            assert isinstance(p, float)

    def test_prices_in_plausible_range(self):
        """All prices are in a plausible range for Irish electricity (€0.10–€0.50/kWh)."""
        for p in MockPriceConnector().get_day_ahead_prices():
            assert 0.10 <= p <= 0.50, f"Price {p:.3f} EUR/kWh outside expected range"

    def test_night_rate_cheaper_than_peak(self):
        """Night-time prices (00:00–07:00) are lower than evening peak (17:00–19:00)."""
        prices = MockPriceConnector().get_day_ahead_prices()
        avg_night = sum(prices[0:8]) / 8
        avg_peak = sum(prices[17:20]) / 3
        assert (
            avg_night < avg_peak
        ), f"Night avg {avg_night:.3f} should be < peak avg {avg_peak:.3f}"

    def test_same_result_repeated_calls(self):
        """Repeated calls return identical lists (deterministic mock)."""
        pc = MockPriceConnector()
        assert pc.get_day_ahead_prices() == pc.get_day_ahead_prices()
