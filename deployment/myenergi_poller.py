"""
deployment.myenergi_poller
===========================
Daily poller for MyEnergi hub data (read-only — never writes to Eddi).

Scheduled at 23:30 Europe/Dublin to capture the full day's data.

What it does:
  1. Fetches minute-level `imp` (grid import), `h1b`/`h1d` (Eddi grid+solar),
     `exp` (solar export) from /cgi-jday-E{serial}-{YYYY}-{MM}-{DD} endpoint.
  2. Aggregates to 30-min intervals and upserts into `myenergi_readings`.
  3. Upserts daily totals → `solar_actuals.eddi_kwh` + `solar_actuals.ghi_actual`.
  4. Logs the actual GHI from Open-Meteo historical API into weather_log.

Conversion:
  MyEnergi energy fields (imp, exp, h1b, h1d) are **Joules per 1-minute interval**
  (total energy in that minute), NOT instantaneous centi-Watts.
  Verified 2026-05-07: h1b=181,680 → 181,680 J / 60 s = 3,028 W (3 kW immersion ✓).
  30-min kWh = sum_of_J_in_slot / 3,600,000
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
    # Response is a dict: {"U{serial}": [minute_entries...], ...}
    return data.get(f"U{HUB_SERIAL}", [])


def _aggregate_to_30min(
    minutes: list[dict],
    target_date: date,
) -> list[dict]:
    """
    Aggregate minute samples to 30-min intervals.
    Returns list of dicts: {interval_start (UTC), import_kwh, eddi_kwh, sample_count}.

    Timezone note
    -------------
    The API returns `hr`/`min` in **UTC** (not Dublin local time).
    `by_minute` keys are therefore UTC-based (hr*60+min = UTC offset from UTC midnight).
    `start_min` is a Dublin-local offset from Dublin midnight.
    In BST (UTC+1) these differ by 60 minutes — corrected via `utc_start` below.
    Without this correction every slot would pull data from 1 hour too late (UTC),
    making the 07:00 Dublin boost appear in the 06:00 Dublin slot in the DB.
    """
    import pytz
    dublin = pytz.timezone("Europe/Dublin")
    local_midnight = dublin.localize(datetime(target_date.year, target_date.month, target_date.day))
    # UTC offset in minutes: 0 in winter (GMT), 60 in summer (BST).
    utc_offset_min = int(local_midnight.utcoffset().total_seconds() / 60)

    # Build minute-indexed lookup keyed by UTC offset: hr*60+min (0-1439 in the API).
    by_minute: dict[int, dict] = {}
    for entry in minutes:
        m = entry.get("hr", 0) * 60 + entry.get("min", 0)
        by_minute[m] = entry

    slots = []
    for slot_idx in range(48):  # 48 × 30-min slots per day
        start_min = slot_idx * 30  # Dublin-local minutes from midnight
        # Align to UTC: subtract UTC offset so we index the correct API entries.
        # In BST: utc_start = start_min - 60.  First 2 slots (Dublin 00:00-01:00)
        # yield utc_start < 0 → no API data → skipped; that data lives in the
        # previous UTC day's API response and is counted in yesterday's last 2 slots.
        utc_start = start_min - utc_offset_min
        slot_samples = [by_minute[m] for m in range(utc_start, utc_start + 30) if m in by_minute]
        if not slot_samples:
            continue

        # API values are Joules per 1-minute interval (NOT centi-Watts).
        # Verified 2026-05-07: h1b=181,680 J → 181,680/60 = 3,028 W (3 kW immersion ✓).
        # hsk is a heat-sink status counter, NOT energy — do not use it here.
        # kWh = sum_J / 3,600,000
        import_kwh       = round(sum(s.get("imp", 0)                      for s in slot_samples) / 3_600_000, 6)
        eddi_kwh         = round(sum(s.get("h1b", 0) + s.get("h1d", 0)   for s in slot_samples) / 3_600_000, 6)
        eddi_divert_kwh  = round(sum(s.get("h1d", 0)                      for s in slot_samples) / 3_600_000, 6)  # solar → Eddi only
        export_kwh       = round(sum(s.get("exp", 0)                      for s in slot_samples) / 3_600_000, 6)  # solar → grid

        # interval_start is anchored to Dublin local midnight + Dublin-local offset → UTC.
        interval_start = (local_midnight + timedelta(minutes=start_min)).astimezone(timezone.utc)

        slots.append({
            "interval_start":    interval_start,
            "import_kwh":        import_kwh,
            "eddi_kwh":          eddi_kwh,
            "eddi_divert_kwh":   eddi_divert_kwh,
            "export_kwh":        export_kwh,
            "sample_count":      len(slot_samples),
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


# ─── Open-Meteo forecast (7-day, all variables) ─────────────────────────────

def _fetch_weather_forecast() -> list[dict]:
    """
    Fetch 7-day hourly weather forecast from Open-Meteo (free, no API key).
    Returns one dict per hour with the same variable set as the Gardening
    project's weather_poller.py — keeps both pipelines in sync.

    Variables captured (all stored in weather_log with data_type='forecast'):
        ghi_wh_m2    — shortwave_radiation W/m² (solar irradiance)
        temp_c       — 2m air temperature °C
        rh_pct       — relative humidity %
        precip_mm    — precipitation mm/h
        wind_kmh     — wind speed km/h at 10m
        cloud_pct    — cloud cover 0–100 %
        weather_code — WMO weather interpretation code

    Note: forecast values are overwritten on each run (upsert).  The 7-day
    window means any given hour is captured ≥7 times before it becomes actual.
    Run this job daily (06:00 Dublin) to maintain a continuous forecast record.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={MAYNOOTH_LAT}&longitude={MAYNOOTH_LON}"
        f"&hourly=shortwave_radiation,temperature_2m,relative_humidity_2m,"
        f"precipitation,windspeed_10m,cloud_cover,weather_code"
        f"&forecast_days=7"
        f"&timezone=UTC"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()["hourly"]

    rows = []
    fields = ("shortwave_radiation", "temperature_2m", "relative_humidity_2m",
              "precipitation", "windspeed_10m", "cloud_cover", "weather_code")
    for values in zip(data["time"], *(data[f] for f in fields)):
        ts_str, ghi, temp, rh, precip, wind, cloud, wcode = values
        dt_utc = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
        rows.append({
            "hour_utc":     dt_utc,
            "ghi_wh_m2":    round(ghi,    2) if ghi    is not None else None,
            "temp_c":       round(temp,   2) if temp   is not None else None,
            "rh_pct":       round(rh,     1) if rh     is not None else None,
            "precip_mm":    round(precip, 2) if precip is not None else None,
            "wind_kmh":     round(wind,   1) if wind   is not None else None,
            "cloud_pct":    int(cloud)       if cloud  is not None else None,
            "weather_code": int(wcode)       if wcode  is not None else None,
        })
    return rows


