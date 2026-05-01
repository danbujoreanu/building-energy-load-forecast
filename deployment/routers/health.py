"""Health and metrics endpoints."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Repo root — needed to locate drift reports ────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


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


@router.get("/health")
def health_check(request: Request):
    """Liveness check — returns model status (real or mock) for each loaded model."""
    models = getattr(request.app.state, "models", {})
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


@router.get("/metrics")
async def get_metrics(request: Request):
    """DAN-115: Structured MLOps health KPIs — data freshness, model health, advisory delivery.

    Returns 200 with partial data even if DB is unavailable (degrades gracefully).
    """
    pool = getattr(request.app.state, "db_pool", None)
    models = getattr(request.app.state, "models", {})
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
