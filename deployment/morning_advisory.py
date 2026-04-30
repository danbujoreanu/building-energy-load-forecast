"""
deployment.morning_advisory
============================
Solar advisory for the 07:00 Eddi hot-water grid boost.

Fetches next-day GHI forecast from Open-Meteo (free, no API key — same
endpoint as the Gardening project's weather_poller.py), estimates solar
panel output, and recommends whether to skip the 07:00 boost.

Logic:
  peak_sun_hours >= 5  → SKIP_BOOST   (solar fills tank by midday)
  peak_sun_hours  2-4  → PARTIAL      (solar warms but may not fill; keep boost)
  peak_sun_hours  < 2  → KEEP_BOOST   (insufficient solar)

Read-only advisory only — never calls Eddi write endpoints.

Calibration (Maynooth, south-facing roof):
  Estimated annual generation ~3,000 kWh (from ESB export + Eddi diversion).
  Annual GHI at Maynooth ≈ 1,050 kWh/m²/year (Open-Meteo historical).
  Panel factor = 3,000 / 1,050 = 2.86 kWh output per kWh/m² GHI.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)

MAYNOOTH_LAT = 53.38
MAYNOOTH_LON = -6.59
PANEL_FACTOR = 1.6  # kWh solar per kWh/m² GHI (live-calibrated 2026-04-29: lower bound 1.418 from export+Eddi; ~1.6 includes estimated house self-consumption)

SKIP_BOOST_THRESHOLD  = 5  # peak sun hours (GHI > 200 W/m²) → solar fills tank
KEEP_BOOST_THRESHOLD  = 2  # below this → insufficient solar

# DAN-141: Hot water tank sizing (2-person household, 150L cylinder)
TANK_DAILY_KWH = 3.5   # kWh needed to heat tank from cold to 60°C
BOOST_KWH      = 0.55  # kWh consumed by Eddi 07:00 + 30-min grid boost


@dataclass
class SolarAdvisory:
    target_date: date
    ghi_forecast_kwh_m2: float
    peak_sun_hours: int
    estimated_solar_kwh: float
    expected_diversion_kwh: float  # DAN-141: min(estimated_solar, TANK_DAILY_KWH)
    recommendation: str            # "SKIP_BOOST" | "PARTIAL" | "KEEP_BOOST"
    pushover_title: str
    pushover_message: str
    issued_at: datetime
    daily_cost_eur: float | None = None  # DAN-143: tomorrow's predicted cost in €


def _fetch_ghi(target_date: date) -> tuple[float, int]:
    """Fetch daily GHI total (kWh/m²) and peak sun hours for target_date."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={MAYNOOTH_LAT}&longitude={MAYNOOTH_LON}"
        f"&hourly=shortwave_radiation"
        f"&forecast_days=2"
        f"&timezone=Europe%2FDublin"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()["hourly"]
    target_str = str(target_date)
    # Filter to only the 24 hours belonging to target_date
    pairs = [
        (t, v)
        for t, v in zip(data["time"], data["shortwave_radiation"])
        if t.startswith(target_str) and v is not None
    ]
    total_kwh_m2 = sum(v / 1000.0 for _, v in pairs)
    peak_hours = sum(1 for _, v in pairs if v > 200)
    return round(total_kwh_m2, 3), peak_hours


