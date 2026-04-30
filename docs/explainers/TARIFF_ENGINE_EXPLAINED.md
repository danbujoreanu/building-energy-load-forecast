# Tariff Engine — Complete Technical Walkthrough
*Part of the Explainers/ series. Local only — not tracked in git.*
*Covers: DAN-129, DAN-131, DAN-132, DAN-133, DAN-143*
*Last updated: 2026-04-30*

---

## What This Document Is

A deep technical walkthrough of everything Sparc does with electricity tariff rates — from the single source-of-truth rate table, to counterfactual plan comparisons, to real-time cost breakdown panels, to predicted tomorrow's bill. Written for an engineer joining the project who needs to understand why the tariff logic lives where it does and how the five DAN issues in this domain connect.

---

## Why Tariff Logic Deserves Its Own Module

Every Sparc feature that involves money touches tariff rates. The morning advisory needs the night rate to calculate the 07:00 boost saving. The day-ahead cost forecast applies per-slot rates to load predictions. The plan comparison replays two years of meter data against six tariff structures. The Grafana cost breakdown panel buckets every 30-min interval into a slot.

If rates are defined inline — in each script, each query, each advisory — they will diverge. The BGE day rate is `0.4034 €/kWh`. If that number appears in twelve places, the day a price change happens, eleven of them will be wrong.

The solution is one canonical file and one import:

```
src/energy_forecast/tariff.py
```

Everything that needs a rate imports from there. No other file contains a literal `0.4034`.

---

## The Rate Table — `src/energy_forecast/tariff.py`

### BGE Free Time Saturday structure

The household is on Bord Gáis Energy's Free Time Saturday plan with a 20% Affinity discount valid until 15 June 2026. The structure has four slots:

| Slot | Hours | Days | Rate (after 20% discount) |
|------|-------|------|--------------------------|
| **Night** | 23:00–08:00 | All | 23.72c/kWh |
| **Day** | 08:00–23:00 | All (excl. below) | 32.27c/kWh |
| **Peak** | 17:00–19:00 | Mon–Fri only | 39.42c/kWh |
| **Free** | 09:00–17:00 | Saturday only | 0c/kWh (capped at 100 kWh/month) |

**Export:** 18.5c/kWh (flat, no slot variation)  
**Standing charge:** 61.52c/day (not discounted)

### Critical detail: peak is weekday-only

The peak slot is Monday–Friday 17:00–19:00. **Saturday and Sunday at 17:00–19:00 are charged at the day rate, not peak.** This is the most common mistake when writing tariff logic from memory. The correct guard is:

```python
if dt.weekday() < 5 and 17 <= dt.hour < 19:
    return PEAK_RATE
```

`weekday()` returns 0 (Monday) through 6 (Sunday). `< 5` covers Monday–Friday. Without this guard, weekend evenings show up at peak rate in cost breakdowns, inflating the figure by ~25% on summer weekends.

### The `rate_for_slot()` function

```python
def rate_for_slot(slot: str) -> float:
    """€/kWh for a named slot. Slot names: 'night', 'day', 'peak', 'free'."""

def rate_slot(dt: datetime | pd.Timestamp) -> str:
    """Return slot name for a given datetime. Handles DST transparently."""
```

`rate_slot()` is timezone-aware. Pass it a `pd.Timestamp` with `tz="Europe/Dublin"` or a Python `datetime` with a Dublin tzinfo and it handles summer/winter transitions correctly. Passing a naive datetime or a UTC timestamp without conversion produces wrong results on DST boundary nights.

---

## DAN-129: Tariff Cost Breakdown Panel

**What it shows:** A stacked bar chart in the Household Intelligence Grafana dashboard showing daily electricity cost split by tariff slot. You can immediately see whether peak hours are the dominant cost driver on a given day.

**Where it lives:** Panel in `infra/grafana/provisioning/dashboards/household_intelligence.json`

**The SQL pattern:**

