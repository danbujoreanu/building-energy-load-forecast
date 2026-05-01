import json
import logging
import math
import os
import sys
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import asyncpg
import joblib
import lightgbm as lgb  # noqa: F401 — imported to verify lightweight dep
import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, field_validator

# ── Path setup (src/ package available inside the container) ──────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from energy_forecast.api import schemas as _feature_schemas
from energy_forecast.api.esb_parser import ESBParseError, parse_esb_csv
from deployment.morning_advisory import SolarAdvisory, build_advisory, send_pushover
from deployment.myenergi_poller import run_daily_poll
from energy_forecast.api.meter_store import (
    fetch_forecasts,
    fetch_recent_advisories,
    household_exists,
    log_advisory,
    resolve_or_create_household,
    upsert_meter_readings,
)
from energy_forecast.api.prediction_store import store_prediction
from energy_forecast.control.actions import EnvironmentState, ForecastBundle
from energy_forecast.control.controller import ControlEngine
from deployment.connectors import MockDeviceConnector, MockPriceConnector
from deployment.mock_data import MOCK_SOLAR_24H
from energy_forecast.api.plan_comparison import PLANS, compare_plans

logger = logging.getLogger(__name__)

# Global model cache — loaded once at startup, reused across requests
models: dict[str, Any] = {}

# Shared ControlEngine instance (stateless — safe to share)
_control_engine = ControlEngine()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class PredictionRequest(BaseModel):
    building_id: str
    timestamp: str
    features: dict[str, float]
    """35 pre-engineered features (see temporal.py).

    When a real LightGBM model is loaded, the exact key set is validated
    against ``model.feature_name_`` at request time — wrong or missing feature
    names return a 422 with the full expected list.

    In mock / no-model mode, any non-empty dict is accepted.
    """

    @field_validator("features")
    @classmethod
    def features_must_be_valid(cls, v: dict[str, float]) -> dict[str, float]:
        if not v:
            raise ValueError("features dict cannot be empty")
        if len(v) > 500:
            raise ValueError(f"features dict too large ({len(v)} keys); expected ~35")
        # E-19: strict model-derived validation (no-op when running in mock mode)
        return _feature_schemas.validate_features(v)


class PredictionResponse(BaseModel):
    request_id: str
    building_id: str
    timestamp: str
    horizon: int
    predictions: list[float]
    inference_mode: str  # "real" or "mock"
    warnings: list[str] = []  # DAN-116: prediction sanity warnings (empty = OK)


_KNOWN_CITIES = {"drammen", "oslo", "dublin"}


class ControlRequest(BaseModel):
    building_id: str
    city: str = "drammen"
    target_hours: list[int] = list(range(6, 23))
    """Hours of the day (0–23) to produce control decisions for (default: 6–22)."""
    dry_run: bool = True
    """When True, use mock solar/price data. Set to False once live connectors are active."""

    @field_validator("city")
    @classmethod
    def city_must_be_known(cls, v: str) -> str:
        if v not in _KNOWN_CITIES:
            raise ValueError(f"city must be one of {sorted(_KNOWN_CITIES)}, got '{v}'")
        return v


class HourDecision(BaseModel):
    hour: int
    action: str
    confidence: float
    reasoning: str
    p50_kwh: float
    solar_wh_m2: float
    price_eur_kwh: float


class ControlResponse(BaseModel):
    request_id: str
    building_id: str
    city: str
    forecast_origin: str
    decisions: list[HourDecision]
    morning_brief: str


class UploadResponse(BaseModel):
    household_id: str
    rows_inserted: int
    date_from: str | None
    date_to: str | None
    skipped: int


class ForecastEntry(BaseModel):
    forecast_date: str
    issued_at: str | None
    p10_kwh: list[float]
    p50_kwh: list[float]
    p90_kwh: list[float]


class ForecastResponse(BaseModel):
    household_id: str
    forecasts: list[ForecastEntry]


class ComparePlansRequest(BaseModel):
    household_id: str
    date_from: str | None = None   # ISO date string, e.g. "2024-03-15"
    date_to: str | None = None
    plan_keys: list[str] | None = None  # defaults to all plans


