#!/usr/bin/env python3
"""
calibrate_panel_factor.py — Auto-calibrate PANEL_FACTOR from solar_actuals data.

Queries solar_actuals for rows where both export_kwh (from ESB upload) and
eddi_kwh (from myenergi) are populated, then computes observed panel factor:

    panel_factor_obs = (export_kwh + eddi_kwh) / ghi_actual

Note: panel_factor_obs is a LOWER BOUND — it excludes house self-consumption
(solar used directly before reaching the meter/Eddi). A 10% uplift is applied
to account for this. Uplift can be removed once a Harvi CT clamp is installed.

Usage:
    python scripts/calibrate_panel_factor.py
    python scripts/calibrate_panel_factor.py --min-days 60 --no-uplift

Requires:
    .env with DB_PASSWORD (default: sparc_local_2026)
    DB listening on localhost:5432 (docker compose must be up)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import asyncpg
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("calibrate")

DB_URL = (
    f"postgresql://sparc:{os.environ.get('DB_PASSWORD', 'sparc_local_2026')}"
    f"@localhost:5432/sparc_energy"
)

SELF_CONSUMPTION_UPLIFT = 0.10  # +10% to account for unmetered house self-consumption

_QUERY = """
SELECT
    solar_date,
    export_kwh,
    eddi_kwh,
    ghi_actual,
    panel_factor_obs
FROM solar_actuals
WHERE export_kwh IS NOT NULL
  AND eddi_kwh   IS NOT NULL
  AND ghi_actual IS NOT NULL
  AND ghi_actual > 0.5          -- exclude near-zero GHI days (winter, cloudy)
ORDER BY solar_date
"""


async def run(min_days: int, apply_uplift: bool) -> None:
    pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=2)
    rows = await pool.fetch(_QUERY)
    await pool.close()

    if not rows:
        logger.warning("No solar_actuals rows with all three fields populated.")
        logger.warning("Ensure ESB data has been uploaded (for export_kwh) and backfill ran (for eddi_kwh + ghi_actual).")
        return

    dates = [r["solar_date"] for r in rows]
    exports = np.array([float(r["export_kwh"]) for r in rows])
    eddis   = np.array([float(r["eddi_kwh"])   for r in rows])
    ghis    = np.array([float(r["ghi_actual"])  for r in rows])
    obs_pf  = np.array([float(r["panel_factor_obs"]) if r["panel_factor_obs"] else 0.0 for r in rows])

    # Recompute for rows where panel_factor_obs may be stale
    computed_pf = (exports + eddis) / ghis

    n = len(rows)
    if n < min_days:
        logger.warning(
            "Only %d qualifying days found (minimum requested: %d). "
            "Calibration result may be noisy — consider re-running with more data.",
            n, min_days,
        )

    median_pf   = float(np.median(computed_pf))
    mean_pf     = float(np.mean(computed_pf))
    p25, p75    = float(np.percentile(computed_pf, 25)), float(np.percentile(computed_pf, 75))

    recommended = round(median_pf * (1 + SELF_CONSUMPTION_UPLIFT if apply_uplift else 1.0), 4)

    print()
    print("=" * 60)
    print("PANEL FACTOR CALIBRATION REPORT")
    print("=" * 60)
    print(f"  Qualifying days analysed : {n}")
    print(f"  Date range               : {dates[0]} → {dates[-1]}")
    print(f"  Total export kWh         : {exports.sum():.1f}")
    print(f"  Total Eddi kWh           : {eddis.sum():.1f}")
    print(f"  Total GHI kWh/m²         : {ghis.sum():.1f}")
    print()
    print(f"  Observed panel factor:")
    print(f"    median                 : {median_pf:.4f}")
    print(f"    mean                   : {mean_pf:.4f}")
    print(f"    P25–P75                : {p25:.4f} – {p75:.4f}")
    print()
    if apply_uplift:
        print(f"  Self-consumption uplift  : +{SELF_CONSUMPTION_UPLIFT*100:.0f}%  (no Harvi CT installed)")
    else:
        print(f"  Self-consumption uplift  : disabled (--no-uplift)")
    print(f"  Recommended PANEL_FACTOR : {recommended:.4f}")
    print()
    print("  Current value in deployment/morning_advisory.py:")
    _show_current()
    print()
    print("  To apply:")
    print(f"    Edit deployment/morning_advisory.py:")
    print(f"    PANEL_FACTOR = {recommended}")
    print("=" * 60)
    print()

    # Show top/bottom 5 days for sanity
    idx_sorted = np.argsort(computed_pf)
    print("  Lowest panel-factor days (cloud cover / partial export):")
    for i in idx_sorted[:5]:
        print(f"    {dates[i]}  export={exports[i]:.2f}  eddi={eddis[i]:.2f}  GHI={ghis[i]:.2f}  pf={computed_pf[i]:.4f}")
    print()
    print("  Highest panel-factor days (peak summer output):")
    for i in idx_sorted[-5:]:
        print(f"    {dates[i]}  export={exports[i]:.2f}  eddi={eddis[i]:.2f}  GHI={ghis[i]:.2f}  pf={computed_pf[i]:.4f}")
    print()


def _show_current() -> None:
    try:
        advisory_path = ROOT / "deployment" / "morning_advisory.py"
        for line in advisory_path.read_text().splitlines():
            if "PANEL_FACTOR" in line and "=" in line and not line.strip().startswith("#"):
                print(f"    {line.strip()}")
    except Exception:
        print("    (could not read current value)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Calibrate PANEL_FACTOR from solar_actuals data")
    p.add_argument(
        "--min-days", type=int, default=30,
        help="Warn if fewer than this many qualifying days are found (default: 30)",
    )
    p.add_argument(
        "--no-uplift", action="store_true",
        help="Disable the 10%% self-consumption uplift (use if Harvi CT clamp installed)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.min_days, apply_uplift=not args.no_uplift))
