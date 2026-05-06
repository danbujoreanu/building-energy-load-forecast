"""Database query functions for the Energy Forecast API.

All raw SQL lives here. Scheduler and router functions import from this
module so they stay focused on orchestration, not query construction.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Household queries
# ---------------------------------------------------------------------------

async def fetch_all_households(pool) -> list:
    """Return all households with id and city."""
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT id, city FROM households")


async def fetch_household_ids(pool) -> list:
    """Return all household ids."""
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT id FROM households")


# ---------------------------------------------------------------------------
# Solar actuals
# ---------------------------------------------------------------------------

async def upsert_solar_actuals(pool, household_id: str, days: int = 90) -> str:
    """Aggregate export_kwh from meter_readings into solar_actuals for the last N days.

    Returns the asyncpg status string (e.g. 'INSERT 0 30').
    """
    async with pool.acquire() as conn:
        return await conn.execute(
            """
            INSERT INTO solar_actuals (solar_date, export_kwh)
            SELECT
              DATE(recorded_at AT TIME ZONE 'Europe/Dublin') AS solar_date,
              ROUND(SUM(export_kwh)::NUMERIC, 3)              AS export_kwh
            FROM meter_readings
            WHERE household_id = $1
              AND export_kwh IS NOT NULL
              AND DATE(recorded_at AT TIME ZONE 'Europe/Dublin')
                  >= CURRENT_DATE - INTERVAL '1 day' * $2
            GROUP BY 1
            ON CONFLICT (solar_date)
            DO UPDATE SET export_kwh = EXCLUDED.export_kwh
            """,
            household_id,
            days,
        )


# ---------------------------------------------------------------------------
# Panel factor seasonal
# ---------------------------------------------------------------------------

async def fetch_panel_factor_by_month(pool) -> list:
    """Compute per-month panel_factor from solar_actuals (months with >= 10 clean days)."""
    async with pool.acquire() as conn:
        return await conn.fetch(
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


async def update_household_panel_factor(pool, household_id: str, seasonal: dict) -> None:
    """Persist panel_factor_seasonal JSONB on a household row."""
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE households SET panel_factor_seasonal = $1::jsonb WHERE id = $2",
            json.dumps(seasonal),
            household_id,
        )


async def get_household_panel_factor_seasonal(pool, household_id: str):
    """Return the raw panel_factor_seasonal JSONB value (str or None)."""
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT panel_factor_seasonal FROM households WHERE id = $1",
            household_id,
        )


# ---------------------------------------------------------------------------
# Meter gap / recency
# ---------------------------------------------------------------------------

async def check_meter_recency(pool, household_id: str):
    """Return recency and gap stats for meter_readings over the last 30 days.

    Columns: last_ts, days_with_data, missing_days_30d
    Returns None if no rows.
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT
                MAX(recorded_at) AS last_ts,
                COUNT(DISTINCT DATE(recorded_at AT TIME ZONE 'Europe/Dublin')) AS days_with_data,
                30 - COUNT(DISTINCT DATE(recorded_at AT TIME ZONE 'Europe/Dublin')) AS missing_days_30d
            FROM meter_readings
            WHERE household_id = $1
              AND recorded_at >= NOW() - INTERVAL '30 days'
            """,
            household_id,
        )


# ---------------------------------------------------------------------------
# DAN-163 — Drift monitoring
# ---------------------------------------------------------------------------

async def get_recent_mae(pool, household_id: str, days: int = 7) -> float | None:
    """Compute mean absolute error between H+24 predictions and actual meter readings.

    Matches each prediction's p50_kwh[hour] against the actual import_kwh for that
    30-min slot (using hour index 0–23 mapped to 30-min pairs).

    Returns MAE in kWh over the last `days` days, or None if < 24h of paired data.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            WITH paired AS (
                SELECT
                    p.forecast_date,
                    -- p50_kwh is a 24-element array (one per hour).
                    -- Sum consecutive 30-min readings per hour bucket.
                    ABS(
                        p.p50_kwh[gs.h + 1]  -- 1-indexed in Postgres arrays
                        - COALESCE(
                            (SELECT SUM(mr.import_kwh)
                             FROM meter_readings mr
                             WHERE mr.household_id = p.household_id
                               AND mr.recorded_at >= (p.forecast_date + (gs.h * INTERVAL '1 hour'))
                                                      AT TIME ZONE 'Europe/Dublin'
                               AND mr.recorded_at <  (p.forecast_date + ((gs.h + 1) * INTERVAL '1 hour'))
                                                      AT TIME ZONE 'Europe/Dublin'
                            ), p.p50_kwh[gs.h + 1]  -- fallback to prediction if no actual
                        )
                    ) AS abs_error
                FROM predictions p
                CROSS JOIN generate_series(0, 23) AS gs(h)
                WHERE p.household_id = $1
                  AND p.forecast_date >= CURRENT_DATE - INTERVAL '1 day' * $2
            )
            SELECT ROUND(AVG(abs_error)::NUMERIC, 4) AS mae
            FROM paired
            """,
            household_id,
            days,
        )
        return float(row["mae"]) if row and row["mae"] is not None else None


async def upsert_semo_prices(
    pool, price_date: "date", prices: list[float], source: str = "eirgrid"
) -> None:
    """Upsert 24 hourly SEMO prices for price_date into semo_prices table."""
    from datetime import date  # noqa: PLC0415
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO semo_prices (price_date, hour, price_eur_kwh, source)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (price_date, hour) DO UPDATE SET
                price_eur_kwh = EXCLUDED.price_eur_kwh,
                source        = EXCLUDED.source,
                fetched_at    = NOW()
            """,
            [(price_date, h, prices[h], source) for h in range(len(prices))],
        )


async def get_semo_prices(pool, price_date: "date") -> list[float] | None:
    """Return 24 hourly prices in EUR/kWh for price_date, or None if not stored."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT hour, price_eur_kwh FROM semo_prices "
            "WHERE price_date = $1 ORDER BY hour",
            price_date,
        )
    if len(rows) < 24:
        return None
    return [float(r["price_eur_kwh"]) for r in rows]


async def insert_drift_log(
    pool,
    household_id: str,
    mae_7d: float | None,
    mae_28d: float | None,
    alert_sent: bool = False,
    notes: str | None = None,
) -> None:
    """Insert one row into model_drift_log."""
    drift_ratio = None
    if mae_7d and mae_28d and mae_28d > 0:
        drift_ratio = round(mae_7d / mae_28d, 3)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO model_drift_log
                (household_id, checked_at, model_mae_7d, model_mae_28d, drift_ratio, alert_sent, notes)
            VALUES ($1, NOW(), $2, $3, $4, $5, $6)
            """,
            household_id,
            mae_7d,
            mae_28d,
            drift_ratio,
            alert_sent,
            notes,
        )
