# Solar Advisory — Complete Technical Walkthrough
*Part of the Explainers/ series. Local only — not tracked in git.*
*Covers: DAN-141, DAN-142*
*Last updated: 2026-05-06*

---

## What This Document Is

A deep technical walkthrough of the morning solar advisory system — from raw GHI forecast through panel output estimation to the Pushover message sent at 08:00. Covers the Eddi diversion model (DAN-141) and the panel factor calibration pipeline (DAN-142). Written for an engineer who needs to modify the advisory logic, recalibrate the panel factor, or understand why the numbers in the Pushover message look the way they do.

---

## The Problem Being Solved

The household has a south-facing solar array and a myenergi Eddi hot-water diverter. The Eddi is scheduled to run a 30-minute grid boost at 07:00 (end of night rate: 23.72c/kWh). On sunny days, solar will fully heat the tank by midday anyway — the 07:00 grid boost costs ~13c for no benefit. On cloudy days, skipping it means cold showers.

The advisory answers: **should you disable the 07:00 boost today?** Pushed to your phone at 08:00 every morning, automatically, without you having to check a weather app or think about it.

---

## Architecture Overview

```
20:00 APScheduler job in scheduler.py   ← fires the EVENING BEFORE
    │
    ├── 1. _get_seasonal_panel_factor(pool, hid)   [scheduler.py]
    │       │
    │       └── households.panel_factor_seasonal JSONB keyed by "YYYY-MM"
    │           Falls back to 1.6 if month not yet populated (DAN-160)
    │
    ├── 2. build_advisory(target_date=tomorrow, panel_factor=...)  [morning_advisory.py]
    │       │
    │       ├── _fetch_ghi(target_date)             [Open-Meteo forecast API]
    │       │       Returns: (ghi_kwh_m2, peak_sun_hours)
    │       │
    │       ├── est_solar = ghi * panel_factor       [seasonal, not constant]
    │       │
    │       ├── expected_diversion = min(est_solar, TANK_DAILY_KWH)   [DAN-141]
    │       │
    │       └── recommendation: SKIP_BOOST | PARTIAL | KEEP_BOOST
    │
    ├── 3. _compute_tomorrow_cost(pool, hid, tomorrow)  [DAN-143]
    │
    ├── 4. log_advisory(pool, household_id, advisory)   → advisory_log table
    │
    └── 5. send_pushover(advisory)
```

**Why 20:00?** The advisory covers *tomorrow*. Sending it the evening before gives you time to act on a SKIP_BOOST before you go to sleep — e.g., pause the 07:00 Eddi schedule via the myenergi app. Open-Meteo's day-ahead forecast is stable by 18:00–20:00 and does not change materially overnight for the next day.

---

## Step 1: Fetching GHI

`_fetch_ghi(target_date)` calls the Open-Meteo free forecast API:

```
GET https://api.open-meteo.com/v1/forecast
    ?latitude=53.38&longitude=-6.59
    &hourly=shortwave_radiation
    &forecast_days=2
    &timezone=Europe%2FDublin
```

**`forecast_days=2`** is required even when asking about tomorrow. Open-Meteo's free tier returns only today + tomorrow in a single array. The function filters to only the 24 hours that start with `str(target_date)` (format: `"2026-05-01"`).

**`shortwave_radiation`** is returned in W/m² at hourly resolution. To convert to kWh/m²:
```python
total_kwh_m2 = sum(v / 1000.0 for _, v in pairs)
```
Each hourly value represents one hour, so W/m² ÷ 1000 = kWh/m² for that hour. Sum all 24 hours for daily total GHI.

**`peak_sun_hours`** is the count of hours where GHI > 200 W/m². This threshold is the conventional definition of "productive" solar irradiance — panels produce meaningful output above 200 W/m² but operate at severely reduced efficiency below it. A peak_sun_hours count of 5 means the panels will be running near rated output for 5 hours.

