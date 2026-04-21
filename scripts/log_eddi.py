"""
log_eddi.py — continuous Eddi status logger
============================================
Polls the myenergi API every minute and appends one row per poll to a CSV.

Usage:
    export MYENERGI_SERIAL=21509692
    export MYENERGI_API_KEY=<your_key>

    # Poll once (e.g. from cron at 23:55 to record today_kwh before midnight reset):
    python scripts/log_eddi.py --once

    # Pull full history via API (no polling needed — works if hub supports it):
    python scripts/log_eddi.py --history 30           # last 30 days via cloud API

    # Continuous polling (advanced — requires always-on device):
    python scripts/log_eddi.py --interval 60

    python scripts/log_eddi.py --output data/home/eddi_log.csv

Output columns:
    timestamp          UTC timestamp (ISO 8601)
    timestamp_dublin   Europe/Dublin local time
    mode               Eddi operating mode string (e.g. "diverting_solar", "stopped")
    diverted_w         Watts currently being diverted to tank
    grid_w             Grid flow in Watts (positive=import, negative=export)
    today_kwh          kWh diverted to tank today (resets at midnight)
    solar_lower_w      Lower-bound solar generation estimate (div - max(0,grd))
    tank_temp_c        Tank temperature in °C (if sensor fitted; else None)
    harvi_ct1          Harvi CT1 reading in Watts (grid incomer)
    frequency_hz       Grid frequency in Hz

Purpose:
    Builds a local tank-state dataset so the app can estimate hot-water availability
    without relying on the Eddi history API (which returns status -14 on this hub).
    After ~2 weeks of polling, the dataset is sufficient for tank-state ML.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
import time
from datetime import date, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Project root on path
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "deployment"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

COLUMNS = [
    "timestamp",
    "timestamp_dublin",
    "mode",
    "diverted_w",
    "grid_w",
    "today_kwh",
    "solar_lower_w",
    "tank_temp_c",
    "harvi_ct1",
    "frequency_hz",
]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Eddi status logger")
    p.add_argument(
        "--interval", type=int, default=60, help="Poll interval in seconds (default: 60)"
    )
    p.add_argument(
        "--output",
        type=str,
        default=str(ROOT / "data" / "home" / "eddi_log.csv"),
        help="Output CSV path",
    )
    p.add_argument(
        "--once", action="store_true", help="Poll once and exit (useful for cron at 23:55 nightly)"
    )
    p.add_argument(
        "--history",
        type=int,
        default=0,
        metavar="DAYS",
        help="Pull last N days of history via cloud API and exit "
        "(no polling needed; requires hub to support history endpoint)",
    )
    return p.parse_args()


def _append_row(path: Path, row: dict) -> None:
    """Append one dict row to CSV, creating the file with headers if absent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def _poll_once(connector) -> dict | None:
    """Fetch Eddi status and return a flat row dict, or None on failure."""
    try:
        status = connector.get_status()
    except Exception as exc:
        logger.warning("Eddi API error: %s", exc)
        return None

    if status is None:
        logger.warning("Eddi returned None status")
        return None

    now_utc = pd.Timestamp.now(tz=timezone.utc)
    now_dublin = now_utc.tz_convert("Europe/Dublin")

    return {
        "timestamp": now_utc.isoformat(),
        "timestamp_dublin": now_dublin.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": status.get("mode", ""),
        "diverted_w": status.get("diverted_w", 0),
        "grid_w": status.get("grid_w", 0),
        "today_kwh": status.get("today_kwh", 0.0),
        "solar_lower_w": status.get("solar_lower_w", 0),
        "tank_temp_c": status.get("tank_temp_c"),
        "harvi_ct1": status.get("ct1_load", 0),
        "frequency_hz": status.get("frequency_hz"),
    }


def main() -> None:
    args = _parse_args()
    output = Path(args.output)

    serial = os.environ.get("MYENERGI_SERIAL", "")
    api_key = os.environ.get("MYENERGI_API_KEY", "")
    if not serial or not api_key:
        logger.error(
            "Set MYENERGI_SERIAL and MYENERGI_API_KEY environment variables.\n"
            "  export MYENERGI_SERIAL=21509692\n"
            "  export MYENERGI_API_KEY=<your_key>"
        )
        sys.exit(1)

    from connectors import MyEnergiConnector

    connector = MyEnergiConnector(serial=serial, api_key=api_key)

    # ── History pull mode (no continuous polling required) ──────────────────
    if args.history > 0:
        logger.info("Pulling last %d days of Eddi history via cloud API...", args.history)
        from datetime import timedelta

        end_dt = date.today() - timedelta(days=1)  # yesterday complete
        start_dt = end_dt - timedelta(days=args.history - 1)
        rows = connector.get_history_range(start_dt, end_dt)
        if not rows:
            logger.warning(
                "No history returned. Hub may not support history retrieval.\n"
                "Workaround: run with --once via cron at 23:55 each night to\n"
                "record today_kwh before it resets at midnight."
            )
        else:
            hist_path = output.parent / "eddi_history.csv"
            hist_path.parent.mkdir(parents=True, exist_ok=True)
            import csv as _csv

            write_header = not hist_path.exists() or hist_path.stat().st_size == 0
            with open(hist_path, "a", newline="") as f:
                w = _csv.DictWriter(f, fieldnames=["date", "diverted_kwh", "imported_kwh"])
                if write_header:
                    w.writeheader()
                w.writerows(rows)
            logger.info("Wrote %d rows to %s", len(rows), hist_path)
        return

    logger.info("Logging Eddi status to %s every %d seconds", output, args.interval)
    logger.info("Hub serial: %s  |  Monitor-only (no commands sent)", serial)

    consecutive_failures = 0
    MAX_FAILURES = 10  # pause polling if API repeatedly fails

    while True:
        row = _poll_once(connector)
        if row is not None:
            _append_row(output, row)
            consecutive_failures = 0
            logger.info(
                "mode=%-20s  diverted=%5d W  grid=%+6d W  today=%.3f kWh  solar_lower=%4d W",
                row["mode"],
                row["diverted_w"],
                row["grid_w"],
                row["today_kwh"],
                row["solar_lower_w"],
            )
        else:
            consecutive_failures += 1
            if consecutive_failures >= MAX_FAILURES:
                logger.error(
                    "%d consecutive failures — pausing 10 minutes before retrying",
                    consecutive_failures,
                )
                time.sleep(600)
                consecutive_failures = 0

        if args.once:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
