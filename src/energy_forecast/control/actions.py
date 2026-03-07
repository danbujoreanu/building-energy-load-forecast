"""
energy_forecast.control.actions
================================
Data structures for the demand-response control layer.

ForecastBundle  — P10 / P50 / P90 hourly load predictions (kWh)
EnvironmentState — external signals for a given forecast window
ControlAction   — the decision produced by ControlEngine for one hour
ActionType      — enum of possible device commands
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ActionType(str, Enum):
    """Control commands that can be sent to a managed device."""

    HEAT_NOW = "HEAT_NOW"
    """Draw from the grid immediately — price or solar conditions are favourable."""

    DEFER_HEATING = "DEFER_HEATING"
    """Delay heat / hot-water load — high price or solar forecast makes this hour costly."""

    PARTIAL_HEAT = "PARTIAL_HEAT"
    """Use a reduced setpoint — marginal price, uncertain solar, or soft demand headroom."""

    ALERT_HIGH_DEMAND = "ALERT_HIGH_DEMAND"
    """Forecast P90 exceeds the demand headroom threshold — notify operator / shed load."""


@dataclass
class ForecastBundle:
    """Probabilistic H+24 forecast for a single building.

    Each list holds 24 values, one per forecast hour starting at ``origin_time``.
    Values are in kWh (electricity imported per hour).
    """

    p10: list[float]
    """10th percentile — optimistic (low) consumption scenario."""

    p50: list[float]
    """Median forecast — best point estimate."""

    p90: list[float]
    """90th percentile — pessimistic (high) consumption scenario."""

    origin_time: datetime = field(default_factory=datetime.utcnow)
    """UTC timestamp at which the forecast was issued."""

    def __post_init__(self) -> None:
        if not (len(self.p10) == len(self.p50) == len(self.p90)):
            raise ValueError("p10, p50, p90 must all have the same length.")


@dataclass
class EnvironmentState:
    """External signals used by the ControlEngine for a forecast window.

    All lists are aligned to the same 24-hour forecast horizon.
    """

    solar_forecast_wh_m2: list[float]
    """Hourly direct solar irradiance forecast in W/m² (from Open-Meteo or Ecowitt).
    A value of 0.0 means night / cloudy with no generation expected."""

    grid_price_eur_kwh: list[float]
    """Hourly day-ahead electricity price in EUR/kWh (from SEMO or mock).
    Irish residential peak is typically 0.30–0.45 EUR/kWh; off-peak ~0.15 EUR/kWh."""

    timestamp: datetime
    """UTC timestamp for hour-0 of the forecast window."""

    building_id: str = "unknown"
    """Building identifier (used for logging and audit trail)."""

    def __post_init__(self) -> None:
        if len(self.solar_forecast_wh_m2) != len(self.grid_price_eur_kwh):
            raise ValueError(
                "solar_forecast_wh_m2 and grid_price_eur_kwh must have the same length."
            )


@dataclass
class ControlAction:
    """A single control decision for one forecast hour.

    Produced by :class:`~energy_forecast.control.controller.ControlEngine`.
    """

    target_hour: int
    """Hour offset from forecast origin (0 = current hour, 6 = 6 hours ahead)."""

    action: ActionType
    """The recommended device command."""

    confidence: float
    """Heuristic confidence score in [0, 1].  Higher = more certain recommendation."""

    reasoning: str
    """Human-readable explanation of why this action was chosen."""

    p50_kwh: float = 0.0
    """Median load forecast for this hour (kWh), for display purposes."""

    solar_wh_m2: float = 0.0
    """Solar irradiance forecast for this hour (W/m²), for display purposes."""

    price_eur_kwh: float = 0.0
    """Grid electricity price for this hour (EUR/kWh), for display purposes."""
