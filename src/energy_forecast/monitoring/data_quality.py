"""
monitoring.data_quality
=======================
DAN-159 — MyEnergi vs ESB cross-validation (Layer 1 + Layer 5).

Called nightly at 23:55 by the APScheduler job in deployment/app.py.

Cross-validation logic:
  - ESB meter_readings is the billing source of truth for daily import.
  - MyEnergi CT clamp reads 10-20% lower (consumer-grade vs billing-grade meter).
  - Expected ratio: myenergi_daily / esb_daily ≈ 0.80–0.95.
  - Physical violation: myenergi > esb is impossible — flags data corruption.
  - Ratio anomaly: ratio outside mean ± 2σ of last 30 days (CT may have shifted).
  - CT calibration factor: 30d mean of esb / myenergi — stored on households table,
    used by the solar advisory to correct MyEnergi-derived generation estimates.

Only Layer 1 and Layer 5 are implemented here.
Layer 2 (weekly Pushover report) is in deployment/app.py (_run_weekly_quality_report).
Layer 3 (human-in-the-loop n8n webhook) and Layer 4 (screenshot ingestion) are future.
"""
from __future__ import annotations

import logging
import math
from datetime import date, timedelta

logger = logging.getLogger(__name__)


# ── SQL helpers ───────────────────────────────────────────────────────────────

_SQL_ESB_DAILY = """
    SELECT ROUND(SUM(import_kwh)::NUMERIC, 3) AS esb_kwh
    FROM   meter_readings
    WHERE  household_id = $1
      AND  DATE(recorded_at AT TIME ZONE 'Europe/Dublin') = $2
      AND  import_kwh IS NOT NULL
"""

_SQL_MYENERGI_DAILY = """
    SELECT ROUND(SUM(mr.import_kwh)::NUMERIC, 3) AS me_kwh
    FROM   myenergi_readings mr
    JOIN   households h ON h.hardware_id::text = mr.hub_serial
    WHERE  h.id = $1
      AND  DATE(mr.interval_start AT TIME ZONE 'Europe/Dublin') = $2
      AND  mr.import_kwh IS NOT NULL
"""

_SQL_ROLLING_STATS = """
    SELECT
        AVG(ratio)    AS mean_ratio,
        STDDEV(ratio) AS std_ratio
    FROM data_quality_events
    WHERE household_id = $1
      AND check_date   >= $2
      AND ratio        IS NOT NULL
"""

_SQL_UPSERT_EVENT = """
    INSERT INTO data_quality_events
        (household_id, check_date, esb_daily_kwh, myenergi_daily_kwh, ratio,
         physical_violation, ratio_anomaly, anomaly_detail, ct_calibration_factor)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    ON CONFLICT (household_id, check_date)
    DO UPDATE SET
        esb_daily_kwh        = EXCLUDED.esb_daily_kwh,
        myenergi_daily_kwh   = EXCLUDED.myenergi_daily_kwh,
        ratio                = EXCLUDED.ratio,
        physical_violation   = EXCLUDED.physical_violation,
        ratio_anomaly        = EXCLUDED.ratio_anomaly,
        anomaly_detail       = EXCLUDED.anomaly_detail,
        ct_calibration_factor = EXCLUDED.ct_calibration_factor,
        recorded_at          = NOW()
    RETURNING id
"""

_SQL_CT_ROLLING = """
    SELECT AVG(ct_calibration_factor) AS ct_mean
    FROM   data_quality_events
    WHERE  household_id      = $1
      AND  check_date        >= $2
      AND  ct_calibration_factor IS NOT NULL
"""

_SQL_UPDATE_CT = """
    UPDATE households
    SET    ct_calibration_factor = $1
    WHERE  id = $2
"""


# ── Public entry point ────────────────────────────────────────────────────────

