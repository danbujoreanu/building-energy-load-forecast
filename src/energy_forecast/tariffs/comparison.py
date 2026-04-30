"""
src/energy_forecast/tariffs/comparison.py
==========================================
Plan comparison engine — replay any Irish tariff against a household's actual
30-min meter_readings and rank by annual cost.

Usage:
    from energy_forecast.tariffs.comparison import compare_tariffs, load_readings_from_db

    rows = load_readings_from_db(conn, household_id)       # asyncpg records
    result = compare_tariffs(rows, current_tariff_key="bge_free_sat")
    print(result.ranked[0].name, result.ranked[0].annual_cost_eur)
"""
from __future__ import annotations

import asyncpg
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

import pandas as pd

from energy_forecast.tariffs.registry import TARIFFS, FreeWindow, Tariff


@dataclass
class TariffResult:
    key: str
    name: str
    supplier: str
    annual_cost_eur: float
    annual_standing_eur: float
    annual_usage_eur: float
    annual_export_credit_eur: float
    free_window_kwh: float          # actual kWh consumed in free window
    free_window_over_cap_kwh: float # kWh above monthly cap (charged at day rate)
    months_data: int                # how many months of data were used


@dataclass
class ComparisonResult:
    household_id: str
    months_data: int
    current_key: str
    current_cost_eur: float
    cheapest_key: str
    cheapest_cost_eur: float
    potential_saving_eur: float
    ranked: list[TariffResult]      # cheapest first


def _replay_tariff(
    df: pd.DataFrame,
    tariff: Tariff,
    discount: float = 1.0,
) -> TariffResult:
    """
    Replay tariff against df (columns: recorded_at, import_kwh, export_kwh).
    discount: multiply all usage rates (0.8 = 20% Affinity discount).
    """
    if df.empty:
        return TariffResult(
            key="", name=tariff.name, supplier=tariff.supplier,
            annual_cost_eur=0, annual_standing_eur=0, annual_usage_eur=0,
            annual_export_credit_eur=0, free_window_kwh=0,
            free_window_over_cap_kwh=0, months_data=0,
        )

    df = df.copy()
    df["import_kwh"] = df["import_kwh"].astype(float)
    df["export_kwh"] = df["export_kwh"].astype(float) if "export_kwh" in df.columns else 0.0
    df["ts"] = pd.to_datetime(df["recorded_at"], utc=True).dt.tz_convert("Europe/Dublin")
    df["month"] = df["ts"].dt.to_period("M")
    df["rate"] = df["ts"].apply(tariff.rate)

    # Handle free-window monthly cap
    free_cap = None
    if tariff.free_windows:
        # Use the first free window's cap
        caps = [fw.monthly_cap_kwh for fw in tariff.free_windows if fw.monthly_cap_kwh]
        free_cap = caps[0] if caps else None

    free_window_kwh = 0.0
    free_window_over_cap_kwh = 0.0
    usage_cost = 0.0

    if free_cap is not None:
        for month, group in df.groupby("month"):
            free_rows = group[group["rate"] == 0.0]
            non_free_rows = group[group["rate"] > 0.0]

            month_free_kwh = free_rows["import_kwh"].sum()
            free_window_kwh += month_free_kwh

            if month_free_kwh > free_cap:
                over_cap = month_free_kwh - free_cap
                free_window_over_cap_kwh += over_cap
                # Charge over-cap at day rate
                usage_cost += over_cap * tariff.day * discount

            usage_cost += (non_free_rows["import_kwh"] * non_free_rows["rate"] * discount).sum()
    else:
        usage_cost = (df["import_kwh"] * df["rate"] * discount).sum()

    # Export credit (no discount on export)
    export_credit = 0.0
    if tariff.export > 0 and "export_kwh" in df.columns:
        export_credit = (df["export_kwh"].fillna(0) * tariff.export).sum()

    # Standing charge: number of unique calendar days in dataset
    unique_days = df["ts"].dt.date.nunique()
    standing_cost = unique_days * tariff.standing_daily
    months_data = df["month"].nunique()

    # Annualise if we have < 12 months
    scale = 12.0 / months_data if months_data < 12 else 1.0

    return TariffResult(
        key="",
        name=tariff.name,
        supplier=tariff.supplier,
        annual_cost_eur=round((usage_cost + standing_cost - export_credit) * scale, 2),
        annual_standing_eur=round(standing_cost * scale, 2),
        annual_usage_eur=round(usage_cost * scale, 2),
        annual_export_credit_eur=round(export_credit * scale, 2),
        free_window_kwh=round(free_window_kwh * scale, 1),
        free_window_over_cap_kwh=round(free_window_over_cap_kwh * scale, 1),
        months_data=months_data,
    )


def compare_tariffs(
    rows: Sequence,
    current_tariff_key: str,
    household_id: str = "",
    discount: float = 1.0,
    tariff_keys: list[str] | None = None,
) -> ComparisonResult:
    """
    Replay all (or specified) tariffs against meter reading rows and rank by cost.

    rows: list of asyncpg.Record or dicts with keys: recorded_at, import_kwh, export_kwh
    current_tariff_key: key from TARIFFS registry (e.g. 'bge_free_sat')
    discount: usage-charge multiplier (0.8 for 20% discount, 1.0 for rack rate)
    tariff_keys: subset to compare; defaults to all TARIFFS
    """
    df = pd.DataFrame([dict(r) for r in rows])
    if df.empty:
        raise ValueError("No meter reading rows provided")

    keys = tariff_keys or list(TARIFFS.keys())
    results: list[TariffResult] = []

    for key in keys:
        tariff = TARIFFS[key]
        r = _replay_tariff(df, tariff, discount=discount)
        r = TariffResult(
            key=key,
            name=r.name, supplier=r.supplier,
            annual_cost_eur=r.annual_cost_eur,
            annual_standing_eur=r.annual_standing_eur,
            annual_usage_eur=r.annual_usage_eur,
            annual_export_credit_eur=r.annual_export_credit_eur,
            free_window_kwh=r.free_window_kwh,
            free_window_over_cap_kwh=r.free_window_over_cap_kwh,
            months_data=r.months_data,
        )
        results.append(r)

    results.sort(key=lambda r: r.annual_cost_eur)

    current = next((r for r in results if r.key == current_tariff_key), results[0])
    cheapest = results[0]

    return ComparisonResult(
        household_id=household_id,
        months_data=current.months_data,
        current_key=current_tariff_key,
        current_cost_eur=current.annual_cost_eur,
        cheapest_key=cheapest.key,
        cheapest_cost_eur=cheapest.annual_cost_eur,
        potential_saving_eur=round(current.annual_cost_eur - cheapest.annual_cost_eur, 2),
        ranked=results,
    )


_READINGS_QUERY = """
SELECT
    recorded_at,
    import_kwh,
    export_kwh
FROM meter_readings
WHERE household_id = $1
  AND recorded_at >= NOW() - INTERVAL '24 months'
ORDER BY recorded_at
"""


async def load_readings_from_db(pool, household_id: str) -> list[dict]:
    """Fetch last 24 months of 30-min readings for a household."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(_READINGS_QUERY, household_id)
    return [dict(r) for r in rows]
