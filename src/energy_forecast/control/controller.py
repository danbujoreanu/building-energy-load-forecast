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

import fcntl
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from energy_forecast.control.actions import (
    ActionType,
    ControlAction,
    EnvironmentState,
    ForecastBundle,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Audit log — append-only JSONL, one line per ControlAction decision
# ---------------------------------------------------------------------------

# Resolve repo root: src/energy_forecast/control/controller.py → parents[3] = repo root
_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
_AUDIT_LOG_PATH: Path = _REPO_ROOT / "outputs" / "logs" / "control_decisions.jsonl"


def _append_audit_log(
    action: ControlAction,
    city: str,
    building_id: str,
    dry_run: bool,
) -> None:
    """Append one JSON line to the control audit log.

    Creates the parent directory if needed.  Uses fcntl.flock for concurrent-safe
    writes so multiple processes cannot interleave log entries.  Any exception is
    silently logged at DEBUG level — audit log failure must NEVER break the
    control loop.

    Args:
        action:      The ControlAction to record.
        city:        Dataset / deployment city identifier.
        building_id: Building identifier (from EnvironmentState or caller).
        dry_run:     True if no real device command was sent.
    """
    try:
        _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "city":          city,
            "building_id":   building_id,
            "target_hour":   action.target_hour,
            "action":        action.action.value,
            "confidence":    round(action.confidence, 4),
            "reasoning":     action.reasoning,
            "p50_kwh":       round(action.p50_kwh, 4),
            "solar_wh_m2":   round(action.solar_wh_m2, 2),
            "price_eur_kwh": round(action.price_eur_kwh, 4),
            "dry_run":       dry_run,
        }
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with open(_AUDIT_LOG_PATH, "a", encoding="utf-8") as fh:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX)
                fh.write(line)
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
    except AttributeError:
        # fcntl not available on Windows — fall back to unguarded write
        try:
            with open(_AUDIT_LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(line)  # type: ignore[name-defined]
        except Exception as exc:
            logger.debug("_append_audit_log: fallback write failed: %s", exc)
    except Exception as exc:
        logger.debug("_append_audit_log: failed (non-critical): %s", exc)


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
        city: str = "unknown",
        dry_run: bool = False,
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
        city:
            Dataset / deployment city identifier, used in the audit log.
        dry_run:
            If True, records actions as simulated (no real device command sent).
            Propagated to each ControlAction and the audit log.

        Returns
        -------
        list[ControlAction]
            One :class:`ControlAction` per requested hour, in order.
        """
        n_hours = len(forecast.p50)
        if target_hours is None:
            target_hours = list(range(n_hours))

        building_id = env.building_id

        actions: list[ControlAction] = []
        for h in target_hours:
            if h >= n_hours:
                logger.warning("target_hour=%d exceeds forecast length %d — skipped.", h, n_hours)
                continue
            action = self._decide_one_hour(h, forecast, env)
            # Stamp dry_run flag and plain-English user message
            action.dry_run = dry_run
            action.user_message = self._format_user_message(
                action_type=action.action,
                target_hour=action.target_hour,
                p50_kwh=action.p50_kwh,
                solar_wh_m2=action.solar_wh_m2,
                price_eur_kwh=action.price_eur_kwh,
                confidence=action.confidence,
            )
            actions.append(action)
            _append_audit_log(action, city=city, building_id=building_id, dry_run=dry_run)

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

    def _format_user_message(
        self,
        action_type: ActionType,
        target_hour: int,
        p50_kwh: float,
        solar_wh_m2: float,
        price_eur_kwh: float,
        confidence: float,
    ) -> str:
        """Generate a plain-English consumer-facing explanation for a control action.

        Written in the voice of a knowledgeable friend, not a technical system.
        Short, actionable, and honest about uncertainty.

        Args:
            action_type:    The ActionType enum value for this decision.
            target_hour:    Hour offset from forecast origin (0-indexed).
            p50_kwh:        Median load forecast for this hour (kWh).
            solar_wh_m2:    Solar irradiance forecast (W/m²).
            price_eur_kwh:  Grid electricity price (EUR/kWh).
            confidence:     Heuristic confidence score [0, 1].

        Returns:
            A single plain-English sentence or two suitable for display in a
            consumer app or morning brief.
        """
        savings = price_eur_kwh * p50_kwh

        if action_type == ActionType.DEFER_HEATING:
            if solar_wh_m2 > self.solar_threshold:
                return (
                    f"Good news — your panels should produce enough for hot water around "
                    f"hour {target_hour}. Waiting could save you around "
                    f"\u20ac{savings:.2f}."
                )
            else:
                return (
                    f"Electricity prices are elevated at {price_eur_kwh:.2f} \u20ac/kWh "
                    f"this hour. Deferring your hot water heating should save you around "
                    f"\u20ac{savings:.2f}."
                )

        if action_type == ActionType.HEAT_NOW:
            if price_eur_kwh < self.price_offpeak:
                return (
                    f"Cheap rate running now at {price_eur_kwh:.2f} \u20ac/kWh \u2014 "
                    f"good time to heat the tank. Running your Eddi now costs roughly "
                    f"\u20ac{savings:.2f}."
                )
            # Default HEAT_NOW
            return (
                f"Conditions look normal for hour {target_hour}. Running the Eddi now "
                f"at {price_eur_kwh:.2f} \u20ac/kWh."
            )

        if action_type == ActionType.PARTIAL_HEAT:
            return (
                f"Mixed signals this hour \u2014 moderate solar and mid-range price "
                f"({price_eur_kwh:.2f} \u20ac/kWh). A partial boost balances cost and "
                f"comfort."
            )

        if action_type == ActionType.ALERT_HIGH_DEMAND:
            return (
                f"Heads up: we\u2019re expecting high electricity use around hour "
                f"{target_hour} (forecast: {p50_kwh:.1f} kWh). Consider running large "
                f"appliances earlier or later today."
            )

        # Fallback (should not be reached with known ActionTypes)
        return (
            f"Conditions look normal for hour {target_hour}. Running the Eddi now "
            f"at {price_eur_kwh:.2f} \u20ac/kWh."
        )

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