async def run_cross_check(pool, household_id: str, check_date: date | None = None) -> dict:
    """Run Layer 1 cross-check for one household on check_date (default: yesterday).

    Returns a summary dict suitable for logging.  Also upserts a row into
    ``data_quality_events`` and updates ``households.ct_calibration_factor``.

    Parameters
    ----------
    pool:
        asyncpg connection pool (from app.state.db_pool).
    household_id:
        UUID string.
    check_date:
        Date to check.  Defaults to yesterday Europe/Dublin.

    Returns
    -------
    dict with keys: check_date, esb_kwh, me_kwh, ratio, physical_violation,
                    ratio_anomaly, anomaly_detail, ct_factor, ct_30d_mean
    """
    import pytz
    from datetime import datetime as _dt

    if check_date is None:
        check_date = (_dt.now(pytz.timezone("Europe/Dublin")) - timedelta(days=1)).date()

    result: dict = {
        "household_id": household_id,
        "check_date": check_date,
        "esb_kwh": None,
        "me_kwh": None,
        "ratio": None,
        "physical_violation": False,
        "ratio_anomaly": False,
        "anomaly_detail": None,
        "ct_factor": None,
        "ct_30d_mean": None,
    }

    try:
        async with pool.acquire() as conn:
            esb_row = await conn.fetchrow(_SQL_ESB_DAILY, household_id, check_date)
            me_row = await conn.fetchrow(_SQL_MYENERGI_DAILY, household_id, check_date)

        esb_kwh = float(esb_row["esb_kwh"]) if esb_row and esb_row["esb_kwh"] is not None else None
        me_kwh = float(me_row["me_kwh"]) if me_row and me_row["me_kwh"] is not None else None

        result["esb_kwh"] = esb_kwh
        result["me_kwh"] = me_kwh

        if esb_kwh is None or me_kwh is None:
            logger.debug(
                "[data_quality] household=%s date=%s — missing data (esb=%.3f me=%s), skipping.",
                household_id[:8], check_date, esb_kwh or 0, me_kwh,
            )
            return result

        if esb_kwh <= 0:
            logger.debug(
                "[data_quality] household=%s date=%s — ESB import=%.3f kWh, skipping ratio check.",
                household_id[:8], check_date, esb_kwh,
            )
            return result

        ratio = round(me_kwh / esb_kwh, 4)
        result["ratio"] = ratio

        # Physical constraint: myenergi cannot exceed ESB billing meter
        physical_violation = me_kwh > esb_kwh * 1.05  # 5% tolerance for rounding
        result["physical_violation"] = physical_violation

        # CT calibration factor = esb / myenergi (inverse of ratio)
        ct_factor = round(esb_kwh / me_kwh, 4) if me_kwh > 0 else None
        result["ct_factor"] = ct_factor

        # Ratio anomaly: outside mean ± 2σ of last 30 days
        window_start = check_date - timedelta(days=30)
        async with pool.acquire() as conn:
            stats_row = await conn.fetchrow(_SQL_ROLLING_STATS, household_id, window_start)

        mean_r = float(stats_row["mean_ratio"]) if stats_row and stats_row["mean_ratio"] is not None else None
        std_r = float(stats_row["std_ratio"]) if stats_row and stats_row["std_ratio"] is not None else None

        ratio_anomaly = False
        anomaly_detail = None

        if physical_violation:
            ratio_anomaly = True
            anomaly_detail = (
                f"PHYSICAL VIOLATION: MyEnergi {me_kwh:.3f} kWh > ESB {esb_kwh:.3f} kWh — "
                "likely hub_serial mismatch or API data error."
            )
        elif mean_r is not None and std_r is not None and std_r > 0:
            z = abs(ratio - mean_r) / std_r
            if z > 2.0:
                ratio_anomaly = True
                anomaly_detail = (
                    f"ratio {ratio:.4f} vs 30d mean {mean_r:.4f} ±{std_r:.4f} "
                    f"(z={z:.1f}σ) — CT clamp may have shifted."
                )

        result["ratio_anomaly"] = ratio_anomaly
        result["anomaly_detail"] = anomaly_detail

        # Upsert event row
        async with pool.acquire() as conn:
            await conn.fetchrow(
                _SQL_UPSERT_EVENT,
                household_id,
                check_date,
                esb_kwh,
                me_kwh,
                ratio,
                physical_violation,
                ratio_anomaly,
                anomaly_detail,
                ct_factor,
            )

        # Layer 5: update rolling 30d CT calibration factor on households table
        ct_30d_mean = await _recompute_ct_calibration_factor(pool, household_id)
        result["ct_30d_mean"] = ct_30d_mean

        level = logging.WARNING if (ratio_anomaly or physical_violation) else logging.INFO
        logger.log(
            level,
            "[data_quality] household=%s date=%s esb=%.3f me=%.3f ratio=%.4f "
            "physical_violation=%s ratio_anomaly=%s ct_30d=%.4f",
            household_id[:8], check_date, esb_kwh, me_kwh, ratio,
            physical_violation, ratio_anomaly, ct_30d_mean or 0.0,
        )

    except Exception as exc:
        logger.error("[data_quality] run_cross_check failed for household=%s: %s", household_id[:8], exc)

    return result