# ─── DB writes ───────────────────────────────────────────────────────────────

_UPSERT_MYENERGI = """
INSERT INTO myenergi_readings
    (hub_serial, interval_start, import_kwh, eddi_kwh, eddi_divert_kwh, export_kwh, sample_count)
VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (hub_serial, interval_start) DO UPDATE SET
    import_kwh      = EXCLUDED.import_kwh,
    eddi_kwh        = EXCLUDED.eddi_kwh,
    eddi_divert_kwh = EXCLUDED.eddi_divert_kwh,
    export_kwh      = EXCLUDED.export_kwh,
    sample_count    = EXCLUDED.sample_count,
    fetched_at      = NOW()
"""

_UPSERT_WEATHER_ACTUAL = """
INSERT INTO weather_log (location, hour_utc, ghi_wh_m2, data_type)
VALUES ($1, $2, $3, 'actual')
ON CONFLICT (location, hour_utc, data_type) DO UPDATE SET
    ghi_wh_m2  = EXCLUDED.ghi_wh_m2,
    fetched_at = NOW()
"""

_UPSERT_WEATHER_FORECAST = """
INSERT INTO weather_log
    (location, hour_utc, data_type,
     ghi_wh_m2, temp_c, rh_pct, precip_mm, wind_kmh, cloud_pct, weather_code)
VALUES ($1, $2, 'forecast', $3, $4, $5, $6, $7, $8, $9)
ON CONFLICT (location, hour_utc, data_type) DO UPDATE SET
    ghi_wh_m2    = EXCLUDED.ghi_wh_m2,
    temp_c       = EXCLUDED.temp_c,
    rh_pct       = EXCLUDED.rh_pct,
    precip_mm    = EXCLUDED.precip_mm,
    wind_kmh     = EXCLUDED.wind_kmh,
    cloud_pct    = EXCLUDED.cloud_pct,
    weather_code = EXCLUDED.weather_code,
    fetched_at   = NOW()
"""

