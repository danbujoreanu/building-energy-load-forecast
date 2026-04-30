"""
src/energy_forecast/tariffs/registry.py
=========================================
Irish residential electricity tariff registry.

All rates in €/kWh (VAT included, as shown on bills).
Standing charges in €/day.
Export rates where offered.

Data sources: supplier websites, PCW (bonkers.ie / switcher.ie), CRU Tariff Tracker.
Last updated: 2026-04-30. Verify before financial advice use.

Free-window caps apply where stated. The comparison engine handles the BGE free-slot
cap (100 kWh/month) by penalising over-cap usage at day rate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd


@dataclass(frozen=True)
class FreeWindow:
    """A zero-rate time window with an optional monthly kWh cap."""
    weekday: int | None        # 0=Mon…6=Sun; None = any day
    hour_start: int            # inclusive
    hour_end: int              # exclusive (e.g. 17 means 09:00–16:59)
    monthly_cap_kwh: float | None = None  # None = unlimited


@dataclass(frozen=True)
class Tariff:
    """
    A single Irish residential electricity tariff.

    rate_fn(dt) -> €/kWh for a given timestamp.  Overrides the simple
    day/night/peak fields for tariffs with complex windows.  If None, the
    default slot logic is used.
    """
    name: str
    supplier: str
    day: float                  # €/kWh — default daytime rate
    night: float                # €/kWh — 23:00–08:00
    peak: float                 # €/kWh — Mon–Fri 17:00–19:00 (0 if no peak)
    standing_daily: float       # €/day
    export: float = 0.0         # €/kWh credit for export (0 if none)
    free_windows: tuple[FreeWindow, ...] = field(default_factory=tuple)
    notes: str = ""

    def rate(self, dt: pd.Timestamp) -> float:
        """Return €/kWh for this timestamp."""
        h = dt.hour
        wd = dt.weekday()

        # Check free windows first (highest priority)
        free_used = 0.0
        for fw in self.free_windows:
            day_match = fw.weekday is None or wd == fw.weekday
            hour_match = fw.hour_start <= h < fw.hour_end
            if day_match and hour_match:
                return 0.0  # cap enforcement is done at monthly level by compare_tariffs

        # Peak: Mon–Fri 17:00–19:00
        if self.peak > 0 and wd < 5 and 17 <= h < 19:
            return self.peak

        # Night: 23:00–08:00
        if h >= 23 or h < 8:
            return self.night

        return self.day


# ─── Irish tariff registry (2026 Q2) ─────────────────────────────────────────

# Affinity discount (20%) is only relevant for Dan's specific contract.
# The registry stores UNDISCOUNTED rack rates so the engine works for any household.
# The comparison engine accepts an optional discount multiplier.

TARIFFS: dict[str, Tariff] = {

    # ── Bord Gáis Energy ─────────────────────────────────────────────────────

    "bge_free_sat": Tariff(
        name="BGE Free Time Saturday",
        supplier="Bord Gáis Energy",
        day=0.4034,
        night=0.2965,
        peak=0.4928,
        standing_daily=0.6152,
        export=0.185,
        free_windows=(FreeWindow(weekday=5, hour_start=9, hour_end=17, monthly_cap_kwh=100.0),),
        notes="Free Saturday 09:00–17:00, capped at 100 kWh/month. Peak Mon–Fri 17:00–19:00.",
    ),

    "bge_smart": Tariff(
        name="BGE Smart Electricity",
        supplier="Bord Gáis Energy",
        day=0.3945,
        night=0.2650,
        peak=0.4750,
        standing_daily=0.6300,
        export=0.185,
        notes="Standard TOU (no free window). Night 23:00–08:00. Peak Mon–Fri 17:00–19:00.",
    ),

    "bge_standard": Tariff(
        name="BGE Standard",
        supplier="Bord Gáis Energy",
        day=0.4250,
        night=0.4250,
        peak=0.4250,
        standing_daily=0.6152,
        export=0.185,
        notes="Flat rate — no TOU differentiation.",
    ),

    # ── Electric Ireland ──────────────────────────────────────────────────────

    "ei_homesmart": Tariff(
        name="Electric Ireland HomeSmart",
        supplier="Electric Ireland",
        day=0.3990,
        night=0.2790,
        peak=0.4890,
        standing_daily=0.6240,
        export=0.180,
        notes="TOU. Night 23:00–08:00. Peak Mon–Fri 17:00–19:00.",
    ),

    "ei_standard": Tariff(
        name="Electric Ireland Standard",
        supplier="Electric Ireland",
        day=0.4180,
        night=0.4180,
        peak=0.4180,
        standing_daily=0.6240,
        export=0.0,
        notes="Flat rate.",
    ),

    # ── Energia ──────────────────────────────────────────────────────────────

    "energia_smart": Tariff(
        name="Energia Smart",
        supplier="Energia",
        day=0.4020,
        night=0.2710,
        peak=0.4820,
        standing_daily=0.6180,
        export=0.185,
        notes="TOU. Night 23:00–08:00. Peak Mon–Fri 17:00–19:00.",
    ),

    # ── SSE Airtricity ────────────────────────────────────────────────────────

    "sse_smart": Tariff(
        name="SSE Airtricity Smart",
        supplier="SSE Airtricity",
        day=0.3970,
        night=0.2720,
        peak=0.4780,
        standing_daily=0.6210,
        export=0.183,
        notes="TOU. Night 23:00–08:00. Peak Mon–Fri 17:00–19:00.",
    ),

    # ── Yuno Energy ──────────────────────────────────────────────────────────

    "yuno_standard": Tariff(
        name="Yuno Standard TOU",
        supplier="Yuno Energy",
        day=0.3890,
        night=0.2580,
        peak=0.4650,
        standing_daily=0.5980,
        export=0.175,
        notes="Competitive TOU. Night 23:00–08:00. Peak Mon–Fri 17:00–19:00.",
    ),
}
