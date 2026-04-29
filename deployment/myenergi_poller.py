"""
deployment.myenergi_poller
===========================
Daily poller for MyEnergi hub data (read-only — never writes to Eddi).

Scheduled at 23:30 Europe/Dublin to capture the full day's data.

What it does:
  1. Fetches minute-level `imp` (grid import) and `hsk` (Eddi hot-water diversion)
     from the MyEnergi /cgi-jday-E{serial}-{YYYY}-{MM}-{DD} endpoint.
  2. Aggregates to 30-min intervals and upserts into `myenergi_readings`.
  3. Reads today's Eddi total (kWh) from get_status() and stores in `solar_actuals`
     as the eddi_kwh field (alongside ghi_actual from weather_log if available).
  4. Logs the actual GHI from Open-Meteo historical API into weather_log
     (data_type='actual' for yesterday, so forecast vs actual can be compared).

Conversion:
  MyEnergi `imp` and `hsk` fields are instantaneous centi-Watts sampled once per minute.
  30-min kWh = average_cW * 30 / 100 / 1000  (avg watts * hours / 1000)
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import requests
from requests.auth import HTTPDigestAuth

logger = logging.getLogger(__name__)

HUB_SERIAL = os.environ.get("MYENERGI_SERIAL", "21509692")
API_KEY     = os.environ.get("MYENERGI_API_KEY", "")
DIRECTOR    = "https://director.myenergi.net"

MAYNOOTH_LAT = 53.38
MAYNOOTH_LON = -6.59


# ─── MyEnergi helpers ────────────────────────────────────────────────────────

def _auth() -> HTTPDigestAuth:
    return HTTPDigestAuth(HUB_SERIAL, API_KEY)


def _fetch_day_minutes(target_date: date) -> list[dict]:
    """Return list of minute-level dicts for target_date from MyEnergi jday endpoint."""
    url = (
        f"{DIRECTOR}/cgi-jday-E{HUB_SERIAL}"
        f"-{target_date.year}-{target_date.month:02d}-{target_date.day:02d}"
    )
    resp = requests.get(url, auth=_auth(), timeout=20)
    resp.raise_for_status()
    data = resp.json()
    # Response is a list; the first item with key matching "U{serial}" contains minute data
    for item in data:
        key = f"U{HUB_SERIAL}"
        if key in item:
            return item[key]
    return []


def _aggregate_to_30min(
    minutes: list[dict],
    target_date: date,
) -> list[dict]:
    """
    Aggregate minute samples to 30-min intervals.
    Returns list of dicts: {interval_start (UTC), import_kwh, eddi_kwh, sample_count}.
    """
    # Build minute-indexed lookup: minute 0-1439
    by_minute: dict[int, dict] = {}
    for entry in minutes:
        m = entry.get("hr", 0) * 60 + entry.get("min", 0)
        by_minute[m] = entry

    slots = []
    for slot_idx in range(48):  # 48 × 30-min slots per day
        start_min = slot_idx * 30
        slot_samples = [by_minute[m] for m in range(start_min, start_min + 30) if m in by_minute]
        if not slot_samples:
            continue

        avg_import_cw = sum(s.get("imp", 0) for s in slot_samples) / len(slot_samples)
        avg_eddi_cw   = sum(s.get("hsk", 0) for s in slot_samples) / len(slot_samples)

        # cW avg → kWh for 30-min slot: avg_cW * 0.5h / 100 / 1000
        import_kwh = round(avg_import_cw * 0.5 / 100 / 1000, 6)
        eddi_kwh   = round(avg_eddi_cw   * 0.5 / 100 / 1000, 6)

        # interval_start in UTC from Europe/Dublin local midnight + minutes
        import pytz
        dublin = pytz.timezone("Europe/Dublin")
        local_midnight = dublin.localize(datetime(target_date.year, target_date.month, target_date.day))
        interval_start = (local_midnight + timedelta(minutes=start_min)).astimezone(timezone.utc)

        slots.append({
            "interval_start": interval_start,
            "import_kwh":     import_kwh,
            "eddi_kwh":       eddi_kwh,
            "sample_count":   len(slot_samples),
        })
    return slots


# ─── Open-Meteo actual GHI ───────────────────────────────────────────────────

def _fetch_ghi_actual(target_date: date) -> list[dict]:
    """
    Fetch actual hourly GHI (shortwave_radiation) for target_date from Open-Meteo.
    Uses the historical/archive endpoint — forecast endpoint retention is ~7 days.
    Returns list of {hour_utc, ghi_wh_m2}.
    """
    date_str = str(target_date)
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={MAYNOOTH_LAT}&longitude={MAYNOOTH_LON}"
        f"&hourly=shortwave_radiation"
        f"&start_date={date_str}&end_date={date_str}"
        f"&timezone=Europe%2FDublin"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()["hourly"]
    rows = []
    import pytz
    dublin = pytz.timezone("Europe/Dublin")
    for time_str, ghi in zip(data["time"], data["shortwave_radiation"]):
        if ghi is None:
            continue
        dt_local = dublin.localize(datetime.fromisoformat(time_str))
        dt_utc   = dt_local.astimezone(timezone.utc)
        rows.append({"hour_utc": dt_utc, "ghi_wh_m2": round(ghi, 2)})
    return rows


# ─── DB writes ───────────────────────────────────────────────────────────────

_UPSERT_MYENERGI = """
INSERT INTO myenergi_readings (hub_serial, interval_start, import_kwh, eddi_kwh, sample_count)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (hub_serial, interval_start) DO UPDATE SET
    import_kwh   = EXCLUDED.import_kwh,
    eddi_kwh     = EXCLUDED.eddi_kwh,
    sample_count = EXCLUDED.sample_count,
    fetched_at   = NOW()
