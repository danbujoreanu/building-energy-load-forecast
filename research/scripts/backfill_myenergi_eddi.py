"""
scripts/backfill_myenergi_eddi.py
===================================
One-shot backfill: re-fetch all historical MyEnergi days and correct
myenergi_readings.eddi_kwh from the wrong hsk field to h1b + h1d.

Also refreshes solar_actuals.eddi_kwh for every day that already has
an export_kwh row (enabling a valid panel_factor_obs recompute).

Usage:
    export $(cat .env | grep -v '#' | xargs)
    python scripts/backfill_myenergi_eddi.py [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--dry-run]

Defaults to all days currently in myenergi_readings.
Sleeps 0.4 s between API calls to avoid hammering the hub.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import date, timedelta

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg

from deployment.myenergi_poller import (
    HUB_SERIAL,
    _UPSERT_MYENERGI,
    _UPSERT_SOLAR_ACTUALS,
    _aggregate_to_30min,
    _fetch_day_minutes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DB_DSN = (
    f"postgresql://sparc:{os.environ.get('DB_PASSWORD', 'sparc_local_2026')}"
    "@localhost:5432/sparc_energy"
)

_FETCH_DATES = """
SELECT DISTINCT DATE(interval_start AT TIME ZONE 'Europe/Dublin') AS d
FROM myenergi_readings
ORDER BY 1
"""

_FETCH_GHI_FOR_DATE = """
SELECT ROUND(SUM(ghi_wh_m2) / 1000.0, 3)
FROM weather_log
WHERE location = 'maynooth'
  AND data_type = 'actual'
  AND DATE(hour_utc AT TIME ZONE 'Europe/Dublin') = $1
"""


async def backfill(
    from_date: date,
    to_date: date,
    dry_run: bool = False,
) -> None:
    pool = await asyncpg.create_pool(DB_DSN, min_size=1, max_size=3)

    # Fetch candidate dates within the requested range
    async with pool.acquire() as conn:
        rows = await conn.fetch(_FETCH_DATES)
    all_dates = [r["d"] for r in rows if from_date <= r["d"] <= to_date]
    logger.info("Backfilling %d days (%s → %s)", len(all_dates), from_date, to_date)

    ok = err = skipped = 0
    for d in all_dates:
        try:
            minutes_raw = await asyncio.to_thread(_fetch_day_minutes, d)
        except Exception as exc:
            logger.warning("  [%s] API fetch failed: %s — skipping", d, exc)
            err += 1
            await asyncio.sleep(0.4)
            continue

        slots = _aggregate_to_30min(minutes_raw, d)
        if not slots:
            logger.info("  [%s] No slots returned — skipping", d)
            skipped += 1
            await asyncio.sleep(0.4)
            continue

        daily_eddi_kwh = round(sum(s["eddi_kwh"] for s in slots), 3)

        if dry_run:
            logger.info("  [%s] DRY-RUN — eddi_kwh=%.3f (%d slots)", d, daily_eddi_kwh, len(slots))
            ok += 1
            await asyncio.sleep(0.4)
            continue

        async with pool.acquire() as conn:
            # Update 30-min readings
            await conn.executemany(
                _UPSERT_MYENERGI,
                [
                    (HUB_SERIAL, s["interval_start"], s["import_kwh"], s["eddi_kwh"], s["sample_count"])
                    for s in slots
                ],
            )
            # Fetch GHI for the solar_actuals upsert (may be NULL — that's fine)
            daily_ghi = await conn.fetchval(_FETCH_GHI_FOR_DATE, d)
            await conn.execute(
                _UPSERT_SOLAR_ACTUALS,
                d,
                daily_eddi_kwh,
                daily_ghi,
            )

        logger.info("  [%s] eddi_kwh=%.3f  ghi=%.3f  slots=%d", d, daily_eddi_kwh, daily_ghi or 0.0, len(slots))
        ok += 1
        await asyncio.sleep(0.4)

    await pool.close()
    logger.info(
        "Backfill complete — ok=%d  err=%d  skipped=%d",
        ok, err, skipped,
    )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill myenergi eddi_kwh (h1b+h1d correction)")
    p.add_argument("--from", dest="from_date", default="2024-01-01",
                   help="Start date YYYY-MM-DD (default: 2024-01-01)")
    p.add_argument("--to", dest="to_date", default=str(date.today()),
                   help="End date YYYY-MM-DD (default: today)")
    p.add_argument("--dry-run", action="store_true",
                   help="Fetch from API but do not write to DB")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(backfill(
        from_date=date.fromisoformat(args.from_date),
        to_date=date.fromisoformat(args.to_date),
        dry_run=args.dry_run,
    ))
