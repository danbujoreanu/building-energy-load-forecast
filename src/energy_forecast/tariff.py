"""BGE 'Free Time Saturday' tariff rates and rate-slot helpers.

Rates are post-20% Affinity discount (applied to all usage charges except export).
Contract: Bord Gáis Energy, valid to 15 June 2026.

Single source of truth — import from here rather than duplicating in scripts.
"""

from __future__ import annotations

import pandas as pd

# Rates in €/kWh (20% Affinity discount applied to all usage charges)
BGE: dict[str, float] = {
    "day":            0.4034 * 0.80,   # €0.32272/kWh  — all other hours
    "night":          0.2965 * 0.80,   # €0.23720/kWh  — 23:00–08:00
    "peak":           0.4928 * 0.80,   # €0.39424/kWh  — Mon–Fri 17:00–19:00 only
    "free":           0.00,            # €0.00/kWh     — Saturday 09:00–17:00
    "export":         0.185,           # €0.18500/kWh  (no Affinity discount on export)
    "standing_daily": 0.6152,          # €/day
}

FREE_CAP_KWH: float = 100.0  # BGE monthly free-slot allowance cap


def rate_slot(dt: pd.Timestamp) -> str:
    """Return rate slot name for a given timestamp.

    Priority order:
      1. Saturday 09:00–16:59  → 'free'
      2. Mon–Fri 17:00–18:59   → 'peak'
      3. 23:00–07:59           → 'night'
      4. otherwise             → 'day'
    """
    h = dt.hour
    wd = dt.weekday()  # 0=Mon … 6=Sun
    if wd == 5 and 9 <= h < 17:
        return "free"
    if wd < 5 and 17 <= h < 19:
        return "peak"
    if h >= 23 or h < 8:
        return "night"
    return "day"


def rate_for_slot(dt: pd.Timestamp) -> tuple[str, float]:
    """Return (slot_name, €/kWh) for a given timestamp."""
    name = rate_slot(dt)
    return name, BGE[name]