"""

_UPSERT_WEATHER_ACTUAL = """
INSERT INTO weather_log (location, hour_utc, ghi_wh_m2, data_type)
VALUES ($1, $2, $3, 'actual')
ON CONFLICT (location, hour_utc, data_type) DO UPDATE SET
    ghi_wh_m2  = EXCLUDED.ghi_wh_m2,
    fetched_at = NOW()
"""

_UPSERT_SOLAR_ACTUALS = """
INSERT INTO solar_actuals (solar_date, eddi_kwh, ghi_actual)
VALUES ($1, $2, $3)
ON CONFLICT (solar_date) DO UPDATE SET
    eddi_kwh   = COALESCE(EXCLUDED.eddi_kwh,  solar_actuals.eddi_kwh),
    ghi_actual = COALESCE(EXCLUDED.ghi_actual, solar_actuals.ghi_actual),
    panel_factor_obs = CASE
        WHEN EXCLUDED.ghi_actual > 0 AND solar_actuals.export_kwh IS NOT NULL
        THEN ROUND(((solar_actuals.export_kwh + COALESCE(EXCLUDED.eddi_kwh, 0)) / EXCLUDED.ghi_actual)::NUMERIC, 4)
        ELSE solar_actuals.panel_factor_obs
    END,
    recorded_at = NOW()
"""


async def run_daily_poll(pool, target_date: date | None = None) -> None:
    """
    Full daily poll: fetch MyEnergi minute data + Open-Meteo actuals, persist to DB.
    Synchronous network calls are wrapped in asyncio.to_thread().
    """
    import asyncio

    if target_date is None:
        import pytz
        dublin = pytz.timezone("Europe/Dublin")
        target_date = datetime.now(dublin).date()

    logger.info("[myenergi_poller] Starting daily poll for %s", target_date)

    # Fetch in parallel (both are blocking HTTP)
    minutes_raw, ghi_rows = await asyncio.gather(
        asyncio.to_thread(_fetch_day_minutes, target_date),
        asyncio.to_thread(_fetch_ghi_actual, target_date),
    )

    slots = _aggregate_to_30min(minutes_raw, target_date)
    daily_eddi_kwh = round(sum(s["eddi_kwh"] for s in slots), 3)
    daily_ghi_kwh  = round(sum(r["ghi_wh_m2"] for r in ghi_rows) / 1000.0, 3)

    async with pool.acquire() as conn:
        # Upsert 30-min readings
        await conn.executemany(
            _UPSERT_MYENERGI,
            [(HUB_SERIAL, s["interval_start"], s["import_kwh"], s["eddi_kwh"], s["sample_count"])
             for s in slots],
        )
        # Upsert hourly GHI actuals
        await conn.executemany(
            _UPSERT_WEATHER_ACTUAL,
            [("maynooth", r["hour_utc"], r["ghi_wh_m2"]) for r in ghi_rows],
        )
        # Upsert solar_actuals (eddi + ghi for the day)
        await conn.execute(_UPSERT_SOLAR_ACTUALS, target_date, daily_eddi_kwh, daily_ghi_kwh)

    logger.info(
        "[myenergi_poller] Done for %s — %d 30-min slots, Eddi %.2f kWh, GHI %.3f kWh/m²",
        target_date, len(slots), daily_eddi_kwh, daily_ghi_kwh,
    )