**Why not use `start_date` + `end_date`?** The Open-Meteo API treats `start_date`/`end_date` as a historical/archive mode that conflicts with `forecast_days`. Mixing them causes the API to return empty or malformed data. Always use `forecast_days=2` for day-ahead forecasts. See `HOW_WE_WORK.md` § Token Efficiency Protocol for this known gotcha.

---

## Step 2: Panel Factor — Converting GHI to kWh Output

```python
PANEL_FACTOR = 1.6  # kWh solar per kWh/m² GHI
```

This constant converts the raw solar resource (GHI, a physics measurement of sunlight hitting a flat surface) into actual panel electricity output.

### What PANEL_FACTOR actually encodes

```
panel_output_kwh = GHI_kwh_m2 × panel_area_m2 × panel_efficiency × shading_factor × ...
```

All those physical parameters collapse into a single empirical constant. Rather than modelling each factor separately (panel area, efficiency, orientation, shading), PANEL_FACTOR is derived from observed data: how many kWh does this specific installation produce per kWh/m² of measured GHI?

### Why 1.6 specifically

The calibration process (DAN-142) produces a lower bound from observed data:

```
panel_factor_obs = (ESB_export_kwh + Eddi_diversion_kwh) / GHI_actual_kwh_m2
```

This is a **lower bound** because it excludes house self-consumption (solar powering appliances before reaching the ESB meter or Eddi). If the array generates 10 kWh and the house uses 1 kWh directly, ESB sees 9 kWh export and Eddi sees (say) 2 kWh — the formula gives 11/GHI, not 10/GHI.

The observed lower bound from available data is ~1.418. A +10% uplift is applied to account for estimated self-consumption:

```
PANEL_FACTOR = 1.418 × 1.10 = 1.56 → rounded to 1.6
```

Once a Harvi CT clamp is installed (measures total array output directly), self-consumption becomes measurable and the uplift is no longer needed. Use `calibrate_panel_factor.py --no-uplift` at that point.

---

## DAN-141: Eddi Diversion Estimate

Previously, the advisory only said "solar will fill the tank" or "solar will warm but may not fill." DAN-141 adds a quantified diversion estimate:

```
Expected solar diversion: ~3.2 kWh (of 3.5 kWh needed).
```

### The model

```python
TANK_DAILY_KWH = 3.5   # kWh needed to heat 150L tank from cold to 60°C
BOOST_KWH      = 0.55  # kWh consumed by 07:00 + 30-min grid boost

expected_diversion = round(min(est_solar, TANK_DAILY_KWH), 1)
tank_met = expected_diversion >= TANK_DAILY_KWH * 0.9   # within 10% = "met"
```

`min(est_solar, TANK_DAILY_KWH)` is the diversion cap. The Eddi won't divert more than the tank can absorb. If `est_solar = 8.0 kWh` and the tank needs 3.5 kWh, the Eddi will divert 3.5 kWh and surplus solar goes to export. The advisory shows `~3.5 kWh (tank fully met ✅)` rather than `~8.0 kWh`.

**`tank_met = diversion >= 3.5 * 0.9 = 3.15 kWh`:** The 10% tolerance accounts for model uncertainty. If the forecast says 3.2 kWh diversion, we consider the tank "met" rather than showing "of 3.5 kWh needed" which would be misleading given the precision of the estimate.

### What this enables in the message

**SKIP_BOOST (sunny day):**
```
5h productive sun (GHI 5.2 kWh/m², ~8 kWh panel output).
Expected solar diversion: ~3.5 kWh (tank fully met ✅).
Solar will fill the tank by midday — 07:00 grid boost not needed.
Consider skipping → save ~13c (0.55 kWh × 23.72c night rate).
```

**PARTIAL (mixed day):**
```
3h sun forecast (GHI 2.1 kWh/m², ~3 kWh panel output).
Expected solar diversion: ~3.0 kWh (of 3.5 kWh needed).
Solar will warm but may not fully heat tank — 07:00 boost is the safe call.
```