_UPSERT_SOLAR_ACTUALS = """
INSERT INTO solar_actuals (solar_date, eddi_kwh, ghi_actual)
VALUES ($1, $2, $3)
ON CONFLICT (solar_date) DO UPDATE SET
    eddi_kwh   = COALESCE(EXCLUDED.eddi_kwh,  solar_actuals.eddi_kwh),
    ghi_actual = COALESCE(EXCLUDED.ghi_actual, solar_actuals.ghi_actual),
    -- panel_factor_obs is NOT computed here because ghi_actual is always NULL on the
    -- eddi insert (GHI is written via a separate UPDATE for yesterday).
    -- It is recomputed nightly by db_repository.upsert_solar_actuals (step 3)
    -- after ESB CSV export_kwh is available.
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

    # Open-Meteo archive API only has data for dates that are already past —
    # calling it for today returns 400.  Always fetch GHI for yesterday.
    ghi_date = target_date - timedelta(days=1)

    # Fetch in parallel (both are blocking HTTP)
    minutes_raw, ghi_rows = await asyncio.gather(
        asyncio.to_thread(_fetch_day_minutes, target_date),
        asyncio.to_thread(_fetch_ghi_actual, ghi_date),
    )

    slots = _aggregate_to_30min(minutes_raw, target_date)
    daily_eddi_kwh = round(sum(s["eddi_kwh"] for s in slots), 3)
    daily_ghi_kwh  = round(sum(r["ghi_wh_m2"] for r in ghi_rows) / 1000.0, 3)

    async with pool.acquire() as conn:
        # Upsert 30-min readings
        await conn.executemany(
            _UPSERT_MYENERGI,
            [(HUB_SERIAL, s["interval_start"], s["import_kwh"], s["eddi_kwh"],
              s["eddi_divert_kwh"], s["export_kwh"], s["sample_count"])
             for s in slots],
        )
        # Upsert hourly GHI actuals
        await conn.executemany(
            _UPSERT_WEATHER_ACTUAL,
            [("maynooth", r["hour_utc"], r["ghi_wh_m2"]) for r in ghi_rows],
        )
        # Upsert solar_actuals: eddi for today, GHI for yesterday (archive lag).
        # Note: export_kwh is NOT written here — the Eddi API has no exp field.
        # Export is sourced from ESB CSV via db_repository.upsert_solar_actuals (00:45 job).
        await conn.execute(_UPSERT_SOLAR_ACTUALS, target_date, daily_eddi_kwh, None)
        if daily_ghi_kwh > 0:
            # Write GHI into yesterday's solar_actuals row (that's what the archive returned)
            await conn.execute(
                "UPDATE solar_actuals SET ghi_actual = $1 WHERE solar_date = $2",
                daily_ghi_kwh, ghi_date,
            )

    logger.info(
        "[myenergi_poller] Done for %s — %d 30-min slots, Eddi %.2f kWh | GHI for %s: %.3f kWh/m²",
        target_date, len(slots), daily_eddi_kwh, ghi_date, daily_ghi_kwh,
    )


async def run_weather_forecast_poll(pool) -> None:
    """
    Fetch 7-day hourly weather forecast from Open-Meteo and persist to weather_log.

    Scheduled daily at 06:00 Europe/Dublin (APScheduler CronTrigger).
    Captures: GHI, temperature, humidity, precipitation, wind, cloud cover, WMO code.
    Matches the Gardening project's weather_poller.py variable set so both pipelines
    draw from the same Open-Meteo fields (Energy → TimescaleDB, Gardening → InfluxDB).

    Why 06:00?
    - Open-Meteo updates its forecast model overnight; 06:00 captures the latest run.
    - The morning_advisory.py job runs at 20:00 and reads from this table for GHI.
    - 7-day window → each future hour is captured multiple times before becoming actual.

    The morning_advisory Pushover is NOT affected — it fetches GHI live from Open-Meteo
    at 20:00 via _fetch_ghi(). This job is purely for persistent forecast storage.
    """
    import asyncio

    logger.info("[weather_forecast] Fetching 7-day forecast from Open-Meteo")
    rows = await asyncio.to_thread(_fetch_weather_forecast)

    async with pool.acquire() as conn:
        await conn.executemany(
            _UPSERT_WEATHER_FORECAST,
            [
                ("maynooth", r["hour_utc"],
                 r["ghi_wh_m2"], r["temp_c"], r["rh_pct"],
                 r["precip_mm"], r["wind_kmh"], r["cloud_pct"], r["weather_code"])
                for r in rows
            ],
        )

    logger.info("[weather_forecast] Upserted %d forecast hours (7 days)", len(rows))
