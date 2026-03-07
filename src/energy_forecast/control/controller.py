"""
energy_forecast.control.controller
====================================
Probabilistic demand-response ControlEngine.

Translates a :class:`~energy_forecast.control.actions.ForecastBundle` and an
:class:`~energy_forecast.control.actions.EnvironmentState` into a list of
:class:`~energy_forecast.control.actions.ControlAction` objects — one per
requested target hour.

Decision Logic
--------------
For each target hour *h* (0-indexed from forecast origin):

1. DEFER_HEATING  — if solar_forecast[h] > solar_threshold  AND
                       grid_price[h]     > price_peak_threshold
   Rationale: strong solar generation expected, price is high → wait for PV.

2. ALERT_HIGH_DEMAND — if p90_load[h] > demand_headroom_kw
   Rationale: worst-case consumption exceeds building capacity → notify operator.

3. HEAT_NOW (off-peak window) — if grid_price[h] < price_offpeak_threshold
   Rationale: cheap electricity → heat water or charge battery now.

4. HEAT_NOW (default) — baseline safe action when no signal is strong.

Thresholds are set to sensible Irish-home defaults but are fully configurable
via constructor arguments or ``config.yaml`` entries (when integrated).

Usage
-----
    from energy_forecast.control.controller import ControlEngine
    from energy_forecast.control.actions import ForecastBundle, EnvironmentState

    engine = ControlEngine()
    actions = engine.decide(forecast, env, target_hours=[6, 7, 8])
    print(engine.explain(actions))
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from energy_forecast.control.actions import (
    ActionType,
    ControlAction,
    EnvironmentState,
    ForecastBundle,
)

logger = logging.getLogger(__name__)


class ControlEngine:
    """Rule-based demand-response controller driven by probabilistic load forecasts.

    Parameters
    ----------
    solar_threshold_wh_m2:
        Minimum direct solar irradiance (W/m²) that makes PV contribution
        meaningful.  Default 150 W/m² ≈ bright overcast Irish day.
    price_peak_threshold_eur:
        Grid price above which drawing electricity is considered expensive.
        Default 0.28 EUR/kWh (typical Irish peak tier).
    price_offpeak_threshold_eur:
        Grid price below which drawing electricity is considered cheap.
        Default 0.16 EUR/kWh (Irish night-rate / off-peak tier).
    demand_headroom_kw:
        If the P90 forecast exceeds this value (kWh in the hour), trigger
        ALERT_HIGH_DEMAND.  Set to the building's contracted capacity limit.
        Default 80 kWh/h — reasonable for a medium school building.
    """

    def __init__(
        self,
        solar_threshold_wh_m2: float = 150.0,
        price_peak_threshold_eur: float = 0.28,
        price_offpeak_threshold_eur: float = 0.16,
        demand_headroom_kw: float = 80.0,
    ) -> None:
        self.solar_threshold = solar_threshold_wh_m2
        self.price_peak = price_peak_threshold_eur
        self.price_offpeak = price_offpeak_threshold_eur
        self.demand_headroom = demand_headroom_kw

        logger.info(
            "ControlEngine initialised — solar_threshold=%.0f W/m², "
            "price_peak=%.2f EUR/kWh, price_offpeak=%.2f EUR/kWh, "
            "demand_headroom=%.0f kWh/h",
            self.solar_threshold,
            self.price_peak,
            self.price_offpeak,
            self.demand_headroom,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def decide(
        self,
        forecast: ForecastBundle,
        env: EnvironmentState,
        target_hours: list[int] | None = None,
    ) -> list[ControlAction]:
        """Produce a control action for each requested forecast hour.

        Parameters
        ----------
        forecast:
            P10/P50/P90 load predictions (kWh per hour) for the next 24 hours.
        env:
            Aligned solar irradiance and grid price signals (24 values each).
        target_hours:
            List of hour offsets (0-indexed from forecast origin) for which
            decisions are needed.  Defaults to all 24 hours.

        Returns
        -------
        list[ControlAction]
            One :class:`ControlAction` per requested hour, in order.
        """
        n_hours = len(forecast.p50)
        if target_hours is None:
            target_hours = list(range(n_hours))

        actions: list[ControlAction] = []
        for h in target_hours:
            if h >= n_hours:
                logger.warning("target_hour=%d exceeds forecast length %d — skipped.", h, n_hours)
                continue
            action = self._decide_one_hour(h, forecast, env)
            actions.append(action)

        return actions

    def explain(self, actions: list[ControlAction]) -> str:
        """Return a human-readable morning brief from a list of ControlActions.

        Example output::

            === Demand-Response Morning Brief ===
            06:00  DEFER_HEATING   [conf=0.85]  Solar 320 W/m², price 0.34 EUR/kWh → wait for PV
            07:00  DEFER_HEATING   [conf=0.90]  Solar 480 W/m², price 0.36 EUR/kWh → wait for PV
            08:00  HEAT_NOW        [conf=0.60]  Solar  80 W/m², price 0.30 EUR/kWh → default safe action
        """
        lines = ["=== Demand-Response Morning Brief ==="]
        for a in actions:
            hour_str = f"{a.target_hour:02d}:00"
            action_str = a.action.value.ljust(20)
            conf_str = f"[conf={a.confidence:.2f}]"
            lines.append(
                f"  {hour_str}  {action_str}  {conf_str}  {a.reasoning}"
            )
        lines.append(f"  Generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _decide_one_hour(
        self,
        h: int,
        forecast: ForecastBundle,
        env: EnvironmentState,
    ) -> ControlAction:
        """Apply the decision tree for a single hour offset *h*."""
        solar = env.solar_forecast_wh_m2[h] if h < len(env.solar_forecast_wh_m2) else 0.0
        price = env.grid_price_eur_kwh[h] if h < len(env.grid_price_eur_kwh) else self.price_peak
        p50 = forecast.p50[h]
        p90 = forecast.p90[h]

        # Rule 1: Demand alert — P90 exceeds headroom (safety, highest priority)
        if p90 > self.demand_headroom:
            return ControlAction(
                target_hour=h,
                action=ActionType.ALERT_HIGH_DEMAND,
                confidence=min(0.5 + (p90 - self.demand_headroom) / self.demand_headroom, 0.99),
                reasoning=(
                    f"P90 load {p90:.1f} kWh/h exceeds headroom {self.demand_headroom:.0f} kWh/h "
                    f"→ shed non-critical loads or alert building manager"
                ),
                p50_kwh=p50,
                solar_wh_m2=solar,
                price_eur_kwh=price,
            )

        # Rule 2: Defer heating — strong solar + expensive grid
        if solar >= self.solar_threshold and price >= self.price_peak:
            solar_score = min((solar - self.solar_threshold) / self.solar_threshold, 1.0)
            price_score = min((price - self.price_peak) / self.price_peak, 1.0)
            confidence = 0.60 + 0.35 * (solar_score + price_score) / 2
            return ControlAction(
                target_hour=h,
                action=ActionType.DEFER_HEATING,
                confidence=round(min(confidence, 0.97), 2),
                reasoning=(
                    f"Solar {solar:.0f} W/m² (≥{self.solar_threshold:.0f}), "
                    f"price {price:.3f} EUR/kWh (≥{self.price_peak:.2f}) "
                    f"→ wait for PV generation to cover load"
                ),
                p50_kwh=p50,
                solar_wh_m2=solar,
                price_eur_kwh=price,
            )

        # Rule 3: Off-peak window — cheap electricity → heat now
        if price < self.price_offpeak:
            return ControlAction(
                target_hour=h,
                action=ActionType.HEAT_NOW,
                confidence=round(min(0.70 + (self.price_offpeak - price) / self.price_offpeak * 0.25, 0.95), 2),
                reasoning=(
                    f"Price {price:.3f} EUR/kWh (< off-peak threshold {self.price_offpeak:.2f}) "
                    f"→ cheap window, heat water / charge battery now"
                ),
                p50_kwh=p50,
                solar_wh_m2=solar,
                price_eur_kwh=price,
            )

        # Rule 4: Marginal conditions — partial heat if solar is moderate
        if solar >= self.solar_threshold * 0.5 and price < self.price_peak:
            return ControlAction(
                target_hour=h,
                action=ActionType.PARTIAL_HEAT,
                confidence=0.55,
                reasoning=(
                    f"Moderate solar {solar:.0f} W/m², acceptable price {price:.3f} EUR/kWh "
                    f"→ run at reduced setpoint"
                ),
                p50_kwh=p50,
                solar_wh_m2=solar,
                price_eur_kwh=price,
            )

        # Default: safe baseline
        return ControlAction(
            target_hour=h,
            action=ActionType.HEAT_NOW,
            confidence=0.50,
            reasoning=(
                f"No strong signal (solar {solar:.0f} W/m², price {price:.3f} EUR/kWh, "
                f"P50 {p50:.1f} kWh) → default safe action"
            ),
            p50_kwh=p50,
            solar_wh_m2=solar,
            price_eur_kwh=price,
        )