```sql
SELECT
  DATE(recorded_at AT TIME ZONE 'Europe/Dublin') AS day,
  ROUND(SUM(import_kwh) FILTER (
    WHERE EXTRACT(HOUR FROM recorded_at AT TIME ZONE 'Europe/Dublin') >= 23
       OR EXTRACT(HOUR FROM recorded_at AT TIME ZONE 'Europe/Dublin') < 8
  ) * 0.2372, 3) AS night_cost_eur,

  ROUND(SUM(import_kwh) FILTER (
    WHERE EXTRACT(DOW FROM recorded_at AT TIME ZONE 'Europe/Dublin') BETWEEN 1 AND 5
      AND EXTRACT(HOUR FROM recorded_at AT TIME ZONE 'Europe/Dublin') BETWEEN 17 AND 18
  ) * 0.3942, 3) AS peak_cost_eur,

  -- free Saturday: cost is 0 for first 100 kWh/month
  ...
FROM meter_readings
WHERE household_id = $household_id
  AND $__timeFilter(recorded_at)
GROUP BY 1
ORDER BY 1
```

**`EXTRACT(DOW ...)` vs `weekday()`:** PostgreSQL's `EXTRACT(DOW ...)` returns 0=Sunday, 1=Monday … 6=Saturday. To match the peak slot (Mon–Fri), use `BETWEEN 1 AND 5`. This is different from Python's `weekday()` which starts at 0=Monday. Don't cross-contaminate the two conventions.

**Why stacked bar instead of a time series:** The question being answered is "how does my daily cost break down by slot?" not "how does my instantaneous consumption vary?" A stacked bar makes the ratio immediately visible. A 30-minute spike in peak hours becomes a red sliver on a Wednesday bar — easy to see and act on.

---

## DAN-131: Plan Comparison Engine

**File:** `src/energy_forecast/api/plan_comparison.py`  
**Endpoint:** `POST /compare-plans`

### The design question: replay vs estimate

Two approaches exist for answering "would I save money on a different plan?"

1. **Estimate:** Take monthly kWh totals from the last bill and apply alternative rates.
2. **Replay:** Take every 30-minute interval from `meter_readings` and apply each plan's rate to the actual consumption at that exact timestamp.

Sparc uses replay. Estimation misses everything that matters: the fact that 45% of consumption happens on Saturday (free under BGE FTS), that peak hours are consistently high on Wednesday evenings, that the household's load profile is not a flat average. Replay is expensive (iterates every row) but produces exact counterfactual bills.

### The `TariffPlan` dataclass

```python
@dataclass
class TariffPlan:
    key: str
    name: str
    supplier: str
    day_rate: float
    night_rate: float
    peak_rate: float
    free_sat: bool
    export_rate: float
    standing_daily: float
    notes: str = ""

    def rate_for(self, dt: pd.Timestamp) -> float:
        ...
    def slot_name(self, dt: pd.Timestamp) -> str:
        ...
```

The `rate_for()` method encapsulates slot logic per-plan. Some plans have no peak slot (SSE One Rate is completely flat: every hour is 38.5c). Some plans have no free Saturday. The dataclass makes this explicit — `free_sat: bool` is a first-class field, not an implicit assumption in a CASE statement.

### The six plans

| Key | Name | Notes |
|-----|------|-------|
| `BGE_FTS_AFFINITY` | BGE Free Time Saturday (20% Affinity) | **Current plan.** Exact rates. |
| `BGE_FTS_STANDARD` | BGE Free Time Saturday (no discount) | Post-June-15 scenario. Exact rates. |
| `BGE_STANDARD_NOSAT` | BGE Standard (no free Saturday) | Quantifies Saturday value exactly. |
| `ENERGIA_NIGHT_BOOST` | Energia Night Boost | Approx Q1 2026. Verify before use. |
| `SSE_ONE_RATE` | SSE Airtricity One Rate | Flat rate. No TOU benefit at all. |
| `ELECTRIC_IRELAND_SMART` | Electric Ireland Smart TOU | Approx Q1 2026. Verify before use. |

`BGE_STANDARD_NOSAT` is the most analytically useful plan in this set — it answers "how much is the Free Saturday window actually worth to me?" by holding all other variables constant and removing only the Saturday benefit. The answer (from the Oct 2023–Oct 2025 replay) is €178.65/year in unused allowance.

