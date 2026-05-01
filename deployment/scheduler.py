"""APScheduler job definitions and scheduler factory for the Energy Forecast API."""

import asyncio
import logging
import os
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Alert helper
# ---------------------------------------------------------------------------

def _send_alert_pushover(title: str, message: str, priority: int = -1) -> None:
    """Send a plain-text Pushover alert (not a SolarAdvisory object).

    priority: -2 = lowest, -1 = low, 0 = normal, 1 = high, 2 = emergency.
    Synchronous — wrap in asyncio.to_thread() when calling from async context.
    """
    import requests as _requests

    token = os.environ.get("PUSHOVER_APP_TOKEN", "")
    user = os.environ.get("PUSHOVER_USER_KEY", "")
    if not token or not user:
        logger.warning("[pushover_alert] PUSHOVER_APP_TOKEN or PUSHOVER_USER_KEY not set — skipping.")
        return
    resp = _requests.post(
        "https://api.pushover.net/1/messages.json",
        data={"token": token, "user": user, "title": title, "message": message, "priority": priority},
        timeout=10,
    )
    resp.raise_for_status()
    logger.info("[pushover_alert] Sent: %s", title)


# ---------------------------------------------------------------------------
# Scheduler job functions
# ---------------------------------------------------------------------------

async def _run_scheduled_inference(app: FastAPI) -> None:
    """Daily 16:00 job — run H+24 inference for all registered households."""
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        logger.warning("[scheduler] DB pool not available — skipping inference run.")
        return
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, city FROM households")
        if not rows:
            logger.info("[scheduler] No households registered — nothing to forecast.")
            return
        for row in rows:
            household_id = str(row["id"])
            city = row["city"] or "ireland"
            try:
                # Reuse existing morning-brief logic (dry_run=False stores predictions)
                from deployment.live_inference import run_morning_brief  # noqa: PLC0415
                run_morning_brief(
                    city=city,
                    building_id=household_id,
                    dry_run=False,
                )
                logger.info("[scheduler] Inference complete for %s (%s)", household_id, city)
            except Exception as exc:
                logger.error("[scheduler] Inference failed for %s: %s", household_id, exc)
    except Exception as exc:
        logger.error("[scheduler] Scheduled inference run failed: %s", exc)


async def _run_myenergi_poll(app: FastAPI) -> None:
    """23:30 job — fetch today's MyEnergi minute data, aggregate to 30-min, store in DB."""
    from deployment.myenergi_poller import run_daily_poll

    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        logger.warning("[myenergi_poller] DB pool not available — skipping.")
        return
    try:
        await run_daily_poll(pool)
    except Exception as exc:
        logger.error("[myenergi_poller] Daily poll failed: %s", exc)


async def _sync_solar_actuals(app: FastAPI) -> None:
    """23:45 job — aggregate daily export_kwh from meter_readings into solar_actuals.

    Runs after the 23:30 MyEnergi poll so eddi_kwh is fresh before
    panel_factor_obs is recomputed by calibrate_panel_factor.py.
    Updates the last 90 days to catch any late ESB CSV uploads.
    """
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        logger.warning("[solar_actuals_sync] DB pool not available — skipping.")
        return
    try:
        async with pool.acquire() as conn:
            households = await conn.fetch("SELECT id FROM households")
        if not households:
            logger.info("[solar_actuals_sync] No households registered — nothing to sync.")
            return
        for row in households:
            household_id = str(row["id"])
            async with pool.acquire() as conn:
                status = await conn.execute(
                    """
                    INSERT INTO solar_actuals (solar_date, export_kwh)
                    SELECT
                      DATE(recorded_at AT TIME ZONE 'Europe/Dublin') AS solar_date,
                      ROUND(SUM(export_kwh)::NUMERIC, 3)              AS export_kwh
                    FROM meter_readings
                    WHERE household_id = $1
                      AND export_kwh IS NOT NULL
                      AND DATE(recorded_at AT TIME ZONE 'Europe/Dublin')
                          >= CURRENT_DATE - INTERVAL '90 days'
                    GROUP BY 1
                    ON CONFLICT (solar_date)
                    DO UPDATE SET export_kwh = EXCLUDED.export_kwh
                    """,
                    household_id,
                )
            logger.info("[solar_actuals_sync] household=%s %s", household_id, status)
    except Exception as exc:
        logger.error("[solar_actuals_sync] Sync failed: %s", exc)
        return

    # DAN-160: after export_kwh is fresh, recompute seasonal panel factors
    pool = getattr(app.state, "db_pool", None)
    await _recompute_panel_factor_seasonal(pool)