class SlotBreakdownResponse(BaseModel):
    day_kwh: float
    night_kwh: float
    peak_kwh: float
    free_kwh: float
    free_cap_exceeded_kwh: float


class PlanResultResponse(BaseModel):
    plan_key: str
    plan_name: str
    supplier: str
    notes: str
    days_analysed: int
    total_import_kwh: float
    total_export_kwh: float
    import_cost_eur: float
    export_credit_eur: float
    standing_charge_eur: float
    net_cost_eur: float
    annualised_cost_eur: float
    slots: SlotBreakdownResponse


class ComparePlansResponse(BaseModel):
    household_id: str
    date_from: str
    date_to: str
    days_analysed: int
    total_import_kwh: float
    total_export_kwh: float
    results: list[PlanResultResponse]   # sorted cheapest first
    cheapest_plan: str
    current_plan: str = "BGE_FTS_AFFINITY"
    savings_vs_current_eur: float       # annual savings if switching to cheapest


# ---------------------------------------------------------------------------
# Lifespan — load models + DB pool + scheduler on startup
# ---------------------------------------------------------------------------

async def _run_scheduled_inference() -> None:
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


async def _run_myenergi_poll() -> None:
    """23:30 job — fetch today's MyEnergi minute data, aggregate to 30-min, store in DB."""
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        logger.warning("[myenergi_poller] DB pool not available — skipping.")
        return
    try:
        await run_daily_poll(pool)
    except Exception as exc:
        logger.error("[myenergi_poller] Daily poll failed: %s", exc)


async def _sync_solar_actuals() -> None:
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


async def _check_data_gaps() -> None:
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