### The monthly free cap

BGE Free Time Saturday gives up to 100 kWh/month at 0c. This is a hard cap — usage above 100 kWh in the Sat 09:00–17:00 window in a given calendar month is charged at the day rate.

The `_apply_plan()` function tracks this per calendar month using a `dict[str, float]` keyed on `"YYYY-MM"`:

```python
monthly_free: dict[str, float] = {}
...
ym = row["ts"].strftime("%Y-%m")
monthly_free[ym] = monthly_free.get(ym, 0.0) + kwh
if monthly_free[ym] <= MONTHLY_FREE_CAP_KWH:
    slots.free_kwh += kwh
    # rate is 0 — no cost added
else:
    slots.free_cap_exceeded_kwh += kwh
    import_cost += kwh * plan.day_rate
```

**Why this matters in practice:** The household uses ~54% of its monthly free Saturday allowance on average. That means for 46% of available free kWh each month, there is no cap risk. But on bank holiday weekends or during a week with guests, Saturday usage could spike past 100 kWh. The cap logic prevents over-crediting those months.

### The `compare_plans()` async function

```python
async def compare_plans(
    pool,
    household_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
    plan_keys: list[str] | None = None,
) -> tuple[list[PlanResult], dict]:
```

Returns `PlanResult` objects sorted cheapest first by `net_cost_eur`. Each result includes:
- `import_cost_eur`, `export_credit_eur`, `standing_charge_eur`, `net_cost_eur`
- `annualised_cost_eur` — net cost scaled to 365 days (useful when comparing periods of different lengths)
- `slots: SlotBreakdown` — kWh by slot category (day/night/peak/free/excess)

### Rate accuracy caveat

BGE rates in `PLANS["BGE_FTS_AFFINITY"]` and `PLANS["BGE_FTS_STANDARD"]` are **exact** — verified against the June 2026 bill. Other suppliers (`ENERGIA_NIGHT_BOOST`, `SSE_ONE_RATE`, `ELECTRIC_IRELAND_SMART`) are **approximate Q1 2026 figures**. The `notes` field on each plan states this explicitly. Before making a contract switching decision, verify rates at the supplier's website. The comparison engine is a starting point, not a contract offer.

---

## DAN-132: Free Saturday Utilisation Panel

**What it shows:** Monthly kWh used in the Sat 09:00–17:00 free window vs the 100 kWh cap, plus estimated € value of unused allowance.

**The key insight it surfaces:** If the household is consistently at 54% utilisation (as of Oct 2025), there are ~46 kWh/month × 32.27c = **~€14.80/month of free electricity not being claimed**. The panel makes this visible and actionable — "do more laundry on Saturday morning."

**SQL pattern:**
```sql
SELECT
  DATE_TRUNC('month', recorded_at AT TIME ZONE 'Europe/Dublin') AS month,
  ROUND(SUM(import_kwh) FILTER (
    WHERE EXTRACT(DOW ...) = 6           -- Saturday
      AND EXTRACT(HOUR ...) BETWEEN 9 AND 16
  )::NUMERIC, 2) AS free_sat_kwh,
  100.0 AS cap_kwh,
  ROUND((100.0 - SUM(...)) * 0.3227, 2) AS eur_left_on_table
FROM meter_readings
WHERE household_id = $household_id
GROUP BY 1
ORDER BY 1
```

`EXTRACT(DOW ...) = 6` in PostgreSQL is Saturday (0=Sunday, 6=Saturday). The `FILTER` clause is PostgreSQL's conditional aggregate — cleaner than a `CASE WHEN ... THEN kwh ELSE 0 END` pattern.

---

## DAN-133: Export Revenue Tracker

**What it shows:** Monthly solar export revenue at 18.5c/kWh.

**Where the data comes from:** `meter_readings.export_kwh` — populated by the `/upload` endpoint from ESB HDF CSV files. This is the **net export** as measured by the ESB smart meter: solar generation that exceeded household consumption + Eddi diversion and was pushed to the grid.

