#!/usr/bin/env python3
"""
scripts/verify_tariffs.py
==========================
DAN-157 — Tariff freshness audit for plan_comparison.PLANS.

Warns when any plan's last_verified date is older than STALE_DAYS (default 90).
Exits with code 1 if stale entries found — safe to run in CI or as a pre-deploy check.

Usage:
    python scripts/verify_tariffs.py
    python scripts/verify_tariffs.py --stale-days 60
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

# ── ensure project root is on the path ───────────────────────────────────────
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.energy_forecast.api.plan_comparison import PLANS

STALE_DAYS_DEFAULT = 90


def main(stale_days: int = STALE_DAYS_DEFAULT) -> int:
    today = date.today()
    rows = []
    stale_count = 0

    for key, plan in PLANS.items():
        lv = plan.last_verified
        if lv is None:
            age_days = None
            status = "⚠️  UNVERIFIED (no last_verified date)"
            stale_count += 1
        else:
            age_days = (today - lv).days
            if age_days > stale_days:
                status = f"⚠️  STALE ({age_days}d — threshold {stale_days}d)"
                stale_count += 1
            else:
                status = f"✅  OK ({age_days}d ago)"

        rows.append({
            "key": key,
            "name": plan.name,
            "supplier": plan.supplier,
            "last_verified": str(lv) if lv else "—",
            "age_days": age_days,
            "status": status,
            "url": plan.product_url or "—",
        })

    # ── Print table ──────────────────────────────────────────────────────────
    print(f"\nTariff freshness audit — threshold: {stale_days} days")
    print(f"Today: {today}   Plans in registry: {len(PLANS)}\n")

    col_key  = max(len(r["key"])  for r in rows) + 2
    col_name = max(len(r["name"]) for r in rows) + 2
    col_supp = max(len(r["supplier"]) for r in rows) + 2

    header = f"{'Key':<{col_key}} {'Plan':<{col_name}} {'Supplier':<{col_supp}} {'Verified':<14} {'Status'}"
    print(header)
    print("─" * len(header))
    for r in rows:
        print(f"{r['key']:<{col_key}} {r['name']:<{col_name}} {r['supplier']:<{col_supp}} {r['last_verified']:<14} {r['status']}")

    print()
    if stale_count:
        print(f"⚠️  {stale_count} plan(s) need verification. Check URLs below:")
        for r in rows:
            if "STALE" in r["status"] or "UNVERIFIED" in r["status"]:
                print(f"  {r['key']}: {r['url']}")
        return 1
    else:
        print(f"All {len(PLANS)} plans verified within {stale_days} days.")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit tariff freshness")
    parser.add_argument("--stale-days", type=int, default=STALE_DAYS_DEFAULT,
                        help=f"Days before a plan is considered stale (default: {STALE_DAYS_DEFAULT})")
    args = parser.parse_args()
    sys.exit(main(stale_days=args.stale_days))
