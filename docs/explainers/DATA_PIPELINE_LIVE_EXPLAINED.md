# Live Data Pipeline Explainer
*How live household data flows from devices → DB → Grafana → predictions*

---

## Data sources: what goes where

```
ESB Networks (Smart Meter)       MyEnergi Hub          Open-Meteo (free API)
  ↓ monthly CSV export             ↓ REST API              ↓ REST API
  ↓ POST /upload                   ↓ 23:30 scheduler       ↓ 16:00 + 23:30
  meter_readings (TimescaleDB)     myenergi_readings       weather_log
        ↓                                ↓                      ↓
        └──────────────────┬────────────┘                       │
                           ↓                                    │
                 load_disaggregation.py                         │
                 base_load_kwh = import_kwh - eddi_kwh          │
                           ↓                                    ↓
                     LightGBM model ←──── solar_baseline.py (cloud_cover)
                           ↓
                     predictions (24h array)
                           ↓
                     ControlEngine
                           ↓
                     recommendations
                           ↓
                     Pushover notification (20:00)
```

---

## ESB Smart Meter CSV

**What**: 30-minute interval grid import/export data from your electricity meter.
**Source**: esb.ie → My Account → Smart Meter → Download Usage Data → HDF calckWh file.
**Frequency**: Download monthly (ESB retains ~13 months).
**Ingest**: `POST http://localhost:8000/upload` (multipart form, any browser or curl).
**Table**: `meter_readings` — hypertable partitioned by month, unique on `(household_id, recorded_at)`.

**Once Harvi is installed** (this week): Harvi clips onto your ESB meter tails and sends real-time
CT clamp readings to the myenergi hub. The `myenergi_poller.py` will capture grid import at
30-min resolution overnight, eliminating the need for manual ESB CSV downloads for live predictions.
ESB CSV is still useful for:
- Model retraining (official metered data)
- Accuracy audits (ESB vs MyEnergi reconciliation, visible in Solar Pipeline dashboard)

**Recommendation**: Download a fresh ESB CSV once per month until Harvi is configured
and you've validated the `myenergi_readings.import_kwh` matches within 5% (visible in
Grafana → Solar Data Pipeline → "ESB vs MyEnergi Daily Import Reconciliation").

---

## myenergi Poller (scheduler.py — 23:30 every night)

**What**: Fetches today's minute-level data from the myenergi hub API and aggregates to 30-min.
**Fields captured**:
- `import_kwh` — grid import (CT clamp, from Harvi when installed)
- `eddi_kwh` — hot water diversion (h1b = grid boost, h1d = solar diversion)

**Scheduler job**: `myenergi_poll` at 23:30 Europe/Dublin — captures the full day.
**Status**: **Live as of 2026-05-06** — 19 slots captured for today (00:00–09:00).

**To trigger manually** (e.g. to backfill):
```bash
ssh dan@192.168.68.119 "cd ~/sparc && docker compose exec -T api python3 -c \"
import asyncio, asyncpg, os, sys
sys.path.insert(0, '/app')
from deployment.myenergi_poller import run_daily_poll
from datetime import date

async def main():
    pool = await asyncpg.create_pool(os.environ['DATABASE_URL'], min_size=1, max_size=2)
    await run_daily_poll(pool, date.today())
    await pool.close()
    print('Done')

asyncio.run(main())
\""
```

---

## Open-Meteo Weather (no API key required)

**Connected**: ✅ `deployment/connectors/weather.py` → `OpenMeteoConnector`
**Variables fetched** (as of DAN-164 Stream 2):
- `temperature_2m` → `Temperature_Outdoor_C`
- `direct_radiation` → `Global_Solar_Horizontal_Radiation_W_m2`
- `cloud_cover` → `cloud_cover_pct` ← **NEW** (feeds SolarBaselineModel)
- `shortwave_radiation` → `shortwave_radiation_W_m2` ← **NEW** (ensemble feature)

**Historical actuals**: `myenergi_poller.py` fetches `shortwave_radiation` from the
Open-Meteo archive API nightly and stores in `weather_log (data_type='actual')`.
This allows forecast vs actual GHI comparison in Grafana.

**Coordinates**: Dublin/Maynooth (53.38°N, 6.59°W).

---

## Load Disaggregation (DAN-164 Stream 1)

**Module**: `src/energy_forecast/features/load_disaggregation.py`
**What it does**: Subtracts `eddi_kwh` from `import_kwh` to produce `base_load_kwh`.

```python
base_load_kwh = max(0, import_kwh - eddi_kwh)
```

