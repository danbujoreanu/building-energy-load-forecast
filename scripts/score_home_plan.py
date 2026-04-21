#!/usr/bin/env python3
"""
score_home_plan.py — BGE "Free Time Saturday" Plan Optimisation Scorer
=======================================================================
Loads an ESB Networks HDF CSV export and computes a full billing analysis
against the Bord Gáis Energy "Free Time Saturday" tariff, including the
20% Affinity discount applied to all usage charges.

Plan summary:
  - Free slot:  Saturday 09:00–17:00 (up to 100 kWh/month at €0.00)
  - Peak slot:  Mon–Fri 17:00–19:00 at 49.28c/kWh (before discount)
  - Night slot: 23:00–08:00 at 29.65c/kWh (before discount)
  - Day slot:   all other times at 40.34c/kWh (before discount)
  - Export:     18.5c/kWh net export credit (no discount applied)
  - Standing:   61.52c/day

Optimisation Score (0–100):
  A composite score measuring how well the household exploits the plan.
  - 50% weight: utilisation of the 100 kWh/month Saturday free allowance
  - 30% weight: avoidance of Mon–Fri peak-rate hours
  - 20% weight: shift of consumption to night-rate hours
  Score ≥ 80 = excellent; 60–80 = good; < 60 = significant savings available.

Usage:
    python scripts/score_home_plan.py --csv /path/to/HDF_export.csv
    python scripts/score_home_plan.py --csv /path/to/HDF_export.csv \
        --output outputs/results/home_plan_score.json
"""

import argparse
import json
import logging
import sys
from calendar import monthrange
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from energy_forecast.tariff import BGE, FREE_CAP_KWH, rate_slot  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_esb_csv(path: str) -> pd.DataFrame:
    """Load ESB Networks HDF CSV and return hourly import/export DataFrame.

    Handles DST duplicates by groupby-summing before resampling.
    Returns a DataFrame with DatetimeIndex (hourly, Europe/Dublin) and
    columns: import_kwh, export_kwh.
    """
    df = pd.read_csv(path)
    df["ts"] = pd.to_datetime(df["Read Date and End Time"], dayfirst=True)
    df = df.sort_values("ts").reset_index(drop=True)

    pivot = df.groupby(["ts", "Read Type"])["Read Value"].sum().unstack("Read Type").fillna(0)
    col_map = {c: ("import_kwh" if "Import" in c else "export_kwh") for c in pivot.columns}
    pivot = pivot.rename(columns=col_map)

    for col in ("import_kwh", "export_kwh"):
        if col not in pivot.columns:
            pivot[col] = 0.0

    hourly = pivot.resample("1h").sum()
    hourly.index = hourly.index.tz_localize(
        "Europe/Dublin", ambiguous="NaT", nonexistent="shift_forward"
    )
    hourly = hourly[hourly.index.notna()]
    return hourly


# ─────────────────────────────────────────────────────────────────────────────
# Monthly breakdown
# ─────────────────────────────────────────────────────────────────────────────


def compute_monthly_breakdown(hourly: pd.DataFrame) -> list[dict]:
    """Compute per-month billing breakdown."""
    records = []

    hourly = hourly.copy()
    hourly["slot"] = hourly.index.map(rate_slot)
    hourly["year_month"] = hourly.index.to_period("M")

    for period, grp in hourly.groupby("year_month"):
        year = period.year
        month = period.month
        days_in_month = monthrange(year, month)[1]

        import_kwh = grp["import_kwh"].sum()
        export_kwh = grp["export_kwh"].sum()
        free_kwh = grp.loc[grp["slot"] == "free", "import_kwh"].sum()
        peak_kwh = grp.loc[grp["slot"] == "peak", "import_kwh"].sum()
        night_kwh = grp.loc[grp["slot"] == "night", "import_kwh"].sum()
        day_kwh = grp.loc[grp["slot"] == "day", "import_kwh"].sum()

        # Free slot is capped at 100 kWh — usage beyond cap is billed at day rate
        billed_free_kwh = min(free_kwh, FREE_CAP_KWH)
        overflow_kwh = max(0.0, free_kwh - FREE_CAP_KWH)

        energy_cost = (
            billed_free_kwh * BGE["free"]
            + overflow_kwh * BGE["day"]
            + peak_kwh * BGE["peak"]
            + night_kwh * BGE["night"]
            + day_kwh * BGE["day"]
        )
        export_credit = export_kwh * BGE["export"]
        standing = days_in_month * BGE["standing_daily"]
        net_bill = energy_cost + standing - export_credit

        records.append(
            {
                "month": str(period),
                "days_in_month": days_in_month,
                "import_kwh": round(import_kwh, 2),
                "export_kwh": round(export_kwh, 2),
                "free_kwh": round(free_kwh, 2),
                "peak_kwh": round(peak_kwh, 2),
                "night_kwh": round(night_kwh, 2),
                "day_kwh": round(day_kwh, 2),
                "overflow_kwh": round(overflow_kwh, 2),
                "energy_cost": round(energy_cost, 2),
                "export_credit": round(export_credit, 2),
                "standing_charge": round(standing, 2),
                "net_bill": round(net_bill, 2),
            }
        )

    return records


