"""
scripts/compare_plans.py
========================
Compare all Irish electricity tariffs against a household's actual consumption.

Usage:
    export $(cat .env | grep -v '#' | xargs)
    python scripts/compare_plans.py [--household-id UUID] [--discount 0.80] [--current bge_free_sat]

Reads meter_readings from local TimescaleDB and outputs a ranked table.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import warnings

warnings.filterwarnings("ignore")

import asyncpg

DB_DSN = (
    f"postgresql://sparc:{os.environ.get('DB_PASSWORD', 'sparc_local_2026')}"
    "@localhost:5432/sparc_energy"
)

_FIRST_HOUSEHOLD = "SELECT id FROM households LIMIT 1"


async def run(household_id: str | None, discount: float, current_key: str) -> None:
    import sys; sys.path.insert(0, "src")
    from energy_forecast.tariffs.comparison import compare_tariffs, load_readings_from_db

    pool = await asyncpg.create_pool(DB_DSN)

    if household_id is None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(_FIRST_HOUSEHOLD)
            household_id = str(row["id"])

    rows = await load_readings_from_db(pool, household_id)
    await pool.close()

    if not rows:
        print("No meter readings found.")
        return

    result = compare_tariffs(rows, current_tariff_key=current_key,
                             household_id=household_id, discount=discount)

    print(f"\nPlan comparison for household {household_id}")
    print(f"Based on {result.months_data} months of data (annualised)")
    if discount < 1.0:
        print(f"Note: {(1-discount)*100:.0f}% usage discount applied to all plans")
        print("      (Replace with supplier-specific discounts for more accurate results)")
    print()
    print(f"{'Supplier':<28} {'Plan':<38} {'Annual cost':>12}  {'Saving vs current':>18}")
    print("─" * 104)

    for r in result.ranked:
        is_current = r.key == current_key
        saving = result.current_cost_eur - r.annual_cost_eur
        saving_str = f"+€{abs(saving):.0f} more" if saving < 0 else (f"€{saving:.0f} saved" if saving > 0 else "← CURRENT (cheapest!)" if is_current else "← CURRENT")
        marker = " ◀ CURRENT" if is_current else ""
        print(f"  {r.supplier:<26} {r.name:<38} €{r.annual_cost_eur:>8.2f}/yr  {saving_str}{marker}")

    print()
    if result.potential_saving_eur > 0:
        print(f"💡 Switching to {result.cheapest_key} could save €{result.potential_saving_eur:.2f}/yr")
    else:
        print(f"✓ Your current plan ({current_key}) is already the cheapest option.")


def main():
    p = argparse.ArgumentParser(description="Compare Irish electricity tariffs")
    p.add_argument("--household-id", default=None)
    p.add_argument("--discount", type=float, default=1.0,
                   help="Usage rate multiplier (e.g. 0.80 for 20%% discount)")
    p.add_argument("--current", default="bge_free_sat",
                   help="Current tariff key (see tariffs/registry.py)")
    args = p.parse_args()
    asyncio.run(run(args.household_id, args.discount, args.current))


if __name__ == "__main__":
    main()