async def _recompute_ct_calibration_factor(pool, household_id: str) -> float | None:
    """Layer 5: compute 30d rolling mean of ct_calibration_factor, store on households.

    Returns the computed factor, or None if insufficient data.
    """
    window_start = date.today() - timedelta(days=30)
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(_SQL_CT_ROLLING, household_id, window_start)
        if row is None or row["ct_mean"] is None:
            return None
        ct_mean = round(float(row["ct_mean"]), 4)
        async with pool.acquire() as conn:
            await conn.execute(_SQL_UPDATE_CT, ct_mean, household_id)
        return ct_mean
    except Exception as exc:
        logger.error("[data_quality] CT factor recompute failed for household=%s: %s", household_id[:8], exc)
        return None


async def weekly_summary(pool, household_id: str, days: int = 7) -> dict:
    """Summarise data quality events over the last N days (Layer 2 helper).

    Returns dict with: mean_ratio, std_ratio, anomaly_count, days_checked,
    days_missing, ct_calibration_factor.
    """
    window_start = date.today() - timedelta(days=days)
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT check_date, ratio, physical_violation, ratio_anomaly,
                       anomaly_detail, ct_calibration_factor
                FROM   data_quality_events
                WHERE  household_id = $1
                  AND  check_date  >= $2
                ORDER BY check_date DESC
                """,
                household_id,
                window_start,
            )
            ct_row = await conn.fetchrow(
                "SELECT ct_calibration_factor FROM households WHERE id = $1", household_id
            )

        if not rows:
            return {
                "days_checked": 0, "anomaly_count": 0, "mean_ratio": None,
                "std_ratio": None, "days_missing": days,
                "ct_calibration_factor": None,
            }

        ratios = [float(r["ratio"]) for r in rows if r["ratio"] is not None]
        mean_ratio = round(sum(ratios) / len(ratios), 4) if ratios else None
        variance = (sum((x - mean_ratio) ** 2 for x in ratios) / len(ratios)) if len(ratios) > 1 else 0.0
        std_ratio = round(math.sqrt(variance), 4) if ratios else None
        anomaly_count = sum(1 for r in rows if r["ratio_anomaly"] or r["physical_violation"])
        ct_factor = float(ct_row["ct_calibration_factor"]) if ct_row and ct_row["ct_calibration_factor"] else None

        return {
            "days_checked": len(rows),
            "anomaly_count": anomaly_count,
            "mean_ratio": mean_ratio,
            "std_ratio": std_ratio,
            "days_missing": days - len(rows),
            "ct_calibration_factor": ct_factor,
        }

    except Exception as exc:
        logger.error("[data_quality] weekly_summary failed for household=%s: %s", household_id[:8], exc)
        return {
            "days_checked": 0, "anomaly_count": 0, "mean_ratio": None,
            "std_ratio": None, "days_missing": days, "ct_calibration_factor": None,
        }