**KEEP_BOOST (cloudy):**
```
Only 1h productive sun (GHI 0.8 kWh/m², ~1 kWh panel output).
Expected solar diversion: ~1.0 kWh (of 3.5 kWh needed).
Insufficient solar — 07:00 grid boost needed. No action required.
```

### The decision thresholds

```python
SKIP_BOOST_THRESHOLD = 5   # peak_sun_hours ≥ 5 → SKIP_BOOST
KEEP_BOOST_THRESHOLD = 2   # peak_sun_hours < 2 → KEEP_BOOST
                           # 2–4 → PARTIAL
```

These are conservative by design. The cost of a wrong SKIP_BOOST is a cold shower. The cost of a wrong KEEP_BOOST is 13c wasted. The asymmetric downside justifies a high threshold for skipping. Summer Irish days typically see 6–8 peak sun hours; cloudy winter days 0–1.

---

## DAN-142: Panel Factor Auto-Calibration

**Script:** `scripts/calibrate_panel_factor.py`

### Why calibration needs a script

PANEL_FACTOR should not be a number you guess once and forget. As seasonal data accumulates, as the panels age (efficiency degrades ~0.5%/year), and once a Harvi CT clamp is installed, the optimal value changes. The calibration script re-derives PANEL_FACTOR from real observations and tells you exactly what to set it to.

### Data requirements

The script queries `solar_actuals` for rows where all three of these are populated:
- `export_kwh` — from ESB CSV upload (currently NULL for all rows — see data gap below)
- `eddi_kwh` — from myenergi nightly backfill (populated)
- `ghi_actual` — from Open-Meteo archive (populated)

**Minimum quality filter:** `ghi_actual > 0.5`. Near-zero GHI days (deep winter, overcast) produce division-by-near-zero instability in the panel factor ratio and should be excluded.

### The computation

```python
computed_pf = (exports + eddis) / ghis   # per-day observed panel factor

median_pf   = float(np.median(computed_pf))
recommended = round(median_pf * (1 + SELF_CONSUMPTION_UPLIFT), 4)
```

Median is used instead of mean because a few days with partial panel shading (e.g., snow, leaves, scaffolding) or data gaps produce outlier low values that would drag the mean down. Median is robust to those.

### Reading the output

```
============================
PANEL FACTOR CALIBRATION REPORT
============================
  Qualifying days analysed : 47
  Date range               : 2026-02-15 → 2026-04-22
  Total export kWh         : 187.3
  Total Eddi kWh           : 52.4
  Total GHI kWh/m²         : 167.8

  Observed panel factor:
    median                 : 1.4183
    mean                   : 1.3956
    P25–P75                : 1.1802 – 1.6441

  Self-consumption uplift  : +10%  (no Harvi CT installed)
  Recommended PANEL_FACTOR : 1.5601

  Lowest panel-factor days (cloud cover / partial export):
    2026-02-18  export=0.12  eddi=0.44  GHI=0.63  pf=0.8889
    ...
  Highest panel-factor days (peak summer output):
    2026-04-17  export=4.81  eddi=3.50  GHI=5.28  pf=1.5739
    ...
```

The P25–P75 spread (1.18–1.64) shows natural day-to-day variation. The median (1.42) is the right central estimate. The lowest days are likely overcast days where GHI was just above the 0.5 kWh/m² filter — not enough sun for good panel efficiency.

### Applying the update

The script prints:
```
  To apply:
    Edit deployment/morning_advisory.py:
    PANEL_FACTOR = 1.5601
```

It does not auto-apply. This is intentional — a regression of even 0.1 in PANEL_FACTOR changes the advisory's recommendation for borderline days. The engineer should review the report, check the P25–P75 spread, verify the date range is representative, and then apply manually.

### The data gap: why `solar_actuals.export_kwh` is NULL

As of 2026-04-30, the calibration script will report "No solar_actuals rows with all three fields populated" because `solar_actuals.export_kwh` is NULL for all 848 rows. Here is why:

**The upload path:**
```
/upload endpoint → meter_store.py → meter_readings (✅ populated)
```