def build_advisory(
    target_date: date | None = None,
    daily_cost_eur: float | None = None,
) -> SolarAdvisory:
    """Fetch GHI forecast and build advisory.  Synchronous — wrap in asyncio.to_thread().

    Args:
        target_date:    Date to advise for (defaults to tomorrow Dublin time).
        daily_cost_eur: Optional predicted cost for target_date in €. When provided,
                        appended to the Pushover message. Computed by caller from the
                        16:00 LightGBM forecast × tariff slot rates (DAN-143).
    """
    import pytz
    dublin = pytz.timezone("Europe/Dublin")
    if target_date is None:
        target_date = (datetime.now(dublin) + timedelta(days=1)).date()

    ghi, peak_hours = _fetch_ghi(target_date)
    est_solar = round(ghi * PANEL_FACTOR, 1)

    # DAN-141: explicit diversion estimate — capped at tank daily need
    expected_diversion = round(min(est_solar, TANK_DAILY_KWH), 1)
    tank_met = expected_diversion >= TANK_DAILY_KWH * 0.9  # within 10% = "met"
    diversion_line = (
        f"Expected solar diversion: ~{expected_diversion:.1f} kWh "
        f"({'tank fully met ✅' if tank_met else f'of {TANK_DAILY_KWH:.1f} kWh needed'})."
    )

    # DAN-143: optional cost forecast line
    cost_line = ""
    if daily_cost_eur is not None:
        cost_line = f"\nForecast cost tomorrow: ~€{daily_cost_eur:.2f} (incl. standing charge)."

    if peak_hours >= SKIP_BOOST_THRESHOLD:
        rec = "SKIP_BOOST"
        title = f"☀️ Skip 07:00 Eddi boost — {target_date}"
        msg = (
            f"{peak_hours}h productive sun (GHI {ghi:.1f} kWh/m², ~{est_solar:.0f} kWh panel output).\n"
            f"{diversion_line}\n"
            f"Solar will fill the tank by midday — 07:00 grid boost not needed.\n"
            f"Consider skipping → save ~{BOOST_KWH * 23.72:.0f}c "
            f"({BOOST_KWH} kWh × 23.72c night rate)."
            f"{cost_line}\n"
            f"✅ Advisory only — Eddi schedule unchanged."
        )
    elif peak_hours >= KEEP_BOOST_THRESHOLD:
        rec = "PARTIAL"
        title = f"⛅ Partial sun — keep 07:00 boost ({target_date})"
        msg = (
            f"{peak_hours}h sun forecast (GHI {ghi:.1f} kWh/m², ~{est_solar:.0f} kWh panel output).\n"
            f"{diversion_line}\n"
            f"Solar will warm but may not fully heat tank — 07:00 boost is the safe call.\n"
            f"Solar diversion will top up during the day regardless."
            f"{cost_line}\n"
            f"ℹ️ Advisory only — Eddi schedule unchanged."
        )
    else:
        rec = "KEEP_BOOST"
        title = f"☁️ Keep 07:00 boost — low sun ({target_date})"
        msg = (
            f"Only {peak_hours}h productive sun (GHI {ghi:.1f} kWh/m², ~{est_solar:.0f} kWh panel output).\n"
            f"{diversion_line}\n"
            f"Insufficient solar — 07:00 grid boost needed. No action required."
            f"{cost_line}\n"
            f"ℹ️ Advisory only — Eddi schedule unchanged."
        )

    logger.info(
        "Solar advisory for %s: %s (GHI=%.2f, peak=%dh, est=%.1f kWh, diversion=%.1f kWh%s)",
        target_date, rec, ghi, peak_hours, est_solar, expected_diversion,
        f", cost=€{daily_cost_eur:.2f}" if daily_cost_eur is not None else "",
    )
    return SolarAdvisory(
        target_date=target_date,
        ghi_forecast_kwh_m2=ghi,
        peak_sun_hours=peak_hours,
        estimated_solar_kwh=est_solar,
        expected_diversion_kwh=expected_diversion,
        recommendation=rec,
        pushover_title=title,
        pushover_message=msg,
        issued_at=datetime.now(timezone.utc),
        daily_cost_eur=daily_cost_eur,
    )


def send_pushover(advisory: SolarAdvisory) -> None:
    """POST advisory to Pushover. Synchronous — wrap in asyncio.to_thread()."""
    token = os.environ.get("PUSHOVER_APP_TOKEN", "")
    user  = os.environ.get("PUSHOVER_USER_KEY", "")
    if not token or not user:
        logger.warning("[pushover] PUSHOVER_APP_TOKEN or PUSHOVER_USER_KEY not set — skipping.")
        return

    priority_map = {"SKIP_BOOST": 0, "PARTIAL": -1, "KEEP_BOOST": -2}
    resp = requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token":    token,
            "user":     user,
            "title":    advisory.pushover_title,
            "message":  advisory.pushover_message,
            "priority": priority_map.get(advisory.recommendation, -1),
        },
        timeout=10,
    )
    resp.raise_for_status()
    logger.info("[pushover] Advisory sent: %s", advisory.recommendation)