async def _run_morning_advisory() -> None:
    """20:00 job — fetch next-day solar forecast + predicted cost, log to DB, push to Pushover."""
    import asyncio
    import pytz
    dublin = pytz.timezone("Europe/Dublin")
    pool = getattr(app.state, "db_pool", None)
    try:
        tomorrow = (datetime.now(dublin) + __import__("datetime").timedelta(days=1)).date()

        # DAN-143: attempt to compute tomorrow's predicted cost from the 16:00 LightGBM forecast
        daily_cost = None
        if pool is not None:
            async with pool.acquire() as conn:
                households = await conn.fetch("SELECT id FROM households")
            for row in households:
                daily_cost = await _compute_tomorrow_cost(pool, str(row["id"]), tomorrow)
                break  # single-household MVP; extend when multi-household is needed

        advisory: SolarAdvisory = await asyncio.to_thread(
            build_advisory, tomorrow, daily_cost
        )
        if pool is not None:
            for row in households:
                await log_advisory(pool, str(row["id"]), advisory)
        await asyncio.to_thread(send_pushover, advisory)
    except Exception as exc:
        logger.error("[advisory] Morning advisory failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 1. Load ML models ────────────────────────────────────────────────────
    logger.info("Loading Machine Learning models into memory...")
    try:
        models_dir = _REPO_ROOT / "outputs" / "models"

        lgbm_path = next(models_dir.glob("*_LightGBM_*.joblib"), None)
        stacking_path = next(models_dir.glob("*_Stacking_Ensemble_*.joblib"), None)

        if lgbm_path and lgbm_path.exists():
            models["LightGBM"] = joblib.load(lgbm_path)
            logger.info("Loaded LightGBM from %s", lgbm_path)
            feature_names = getattr(models["LightGBM"], "feature_name_", None)
            if feature_names is not None:
                _feature_schemas.register_model_features(feature_names)
        else:
            logger.warning("LightGBM model not found in outputs/models/. Inference will be mocked.")
            models["LightGBM"] = "MOCK_LGBM"

        if stacking_path and stacking_path.exists():
            models["Stacking_Ensemble"] = joblib.load(stacking_path)
            logger.info("Loaded Stacking Ensemble from %s", stacking_path)
        else:
            logger.warning("Stacking Ensemble not found. Inference will be mocked.")
            models["Stacking_Ensemble"] = "MOCK_STACKING"

    except Exception as exc:
        logger.error("Failed to load models during startup: %s", exc)

    # ── 2. Async DB pool (asyncpg) ───────────────────────────────────────────
    db_url = os.environ.get("DATABASE_URL", "")
    db_pool = None
    if db_url:
        try:
            db_pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
            app.state.db_pool = db_pool
            logger.info("asyncpg pool connected to %s", db_url.split("@")[-1])
        except Exception as exc:
            logger.warning("Could not connect asyncpg pool: %s — DB endpoints will return 503.", exc)
            app.state.db_pool = None
    else:
        app.state.db_pool = None
        logger.warning("DATABASE_URL not set — DB endpoints disabled.")

    # ── 3. Startup catchup — run inference if 16:00 job was missed today ────
    # Fires once on container start. If it's past 16:00 Dublin and no
    # prediction is stored for today, runs inference immediately so the user
    # doesn't wait until tomorrow after a laptop restart.
    if db_pool:
        try:
            import pytz as _pytz
            _dublin = _pytz.timezone("Europe/Dublin")
            _now_dublin = datetime.now(_dublin)
            if _now_dublin.hour >= 16:
                async with db_pool.acquire() as _conn:
                    _today_count = await _conn.fetchval(
                        "SELECT COUNT(*) FROM predictions WHERE forecast_date = CURRENT_DATE"
                    )
                if not _today_count:
                    logger.info("[startup_catchup] Past 16:00, no prediction for today — running catchup inference.")
                    asyncio.create_task(_run_scheduled_inference())
                else:
                    logger.info("[startup_catchup] Today's predictions already stored (%d rows) — no catchup needed.", _today_count)
        except Exception as _exc:
            logger.warning("[startup_catchup] Catchup check failed: %s", _exc)

    # ── 4. APScheduler — daily inference at 16:00 Europe/Dublin ─────────────
    scheduler = AsyncIOScheduler(timezone="Europe/Dublin")
    scheduler.add_job(
        _run_scheduled_inference,
        CronTrigger(hour=16, minute=0),
        id="daily_inference",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_morning_advisory,
        CronTrigger(hour=20, minute=0),
        id="morning_advisory",
        replace_existing=True,
    )
    scheduler.add_job(
        _check_data_gaps,
        CronTrigger(hour=9, minute=0),
        id="data_gap_check",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_myenergi_poll,
        CronTrigger(hour=23, minute=30),
        id="myenergi_poll",
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_solar_actuals,
        CronTrigger(hour=23, minute=45),
        id="solar_actuals_sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "APScheduler started — gap check 09:00, inference 16:00, advisory 20:00, "
        "myenergi poll 23:30, solar_actuals sync 23:45 Europe/Dublin."
    )

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)
    if db_pool:
        await db_pool.close()
    logger.info("Shutting down model inference service...")
    models.clear()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Building Energy Load Forecast API",
    description=(
        "Day-ahead electricity load forecasting and demand-response control "
        "for Norwegian public buildings. H+24 horizon, LightGBM + Stacking Ensemble."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ── Intel module routes (/intel/query, /intel/status, /intel/tiers) ──────────
try:
    from intel.routes import router as _intel_router  # noqa: E402
    app.include_router(_intel_router)
    logger.info("Intel routes registered at /intel/*")
except ImportError as _intel_err:
    logger.warning("Intel module not available — /intel/* routes disabled: %s", _intel_err)


# ---------------------------------------------------------------------------
# Drift report helper
# ---------------------------------------------------------------------------

def _load_latest_drift_report(city: str) -> dict:
    """Load the most recent drift report JSON for a city.

    Looks for files matching ``outputs/results/drift_reports/drift_{city}_*.json``
    and returns the last one in sorted filename order (most recent by filename).

    Returns a minimal dict with the fields relevant to the health endpoint.
    Falls back to a safe default dict on any error so the /health endpoint
    never fails because of drift reporting.

    Args:
        city: City identifier, e.g. "drammen".

    Returns:
        Dict with keys: severity, recommended_action, checked_at, rolling_mae_triggered.
    """
    try:
        drift_dir = _REPO_ROOT / "outputs" / "results" / "drift_reports"
        candidates = sorted(drift_dir.glob(f"drift_{city}_*.json"))
        if not candidates:
            return {
                "severity": "unknown",
                "recommended_action": "run scripts/run_drift_check.py",
                "checked_at": None,
                "rolling_mae_triggered": None,
            }
        latest = candidates[-1]
        with open(latest, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        rolling = data.get("rolling_mae_result") or {}
        return {
            "severity": data.get("overall_severity", "unknown"),
            "recommended_action": data.get("recommended_action", "unknown"),
            "checked_at": data.get("checked_at"),
            "rolling_mae_triggered": rolling.get("is_triggered"),
        }
    except Exception as exc:
        logger.debug("Could not load drift report for city='%s': %s", city, exc)
        return {
            "severity": "unknown",
            "recommended_action": "run scripts/run_drift_check.py",
            "checked_at": None,
            "rolling_mae_triggered": None,
        }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# DAN-116: Prediction sanity checks
# ---------------------------------------------------------------------------

def _sanity_check_predictions(request_id: str, preds: list[float]) -> list[str]:
    """Return list of warning strings. Empty list means predictions look sane."""
    warnings: list[str] = []
    if any(math.isnan(v) or math.isinf(v) for v in preds):
        warnings.append("NaN or Inf values detected in predictions")
    if any(v < 0 for v in preds):
        warnings.append(f"Negative predictions detected: min={min(preds):.3f}")
    if any(v > 500 for v in preds):
        warnings.append(f"Implausibly large predictions: max={max(preds):.1f} kWh/h")
    if len(preds) > 1 and len(set(round(v, 3) for v in preds)) == 1:
        warnings.append(f"All predictions identical ({preds[0]:.3f}) — possible stuck model")
    for w in warnings:
        logger.warning("[sanity|%s] %s", request_id, w)
    return warnings


# ---------------------------------------------------------------------------
# DAN-143: Compute tomorrow's predicted cost from stored forecast
# ---------------------------------------------------------------------------

async def _compute_tomorrow_cost(pool, household_id: str, target_date: date) -> float | None:
    """Fetch the latest H+24 P50 forecast for target_date and apply BGE tariff rates."""
    try:
        from energy_forecast.tariff import rate_for_slot
        import pytz
        dublin = pytz.timezone("Europe/Dublin")

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT p50_kwh, issued_at FROM predictions
                WHERE household_id = $1
                  AND forecast_date = $2
                ORDER BY issued_at DESC LIMIT 1
                """,
                household_id,
                target_date,
            )
        if not row or not row["p50_kwh"]:
            return None

        p50: list[float] = list(row["p50_kwh"])
        cost = 0.0
        for hour_idx, kwh in enumerate(p50[:24]):
            ts = pd.Timestamp(
                dublin.localize(
                    datetime(target_date.year, target_date.month, target_date.day, hour_idx)
                )
            )
            _, rate = rate_for_slot(ts)
            cost += kwh * rate

        from energy_forecast.tariff import BGE
        cost += BGE["standing_daily"]
        return round(cost, 2)
    except Exception as exc:
        logger.debug("Could not compute tomorrow cost: %s", exc)
        return None


@app.get("/health")
def health_check():
    """Liveness check — returns model status (real or mock) for each loaded model."""
    model_status = {
        name: ("mock" if isinstance(obj, str) and obj.startswith("MOCK") else "real")
        for name, obj in models.items()
    }
    # Read latest drift report if available (failure-safe — health endpoint must not fail)
    drift_status = _load_latest_drift_report(city="drammen")
    return {
        "status": "healthy",
        "models": model_status,
        "inference_ready": any(v == "real" for v in model_status.values()),
        "drift": drift_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/metrics")
async def get_metrics():
    """DAN-115: Structured MLOps health KPIs — data freshness, model health, advisory delivery.

    Returns 200 with partial data even if DB is unavailable (degrades gracefully).
    """
    pool = getattr(app.state, "db_pool", None)
    model_status = {
        name: ("mock" if isinstance(obj, str) and obj.startswith("MOCK") else "real")
        for name, obj in models.items()
    }
    alerts: list[str] = []

    data_metrics: dict = {"available": False}
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                hh_row = await conn.fetchrow("SELECT COUNT(*) AS n FROM households")
                mr_row = await conn.fetchrow("SELECT COUNT(*) AS n, MAX(recorded_at) AS last_ts FROM meter_readings")
                me_row = await conn.fetchrow(
                    """SELECT COUNT(DISTINCT DATE(interval_start AT TIME ZONE 'Europe/Dublin')) AS days
                       FROM myenergi_readings
                       WHERE interval_start >= NOW() - INTERVAL '30 days'"""
                )
                missing_days = 30 - int(me_row["days"] or 0)
                pred_row = await conn.fetchrow(
                    "SELECT COUNT(*) AS n, MAX(issued_at) AS last_ts FROM predictions "
                    "WHERE issued_at >= NOW() - INTERVAL '7 days'"
                )
                adv_row = await conn.fetchrow(
                    "SELECT COUNT(*) AS n, MAX(issued_at) AS last_ts FROM advisory_log "
                    "WHERE issued_at >= NOW() - INTERVAL '7 days'"
                )

            last_upload = mr_row["last_ts"].isoformat() if mr_row["last_ts"] else None
            stale_hours = None
            if mr_row["last_ts"]:
                stale_hours = round((datetime.now(timezone.utc) - mr_row["last_ts"].replace(tzinfo=timezone.utc)).total_seconds() / 3600, 1)

            data_metrics = {
                "available": True,
                "active_households": int(hh_row["n"] or 0),
                "meter_readings_total": int(mr_row["n"] or 0),
                "last_upload_ts": last_upload,
                "stale_upload_hours": stale_hours,
                "myenergi_days_last_30d": int(me_row["days"] or 0),
                "missing_myenergi_days_30d": missing_days,
                "predictions_last_7d": int(pred_row["n"] or 0),
                "last_inference_ts": pred_row["last_ts"].isoformat() if pred_row["last_ts"] else None,
                "advisories_last_7d": int(adv_row["n"] or 0),
                "last_advisory_ts": adv_row["last_ts"].isoformat() if adv_row["last_ts"] else None,
            }

            # Alert thresholds
            if missing_days > 3:
                alerts.append(f"WARN: {missing_days} missing myenergi days in last 30d")
            if stale_hours is not None and stale_hours > 7 * 24:
                alerts.append(f"WARN: No ESB upload in {stale_hours:.0f}h")
            if int(pred_row["n"] or 0) == 0:
                alerts.append("CRITICAL: No predictions generated in last 7 days")
            if int(adv_row["n"] or 0) == 0:
                alerts.append("WARN: No advisories sent in last 7 days")
        except Exception as exc:
            data_metrics = {"available": False, "error": str(exc)}
            alerts.append(f"CRITICAL: DB metrics query failed: {exc}")

    if not any(v == "real" for v in model_status.values()):
        alerts.append("WARN: All models are mocked — running without real ML inference")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "degraded" if alerts else "healthy",
        "models": model_status,
        "data": data_metrics,
        "alerts": alerts,
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest, model_name: str = "LightGBM"):
    """Run H+24 inference from a pre-engineered 35-feature vector.

    The caller is responsible for computing the 35 features using the
    same pipeline as training (see ``src/energy_forecast/features/temporal.py``).
    For end-to-end inference from raw data, use the ``/control`` endpoint instead.
    """
    if model_name not in models:
        raise HTTPException(status_code=400, detail=f"Model '{model_name}' not loaded.")

    model = models[model_name]

    try:
        df_features = pd.DataFrame([request.features])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid feature format: {exc}")

    request_id = str(uuid4())
    logger.info("[predict|%s] building_id=%s model=%s", request_id, request.building_id, model_name)

    is_mock = isinstance(model, str) and model.startswith("MOCK")
    try:
        if is_mock:
            logger.info("[predict|%s] Using mocked inference", request_id)
            preds = [150.0 + i for i in range(24)]
        else:
            raw = model.predict(df_features)
            preds = raw[0].tolist() if hasattr(raw[0], "__len__") else [float(raw[0])] * 24

    except Exception as exc:
        logger.error("[predict|%s] Inference failed: %s", request_id, exc)
        exc_str = str(exc)
        # Detect feature-count / feature-name mismatch — give a helpful 422 rather than 500
        if "number of features" in exc_str or "feature names" in exc_str.lower():
            expected_n = len(getattr(model, "feature_name_", []))
            model_names = getattr(model, "feature_name_", [])
            has_generic = expected_n > 0 and all(
                n.startswith("Column_") for n in model_names
            )
            detail = (
                f"Feature mismatch: model expects {expected_n} features, "
                f"got {len(request.features)}. "
            )
            if has_generic:
                detail += (
                    "This model was trained without named features (Column_0..N). "
                    "Re-run scripts/run_pipeline.py to retrain with semantic names, "
                    "then send features like {'lag_24h': ..., 'hour_of_day': ...}."
                )
            raise HTTPException(status_code=422, detail=detail)
        raise HTTPException(status_code=500, detail=f"Model inference failed: {exc_str}")

    # DAN-116: sanity check before persisting
    warnings = _sanity_check_predictions(request_id, preds)

    # E-27: persist prediction to history store (JSONL + optional PostgreSQL)
    store_prediction(
        building_id=request.building_id,
        issued_at=datetime.now(timezone.utc),
        p10=[v * 0.85 for v in preds],
        p50=preds,
        p90=[v * 1.15 for v in preds],
        model_version=model_name,
    )

    return PredictionResponse(
        request_id=request_id,
        building_id=request.building_id,
        timestamp=request.timestamp,
        horizon=len(preds),
        predictions=preds,
        inference_mode="mock" if is_mock else "real",
        warnings=warnings,
    )


@app.post("/control", response_model=ControlResponse)
def control(request: ControlRequest):
    """Run H+24 forecast and return per-hour demand-response decisions.

    This endpoint chains:
      1. Load forecast (LightGBM or mock)
      2. Solar irradiance + price signals (mock or live connectors)
      3. ControlEngine decision per requested hour

    Returns a ``ControlResponse`` with per-hour actions and a human-readable
    morning brief suitable for display or logging.

    Live connectors (OpenMeteoConnector, SEMOConnector) are activated by
    setting ``dry_run: false`` once the API keys are configured.
    """
    # ── Step 1: P10/P50/P90 forecast ──────────────────────────────────────
    model = models.get("LightGBM")
    if model is None:
        raise HTTPException(status_code=503, detail="LightGBM model not loaded.")

    if isinstance(model, str) and model.startswith("MOCK"):
        # Mock 24h load profile
        p50 = [20.0 + 15 * math.sin(math.pi * h / 12) for h in range(24)]
    else:
        # No live historical data in this path — use recent model output
        # For a production endpoint backed by a DataConnector, replace with:
        #   history = CSVConnector().fetch_last_n_hours(request.building_id, 72, request.city)
        #   X_scaled, _ = _build_inference_features(history, cfg, scaler_path)
        #   raw = model.predict(X_scaled.iloc[[-1]])
        p50 = [20.0 + 15 * math.sin(math.pi * h / 12) for h in range(24)]
        logger.info(
            "Model loaded but live DataConnector not configured — using P50 heuristic. "
            "Set up CSVConnector or OpenMeteoConnector in deployment/connectors.py."
        )

    p50 = [max(0.0, v) for v in p50]  # load is non-negative; clamp before PI scaling
    p10 = [v * 0.85 for v in p50]
    p90 = [v * 1.15 for v in p50]
    forecast = ForecastBundle(p10=p10, p50=p50, p90=p90)

    # ── Step 2: Environmental signals ─────────────────────────────────────
    if request.dry_run:
        solar_24h = MOCK_SOLAR_24H
        prices_24h = MockPriceConnector().get_day_ahead_prices()
    else:
        # Live connectors — add OpenMeteoConnector + SEMOConnector here
        # when API tokens are available (see deployment/connectors.py)
        raise HTTPException(
            status_code=501,
            detail=(
                "Live mode not yet enabled. "
                "Configure OpenMeteoConnector and SEMOConnector in connectors.py, "
                "then remove this guard. Use dry_run=true for demo mode."
            ),
        )

    env = EnvironmentState(
        solar_forecast_wh_m2=solar_24h,
        grid_price_eur_kwh=prices_24h,
        timestamp=datetime.now(timezone.utc),
        building_id=request.building_id,
    )

    # ── Step 3: Control decisions ──────────────────────────────────────────
    target_hours = [h for h in request.target_hours if 0 <= h < 24]
    if not target_hours:
        raise HTTPException(
            status_code=400,
            detail="target_hours must contain at least one value in [0, 23].",
        )
    actions = _control_engine.decide(forecast, env, target_hours=target_hours)

    # ── Step 4: Send to mock device ────────────────────────────────────────
    device = MockDeviceConnector()
    for a in actions:
        if a.action.value in {"DEFER_HEATING", "ALERT_HIGH_DEMAND"}:
            device.send_command(a.action.value, building_id=request.building_id)

    ctrl_request_id = str(uuid4())
    logger.info("[control|%s] building_id=%s city=%s", ctrl_request_id, request.building_id, request.city)

    return ControlResponse(
        request_id=ctrl_request_id,
        building_id=request.building_id,
        city=request.city,
        forecast_origin=datetime.now(timezone.utc).isoformat(),
        decisions=[
            HourDecision(
                hour=a.target_hour,
                action=a.action.value,
                confidence=a.confidence,
                reasoning=a.reasoning,
                p50_kwh=a.p50_kwh,
                solar_wh_m2=a.solar_wh_m2,
                price_eur_kwh=a.price_eur_kwh,
            )
            for a in actions
        ],
        morning_brief=_control_engine.explain(actions),
    )


@app.post("/upload", response_model=UploadResponse)
async def upload_meter_data(
    file: UploadFile = File(...),
    household_id: str | None = Form(None),
):
    """Ingest an ESB Networks HDF CSV file into the meter_readings hypertable.

    Accepts both kW and kWh ESB export formats (auto-detected).  Re-uploads are
    idempotent — duplicate timestamps are silently skipped.

    If household_id is not provided, the MPRN in the file is used to look up or
    create the household automatically.
    """
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        mprn, rows = parse_esb_csv(contents)
    except ESBParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if household_id is None:
        try:
            household_id = await resolve_or_create_household(pool, mprn)
        except Exception as exc:
            logger.error("Household resolution failed: %s", exc)
            raise HTTPException(status_code=500, detail="Could not resolve household.")

    total = len(rows)
    try:
        inserted = await upsert_meter_readings(pool, household_id, rows)
    except Exception as exc:
        logger.error("Meter reading upsert failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"DB write failed: {exc}")

    skipped = total - inserted
    timestamps = [r["recorded_at"] for r in rows if r.get("recorded_at")]
    date_from = str(min(timestamps)) if timestamps else None
    date_to = str(max(timestamps)) if timestamps else None

    return UploadResponse(
        household_id=household_id,
        rows_inserted=inserted,
        date_from=date_from,
        date_to=date_to,
        skipped=skipped,
    )


@app.get("/forecast/{household_id}", response_model=ForecastResponse)
async def get_forecast(
    household_id: str,
    days: int = Query(default=7, ge=1, le=30),
):
    """Return the most recent stored H+24 forecasts for a household.

    Query parameter ``days`` controls how many forecast records to return
    (default 7, max 30).  Returns 404 if the household_id is not registered.
    """
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    try:
        exists = await household_exists(pool, household_id)
    except Exception as exc:
        logger.error("Household lookup failed: %s", exc)
        raise HTTPException(status_code=500, detail="DB error.")

    if not exists:
        raise HTTPException(
            status_code=404,
            detail=f"Household '{household_id}' not found. Upload meter data first.",
        )

    try:
        forecasts = await fetch_forecasts(pool, household_id, days)
    except Exception as exc:
        logger.error("Forecast fetch failed: %s", exc)
        raise HTTPException(status_code=500, detail="DB error.")

    return ForecastResponse(
        household_id=household_id,
        forecasts=[ForecastEntry(**f) for f in forecasts],
    )


@app.post("/compare-plans", response_model=ComparePlansResponse)
async def compare_tariff_plans(request: ComparePlansRequest):
    """DAN-131: Replay meter_readings history against multiple tariff plans.

    Answers: "Which plan would have been cheapest given my actual consumption?"
    Results are sorted by annualised net cost (cheapest first).

    Available plan keys:
      BGE_FTS_AFFINITY    — current BGE Free Time Saturday with 20% Affinity discount
      BGE_FTS_STANDARD    — BGE FTS without discount (post-June-15 scenario)
      BGE_STANDARD_NOSAT  — BGE with discount but no free Saturday (shows Saturday value)
      ENERGIA_NIGHT_BOOST — Energia Night Boost (approx Q1 2026 rates)
      SSE_ONE_RATE        — SSE Airtricity flat single rate
      ELECTRIC_IRELAND_SMART — Electric Ireland Smart TOU (approx)

    Note: Non-BGE rates are approximate. Verify at supplier websites before contract decisions.
    """
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    date_from = None
    date_to = None
    try:
        if request.date_from:
            date_from = date.fromisoformat(request.date_from)
        if request.date_to:
            date_to = date.fromisoformat(request.date_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid date format: {exc}")

    plan_keys = request.plan_keys or list(PLANS.keys())
    unknown = [k for k in plan_keys if k not in PLANS]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown plan keys: {unknown}. Valid: {list(PLANS.keys())}",
        )

    try:
        results, meta = await compare_plans(pool, request.household_id, date_from, date_to, plan_keys)
    except Exception as exc:
        logger.error("Plan comparison failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Comparison failed: {exc}")

    if not results:
        raise HTTPException(status_code=404, detail="No meter readings found for this household and date range.")

    cheapest = results[0].plan_key
    current_result = next((r for r in results if r.plan_key == "BGE_FTS_AFFINITY"), results[-1])
    cheapest_result = results[0]
    savings = round(current_result.annualised_cost_eur - cheapest_result.annualised_cost_eur, 2)

    return ComparePlansResponse(
        household_id=request.household_id,
        date_from=meta.get("date_from", ""),
        date_to=meta.get("date_to", ""),
        days_analysed=meta.get("days_analysed", 0),
        total_import_kwh=meta.get("total_import_kwh", 0.0),
        total_export_kwh=meta.get("total_export_kwh", 0.0),
        cheapest_plan=cheapest,
        savings_vs_current_eur=savings,
        results=[
            PlanResultResponse(
                plan_key=r.plan_key,
                plan_name=r.plan_name,
                supplier=r.supplier,
                notes=r.notes,
                days_analysed=r.days_analysed,
                total_import_kwh=r.total_import_kwh,
                total_export_kwh=r.total_export_kwh,
                import_cost_eur=r.import_cost_eur,
                export_credit_eur=r.export_credit_eur,
                standing_charge_eur=r.standing_charge_eur,
                net_cost_eur=r.net_cost_eur,
                annualised_cost_eur=r.annualised_cost_eur,
                slots=SlotBreakdownResponse(
                    day_kwh=r.slots.day_kwh,
                    night_kwh=r.slots.night_kwh,
                    peak_kwh=r.slots.peak_kwh,
                    free_kwh=r.slots.free_kwh,
                    free_cap_exceeded_kwh=r.slots.free_cap_exceeded_kwh,
                ),
            )
            for r in results
        ],
    )