**Why**: The Eddi adds 1.4–3.0 kW of intermittent hot-water diversion load.
Training the LightGBM model on `base_load_kwh` improves forecast accuracy for the
controllable part of demand — the Eddi schedule is then predicted separately by
the LP thermal dispatcher.

**Joins needed** (once myenergi data has enough history):
```sql
SELECT
  m.recorded_at,
  m.import_kwh,
  COALESCE(e.eddi_kwh, 0) AS eddi_kwh,
  GREATEST(0, m.import_kwh - COALESCE(e.eddi_kwh, 0)) AS base_load_kwh
FROM meter_readings m
LEFT JOIN myenergi_readings e
  ON m.recorded_at = e.interval_start
WHERE m.household_id = $1
ORDER BY m.recorded_at
```

---

## Solar Baseline (DAN-164 Stream 2)

**Module**: `src/energy_forecast/features/solar_baseline.py`
**What it does**: Predicts hourly PV output from clear-sky geometry + cloud_cover correction.

```
clear_sky_factor = solar altitude angle (lat/DOY/hour geometry)
cloud_factor     = 1 - (cloud_cover_pct / 100) × cloud_opacity (0.75)
solar_kwh        = pv_peak_power_kw × clear_sky_factor × cloud_factor
```

**If `pv_peak_power_kw == 0`** (no solar): returns zeros — safe to call always.
**Ireland coords**: 53.3°N, 6.3°W (default).
**cloud_opacity = 0.75**: Overcast sky (100% cloud) reduces output by 75% — empirically
reasonable for Ireland's diffuse irradiance conditions.

---

## Where Recommendations Are Stored

```sql
-- ControlEngine writes here after 16:00 inference:
SELECT * FROM recommendations
  WHERE household_id = '<uuid>'
  ORDER BY created_at DESC
  LIMIT 10;

-- After user acts on advice:
SELECT * FROM recommendation_outcomes
  WHERE household_id = '<uuid>';

-- North Star metric:
SELECT * FROM customer_tiers;  -- VIEW: tier_1_optimiser / tier_2_tracker / etc.
SELECT * FROM savings_gap;     -- VIEW: actual_savings vs potential_savings per month
```

**Visible in Grafana**: Sparc Overview → "Recent Control Recommendations" table.
**Pushover notification**: 20:00 job `morning_advisory` sends tomorrow's schedule.

---

## Drift Monitoring (DAN-163)

**Table**: `model_drift_log`
**Populated by**: `check_drift_sunday` scheduler job — every Sunday at 02:00.
**Logic**:
1. Compute 7d rolling MAE (predictions.p50_kwh vs meter_readings.import_kwh)
2. Compute 28d baseline MAE
3. `drift_ratio = mae_7d / mae_28d`
4. If `drift_ratio > 1.25` → Pushover alert + `alert_sent = TRUE`

**Visible in Grafana**: Sparc Overview → "Model Drift — DAN-163" section:
- Rolling MAE (7d orange / 28d blue timeseries)
- Drift ratio gauge (green < 1.1 / yellow < 1.25 / red ≥ 1.25)
- Alert history table

---

## Intel NUC — Is It a Good Choice?

**Yes — for this phase.** The N3700 Pentium (2015, 4-core, 2.4GHz) is:
- Sufficient for inference: LightGBM prediction in <50ms, APScheduler jobs in seconds
- Efficient: ~6W idle, runs 24/7 without burning Mac battery
- Cost: already owned — zero marginal infrastructure cost

**Constraints** (plan for):
- Training stays on Mac (N3700 takes 8 min to build a Docker image)
- No GPU → no neural net inference locally
- 6.4GB RAM currently 90% free → can add more services without issue

**When to move to cloud**: AWS Activate credits (DAN-69) → migrate API to App Runner or ECS.
NUC stays as local dev + home trial server.

---

## Grafana Dashboard Quick Reference

| Dashboard | URL | Key panels |
|-----------|-----|------------|
| Sparc Overview | http://localhost:3001/d/sparc-overview | System stats, meter readings, H+24 forecast, drift monitoring |
| Solar Data Pipeline | http://localhost:3001/d/solar-pipeline | MyEnergi 30-min, GHI forecast vs actual, ESB reconciliation |
| Meter Readings | http://localhost:3001/d/meter-readings | Grid import timeseries (2 years), forecast overlay |
| Household Intelligence | http://localhost:3001/d/household-intelligence | Behavioural tiers, savings gap, recommendations |
| NUC Monitoring | http://localhost:3001/d/nuc-overview | CPU, RAM, disk, per-container stats |
