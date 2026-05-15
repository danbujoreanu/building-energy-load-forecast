#!/usr/bin/env python3
"""
myenergi_backfill.py — Historical backfill for myenergi_readings, weather_log, solar_actuals.

Runs run_daily_poll() for each date from --start-date to yesterday (inclusive).
Safe to re-run: all upserts use ON CONFLICT DO UPDATE.

Usage:
    python scripts/myenergi_backfill.py --start-date 2024-01-01
    python scripts/myenergi_backfill.py --start-date 2024-06-01 --end-date 2024-12-31

Requires:
    .env with MYENERGI_API_KEY, MYENERGI_SERIAL, DB_PASSWORD (default: sparc_local_2026)
    DB listening on localhost:5432 (docker compose must be up)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# ── project root on sys.path ──────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import asyncpg

from deployment.myenergi_poller import run_daily_poll, HUB_SERIAL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backfill")

DB_URL = os.environ.get(
    "DATABASE_URL",
    f"postgresql://sparc:{os.environ.get('DB_PASSWORD', 'sparc_local_2026')}"
    f"@localhost:5432/sparc_energy",
)

SLEEP_BETWEEN_DAYS = 1.2  # seconds — avoid hammering MyEnergi API


async def dates_already_present(pool: asyncpg.Pool, start: date, end: date) -> set[date]:
    """Return set of dates that already have ≥ 40 rows in myenergi_readings."""
    rows = await pool.fetch(
        """
        SELECT DATE(interval_start AT TIME ZONE 'Europe/Dublin') AS d, COUNT(*) AS cnt
        FROM myenergi_readings
        WHERE hub_serial = $1
          AND interval_start >= $2::date
          AND interval_start <  $3::date + INTERVAL '1 day'
        GROUP BY 1
        HAVING COUNT(*) >= 40
        """,
        HUB_SERIAL,
        start,
        end,
    )
    return {r["d"] for r in rows}


async def backfill(start: date, end: date, force: bool = False) -> None:
    pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=3)

    if force:
        already: set[date] = set()
        logger.info("--force: skipping presence check, re-fetching all %d days",
                    (end - start).days + 1)
    else:
        already = await dates_already_present(pool, start, end)
        logger.info("Dates already populated (≥40 slots): %d", len(already))

    total_days = (end - start).days + 1
    done = skipped = failed = 0

    current = start
    while current <= end:
        if current in already:
            skipped += 1
            current += timedelta(days=1)
            continue

        try:
            await run_daily_poll(pool, target_date=current)
            done += 1
            logger.info("✓ %s  [%d/%d done, %d skipped, %d failed]",
                        current, done, total_days, skipped, failed)
        except Exception as exc:
            failed += 1
            logger.warning("✗ %s  %s", current, exc)

        current += timedelta(days=1)
        time.sleep(SLEEP_BETWEEN_DAYS)

    await pool.close()
    logger.info(
        "Backfill complete — done: %d, skipped (already present): %d, failed: %d",
        done, skipped, failed,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill myenergi + GHI historical data")
    p.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=date(2024, 1, 1),
        help="First date to backfill (default: 2024-01-01)",
    )
    p.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=date.today() - timedelta(days=1),
        help="Last date to backfill (default: yesterday)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch and overwrite all dates, even those already populated. "
             "Use after a formula fix to correct stored kWh values.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.start_date > args.end_date:
        sys.exit("--start-date must be before --end-date")
    logger.info("Backfill range: %s → %s (%d days)",
                args.start_date, args.end_date,
                (args.end_date - args.start_date).days + 1)
    asyncio.run(backfill(args.start_date, args.end_date, force=args.force))