**What's missing:**
```
meter_readings.export_kwh → [needs aggregation job] → solar_actuals.export_kwh
```

The `/upload` endpoint writes to `meter_readings` at 30-min resolution. `solar_actuals` needs a **daily aggregation** of that data: `SUM(export_kwh) WHERE DATE(...) = solar_date`. This aggregation job does not yet exist. It needs to be added to the APScheduler (or as a nightly SQL trigger) that runs after each ESB CSV upload. Until this is implemented, the calibration script and the panel factor Grafana panels will remain blank.

**Workaround until the job is built:** After uploading an ESB CSV, manually run:
```sql
INSERT INTO solar_actuals (solar_date, export_kwh)
SELECT
  DATE(recorded_at AT TIME ZONE 'Europe/Dublin') AS solar_date,
  ROUND(SUM(export_kwh)::NUMERIC, 3) AS export_kwh
FROM meter_readings
WHERE household_id = '...'
  AND export_kwh IS NOT NULL
GROUP BY 1
ON CONFLICT (solar_date) DO UPDATE SET export_kwh = EXCLUDED.export_kwh;
```

---

## The `SolarAdvisory` Dataclass

```python
@dataclass
class SolarAdvisory:
    target_date: date
    ghi_forecast_kwh_m2: float
    peak_sun_hours: int
    estimated_solar_kwh: float
    expected_diversion_kwh: float    # DAN-141: min(estimated_solar, TANK_DAILY_KWH)
    recommendation: str              # "SKIP_BOOST" | "PARTIAL" | "KEEP_BOOST"
    pushover_title: str
    pushover_message: str
    issued_at: datetime
    daily_cost_eur: float | None     # DAN-143: predicted € cost for target_date
```

All computed fields are retained in the dataclass rather than only the final string. This makes the advisory loggable and testable — `advisory.peak_sun_hours`, `advisory.expected_diversion_kwh`, and `advisory.recommendation` can be asserted in unit tests independently of the message formatting.

---

## Pushover Priority Mapping

```python
priority_map = {"SKIP_BOOST": 0, "PARTIAL": -1, "KEEP_BOOST": -2}
```

Pushover priority levels:
- `-2` (Lowest): delivered silently, no sound. KEEP_BOOST = no action needed. Silent delivery at 08:00.
- `-1` (Low): delivered quietly. PARTIAL = informational. You might want to consider keeping the boost.
- `0` (Normal): standard notification sound. SKIP_BOOST = actionable — you need to do something (manually pause the Eddi boost) to capture the saving.

The inversion — higher priority for SKIP_BOOST, lower for KEEP_BOOST — is deliberate. KEEP_BOOST is the default state (do nothing). Only SKIP_BOOST requires an action, so it warrants a proper notification.

---

## Testing Without Live API Calls

To test the advisory logic without hitting Open-Meteo:

```python
from deployment.morning_advisory import build_advisory, SolarAdvisory
from unittest.mock import patch

with patch("deployment.morning_advisory._fetch_ghi", return_value=(6.2, 7)):
    advisory = build_advisory(target_date=date(2026, 6, 15))

assert advisory.recommendation == "SKIP_BOOST"
assert advisory.expected_diversion_kwh == 3.5    # min(6.2*1.6=9.9, 3.5)
```

---

## Seasonal Behaviour

Seasonality affects the advisory through two independent channels. Both matter.

### Channel 1: GHI input (automatic)

The raw irradiance changes dramatically across the year at 53.38°N:

| Season | Typical GHI (kWh/m²/day) | Peak sun hours | Most common advisory |
|--------|--------------------------|----------------|---------------------|
| Winter (Dec–Feb) | 0.2–1.5 | 0–1 | KEEP_BOOST almost always |
| Spring (Mar–May) | 1.5–5.0 | 2–6 | Mix of PARTIAL and SKIP_BOOST |
| Summer (Jun–Aug) | 4.0–7.0 | 5–9 | SKIP_BOOST most days |
| Autumn (Sep–Nov) | 1.0–4.0 | 1–5 | Transitions across all three |

