"""
energy_forecast.api.plan_comparison
=====================================
Replay meter_readings history against multiple tariff plans.

Used by POST /compare-plans to answer: "Should I stay on my current plan
or switch to an alternative?"

IMPORTANT — Rate accuracy:
  BGE rates are exact (from tariff.py, verified 2026-04-30).
  Other supplier rates are approximate Q1 2026 figures.
  Verify at supplier websites before making a contract decision.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

MONTHLY_FREE_CAP_KWH: float = 100.0  # BGE FTS monthly free-slot allowance cap


# ─── Tariff plan definitions ─────────────────────────────────────────────────

@dataclass
class TariffPlan:
    key: str
    name: str
    supplier: str
    day_rate: float        # €/kWh — all other hours
    night_rate: float      # €/kWh — 23:00–08:00
    peak_rate: float       # €/kWh — Mon–Fri 17:00–19:00 (= day_rate if no peak)
    free_sat: bool         # True if Sat 09:00–17:00 is free
    export_rate: float     # €/kWh received for export
    standing_daily: float  # €/day
    notes: str = ""
    last_verified: Optional[date] = None    # DAN-157: date rates were last cross-checked at supplier website
    product_url: str = ""                   # DAN-157: direct link to plan page

    def rate_for(self, dt: pd.Timestamp) -> float:
        h = dt.hour
        wd = dt.weekday()  # 0=Mon … 6=Sun
        if self.free_sat and wd == 5 and 9 <= h < 17:
            return 0.0
        if wd < 5 and 17 <= h < 19:
            return self.peak_rate
        if h >= 23 or h < 8:
            return self.night_rate
        return self.day_rate

    def slot_name(self, dt: pd.Timestamp) -> str:
        h = dt.hour
        wd = dt.weekday()
        if self.free_sat and wd == 5 and 9 <= h < 17:
            return "free"
        if wd < 5 and 17 <= h < 19:
            return "peak"
        if h >= 23 or h < 8:
            return "night"
        return "day"


PLANS: dict[str, TariffPlan] = {
    "BGE_FTS_AFFINITY": TariffPlan(
        key="BGE_FTS_AFFINITY",
        name="BGE Free Time Saturday (20% Affinity)",
        supplier="Bord Gáis Energy",
        day_rate=round(0.4034 * 0.80, 5),
        night_rate=round(0.2965 * 0.80, 5),
        peak_rate=round(0.4928 * 0.80, 5),
        free_sat=True,
        export_rate=0.185,
        standing_daily=0.6152,
        notes="Current plan. 20% Affinity discount on usage (BGE customers only). Valid to 15 June 2026.",
        last_verified=date(2026, 4, 30),
        product_url="https://www.bordgaisenergy.ie/home/our-plans/electricity",
    ),
    "BGE_FTS_STANDARD": TariffPlan(
        key="BGE_FTS_STANDARD",
        name="BGE Free Time Saturday (no discount)",
        supplier="Bord Gáis Energy",
        day_rate=0.4034,
        night_rate=0.2965,
        peak_rate=0.4928,
        free_sat=True,
        export_rate=0.185,
        standing_daily=0.6152,
        notes="Post-June-15 scenario: no Affinity discount. EXACT rack rates verified 2026-04-30.",
        last_verified=date(2026, 4, 30),
        product_url="https://www.bordgaisenergy.ie/home/our-plans/electricity",
    ),
    "BGE_STANDARD_NOSAT": TariffPlan(
        key="BGE_STANDARD_NOSAT",
        name="BGE Standard (no free Saturday)",
        supplier="Bord Gáis Energy",
        day_rate=round(0.4034 * 0.80, 5),
        night_rate=round(0.2965 * 0.80, 5),
        peak_rate=round(0.4928 * 0.80, 5),
        free_sat=False,
        export_rate=0.185,
        standing_daily=0.6152,
        notes="Hypothetical: BGE rack rates with Affinity discount but no free Saturday window. Quantifies Saturday free-window value.",
        last_verified=date(2026, 4, 30),
        product_url="https://www.bordgaisenergy.ie/home/our-plans/electricity",
    ),
    "ENERGIA_NIGHT_BOOST": TariffPlan(
        key="ENERGIA_NIGHT_BOOST",
        name="Energia Night Boost",
        supplier="Energia",
        day_rate=0.4100,
        night_rate=0.2650,
        peak_rate=0.4100,  # no separate peak window
        free_sat=False,
        export_rate=0.180,
        standing_daily=0.6200,
        notes="APPROXIMATE Q1 2026. No free Saturday. Verify before use.",
        last_verified=date(2026, 4, 30),
        product_url="https://www.energia.ie/home/electricity-plans",
    ),
    "SSE_ONE_RATE": TariffPlan(
        key="SSE_ONE_RATE",
        name="SSE Airtricity One Rate",
        supplier="SSE Airtricity",
        day_rate=0.3850,
        night_rate=0.3850,
        peak_rate=0.3850,
        free_sat=False,
        export_rate=0.185,
        standing_daily=0.6000,
        notes="APPROXIMATE Q1 2026. Flat single rate — no TOU benefit. Verify before use.",
        last_verified=date(2026, 4, 30),
        product_url="https://www.sseairtricity.com/ie/home/electricity-gas/electricity-plans/",
    ),
    "ELECTRIC_IRELAND_SMART": TariffPlan(
        key="ELECTRIC_IRELAND_SMART",
        name="Electric Ireland Smart TOU",
        supplier="Electric Ireland",
        day_rate=0.4200,
        night_rate=0.2950,
        peak_rate=0.5100,
        free_sat=False,
        export_rate=0.185,
        standing_daily=0.6300,
        notes="APPROXIMATE Q1 2026. No free Saturday. Verify before use.",
        last_verified=date(2026, 4, 30),
        product_url="https://www.electricireland.ie/switch/home/electricity",
    ),
}


# ─── Result types ────────────────────────────────────────────────────────────

@dataclass
class SlotBreakdown:
    day_kwh: float = 0.0
    night_kwh: float = 0.0
    peak_kwh: float = 0.0
    free_kwh: float = 0.0
    free_cap_exceeded_kwh: float = 0.0    # kWh charged at day rate due to 100 kWh/month cap
    free_cap_months_affected: int = 0     # DAN-157: number of months where cap was exceeded


@dataclass
class PlanResult:
    plan_key: str
    plan_name: str
    supplier: str
    notes: str
    product_url: str
    last_verified: Optional[date]
    days_analysed: int
    total_import_kwh: float
    total_export_kwh: float
    import_cost_eur: float
    export_credit_eur: float
    standing_charge_eur: float
    net_cost_eur: float           # import + standing - export
    annualised_cost_eur: float    # net_cost scaled to 365 days
    cap_impact_note: str = ""     # DAN-157: human-readable free-window cap impact
    slots: SlotBreakdown = field(default_factory=SlotBreakdown)


# ─── Fetch + compare ────────────────────────────────────────────────────────

_FETCH_READINGS = """
SELECT
    recorded_at AT TIME ZONE 'Europe/Dublin' AS local_ts,
    import_kwh,
    export_kwh
