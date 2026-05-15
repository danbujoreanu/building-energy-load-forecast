"""APScheduler job definitions and scheduler factory for the Energy Forecast API."""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from deployment import db_repository as db

logger = logging.getLogger(__name__)

_DUBLIN = pytz.timezone("Europe/Dublin")


# ---------------------------------------------------------------------------
# Alert helper
# ---------------------------------------------------------------------------

def _send_alert_pushover(title: str, message: str, priority: int = -1) -> None:
    """Send a Pushover alert. priority: -2=lowest … 2=emergency.

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
        rows = await db.fetch_all_households(pool)
        if not rows:
            logger.info("[scheduler] No households registered — nothing to forecast.")
            return
        for row in rows:
            household_id = str(row["id"])
            city = row["city"] or "ireland"
            try:
                from deployment.live_inference import run_morning_brief  # noqa: PLC0415
                run_morning_brief(city=city, building_id=household_id, dry_run=False)
                logger.info("[scheduler] Inference complete for %s (%s)", household_id, city)
            except Exception as exc:
                logger.error("[scheduler] Inference failed for %s: %s", household_id, exc)
    except Exception as exc:
        logger.error("[scheduler] Scheduled inference run failed: %s", exc)


async def _run_myenergi_poll(app: FastAPI) -> None:
    """00:15 job — fetch YESTERDAY's MyEnergi data + GHI archive, store in DB.

    Runs just after midnight so the full 24h is complete and the Open-Meteo
    archive endpoint (which requires the date to be in the past) can return actual
    GHI for yesterday.  Previous schedule (23:30 for today) caused a 400 error
    because the archive has no data for the current day.
    """
    import pytz
    from datetime import timedelta
    from deployment.myenergi_poller import run_daily_poll

    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        logger.warning("[myenergi_poller] DB pool not available — skipping.")
        return
    # Always poll yesterday — the full day is complete and archive data is available
    yesterday = datetime.now(pytz.timezone("Europe/Dublin")).date() - timedelta(days=1)
    try:
        await run_daily_poll(pool, target_date=yesterday)
    except Exception as exc:
        logger.error("[myenergi_poller] Daily poll failed: %s", exc)
        await asyncio.to_thread(
            _send_alert_pushover,
            "⚡ Sparc: MyEnergi poll failed",
            f"Daily energy data NOT saved.\n\nError: {exc}\n\nFix: ssh dan@192.168.68.119 and rerun backfill.",
            priority=0,  # normal priority — will notify but not interrupt
        )


async def _run_weather_forecast_poll(app: FastAPI) -> None:
    """06:00 job — fetch 7-day Open-Meteo forecast, persist to weather_log.

    Captures GHI, temp, humidity, precipitation, wind, cloud cover, WMO code —
    matching the Gardening project's variable set so both pipelines stay in sync.
    Runs at 06:00 to pick up the overnight model update from Open-Meteo.
    """
    from deployment.myenergi_poller import run_weather_forecast_poll

    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        logger.warning("[weather_forecast] DB pool not available — skipping.")
        return
    try:
        await run_weather_forecast_poll(pool)
    except Exception as exc:
        logger.error("[weather_forecast] Forecast poll failed: %s", exc)
        await asyncio.to_thread(
            _send_alert_pushover,
            "⚡ Sparc: Weather forecast poll failed",
            f"7-day forecast NOT updated.\n\nError: {exc}",
            priority=-1,  # low priority — informational
        )


async def _sync_solar_actuals(app: FastAPI) -> None:
    """23:45 job — aggregate daily export_kwh from meter_readings into solar_actuals.

    Updates the last 90 days to catch any late ESB CSV uploads.
    Runs after 23:30 MyEnergi poll so eddi_kwh is fresh before panel_factor recompute.
    """
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        logger.warning("[solar_actuals_sync] DB pool not available — skipping.")
        return
    try:
        households = await db.fetch_household_ids(pool)
        if not households:
            logger.info("[solar_actuals_sync] No households registered — nothing to sync.")
            return
        for row in households:
            household_id = str(row["id"])
            status = await db.upsert_solar_actuals(pool, household_id)
            logger.info("[solar_actuals_sync] household=%s %s", household_id, status)
    except Exception as exc:
        logger.error("[solar_actuals_sync] Sync failed: %s", exc)
        return

    # DAN-160: recompute seasonal panel factors after export_kwh is fresh
    await _recompute_panel_factor_seasonal(pool)


async def _recompute_panel_factor_seasonal(pool) -> None:
    """DAN-160: Recompute per-month panel_factor_seasonal JSONB on each household.

    Computes panel_factor = (export_kwh + eddi_kwh) / ghi_actual per calendar month,
    requiring >= 10 days of clean data. Called at end of _sync_solar_actuals.
    """
    try:
        rows = await db.fetch_panel_factor_by_month(pool)
        if not rows:
            logger.info("[panel_factor_seasonal] No months with >=10 clean days — skipping.")
            return

        seasonal = {r["month_key"]: float(r["pf"]) for r in rows}
        logger.info("[panel_factor_seasonal] Recomputed %d months: %s", len(seasonal), seasonal)

        households = await db.fetch_household_ids(pool)
        for row in households:
            await db.update_household_panel_factor(pool, row["id"], seasonal)
            logger.info("[panel_factor_seasonal] Updated household=%s", row["id"])
    except Exception as exc:
        logger.error("[panel_factor_seasonal] Recompute failed: %s", exc)


async def _get_seasonal_panel_factor(pool, household_id: str) -> float:
    """DAN-160: Look up per-household monthly panel_factor for current month.

    Falls back to 1.6 if no row, month not in JSONB, or any exception.
    """
    _FALLBACK = 1.6
    try:
        month_key = datetime.now(_DUBLIN).strftime("%Y-%m")
        result = await db.get_household_panel_factor_seasonal(pool, household_id)
        if result is None:
            return _FALLBACK
        seasonal = json.loads(result) if isinstance(result, str) else result
        return float(seasonal.get(month_key, _FALLBACK))
    except Exception as exc:
        logger.warning("[panel_factor_seasonal] Lookup failed (%s) — fallback %.1f", exc, _FALLBACK)
        return _FALLBACK


async def _run_data_quality_check(app: FastAPI) -> None:
    """23:55 job — DAN-159 Layer 1+5: cross-validate MyEnergi vs ESB for yesterday."""
    from energy_forecast.monitoring.data_quality import run_cross_check

    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        logger.warning("[data_quality] DB pool not available — skipping.")
        return
    try:
        households = await db.fetch_household_ids(pool)
        if not households:
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
    """Mon 08:30 job — DAN-159 Layer 2: weekly MyEnergi data quality Pushover report."""
    from energy_forecast.monitoring.data_quality import weekly_summary

    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        return
    try:
        households = await db.fetch_household_ids(pool)
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
                _send_alert_pushover, f"{ok_icon} Sparc: Weekly data quality", msg, -1
            )
            logger.info("[data_quality_weekly] household=%s report sent: %s", hid[:8], anomaly_line)
    except Exception as exc:
        logger.error("[data_quality_weekly] Weekly report failed: %s", exc)


async def _fetch_semo_prices(app: FastAPI) -> None:
    """14:00 job — DAN-164 Stream 4: fetch tomorrow's day-ahead SMP from EirGrid.

    EirGrid publishes day-ahead prices at ~13:00. We fetch at 14:00 to ensure
    availability. Stored in semo_prices table for use by LPThermalDispatcher (16:00).
    Falls back to MockPriceConnector on API failure — LP dispatch still works.
    """
    from datetime import datetime as _dt
    from deployment.connectors.markets import SEMOConnector

    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        logger.warning("[semo_prices] DB pool not available — skipping.")
        return
    try:
        tomorrow = (_dt.now(_DUBLIN) + __import__("datetime").timedelta(days=1)).date()
        connector = SEMOConnector()
        prices = await asyncio.to_thread(connector.get_day_ahead_prices, tomorrow)
        source = "eirgrid" if len(prices) == 24 else "mock"
        await db.upsert_semo_prices(pool, tomorrow, prices, source)
        logger.info(
            "[semo_prices] Stored %d prices for %s (source=%s, range=%.4f–%.4f EUR/kWh)",
            len(prices), tomorrow, source, min(prices), max(prices),
        )
    except Exception as exc:
        logger.error("[semo_prices] Price fetch failed: %s", exc)


async def _check_drift_sunday(app: FastAPI) -> None:
    """Sun 02:00 job — DAN-163: compute rolling MAE, log drift, alert if ratio > 1.25.

    Computes 7-day MAE vs 28-day baseline MAE per household.
    Drift ratio > 1.25 means recent error is 25% worse than baseline → Pushover alert.
    """
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        logger.warning("[drift_check] DB pool not available — skipping.")
        return
    try:
        households = await db.fetch_household_ids(pool)
        if not households:
            return
        for row in households:
            hid = str(row["id"])
            mae_7d  = await db.get_recent_mae(pool, hid, days=7)
            mae_28d = await db.get_recent_mae(pool, hid, days=28)

            drift_ratio = (mae_7d / mae_28d) if (mae_7d and mae_28d and mae_28d > 0) else None
            alert_sent  = False
            notes       = None

            if drift_ratio is not None and drift_ratio > 1.25:
                notes = f"Drift detected: 7d MAE={mae_7d:.4f} kWh, 28d MAE={mae_28d:.4f} kWh, ratio={drift_ratio:.2f}"
                await asyncio.to_thread(
                    _send_alert_pushover,
                    "⚡ Sparc: Model drift detected",
                    notes,
                    0,
                )
                alert_sent = True
                logger.warning("[drift_check] household=%s — %s", hid[:8], notes)
            else:
                level = f"{drift_ratio:.2f}" if drift_ratio else "n/a"
                logger.info("[drift_check] household=%s OK — ratio=%s", hid[:8], level)

            await db.insert_drift_log(pool, hid, mae_7d, mae_28d, alert_sent, notes)
    except Exception as exc:
        logger.error("[drift_check] Drift check failed: %s", exc)


async def _run_lp_dispatch(app: FastAPI) -> None:
    """14:30 job — DAN-164 Stream 3: LP-optimal Eddi schedule using household tariff rates.

    Ireland is NOT on dynamic/day-ahead pricing. Retail customers pay fixed day/night
    tariff slots (BGE night rate: 23:00-08:00, day rate: 08:00-23:00, peak Mon-Fri
    17:00-19:00). We use the real tariff curve, NOT wholesale SEMO prices.

    SEMO prices (fetched at 14:00) are stored for monitoring and future dynamic-tariff
    customers, but LP optimisation runs on actual retail rates.
    """
    import datetime as _dt
    from energy_forecast.control.lp_dispatcher import LPThermalDispatcher
    from energy_forecast.tariff import build_price_curve

    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        logger.warning("[lp_dispatch] DB pool not available — skipping.")
        return
    try:
        tomorrow = (_dt.datetime.now(_DUBLIN) + _dt.timedelta(days=1)).date()
        # Use retail tariff rates — night 23:00-08:00, day 08:00-23:00, free Sat 09:00-17:00
        prices = build_price_curve(tomorrow)
        logger.info(
            "[lp_dispatch] Tariff curve for %s: night=%.4f day=%.4f (cheapest hours: 23:00-08:00)",
            tomorrow,
            min(prices),
            max(prices),
        )

        households = await db.fetch_all_households(pool)
        if not households:
            return

        dispatcher = LPThermalDispatcher()

        for row in households:
            hid = str(row["id"])
            try:
                # Use 55°C as a safe default tank temp (no sensor yet — DAN-152)
                result = dispatcher.optimize(
                    initial_temp_c=55.0,
                    prices=prices,
                )
                summary = result.schedule_summary()
                logger.info("[lp_dispatch] household=%s  %s", hid[:8], summary)

                # Store 24 per-hour recommendations
                actions = result.to_control_actions()
                await db.insert_lp_recommendations(pool, hid, actions)

                await asyncio.to_thread(
                    _send_alert_pushover,
                    f"⚡ Sparc: tomorrow's Eddi schedule",
                    f"{tomorrow}\n{summary}",
                    -1,
                )
                break  # single-household MVP
            except Exception as exc:
                logger.error("[lp_dispatch] Failed for household=%s: %s", hid[:8], exc)
    except Exception as exc:
        logger.error("[lp_dispatch] LP dispatch job failed: %s", exc)


async def _check_data_gaps(app: FastAPI) -> None:
    """09:00 job — DAN-148: alert if ESB meter readings are stale (>72h) or have gap streaks."""
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        return
    try:
        households = await db.fetch_household_ids(pool)
        if not households:
            return
        for row in households:
            hid = str(row["id"])
            rec = await db.check_meter_recency(pool, hid)

            if rec is None or rec["last_ts"] is None:
                await asyncio.to_thread(
                    _send_alert_pushover,
                    "⚡ Sparc: No meter data",
                    f"Household {hid[:8]}: no readings found. Upload ESB CSV at http://localhost:8000/upload",
                    0,
                )
                continue

            stale_h = (
                datetime.now(timezone.utc) - rec["last_ts"].replace(tzinfo=timezone.utc)
            ).total_seconds() / 3600
            missing_days = int(rec["missing_days_30d"] or 0)

            if stale_h > 336:   # 14 days — ESB CSV upload cadence is biweekly
                await asyncio.to_thread(
                    _send_alert_pushover,
                    "⚡ Sparc: ESB upload overdue",
                    f"No new ESB readings for {stale_h/24:.0f} days. Last: {rec['last_ts'].date()}. "
                    f"Download latest CSV from myaccount.esbnetworks.ie and upload.",
                    0,
                )
                logger.warning("[data_gap] household=%s stale %.0fh", hid, stale_h)
            elif stale_h > 288:  # 12 days — reminder 2 days before overdue
                await asyncio.to_thread(
                    _send_alert_pushover,
                    "📋 Sparc: ESB upload due soon",
                    f"ESB meter data is {stale_h/24:.0f} days old (last: {rec['last_ts'].date()}). "
                    f"Upload a fresh CSV this week to avoid a gap.",
                    -1,
                )
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
    """20:00 job — fetch next-day solar forecast + predicted cost, push to Pushover."""
    import datetime as _dt
    from deployment.morning_advisory import build_advisory, send_pushover
    from energy_forecast.api.meter_store import log_advisory

    pool = getattr(app.state, "db_pool", None)
    try:
        tomorrow = (datetime.now(_DUBLIN) + _dt.timedelta(days=1)).date()
        daily_cost = None
        panel_factor = None
        households = []

        if pool is not None:
            households = await db.fetch_household_ids(pool)
            for row in households:
                hid = str(row["id"])
                from deployment.routers.control import _compute_tomorrow_cost
                daily_cost = await _compute_tomorrow_cost(pool, hid, tomorrow)
                panel_factor = await _get_seasonal_panel_factor(pool, hid)
                break  # single-household MVP

        advisory = await asyncio.to_thread(build_advisory, tomorrow, daily_cost, panel_factor)

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
    """Register all cron jobs and return the configured scheduler."""
    scheduler = AsyncIOScheduler(timezone="Europe/Dublin")

    scheduler.add_job(
        _run_scheduled_inference,
        CronTrigger(hour=16, minute=0),
        id="daily_inference", replace_existing=True,
        args=[app],
    )
    scheduler.add_job(
        _run_morning_advisory,
        CronTrigger(hour=20, minute=0),
        id="morning_advisory", replace_existing=True,
        args=[app],
    )
    scheduler.add_job(
        _run_weather_forecast_poll,
        CronTrigger(hour=6, minute=0),
        id="weather_forecast_poll", replace_existing=True,
        args=[app],
    )
    scheduler.add_job(
        _check_data_gaps,
        CronTrigger(hour=9, minute=0),
        id="data_gap_check", replace_existing=True,
        args=[app],
    )
    # 00:15 — fetch YESTERDAY's complete MyEnergi data (full day is complete, archive GHI available)
    scheduler.add_job(
        _run_myenergi_poll,
        CronTrigger(hour=0, minute=15, timezone="Europe/Dublin"),
        id="myenergi_poll", replace_existing=True,
        args=[app],
    )
    # 00:45 — aggregate solar actuals after myenergi poll completes
    scheduler.add_job(
        _sync_solar_actuals,
        CronTrigger(hour=0, minute=45, timezone="Europe/Dublin"),
        id="solar_actuals_sync", replace_existing=True,
        args=[app],
    )
    # 01:00 — data quality check after everything is synced
    scheduler.add_job(
        _run_data_quality_check,
        CronTrigger(hour=1, minute=0, timezone="Europe/Dublin"),
        id="data_quality_check", replace_existing=True,
        args=[app],
    )
    scheduler.add_job(
        _run_weekly_quality_report,
        CronTrigger(day_of_week="mon", hour=8, minute=30),
        id="weekly_quality_report", replace_existing=True,
        args=[app],
    )
    scheduler.add_job(
        _check_drift_sunday,
        CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="drift_check_sunday", replace_existing=True,
        args=[app],
    )
    scheduler.add_job(
        _fetch_semo_prices,
        CronTrigger(hour=14, minute=0),
        id="semo_price_fetch", replace_existing=True,
        args=[app],
    )
    scheduler.add_job(
        _run_lp_dispatch,
        CronTrigger(hour=14, minute=30),
        id="lp_dispatch", replace_existing=True,
        args=[app],
    )

    return scheduler