Open-Meteo captures this automatically — no code changes needed. Even if `PANEL_FACTOR` were fixed at 1.6 forever, the advisory would give KEEP_BOOST in December and SKIP_BOOST in July simply because GHI varies 10×.

### Channel 2: `panel_factor_seasonal` — calibrated monthly conversion (DAN-160)

The fixed `PANEL_FACTOR = 1.6` is an annual median. In reality, panel conversion efficiency shifts with season for physical reasons:

- **Winter**: lower irradiance, lower panel temperature → panels operate *more* efficiently (silicon PV has a negative temperature coefficient ~−0.4%/°C) but real-world output is still low because GHI is low.
- **Summer**: high irradiance, but panels run hot (35–50°C above ambient) → efficiency penalty of 4–8% vs nameplate at 25°C. Offset by much longer days.
- **Spring/Autumn**: closest to rated efficiency — good balance of irradiance and temperature.

The `panel_factor_seasonal` JSONB column on `households` stores a per-month empirical factor derived from actual observations:

```json
{
  "2026-01": 1.41,
  "2026-02": 1.45,
  "2026-03": 1.55,
  "2026-04": 1.62,
  "2026-05": 1.68,
  ...
}
```

**How it's populated:** The `_recompute_panel_factor_seasonal` job (APScheduler 23:45, `scheduler.py`) queries `solar_actuals` for all months with ≥ 10 days of clean data and computes:

```python
monthly_pf[month] = median((export_kwh + eddi_kwh) / ghi_actual)  # per-day, grouped by month
```

**How it's used:** At 20:00 each evening, `_get_seasonal_panel_factor(pool, hid)` reads the JSONB for the **current** month (key = `datetime.now(Dublin).strftime("%Y-%m")`). This is passed directly to `build_advisory()` as `panel_factor`. If the month has no data yet (winter gap, first few months of operation), it falls back to 1.6.

**Practical effect:** In a month where the observed panel factor is 1.75 (a clear summer month), `est_solar = GHI × 1.75` is 9% higher than with the 1.6 fallback — which shifts borderline PARTIAL days to SKIP_BOOST. In a month where the observed factor is 1.42 (spring, lots of cloud), the advisory is appropriately conservative.

**Current status:** `panel_factor_seasonal` is NULL for all households. The backfill (running now, 2023-01-20 → present) will populate `solar_actuals.eddi_kwh`. Once `export_kwh` is also populated (via ESB CSV → `_sync_solar_actuals()`), `_recompute_panel_factor_seasonal` will start computing monthly averages. Until then, the advisory uses the 1.6 fallback.

**To verify once data accumulates:**
```sql
SELECT panel_factor_seasonal FROM households WHERE id = '<your-household-id>';
-- Should return a JSON object with monthly keys once ≥10 qualifying days exist
```

---

## Where Recommendations Live

There are two separate recommendation tables. They serve different purposes and must not be confused:

| Table | Written by | Contents | Used by |
|-------|-----------|---------|---------|
| `advisory_log` | `log_advisory()` (meter_store.py) at 20:00 | Solar advisory per household per date: GHI, est_solar, peak_sun_hours, expected_diversion_kwh, recommendation | Solar Pipeline Grafana panels 25–27; DAN-144 forecast-vs-actual chart |
| `recommendations` | `insert_lp_recommendations()` (db_repository.py) at 14:30 | LP thermal dispatch: 24 hourly HEAT_NOW/DEFER_HEATING actions with price and reasoning | LP Dispatch Grafana panels (Household Intelligence dashboard) |

Both tables use `household_id` as a foreign key — this is the critical JOIN that makes everything work. See the next section on why TimescaleDB not InfluxDB.

### advisory_log schema (key columns)