# ─────────────────────────────────────────────────────────────────────────────
# Saturday free-window analysis
# ─────────────────────────────────────────────────────────────────────────────


def compute_saturday_analysis(hourly: pd.DataFrame) -> dict:
    """Per-Saturday and monthly Saturday free-window statistics.

    NOTE — Summer undercount:
    ``free_kwh`` is grid import only.  In summer, solar panels divert
    energy via Eddi *before* it reaches the grid meter, so ``free_kwh``
    understates true Saturday consumption.
    ``sat_export_kwh`` (export during the Saturday free window) is a proxy
    for solar activity.  Months with ``solar_undercount_flag=True`` have
    >2 kWh Saturday export — true free usage is likely 3–8 kWh higher per
    Saturday (full correction requires Eddi history API).
    """
    free = hourly[
        (hourly.index.weekday == 5) & (hourly.index.hour >= 9) & (hourly.index.hour < 17)
    ].copy()
    free["date"] = free.index.date

    per_sat = free.groupby("date")[["import_kwh", "export_kwh"]].sum().reset_index()
    per_sat.columns = ["date", "free_kwh", "sat_export_kwh"]
    per_sat["month"] = pd.to_datetime(per_sat["date"]).dt.to_period("M").astype(str)
    # Solar active flag: >0.5 kWh export in the free window = panels generating
    per_sat["solar_active"] = per_sat["sat_export_kwh"] > 0.5

    monthly_sat = (
        per_sat.groupby("month")[["free_kwh", "sat_export_kwh"]]
        .sum()
        .reset_index()
        .rename(
            columns={
                "free_kwh": "monthly_free_kwh",
                "sat_export_kwh": "monthly_sat_export_kwh",
            }
        )
    )
    monthly_sat["cap_used_pct"] = (monthly_sat["monthly_free_kwh"] / FREE_CAP_KWH * 100).round(1)
    monthly_sat["headroom_kwh"] = (
        (FREE_CAP_KWH - monthly_sat["monthly_free_kwh"]).clip(lower=0).round(2)
    )
    # Flag months where solar export suggests Eddi diversion is hiding real consumption
    monthly_sat["solar_undercount_flag"] = monthly_sat["monthly_sat_export_kwh"] > 2.0

    sat_list = [
        {
            "date": str(r.date),
            "free_kwh": round(r.free_kwh, 2),
            "sat_export_kwh": round(r.sat_export_kwh, 2),
            "solar_active": bool(r.solar_active),
        }
        for r in per_sat.itertuples()
    ]

    return {
        "per_saturday": sat_list,
        "monthly_saturday": monthly_sat.round(2).to_dict("records"),
        "avg_saturday_kwh": round(per_sat["free_kwh"].mean(), 2),
        "max_saturday_kwh": round(per_sat["free_kwh"].max(), 2),
        "min_saturday_kwh": round(per_sat["free_kwh"].min(), 2),
        "monthly_free_avg_kwh": round(monthly_sat["monthly_free_kwh"].mean(), 2),
        "monthly_headroom_avg": round(monthly_sat["headroom_kwh"].mean(), 2),
        "avg_sat_export_kwh": round(per_sat["sat_export_kwh"].mean(), 2),
        "solar_active_saturdays": int(per_sat["solar_active"].sum()),
        "solar_undercount_note": (
            "free_kwh = grid import only. In summer, Eddi diverts solar to hot "
            "water before it reaches the grid meter — not counted here. "
            "True Saturday consumption = free_kwh + eddi_diverted_kwh. "
            "Months with solar_undercount_flag=True have >2 kWh Saturday export; "
            "true free usage is likely 3–8 kWh/Saturday higher in those months. "
            "Full correction requires Eddi history API (log_eddi.py --once via cron)."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Optimisation score
# ─────────────────────────────────────────────────────────────────────────────


def compute_optimisation_score(
    monthly_breakdown: list[dict],
    saturday_analysis: dict,
) -> dict:
    """Compute the 0–100 composite optimisation score."""
    monthly_free_avg = saturday_analysis["monthly_free_avg_kwh"]

    total_import = sum(m["import_kwh"] for m in monthly_breakdown)
    total_peak = sum(m["peak_kwh"] for m in monthly_breakdown)
    total_night = sum(m["night_kwh"] for m in monthly_breakdown)

    peak_pct = (total_peak / total_import * 100) if total_import > 0 else 0.0
    night_pct = (total_night / total_import * 100) if total_import > 0 else 0.0

    free_score = min(100.0, (monthly_free_avg / FREE_CAP_KWH) * 100.0)
    peak_score = max(0.0, 100.0 - (peak_pct * 15.0))
    night_score = min(100.0, night_pct * 3.0)

    overall = free_score * 0.50 + peak_score * 0.30 + night_score * 0.20

    return {
        "overall": round(overall, 1),
        "free_score": round(free_score, 1),
        "peak_score": round(peak_score, 1),
        "night_score": round(night_score, 1),
        "free_utilisation_pct": round(free_score, 1),
        "peak_pct": round(peak_pct, 2),
        "night_pct": round(night_pct, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Money on the table
# ─────────────────────────────────────────────────────────────────────────────


def compute_money_on_table(
    monthly_breakdown: list[dict],
    saturday_analysis: dict,
) -> dict:
    """Quantify unrealised savings."""
    monthly_free_avg = saturday_analysis["monthly_free_avg_kwh"]
    unused_free_monthly = max(0.0, FREE_CAP_KWH - monthly_free_avg)
    monthly_saving_pot = unused_free_monthly * BGE["day"]
    annual_saving_pot = monthly_saving_pot * 12

    total_peak_kwh = sum(m["peak_kwh"] for m in monthly_breakdown)
    peak_overpay = total_peak_kwh * (BGE["peak"] - BGE["day"])

    return {
        "unused_free_kwh_monthly_avg": round(unused_free_monthly, 2),
        "monthly_saving_potential_eur": round(monthly_saving_pot, 2),
        "annual_saving_potential_eur": round(annual_saving_pot, 2),
        "peak_overpay_total_eur": round(peak_overpay, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Recommendations
# ─────────────────────────────────────────────────────────────────────────────


def generate_recommendations(
    score: dict,
    saturday_analysis: dict,
    monthly_breakdown: list[dict],
) -> list[str]:
    """Return a list of actionable recommendation strings."""
    recs = []
    free_util = score["free_utilisation_pct"]
    peak_pct = score["peak_pct"]
    monthly_free_avg = saturday_analysis["monthly_free_avg_kwh"]

    if free_util < 60:
        recs.append(
            f"Shift laundry, dishwasher, EV charging to Saturday 09:00–17:00. "
            f"You're using only {free_util:.0f}% of your 100 kWh free allowance "
            f"(avg {monthly_free_avg:.1f} kWh/month)."
        )

    if peak_pct > 2.0:
        total_import = sum(m["import_kwh"] for m in monthly_breakdown)
        months = len(monthly_breakdown)
        peak_monthly = (total_import * peak_pct / 100) / max(months, 1)
        recs.append(
            f"You have {peak_monthly:.1f} kWh at peak rate monthly. "
            "Shift Eddi or appliances away from Mon–Fri 17:00–19:00."
        )

    # Summer (May–Sep) free-window analysis — solar undercount aware
    summer_months = [
        m
        for m in saturday_analysis.get("monthly_saturday", [])
        if int(m["month"].split("-")[1]) in (5, 6, 7, 8, 9)
    ]
    if summer_months:
        summer_free_avg = np.mean([m["monthly_free_kwh"] for m in summer_months])
        summer_export_avg = np.mean([m.get("monthly_sat_export_kwh", 0.0) for m in summer_months])
        if summer_free_avg < 40:
            if summer_export_avg > 2.0:
                recs.append(
                    f"Summer Saturday grid import is low ({summer_free_avg:.0f} kWh/month) "
                    f"but solar exported ~{summer_export_avg:.0f} kWh on those Saturdays. "
                    "Eddi is diverting solar to hot water before it reaches the grid meter — "
                    "true free-window consumption is 10–20 kWh higher than shown. "
                    "Score is conservative in summer; no action needed."
                )
            else:
                recs.append(
                    f"In summer (May–Sep), Saturday free usage drops to "
                    f"{summer_free_avg:.0f} kWh — solar may be covering demand via Eddi. "
                    "Consider shifting more appliances (laundry, dishwasher) to the free window."
                )

    if not recs:
        recs.append(
            "Your usage is well-optimised for this plan. Keep Saturday appliances in the 09:00–17:00 window."
        )

    return recs


# ─────────────────────────────────────────────────────────────────────────────
# Report printer
# ─────────────────────────────────────────────────────────────────────────────


def print_report(result: dict) -> None:
    sep = "=" * 64
    print(f"\n{sep}")
    print("  BGE Free Time Saturday — Plan Optimisation Report")
    print(sep)
    print(f"  Period:        {result['date_range']['start']}  to  {result['date_range']['end']}")
    print(f"  Total days:    {result['total_days']}")
    print(f"  Total import:  {result['total_import_kwh']:.1f} kWh")
    print(f"  Total export:  {result['total_export_kwh']:.1f} kWh")

    s = result["optimisation_score"]
    print(f"\n  Optimisation Score:  {s['overall']:.1f} / 100")
    print(
        f"    Free-window score: {s['free_score']:.1f}  (weight 50%)  — utilisation {s['free_utilisation_pct']:.1f}%"
    )
    print(
        f"    Peak-avoid score:  {s['peak_score']:.1f}  (weight 30%)  — peak consumption {s['peak_pct']:.2f}% of total"
    )
    print(
        f"    Night-shift score: {s['night_score']:.1f}  (weight 20%)  — night consumption {s['night_pct']:.2f}% of total"
    )

    sa = result["saturday_analysis"]
    print("\n  Saturday free window:")
    print(f"    Avg per Saturday:  {sa['avg_saturday_kwh']:.1f} kWh  (grid import only)")
    print(
        f"    Monthly avg:       {sa['monthly_free_avg_kwh']:.1f} kWh  (cap: {FREE_CAP_KWH:.0f} kWh)"
    )
    print(f"    Monthly headroom:  {sa['monthly_headroom_avg']:.1f} kWh unused on average")
    if sa.get("avg_sat_export_kwh", 0) > 0.5:
        n_solar = sa.get("solar_active_saturdays", 0)
        print(
            f"    Avg Saturday solar export: {sa['avg_sat_export_kwh']:.1f} kWh/month  "
            f"({n_solar} Saturdays with active solar generation)"
        )
        print("    Note: Eddi solar diversion not in grid data — summer score is conservative.")

    mot = result["money_on_table"]
    print("\n  Savings opportunity:")
    print(f"    Unused free allowance:   {mot['unused_free_kwh_monthly_avg']:.1f} kWh/month")
    print(f"    Monthly saving potential: EUR {mot['monthly_saving_potential_eur']:.2f}")
    print(f"    Annual saving potential:  EUR {mot['annual_saving_potential_eur']:.2f}")
    print(f"    Peak-rate overpay (total): EUR {mot['peak_overpay_total_eur']:.2f}")

    print("\n  Recommendations:")
    for i, rec in enumerate(result["recommendations"], 1):
        # wrap at ~70 chars
        words = rec.split()
        lines, line = [], []
        for w in words:
            if sum(len(x) + 1 for x in line) + len(w) > 68:
                lines.append(" ".join(line))
                line = [w]
            else:
                line.append(w)
        if line:
            lines.append(" ".join(line))
        print(f"  {i}. {lines[0]}")
        for line_part in lines[1:]:
            print(f"     {line_part}")

    print(f"\n{sep}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score your BGE Free Time Saturday plan utilisation."
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to ESB Networks HDF CSV export.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "outputs" / "results" / "home_plan_score.json"),
        help="Output JSON path (default: outputs/results/home_plan_score.json).",
    )
    args = parser.parse_args()

    logger.info("Loading ESB CSV: %s", args.csv)
    hourly = load_esb_csv(args.csv)
    logger.info(
        "Loaded %s hourly rows  (%s → %s)",
        f"{len(hourly):,}",
        hourly.index.min().date(),
        hourly.index.max().date(),
    )

    monthly_breakdown = compute_monthly_breakdown(hourly)
    saturday_analysis = compute_saturday_analysis(hourly)
    score = compute_optimisation_score(monthly_breakdown, saturday_analysis)
    money = compute_money_on_table(monthly_breakdown, saturday_analysis)
    recommendations = generate_recommendations(score, saturday_analysis, monthly_breakdown)

    result = {
        "date_range": {
            "start": str(hourly.index.min().date()),
            "end": str(hourly.index.max().date()),
        },
        "total_days": (hourly.index.max() - hourly.index.min()).days + 1,
        "total_import_kwh": round(hourly["import_kwh"].sum(), 2),
        "total_export_kwh": round(hourly["export_kwh"].sum(), 2),
        "monthly_breakdown": monthly_breakdown,
        "saturday_analysis": saturday_analysis,
        "optimisation_score": score,
        "money_on_table": money,
        "recommendations": recommendations,
        "tariff_used": {k: v for k, v in BGE.items()},
    }

    print_report(result)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2, default=str)
    logger.info("Results saved to: %s", out_path)


if __name__ == "__main__":
    main()