**The BTM equation:**
```
Total solar generation = ESB export_kwh + Eddi_diversion_kwh + House self-consumption_kwh
```

The export revenue panel shows only the ESB export portion. Eddi diversion (free hot water) is separately visible in the MyEnergi panels. House self-consumption (solar powering appliances before reaching the meter) is invisible without a Harvi CT clamp.

**SQL:**
```sql
SELECT
  DATE_TRUNC('month', recorded_at AT TIME ZONE 'Europe/Dublin') AS month,
  ROUND(SUM(export_kwh)::NUMERIC, 2) AS export_kwh,
  ROUND(SUM(export_kwh) * 0.185, 2) AS export_revenue_eur
FROM meter_readings
WHERE household_id = $household_id
  AND export_kwh IS NOT NULL
  AND $__timeFilter(recorded_at)
GROUP BY 1
ORDER BY 1
```

**Annual figure for context:** ~454 kWh export × 18.5c = **~€84/year** in export revenue. This understates total solar value because it excludes Eddi diversion (~€120/year at night rate) and house self-consumption (~€30/year estimated).

---

## DAN-143: Day-Ahead Cost Forecast

**What it adds:** The morning advisory Pushover message now includes a line like:
```
Forecast cost tomorrow: ~€2.40 (incl. standing charge).
```

**How it works:**

1. At 08:00 (when the morning advisory runs), the `_compute_tomorrow_cost()` helper in `deployment/app.py` is called.
2. It fetches tomorrow's P50 load predictions from the `predictions` table (written at 16:00 by the APScheduler job).
3. For each prediction row (one per hour), it applies `rate_for_slot(hour_start)` from `tariff.py`.
4. It sums the hourly cost and adds `standing_daily` (61.52c).
5. Returns a `float | None` — `None` if no predictions exist for tomorrow yet.

```python
async def _compute_tomorrow_cost(pool, household_id: str, target_date: date) -> float | None:
    rows = await pool.fetch(
        "SELECT forecast_hour, p50 FROM predictions "
        "WHERE household_id = $1 AND forecast_date = $2 ORDER BY forecast_hour",
        household_id, target_date
    )
    if not rows:
        return None
    cost = sum(float(r["p50"]) * rate_for_slot(_ts(target_date, r["forecast_hour"])) for r in rows)
    cost += STANDING_DAILY
    return round(cost, 2)
```

**The dependency chain:** This feature only works when the 16:00 inference job has run for tomorrow's date. If the scheduler missed a run (server restart, etc.), `_compute_tomorrow_cost()` returns `None` and the cost line is silently omitted from the Pushover message. There is no error — just no cost line. The `None` path is the intended graceful degradation.

**Accuracy expectations:** This is a rough forecast, not a precise bill. Sources of error:
- Load prediction MAE ~0.171 kWh/hour → ~±€0.18/day at day rate
- Rate changes not yet reflected in tariff.py
- Export not subtracted (morning advisory doesn't know tomorrow's generation)

The `~€` prefix in the message is intentional — "approximately" is honest for a day-ahead estimate.

---

## How the Pieces Fit Together

```
tariff.py                ← single source of truth for all rates
    │
    ├── plan_comparison.py    ← DAN-131: six TariffPlan objects import from here
    ├── app.py                ← DAN-143: _compute_tomorrow_cost() imports rate_for_slot()
    └── Grafana SQL           ← DAN-129, 132, 133: inline SQL uses hardcoded literals
                                 (acceptable — Grafana can't import Python modules)
```

The one exception to "always import from tariff.py" is Grafana SQL. Grafana executes raw PostgreSQL — it cannot import Python. The SQL panels hardcode rate literals (e.g., `* 0.2372`). This is an accepted exception, documented in the panel descriptions. When rates change, update both `tariff.py` and the affected Grafana panel SQL. The `docs/team_meetings/` action log should record rate changes so panel SQL doesn't get missed.

---

## When Rates Change (June 15, 2026)

The BGE Affinity discount expires on 15 June 2026. On that date:

1. Update `tariff.py`: `DAY_RATE = 0.4034` (from `0.4034 * 0.80`)
2. Update `PLANS["BGE_FTS_AFFINITY"]` in `plan_comparison.py` — or retire it and promote `BGE_FTS_STANDARD`
3. Update the Grafana tariff breakdown panel SQL literals
4. Run `scripts/score_home_plan.py` against fresh data to get the new score
5. Re-run `compare_plans()` — the annualised cost jump will be visible in the API response

The annualised cost delta from losing the 20% discount on the current load profile is approximately **€380–420/year** (computed from Oct 2023–Oct 2025 replay: €1,847/year with discount vs ~€2,230/year without).

---

## Troubleshooting

### `/compare-plans` returns empty results

`compare_plans()` returns `([], {"error": "No meter readings found..."})` when:
- `household_id` is not in the `households` table
- `date_from`/`date_to` range has no `meter_readings` rows
- The ESB CSV has not been uploaded yet

Check: `SELECT COUNT(*) FROM meter_readings WHERE household_id = '...'`

### Day-ahead cost is always `None`

The 16:00 inference job has not written predictions for tomorrow. Check:
```sql
SELECT forecast_date, COUNT(*) FROM predictions
WHERE household_id = '...'
GROUP BY forecast_date ORDER BY forecast_date DESC LIMIT 5;
```
If tomorrow's date is missing, the APScheduler job either hasn't run yet (it's before 16:00) or it failed silently. Check the app logs for `[scheduler]` entries.

### Free Saturday cap exceeded kWh is very high

This indicates the household is consistently hitting the 100 kWh/month cap. The `slots.free_cap_exceeded_kwh` field in `PlanResult` shows the excess. If this is regularly > 10 kWh/month, the BGE FTS plan may be less optimal than it appears — the free allowance is saturated.

---

## Decision Log

| Decision | What we chose | Why | Alternatives rejected |
|----------|--------------|-----|----------------------|
| Single source of truth for rates | `src/energy_forecast/tariff.py` | Rate changes propagate to all consumers in one edit. Previously rates were inline in each script. | Inline literals per file — drifts on price changes |
| `DO NOTHING` on upsert conflict | `ON CONFLICT ... DO NOTHING` | ESB readings are final — re-uploading same file should be a no-op, not an overwrite | `DO UPDATE` — would silently overwrite if same row is uploaded twice with different value |
| Replay vs estimate for plan comparison | Full interval replay from `meter_readings` | A household's load profile is not a flat average. Saturday free slot utilisation, peak avoidance, and seasonal variation are only visible in the actual 30-min data. | Monthly kWh estimate — misses the Saturday cap, peaks, and seasonal effects |
| Monthly free cap tracking via `dict[str, float]` | `monthly_free["2024-03"] += kwh` per row iteration | The 100 kWh/month BGE cap resets on calendar month boundaries. A running total per month is the correct model. | Single cumulative counter — doesn't reset on month boundary, overcounts free kWh in Feb if cap was hit in Jan |
| Median not mean for panel factor calibration | `np.median(computed_pf)` | A few overcast days with partial panel shading produce outlier low values. Median is robust to those. | Mean — pulled down by occasional near-zero GHI days that pass the 0.5 kWh/m² filter |
| `~€` prefix on day-ahead cost message | Literal tilde prefix in Pushover message | The forecast has ~±€0.18 MAE-derived uncertainty. "Approximately" is honest; precise figures would imply accuracy we don't have. | No qualifier — would mislead users into trusting a rough estimate as a precise bill prediction |

## References

- `src/energy_forecast/tariff.py` — canonical rate table
- `src/energy_forecast/api/plan_comparison.py` — DAN-131 implementation
- `deployment/app.py` — `/compare-plans` endpoint and `_compute_tomorrow_cost()` (DAN-143)
- `infra/grafana/provisioning/dashboards/household_intelligence.json` — DAN-129, 132, 133 panels
- `scripts/score_home_plan.py` — home plan scoring (62/100 as of Oct 2025)
- `docs/engineering/SOLAR_DATA_PIPELINE.md` — solar export data lineage
- BGE tariff page (verify rates): `bordgaisenergy.ie/home/electricity/tariffs`