```sql
household_id        UUID REFERENCES households(id)
advisory_date       DATE                              -- the date being advised (= tomorrow at issue time)
recommendation      TEXT                              -- 'SKIP_BOOST' | 'PARTIAL' | 'KEEP_BOOST'
ghi_forecast        NUMERIC(6,3)                      -- kWh/m²
peak_sun_hours      INTEGER
estimated_solar_kwh NUMERIC(6,2)
expected_diversion_kwh NUMERIC(6,2)
issued_at           TIMESTAMPTZ                       -- when the advisory was issued
UNIQUE (household_id, advisory_date)                  -- upsert-safe
```

### Grafana panels (Solar Data Pipeline dashboard)

After the 20:00 advisory runs, three stat panels at the bottom of the Solar Data Pipeline dashboard populate:

- **Panel 25**: Boost recommendation with colour (green/yellow/red)
- **Panel 26**: Estimated solar kWh + expected hot-water diversion kWh
- **Panel 27**: GHI forecast (kWh/m²) + peak sun hours

All three query `advisory_log WHERE advisory_date = CURRENT_DATE + 1`.

The historical `advisory_date vs actual_eddi_kwh` comparison (panel 20, "Eddi Solar Diversion — Forecast vs Actual") JOINs `advisory_log` to `solar_actuals` — this is a SQL JOIN that InfluxDB cannot express. See next section.

---

## Why TimescaleDB Not InfluxDB — The Recommendations JOIN Constraint

The recommendations, advisory, meter readings, and predictions all live in the same PostgreSQL database. This enables queries like:

```sql
-- Was the SKIP_BOOST recommendation correct? Compare forecast diversion vs actual Eddi diversion.
SELECT
  al.advisory_date,
  al.recommendation,
  al.expected_diversion_kwh   AS forecast_diversion,
  sa.eddi_kwh                 AS actual_eddi_kwh,
  sa.ghi_actual               AS actual_ghi,
  al.ghi_forecast             AS forecast_ghi
FROM advisory_log al
JOIN solar_actuals sa ON sa.solar_date = al.advisory_date
WHERE al.household_id = $1
  AND al.advisory_date >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY al.advisory_date DESC;
```

Or from the LP dispatch side:
```sql
-- Did the HEAT_NOW recommendation coincide with actual cheap overnight imports?
SELECT r.target_hour, r.action, r.price_eur_kwh, SUM(mr.import_kwh) AS actual_import
FROM recommendations r
JOIN myenergi_readings mr
  ON DATE(mr.interval_start AT TIME ZONE 'Europe/Dublin') = CURRENT_DATE
  AND EXTRACT(HOUR FROM mr.interval_start AT TIME ZONE 'Europe/Dublin') = r.target_hour
WHERE r.household_id = $1
GROUP BY 1, 2, 3;
```

**This is exactly what InfluxDB cannot do.** InfluxDB's Flux/InfluxQL treats each measurement as an independent stream. Joining across `advisory_log` (relational recommendation store) and `myenergi_readings` (time-series) requires either: exporting both to a separate analytical database, or using InfluxDB v3 with its DataFusion SQL layer (which still doesn't share the same data model as the relational tables).

Full decision: `docs/adr/ADR-012-timescaledb-over-influxdb-sqlite.md`

---

## Troubleshooting

### Advisory fires but Pushover not received

1. Check `PUSHOVER_APP_TOKEN` and `PUSHOVER_USER_KEY` env vars are set in the deployment environment.
2. Check the `[pushover]` log lines — `send_pushover()` logs success or warning.
3. Test with `curl` against the Pushover API directly to rule out account issues.

### Advisory always shows `expected_diversion_kwh = 0.0`

`est_solar = ghi * PANEL_FACTOR`. If GHI is 0, this is correct (cloudless night run, or API returning zeros). If GHI is non-zero but est_solar rounds to 0.0, check that `PANEL_FACTOR` is not accidentally set to 0.

### Peak sun hours doesn't match intuition

`_fetch_ghi()` counts hours where `shortwave_radiation > 200 W/m²`. This is hourly average W/m² — a day with two strong sun bursts between clouds can have the same peak sun hours as a day with consistent moderate sun. The GHI total (`ghi_forecast_kwh_m2`) is a better measure of total energy; peak_sun_hours is a proxy for whether the Eddi can work at rated power.