FROM meter_readings
WHERE household_id = $1
  AND recorded_at >= $2
  AND recorded_at < $3
ORDER BY recorded_at
"""


async def compare_plans(
    pool,
    household_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
    plan_keys: list[str] | None = None,
) -> tuple[list[PlanResult], dict]:
    """
    Replay meter_readings history against multiple tariff plans.

    Returns (results sorted cheapest first, metadata dict).
    date_from/date_to are inclusive (UTC midnight boundaries).
    plan_keys defaults to all PLANS if None.
    """
    if plan_keys is None:
        plan_keys = list(PLANS.keys())

    unknown = [k for k in plan_keys if k not in PLANS]
    if unknown:
        raise ValueError(f"Unknown plan keys: {unknown}. Valid: {list(PLANS.keys())}")

    # Default to full available range when not specified
    date_from_dt = datetime(date_from.year, date_from.month, date_from.day) if date_from else datetime(2020, 1, 1)
    date_to_dt = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59) if date_to else datetime(2030, 1, 1)

    async with pool.acquire() as conn:
        rows = await conn.fetch(_FETCH_READINGS, household_id, date_from_dt, date_to_dt)

    if not rows:
        return [], {"error": "No meter readings found for the specified range"}

    df = pd.DataFrame([
        {
            "ts": pd.Timestamp(row["local_ts"]),
            "import_kwh": float(row["import_kwh"] or 0.0),
            "export_kwh": float(row["export_kwh"] or 0.0),
        }
        for row in rows
    ])

    days_analysed = max(1, (df["ts"].max() - df["ts"].min()).days + 1)
    total_import_kwh = round(float(df["import_kwh"].sum()), 3)
    total_export_kwh = round(float(df["export_kwh"].sum()), 3)

    meta = {
        "date_from": str(df["ts"].min().date()),
        "date_to": str(df["ts"].max().date()),
        "days_analysed": days_analysed,
        "total_import_kwh": total_import_kwh,
        "total_export_kwh": total_export_kwh,
        "readings_count": len(df),
    }

    results = []
    for key in plan_keys:
        plan = PLANS[key]
        result = _apply_plan(df, plan, days_analysed)
        results.append(result)

    results.sort(key=lambda r: r.net_cost_eur)
    return results, meta


def _apply_plan(df: pd.DataFrame, plan: TariffPlan, days_analysed: int) -> PlanResult:
    """Apply tariff plan to meter readings DataFrame. Returns PlanResult."""
    slots = SlotBreakdown()
    import_cost = 0.0
    monthly_free: dict[str, float] = {}   # month_key → free kWh used so far

    if plan.free_sat:
        # Track free kWh per month to enforce 100 kWh cap
        df = df.copy()
        df["year_month"] = df["ts"].dt.to_period("M")

        for _, row in df.iterrows():
            ts = row["ts"]
            kwh = row["import_kwh"]
            slot = plan.slot_name(ts)
            rate = plan.rate_for(ts)

            if slot == "free":
                ym = str(row["year_month"])
                monthly_free[ym] = monthly_free.get(ym, 0.0) + kwh
                if monthly_free[ym] <= MONTHLY_FREE_CAP_KWH:
                    slots.free_kwh += kwh
                    # rate is 0 — no cost
                else:
                    # Excess charged at day rate
                    excess = kwh
                    slots.free_cap_exceeded_kwh += excess
                    import_cost += excess * plan.day_rate
            elif slot == "peak":
                slots.peak_kwh += kwh
                import_cost += kwh * rate
            elif slot == "night":
                slots.night_kwh += kwh
                import_cost += kwh * rate
            else:
                slots.day_kwh += kwh
                import_cost += kwh * rate

        # DAN-157: count months where cap was hit (free usage exceeded 100 kWh)
        slots.free_cap_months_affected = sum(
            1 for v in monthly_free.values() if v > MONTHLY_FREE_CAP_KWH
        )
    else:
        for _, row in df.iterrows():
            ts = row["ts"]
            kwh = row["import_kwh"]
            slot = plan.slot_name(ts)
            rate = plan.rate_for(ts)
            if slot == "peak":
                slots.peak_kwh += kwh
            elif slot == "night":
                slots.night_kwh += kwh
            else:
                slots.day_kwh += kwh
            import_cost += kwh * rate

    export_credit = float(df["export_kwh"].sum()) * plan.export_rate
    standing = days_analysed * plan.standing_daily
    net = import_cost + standing - export_credit
    annualised = (net / days_analysed) * 365 if days_analysed > 0 else 0.0

    for attr in ("day_kwh", "night_kwh", "peak_kwh", "free_kwh", "free_cap_exceeded_kwh"):
        setattr(slots, attr, round(getattr(slots, attr), 3))

    # DAN-157: human-readable free-window cap impact note
    cap_note = ""
    if plan.free_sat and slots.free_cap_months_affected > 0:
        total_months = max(1, days_analysed // 30)
        avg_over = round(slots.free_cap_exceeded_kwh / slots.free_cap_months_affected, 1)
        cap_note = (
            f"BGE Saturday 100 kWh/month cap hit in {slots.free_cap_months_affected} of "
            f"~{total_months} months analysed (avg {avg_over} kWh over-cap/month, "
            f"charged at day rate {plan.day_rate:.4f} €/kWh)."
        )

    return PlanResult(
        plan_key=plan.key,
        plan_name=plan.name,
        supplier=plan.supplier,
        notes=plan.notes,
        product_url=plan.product_url,
        last_verified=plan.last_verified,
        days_analysed=days_analysed,
        total_import_kwh=round(float(df["import_kwh"].sum()), 3),
        total_export_kwh=round(float(df["export_kwh"].sum()), 3),
        import_cost_eur=round(import_cost, 2),
        export_credit_eur=round(export_credit, 2),
        standing_charge_eur=round(standing, 2),
        net_cost_eur=round(net, 2),
        annualised_cost_eur=round(annualised, 2),
        cap_impact_note=cap_note,
        slots=slots,
    )