async def _recompute_panel_factor_seasonal(pool) -> None:
    """DAN-160: Recompute per-month panel_factor_seasonal JSONB on each household.

    Computes panel_factor = (export_kwh + eddi_kwh) / ghi_actual per calendar month,
    requiring ≥ 10 days of clean data per month. Stores as JSONB e.g.:
      {"2026-02": 2.0330, "2026-03": 1.4868, "2026-04": 1.2214}

    Called at end of _sync_solar_actuals (23:45 Dublin) so export_kwh is always fresh.
    """
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    TO_CHAR(solar_date, 'YYYY-MM')                             AS month_key,
                    ROUND(
                        AVG(
                            (export_kwh + COALESCE(eddi_kwh, 0.0))
                            / NULLIF(ghi_actual, 0)
                        )::NUMERIC, 4
                    )                                                           AS pf
                FROM solar_actuals
                WHERE ghi_actual > 0
                  AND export_kwh  IS NOT NULL
                  AND export_kwh  > 0
                GROUP BY 1
                HAVING COUNT(*) >= 10
                ORDER BY 1
                """
            )
        if not rows:
            logger.info("[panel_factor_seasonal] No months with ≥10 clean days — skipping.")
            return

        import json as _json
        seasonal = {r["month_key"]: float(r["pf"]) for r in rows}
        seasonal_json = _json.dumps(seasonal)
        logger.info("[panel_factor_seasonal] Recomputed %d months: %s", len(seasonal), seasonal)

        async with pool.acquire() as conn:
            households = await conn.fetch("SELECT id FROM households")
        for row in households:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE households SET panel_factor_seasonal = $1::jsonb WHERE id = $2",
                    seasonal_json,
                    row["id"],
                )
            logger.info("[panel_factor_seasonal] Updated household=%s", row["id"])
    except Exception as exc:
        logger.error("[panel_factor_seasonal] Recompute failed: %s", exc)


async def _get_seasonal_panel_factor(pool, household_id: str) -> float:
    """DAN-160: Look up per-household monthly panel_factor_seasonal from DB.

    Returns value for current month (e.g. '2026-05'). Falls back to 1.6 if:
    - No row in DB
    - Current month not yet in JSONB (not enough data)
    - Any exception
    """
    _FALLBACK = 1.6
    try:
        import pytz as _pytz, json as _json
        month_key = datetime.now(_pytz.timezone("Europe/Dublin")).strftime("%Y-%m")
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT panel_factor_seasonal FROM households WHERE id = $1",
                household_id,
            )
        if result is None:
            logger.debug("[panel_factor_seasonal] No row for household=%s — fallback %.1f", household_id, _FALLBACK)
            return _FALLBACK
        seasonal = _json.loads(result) if isinstance(result, str) else result
        pf = seasonal.get(month_key)
        if pf is None:
            logger.debug(
                "[panel_factor_seasonal] household=%s month=%s not in JSONB — fallback %.1f",
                household_id, month_key, _FALLBACK,
            )
            return _FALLBACK
        logger.info("[panel_factor_seasonal] household=%s month=%s → pf=%.4f", household_id, month_key, pf)
        return float(pf)
    except Exception as exc:
        logger.warning("[panel_factor_seasonal] Lookup failed (%s) — fallback %.1f", exc, _FALLBACK)
        return _FALLBACK


async def _run_data_quality_check(app: FastAPI) -> None:
    """23:55 job — DAN-159 Layer 1+5: cross-validate MyEnergi vs ESB for yesterday.

    For each household:
    - Computes daily ESB import vs MyEnergi import for yesterday.
    - Flags physical violations (myenergi > esb) and ratio anomalies (±2σ vs 30d mean).
    - Updates rolling CT calibration factor on households table (Layer 5).
    - Fires a Pushover alert on anomaly or violation.
    """
    from energy_forecast.monitoring.data_quality import run_cross_check

    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        logger.warning("[data_quality] DB pool not available — skipping.")
        return

    try:
        async with pool.acquire() as conn:
            households = await conn.fetch("SELECT id FROM households WHERE has_solar = TRUE OR TRUE")
        if not households:
            logger.info("[data_quality] No households registered — skipping.")
            return

        for row in households:
            hid = str(row["id"])
            result = await run_cross_check(pool, hid)

            if result.get("physical_violation"):
                await asyncio.to_thread(
                    _send_alert_pushover,
                    "⚡ Sparc: Data integrity issue",
                    f"MyEnergi reading exceeds ESB meter for {result['check_date']} — "
                    f"MyEnergi {result['me_kwh']:.2f} kWh vs ESB {result['esb_kwh']:.2f} kWh. "
                    "Check hub serial / API connection.",
                    0,
                )
            elif result.get("ratio_anomaly") and result.get("anomaly_detail"):
                await asyncio.to_thread(
                    _send_alert_pushover,
                    "⚡ Sparc: CT clamp anomaly",
                    f"{result['check_date']}: {result['anomaly_detail']}",
                    -1,
                )

    except Exception as exc:
        logger.error("[data_quality] Daily cross-check job failed: %s", exc)


async def _run_weekly_quality_report(app: FastAPI) -> None:
    """Mon 08:30 job — DAN-159 Layer 2: send weekly MyEnergi data quality Pushover report.

    Summarises the past 7 days: mean ESB/MyEnergi ratio, anomaly count, CT factor.
    """
    from energy_forecast.monitoring.data_quality import weekly_summary

    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        return

    try:
        async with pool.acquire() as conn:
            households = await conn.fetch("SELECT id FROM households")
        if not households:
            return

        for row in households:
            hid = str(row["id"])
            summary = await weekly_summary(pool, hid, days=7)

            if summary["days_checked"] == 0:
                logger.info("[data_quality_weekly] household=%s — no events in last 7d.", hid[:8])
                continue

            ok_icon = "⚠️" if summary["anomaly_count"] > 0 else "✓"
            anomaly_line = (
                f"⚠️ {summary['anomaly_count']} anomaly day(s)"
                if summary["anomaly_count"] > 0
                else "✓ all normal"
            )
            ct_line = (
                f"CT calibration factor: {summary['ct_calibration_factor']:.3f}"
                if summary["ct_calibration_factor"]
                else "CT factor: insufficient data"
            )
            ratio_line = (
                f"Mean MyEnergi/ESB ratio: {summary['mean_ratio']:.3f} ±{summary['std_ratio']:.3f}"
                if summary["mean_ratio"]
                else "Ratio: no data"
            )

            msg = (
                f"7-day data quality: {summary['days_checked']} days checked, "
                f"{summary['days_missing']} missing.\n"
                f"{ratio_line}\n{ct_line}\n{anomaly_line}"
            )
            await asyncio.to_thread(
                _send_alert_pushover,
                f"{ok_icon} Sparc: Weekly data quality",
                msg,
                -1,
            )
            logger.info("[data_quality_weekly] household=%s report sent: %s", hid[:8], anomaly_line)

    except Exception as exc:
        logger.error("[data_quality_weekly] Weekly report failed: %s", exc)


async def _check_data_gaps(app: FastAPI) -> None:
    """09:00 job — DAN-148: alert if ESB meter readings are stale (>72h) or missing days streak.

    Two checks per household:
    1. Recency: MAX(recorded_at) > 72h ago → WARN upload overdue
    2. Gap streak: any run of 3+ consecutive calendar days with zero readings in last 30d

    Fires a Pushover priority=0 (normal) alert so it shows as a persistent notification.
    """
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        return

    try:
        async with pool.acquire() as conn:
            households = await conn.fetch("SELECT id FROM households")
        if not households:
            return

        for row in households:
            hid = str(row["id"])
            async with pool.acquire() as conn:
                rec = await conn.fetchrow(
                    """
                    SELECT
                        MAX(recorded_at) AS last_ts,
                        COUNT(DISTINCT DATE(recorded_at AT TIME ZONE 'Europe/Dublin')) AS days_with_data,
                        30 - COUNT(DISTINCT DATE(recorded_at AT TIME ZONE 'Europe/Dublin')) AS missing_days_30d
                    FROM meter_readings
                    WHERE household_id = $1
                      AND recorded_at >= NOW() - INTERVAL '30 days'
                    """,
                    hid,
                )

            if rec is None or rec["last_ts"] is None:
                await asyncio.to_thread(
                    _send_alert_pushover,
                    "⚡ Sparc: No meter data",
                    f"Household {hid[:8]}: no readings found at all. Upload ESB CSV at http://localhost:8000/upload",
                    0,
                )
                continue

            stale_h = (datetime.now(timezone.utc) - rec["last_ts"].replace(tzinfo=timezone.utc)).total_seconds() / 3600
            missing_days = int(rec["missing_days_30d"] or 0)

            if stale_h > 72:
                await asyncio.to_thread(
                    _send_alert_pushover,
                    "⚡ Sparc: Upload overdue",
                    f"No new ESB readings for {stale_h:.0f}h. Last reading: {rec['last_ts'].date()}. "
                    f"Upload at http://localhost:8000/upload",
                    0,
                )
                logger.warning("[data_gap] household=%s stale %.0fh", hid, stale_h)
            elif missing_days >= 3:
                await asyncio.to_thread(
                    _send_alert_pushover,
                    "⚡ Sparc: Data gaps detected",
                    f"{missing_days} missing days in last 30d for household {hid[:8]}. "
                    f"Upload latest ESB CSV to fill gaps.",
                    -1,
                )
                logger.warning("[data_gap] household=%s missing_days_30d=%d", hid, missing_days)
            else:
                logger.info("[data_gap] household=%s OK — stale=%.1fh missing_30d=%d", hid, stale_h, missing_days)

    except Exception as exc:
        logger.error("[data_gap] Gap check failed: %s", exc)


async def _run_morning_advisory(app: FastAPI) -> None:
    """20:00 job — fetch next-day solar forecast + predicted cost, log to DB, push to Pushover."""
    import pytz
    from deployment.morning_advisory import SolarAdvisory, build_advisory, send_pushover
    from energy_forecast.api.meter_store import log_advisory

    dublin = pytz.timezone("Europe/Dublin")
    pool = getattr(app.state, "db_pool", None)
    try:
        tomorrow = (datetime.now(dublin) + __import__("datetime").timedelta(days=1)).date()

        # DAN-143: attempt to compute tomorrow's predicted cost from the 16:00 LightGBM forecast
        daily_cost = None
        panel_factor = None
        households = []
        if pool is not None:
            async with pool.acquire() as conn:
                households = await conn.fetch("SELECT id FROM households")
            for row in households:
                hid = str(row["id"])
                from deployment.routers.control import _compute_tomorrow_cost
                daily_cost = await _compute_tomorrow_cost(pool, hid, tomorrow)
                panel_factor = await _get_seasonal_panel_factor(pool, hid)
                break  # single-household MVP; extend when multi-household is needed

        advisory: SolarAdvisory = await asyncio.to_thread(
            build_advisory, tomorrow, daily_cost, panel_factor
        )
        if pool is not None:
            for row in households:
                await log_advisory(pool, str(row["id"]), advisory)
        await asyncio.to_thread(send_pushover, advisory)
    except Exception as exc:
        logger.error("[advisory] Morning advisory failed: %s", exc)


# ---------------------------------------------------------------------------
# Scheduler factory
# ---------------------------------------------------------------------------

def create_scheduler(app: FastAPI) -> AsyncIOScheduler:
    """Register all cron jobs and return the started scheduler.

    All job functions receive ``app`` as their sole argument so they can
    access ``app.state.db_pool``, ``app.state.models``, and
    ``app.state.control_engine`` without relying on module-level globals.
    """
    scheduler = AsyncIOScheduler(timezone="Europe/Dublin")

    scheduler.add_job(
        lambda: asyncio.ensure_future(_run_scheduled_inference(app)),
        CronTrigger(hour=16, minute=0),
        id="daily_inference",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: asyncio.ensure_future(_run_morning_advisory(app)),
        CronTrigger(hour=20, minute=0),
        id="morning_advisory",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: asyncio.ensure_future(_check_data_gaps(app)),
        CronTrigger(hour=9, minute=0),
        id="data_gap_check",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: asyncio.ensure_future(_run_myenergi_poll(app)),
        CronTrigger(hour=23, minute=30),
        id="myenergi_poll",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: asyncio.ensure_future(_sync_solar_actuals(app)),
        CronTrigger(hour=23, minute=45),
        id="solar_actuals_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: asyncio.ensure_future(_run_data_quality_check(app)),
        CronTrigger(hour=23, minute=55),
        id="data_quality_check",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: asyncio.ensure_future(_run_weekly_quality_report(app)),
        CronTrigger(day_of_week="mon", hour=8, minute=30),
        id="weekly_quality_report",
        replace_existing=True,
    )

    return scheduler