### Open-Meteo returns HTTP 400

Usually caused by mixing `start_date` with `forecast_days`. Use `forecast_days=2` only. Do not add `start_date` or `end_date` to the forecast endpoint URL.

---

## Decision Log

| Decision | What we chose | Why | Alternatives rejected |
|----------|--------------|-----|----------------------|
| `forecast_days=2` not `start_date` | `forecast_days=2` on Open-Meteo URL | Mixing `start_date` with `forecast_days` causes the API to return empty or malformed data. `forecast_days=2` returns today + tomorrow in one array consistently. | `start_date=tomorrow&end_date=tomorrow` — conflicts with forecast mode, returns archive data or errors |
| `min(est_solar, TANK_DAILY_KWH)` for diversion | Capped at 3.5 kWh | The Eddi won't divert more than the tank can absorb. Showing `~8 kWh diversion` when the tank only needs 3.5 kWh is misleading — the rest goes to export, not the tank. | Uncapped est_solar — inflates the diversion estimate on sunny days, confuses users |
| SKIP_BOOST threshold = 5 peak sun hours | Conservative high threshold | The cost of wrong SKIP_BOOST is a cold shower; the cost of wrong KEEP_BOOST is 13c. Asymmetric downside justifies a conservative threshold. | Lower threshold (e.g. 3h) — more SKIP_BOOST recommendations, more risk of cold showers on borderline days |
| Median not mean for panel factor | `np.median(computed_pf)` | Winter days with near-zero GHI (barely above 0.5 kWh/m² filter) produce anomalously low panel factors. Median is robust to these outliers. | Mean — dragged down by winter outliers, would underestimate summer output |
| +10% self-consumption uplift | Applied until Harvi CT installed | `(export + eddi) / GHI` is a lower bound — it excludes solar powering household loads before the meter. Without a Harvi, we estimate self-consumption at ~10% of observed. | No uplift (use raw lower bound) — PANEL_FACTOR would be set too low, causing false KEEP_BOOST on borderline sunny days |
| Pushover priority `-2` for KEEP_BOOST | Silent delivery | KEEP_BOOST = no action required. A silent notification at 08:00 maintains the information flow without interrupting the morning. Only SKIP_BOOST (actionable) gets a normal-priority sound. | Equal priority for all — trains users to ignore KEEP_BOOST notifications, reducing chance they notice a SKIP_BOOST |
| Separate `SolarAdvisory` dataclass | All computed fields retained as typed fields | Fields like `peak_sun_hours` and `expected_diversion_kwh` can be asserted in unit tests independently of message formatting. Keeps the logic and the presentation separate. | Build message string directly in `build_advisory()` — untestable without parsing formatted strings |

## References

- `deployment/morning_advisory.py` — full advisory implementation (`build_advisory`, `send_pushover`)
- `deployment/scheduler.py` — `_run_morning_advisory()` at 20:00, `_get_seasonal_panel_factor()`
- `deployment/routers/control.py` — `_compute_tomorrow_cost()` (predicted € cost for tomorrow)
- `src/energy_forecast/api/meter_store.py` — `log_advisory()` writes to advisory_log
- `scripts/calibrate_panel_factor.py` — DAN-142: panel factor calibration
- `infra/grafana/provisioning/dashboards/solar_pipeline.json` — panels 25–27 (tomorrow's advisory), panel 20 (forecast vs actual)
- `docs/adr/ADR-012-timescaledb-over-influxdb-sqlite.md` — full InfluxDB vs TimescaleDB decision
- `docs/explainers/LP_DISPATCH_EXPLAINED.md` — the other recommendation system (HEAT_NOW/DEFER_HEATING)
- Open-Meteo docs: `open-meteo.com/en/docs` — shortwave_radiation, forecast_days parameter
- myenergi Eddi: tank sizing constants from 2-person 150L cylinder calculation (DAN-141)
