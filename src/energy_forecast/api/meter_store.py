"""
energy_forecast.api.meter_store
================================
Async DB operations for meter readings.

Uses asyncpg exclusively (non-blocking, compatible with FastAPI's async event
loop).  The connection pool is created once in the FastAPI lifespan and stored
on app.state.db_pool — callers receive it as a parameter.

Public surface:
  - resolve_or_create_household(pool, mprn) → household_id (UUID str)
  - upsert_meter_readings(pool, household_id, rows) → int (rows inserted)
  - fetch_forecasts(pool, household_id, days) → list[dict]
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_UPSERT_HOUSEHOLD = """
INSERT INTO households (id, user_id, city, hardware_id)
VALUES ($1, $2, $3, $4)
ON CONFLICT (id) DO NOTHING
"""

_GET_HOUSEHOLD_BY_MPRN = """
SELECT id FROM households WHERE hardware_id = $1 LIMIT 1
"""

_UPSERT_READINGS = """
INSERT INTO meter_readings (household_id, recorded_at, import_kwh, export_kwh, source)
VALUES ($1, $2, $3, $4, 'csv_upload')
ON CONFLICT (household_id, recorded_at) DO NOTHING
"""

_FETCH_FORECASTS = """
SELECT forecast_date, issued_at, p10_kwh, p50_kwh, p90_kwh
FROM predictions
WHERE household_id = $1
ORDER BY forecast_date DESC
LIMIT $2
"""

_CHECK_HOUSEHOLD_EXISTS = """
SELECT 1 FROM households WHERE id = $1 LIMIT 1
"""


# ---------------------------------------------------------------------------
# Household helpers
# ---------------------------------------------------------------------------

async def resolve_or_create_household(pool, mprn: str) -> str:
    """Return existing household_id for MPRN or create a new one."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_GET_HOUSEHOLD_BY_MPRN, mprn)
        if row:
            return str(row["id"])

        new_id = str(uuid.uuid4())
        await conn.execute(
            _UPSERT_HOUSEHOLD,
            new_id,
            new_id,      # user_id = household_id (Phase 1 — no auth yet)
            "ireland",
            mprn,        # hardware_id stores MPRN
        )
        logger.info("Created new household %s for MPRN %s", new_id, mprn)
        return new_id


async def household_exists(pool, household_id: str) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_CHECK_HOUSEHOLD_EXISTS, household_id)
        return row is not None


# ---------------------------------------------------------------------------
# Meter readings
# ---------------------------------------------------------------------------

async def upsert_meter_readings(
    pool,
    household_id: str,
    rows: list[dict[str, Any]],
) -> int:
    """Bulk-insert rows into meter_readings.  Returns count of rows inserted.

    Each row must have: recorded_at (datetime, UTC), import_kwh (float),
    export_kwh (float, default 0.0).

    Uses ON CONFLICT DO NOTHING so re-uploads are idempotent.
    """
    if not rows:
        return 0

    records = [
        (
            household_id,
            r["recorded_at"],
            float(r["import_kwh"]),
            float(r.get("export_kwh", 0.0)),
        )
        for r in rows
    ]

    async with pool.acquire() as conn:
        await conn.executemany(_UPSERT_READINGS, records)
        # asyncpg executemany returns None — query actual count instead
        row = await conn.fetchrow(
            "SELECT COUNT(*) FROM meter_readings WHERE household_id = $1",
            household_id,
        )
    inserted = row[0] if row else len(records)
    logger.info("Upserted batch for household %s — total rows in DB: %d", household_id, inserted)
    return inserted


# ---------------------------------------------------------------------------
# Forecast retrieval
# ---------------------------------------------------------------------------

async def fetch_forecasts(pool, household_id: str, days: int = 7) -> list[dict]:
    """Fetch the most recent `days` forecasts for a household."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(_FETCH_FORECASTS, household_id, days)

    return [
        {
            "forecast_date": str(row["forecast_date"]),
            "issued_at": row["issued_at"].isoformat() if row["issued_at"] else None,
            "p10_kwh": list(row["p10_kwh"]) if row["p10_kwh"] else [],
            "p50_kwh": list(row["p50_kwh"]) if row["p50_kwh"] else [],
            "p90_kwh": list(row["p90_kwh"]) if row["p90_kwh"] else [],
        }
        for row in rows
    ]
