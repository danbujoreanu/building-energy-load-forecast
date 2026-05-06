"""
energy_forecast.control.lp_dispatcher
======================================
LPThermalDispatcher — optimal Eddi hot-water schedule using day-ahead SMP prices.

Uses scipy HiGHS linear programming to minimise grid electricity cost while
keeping the tank temperature within comfort bounds [min_temp, max_temp].

Decision variable: grid_boost_kw[h] for h in 0..23
Objective:         min  sum_h  price[h] * grid_boost_kw[h]
                        + 1e-4 * (24-h)  # time penalty: prefer heating later
Constraints:       tank_temp[h] in [min_temp_c, max_temp_c]  for all h

The thermal model is a simple cumulative energy balance (no loss decay term —
acceptable over 24h for a well-insulated cylinder):
    tank_temp[h] = initial_temp
                   + sum_{i<=h} (grid_boost[i] + solar[i]) * eta / cap_kwh_per_c
                   - sum_{i<=h} draw_energy[i] / cap_kwh_per_c

Falls back to a greedy "cheapest N hours" rule if the LP solver fails.

Usage (from scheduler):
    from energy_forecast.control.lp_dispatcher import LPThermalDispatcher
    dispatcher = LPThermalDispatcher()
    result = dispatcher.optimize(
        initial_temp_c=55.0,
        prices=prices_24h,          # list[float], EUR/kWh
        solar_surplus_kw=solar_kw,  # list[float], kW — optional, default zeros
    )
    print(result.schedule_summary())
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

import numpy as np

from energy_forecast.control.actions import ActionType, ControlAction

logger = logging.getLogger(__name__)

# Water: 4.184 kJ/(kg·°C) = 0.001163 kWh/(L·°C)
_SPECIFIC_HEAT_KWH_PER_LITRE_C = 0.001163


@dataclass
class DispatchResult:
    """Output of LPThermalDispatcher.optimize().

    Attributes
    ----------
    grid_boost_kw:
        24-element array of hourly grid boost power (kW). Values near zero
        mean "let solar or thermal inertia cover this hour".
    prices_eur_kwh:
        The 24-element price array used in optimisation.
    estimated_cost_eur:
        Total estimated grid electricity cost for the 24h window (EUR).
    fallback_used:
        True if the LP solver failed and a greedy rule was used instead.
    """

    grid_boost_kw: np.ndarray
    prices_eur_kwh: np.ndarray
    estimated_cost_eur: float
    fallback_used: bool = False
    notes: str = ""

    def heat_hours(self, threshold_kw: float = 0.1) -> List[int]:
        """Return hour indices where Eddi should boost from the grid."""
        return [h for h, kw in enumerate(self.grid_boost_kw) if kw >= threshold_kw]

    def schedule_summary(self) -> str:
        """One-line human-readable summary for Pushover / logs."""
        hot_hours = self.heat_hours()
        if not hot_hours:
            return "No grid boost needed — solar covers demand."
        hour_ranges = _compress_hours(hot_hours)
        avg_price = float(np.mean(self.prices_eur_kwh[hot_hours]))
        tag = " [fallback]" if self.fallback_used else ""
        return (
            f"Heat grid: {hour_ranges}  |  avg {avg_price:.3f} €/kWh  |  "
            f"est. €{self.estimated_cost_eur:.2f}/day{tag}"
        )

    def to_control_actions(self, threshold_kw: float = 0.1) -> List[ControlAction]:
        """Convert result to ControlAction list compatible with ControlEngine.

        Hours where grid_boost_kw >= threshold → HEAT_NOW
        Hours where grid_boost_kw <  threshold → DEFER_HEATING
        """
        actions = []
        for h, kw in enumerate(self.grid_boost_kw):
            if kw >= threshold_kw:
                action = ActionType.HEAT_NOW
                reasoning = (
                    f"LP: boost {kw:.2f} kW at {self.prices_eur_kwh[h]:.3f} €/kWh "
                    f"→ {kw * self.prices_eur_kwh[h]:.3f} € estimated cost"
                )
                confidence = round(min(0.70 + kw / 3.0 * 0.20, 0.90), 2)
            else:
                action = ActionType.DEFER_HEATING
                reasoning = (
                    f"LP: no grid boost needed at {self.prices_eur_kwh[h]:.3f} €/kWh "
                    f"(solar or inertia covers)"
                )
                confidence = 0.75
            actions.append(
                ControlAction(
                    target_hour=h,
                    action=action,
                    confidence=confidence,
                    reasoning=reasoning,
                    price_eur_kwh=float(self.prices_eur_kwh[h]),
                )
            )
        return actions


class LPThermalDispatcher:
    """Minimise hot-water heating cost via linear programming.

    Parameters
    ----------
    tank_volume_liters:
        Cylinder capacity.  Typical Irish combi-tank: 120–200 L.
    max_heater_kw:
        Maximum immersion / Eddi power draw (kW).  Default 3.0 kW.
    heating_efficiency:
        Fraction of grid kWh converted to stored heat.
        Resistive immersion ≈ 1.0; heat pump ≈ 2.5–3.5.
    min_temp_c:
        Lower comfort bound. 45°C prevents Legionella risk.
    max_temp_c:
        Upper safety bound. 65°C is the typical immersion thermostat limit.
    daily_draw_liters:
        Expected daily hot-water draw. Split uniformly across waking hours
        (06:00–22:00) when no per-hour estimate is provided.
    """

    def __init__(
        self,
        tank_volume_liters: float = 200.0,
        max_heater_kw: float = 3.0,
        heating_efficiency: float = 1.0,
        min_temp_c: float = 45.0,
        max_temp_c: float = 65.0,
        daily_draw_liters: float = 150.0,
    ) -> None:
        self.vol = tank_volume_liters
        self.max_kw = max_heater_kw
        self.eta = heating_efficiency
        self.min_temp = min_temp_c
        self.max_temp = max_temp_c
        self.daily_draw_liters = daily_draw_liters

        self._cap = self.vol * _SPECIFIC_HEAT_KWH_PER_LITRE_C  # kWh/°C

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize(
        self,
        initial_temp_c: float,
        prices: list[float] | np.ndarray,
        solar_surplus_kw: list[float] | np.ndarray | None = None,
        predicted_draw_liters: list[float] | np.ndarray | None = None,
    ) -> DispatchResult:
        """Compute the lowest-cost 24h heating schedule.

        Parameters
        ----------
        initial_temp_c:
            Estimated tank temperature at hour 0 (°C).
        prices:
            24 hourly grid prices in EUR/kWh (from semo_prices table).
        solar_surplus_kw:
            24 hourly solar surplus power (kW) — energy already available
            from PV that would otherwise be exported.  Default zeros.
        predicted_draw_liters:
            24 hourly hot-water draw (L).  Default: daily_draw_liters
            spread uniformly over 06:00–22:00.

        Returns
        -------
        DispatchResult
        """
        prices_arr = np.asarray(prices, dtype=float)
        solar_arr = np.zeros(24) if solar_surplus_kw is None else np.asarray(solar_surplus_kw, dtype=float)
        draw_arr = self._default_draw() if predicted_draw_liters is None else np.asarray(predicted_draw_liters, dtype=float)

        # Convert draw in litres to draw in kWh equivalent (raises tank temp by draw × ΔT)
        # We assume cold-fill at 10°C replacing tank water at current temp.
        draw_kwh = draw_arr * _SPECIFIC_HEAT_KWH_PER_LITRE_C * (initial_temp_c - 10.0)
        draw_kwh = np.clip(draw_kwh, 0.0, None)  # never negative

        try:
            result = self._solve_lp(initial_temp_c, prices_arr, solar_arr, draw_kwh)
            return result
        except Exception as exc:
            logger.warning("[lp_dispatcher] LP solve failed (%s) — using greedy fallback.", exc)
            return self._greedy_fallback(prices_arr, solar_arr)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _solve_lp(
        self,
        initial_temp_c: float,
        prices: np.ndarray,
        solar_kw: np.ndarray,
        draw_kwh: np.ndarray,
    ) -> DispatchResult:
        """scipy.optimize.linprog call."""
        from scipy.optimize import linprog  # lazy import — not installed everywhere

        H = 24
        # Objective: minimise cost + tiny time penalty (prefer heating later)
        c = prices.copy()
        c += np.array([1e-4 * (H - h) for h in range(H)])

        # Temperature constraint matrix
        # temp[h] = initial_temp
        #           + sum_{i<=h} (grid[i] + solar[i]) * eta / cap
        #           - sum_{i<=h} draw[i] / cap
        #
        # Cumulative coefficient for grid[i] on temp[h]: eta/cap if i<=h, else 0
        # Lower bound: temp[h] >= min_temp  →  -A_lb x ≤ -(min_temp - base[h])
        # Upper bound: temp[h] <= max_temp  →   A_ub x ≤  (max_temp - base[h])

        # base[h] = initial_temp + cumulative (solar*eta - draw) / cap
        cum_solar_draw = np.cumsum((solar_kw * self.eta - draw_kwh) / self._cap)
        base_temp = initial_temp_c + cum_solar_draw  # shape (H,)

        A_ub = np.zeros((2 * H, H))
        b_ub = np.zeros(2 * H)

        for h in range(H):
            coef = self.eta / self._cap
            # Upper bound row: sum_{i<=h} coef * grid[i] <= max_temp - base[h]
            A_ub[h, : h + 1] = coef
            b_ub[h] = self.max_temp - base_temp[h]
            # Lower bound row: -sum_{i<=h} coef * grid[i] <= -(min_temp - base[h])
            A_ub[H + h, : h + 1] = -coef
            b_ub[H + h] = -(self.min_temp - base_temp[h])

        bounds = [(0.0, self.max_kw)] * H

        res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")

        if not res.success:
            raise RuntimeError(f"linprog: {res.message}")

        grid_boost = np.round(res.x, 4)
        cost = float(np.dot(grid_boost, prices))
        return DispatchResult(
            grid_boost_kw=grid_boost,
            prices_eur_kwh=prices,
            estimated_cost_eur=round(cost, 4),
        )

    def _greedy_fallback(
        self,
        prices: np.ndarray,
        solar_kw: np.ndarray,
    ) -> DispatchResult:
        """Cheapest N-hours rule: heat for enough hours to reach max_temp from min_temp.

        Energy needed: (max_temp - min_temp) * cap_kwh_per_c
        Hours needed:  energy_needed / (max_kw * eta), rounded up.
        Pick the cheapest non-solar hours.
        """
        energy_needed = (self.max_temp - self.min_temp) * self._cap  # kWh
        hours_needed = int(np.ceil(energy_needed / (self.max_kw * self.eta)))

        # Exclude hours with meaningful solar surplus
        solar_hours = set(h for h, kw in enumerate(solar_kw) if kw > 0.5)
        grid_candidates = [h for h in range(24) if h not in solar_hours]

        # Sort by price ascending, take cheapest hours_needed
        grid_candidates.sort(key=lambda h: prices[h])
        heat_hours = set(grid_candidates[:hours_needed])

        grid_boost = np.array(
            [self.max_kw if h in heat_hours else 0.0 for h in range(24)]
        )
        cost = float(np.dot(grid_boost, prices))
        return DispatchResult(
            grid_boost_kw=grid_boost,
            prices_eur_kwh=prices,
            estimated_cost_eur=round(cost, 4),
            fallback_used=True,
            notes="LP solver failed — using greedy cheapest-hours fallback.",
        )

    def _default_draw(self) -> np.ndarray:
        """Spread daily_draw_liters uniformly across waking hours (06:00–22:00)."""
        draw = np.zeros(24)
        waking_hours = list(range(6, 22))
        draw[waking_hours] = self.daily_draw_liters / len(waking_hours)
        return draw


# ------------------------------------------------------------------
# Utility
# ------------------------------------------------------------------

def _compress_hours(hours: List[int]) -> str:
    """Turn [1, 2, 3, 7, 8] into '01:00–03:00, 07:00–08:00'."""
    if not hours:
        return ""
    hours = sorted(hours)
    ranges: list[str] = []
    start = end = hours[0]
    for h in hours[1:]:
        if h == end + 1:
            end = h
        else:
            ranges.append(f"{start:02d}:00–{end:02d}:59")
            start = end = h
    ranges.append(f"{start:02d}:00–{end:02d}:59")
    return ", ".join(ranges)
