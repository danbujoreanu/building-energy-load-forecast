"""Tests for LPThermalDispatcher (DAN-164 Stream 3)."""

from __future__ import annotations

import numpy as np
import pytest

from energy_forecast.control.lp_dispatcher import (
    LPThermalDispatcher,
    DispatchResult,
    _compress_hours,
)
from energy_forecast.control.actions import ActionType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FLAT_PRICES = [0.25] * 24          # constant price — any schedule is equally valid
CHEAP_NIGHT = [0.12] * 8 + [0.35] * 16   # cheap 00:00–07:00, expensive rest of day


@pytest.fixture
def dispatcher() -> LPThermalDispatcher:
    return LPThermalDispatcher(
        tank_volume_liters=150.0,
        max_heater_kw=3.0,
        min_temp_c=45.0,
        max_temp_c=65.0,
        daily_draw_liters=120.0,
    )


# ---------------------------------------------------------------------------
# LPThermalDispatcher.optimize — happy path
# ---------------------------------------------------------------------------

class TestLPThermalDispatcherOptimize:

    def test_returns_dispatch_result(self, dispatcher):
        result = dispatcher.optimize(initial_temp_c=55.0, prices=FLAT_PRICES)
        assert isinstance(result, DispatchResult)

    def test_grid_boost_24_elements(self, dispatcher):
        result = dispatcher.optimize(initial_temp_c=55.0, prices=FLAT_PRICES)
        assert len(result.grid_boost_kw) == 24

    def test_grid_boost_within_bounds(self, dispatcher):
        result = dispatcher.optimize(initial_temp_c=55.0, prices=CHEAP_NIGHT)
        assert np.all(result.grid_boost_kw >= -1e-6)
        assert np.all(result.grid_boost_kw <= dispatcher.max_kw + 1e-6)

    def test_cheap_night_heats_night_hours(self, dispatcher):
        """With cheap 00:00–07:00, LP should concentrate heating in those hours."""
        result = dispatcher.optimize(initial_temp_c=45.0, prices=CHEAP_NIGHT)
        heat = result.heat_hours(threshold_kw=0.1)
        # Most heating should be in the cheap band (0–7)
        cheap_heat = sum(1 for h in heat if h < 8)
        assert cheap_heat > 0, "Expected at least one cheap-hour boost"

    def test_estimated_cost_non_negative(self, dispatcher):
        result = dispatcher.optimize(initial_temp_c=55.0, prices=FLAT_PRICES)
        assert result.estimated_cost_eur >= 0.0

    def test_solar_surplus_reduces_grid_boost(self, dispatcher):
        """Abundant solar surplus should reduce total grid boost."""
        solar_full = [2.0] * 24   # 2 kW all day
        no_solar = np.zeros(24)
        result_solar = dispatcher.optimize(
            initial_temp_c=45.0, prices=FLAT_PRICES, solar_surplus_kw=solar_full
        )
        result_none = dispatcher.optimize(
            initial_temp_c=45.0, prices=FLAT_PRICES, solar_surplus_kw=no_solar
        )
        assert result_solar.grid_boost_kw.sum() <= result_none.grid_boost_kw.sum()

    def test_fallback_not_used_normally(self, dispatcher):
        result = dispatcher.optimize(initial_temp_c=55.0, prices=FLAT_PRICES)
        assert not result.fallback_used


# ---------------------------------------------------------------------------
# DispatchResult helpers
# ---------------------------------------------------------------------------

class TestDispatchResult:

    def test_heat_hours_respects_threshold(self):
        grid_boost = np.array([0.05, 0.5, 2.0, 0.0, 0.15] + [0.0] * 19)
        result = DispatchResult(
            grid_boost_kw=grid_boost,
            prices_eur_kwh=np.array(FLAT_PRICES),
            estimated_cost_eur=0.5,
        )
        assert result.heat_hours(threshold_kw=0.1) == [1, 2, 4]
        assert result.heat_hours(threshold_kw=1.0) == [2]

    def test_schedule_summary_contains_hours(self):
        grid_boost = np.zeros(24)
        grid_boost[2] = 3.0
        grid_boost[3] = 3.0
        result = DispatchResult(
            grid_boost_kw=grid_boost,
            prices_eur_kwh=np.array(FLAT_PRICES),
            estimated_cost_eur=1.5,
        )
        summary = result.schedule_summary()
        assert "02:00" in summary

    def test_schedule_summary_no_boost_message(self):
        result = DispatchResult(
            grid_boost_kw=np.zeros(24),
            prices_eur_kwh=np.array(FLAT_PRICES),
            estimated_cost_eur=0.0,
        )
        assert "solar" in result.schedule_summary().lower()

    def test_to_control_actions_length(self, dispatcher):
        result = dispatcher.optimize(initial_temp_c=55.0, prices=FLAT_PRICES)
        actions = result.to_control_actions()
        assert len(actions) == 24

    def test_to_control_actions_types(self, dispatcher):
        result = dispatcher.optimize(initial_temp_c=45.0, prices=CHEAP_NIGHT)
        actions = result.to_control_actions()
        action_types = {a.action for a in actions}
        assert action_types.issubset({ActionType.HEAT_NOW, ActionType.DEFER_HEATING})

    def test_to_control_actions_hours_sequential(self, dispatcher):
        result = dispatcher.optimize(initial_temp_c=55.0, prices=FLAT_PRICES)
        actions = result.to_control_actions()
        assert [a.target_hour for a in actions] == list(range(24))


# ---------------------------------------------------------------------------
# Greedy fallback
# ---------------------------------------------------------------------------

class TestGreedyFallback:

    def test_fallback_marked_correctly(self, dispatcher):
        """Force fallback by patching linprog — greedy must set fallback_used=True."""
        import unittest.mock as mock
        from scipy.optimize import OptimizeResult
        failed_result = OptimizeResult(success=False, message="infeasible", x=None)
        with mock.patch("scipy.optimize.linprog", return_value=failed_result):
            result = dispatcher.optimize(initial_temp_c=55.0, prices=FLAT_PRICES)
        assert result.fallback_used

    def test_fallback_picks_cheap_hours(self, dispatcher):
        import unittest.mock as mock
        from scipy.optimize import OptimizeResult
        failed_result = OptimizeResult(success=False, message="infeasible", x=None)
        with mock.patch("scipy.optimize.linprog", return_value=failed_result):
            result = dispatcher.optimize(
                initial_temp_c=55.0, prices=CHEAP_NIGHT
            )
        # All heated hours should be in the cheap band (0–7)
        heat = result.heat_hours(threshold_kw=0.1)
        assert all(h < 8 for h in heat), f"Greedy picked expensive hours: {heat}"


# ---------------------------------------------------------------------------
# _compress_hours utility
# ---------------------------------------------------------------------------

class TestCompressHours:

    def test_contiguous_range(self):
        assert _compress_hours([1, 2, 3]) == "01:00–03:59"

    def test_two_separate_ranges(self):
        result = _compress_hours([1, 2, 7, 8])
        assert "01:00" in result
        assert "07:00" in result

    def test_single_hour(self):
        assert _compress_hours([5]) == "05:00–05:59"

    def test_empty(self):
        assert _compress_hours([]) == ""
