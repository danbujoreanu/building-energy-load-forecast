# Solar Data Pipeline — Engineering Reference

**Implemented:** Sessions 49–50 (2026-04-29)
**Commits:** 1bfae79, 7758892, 50cbaf1

---

## Overview

The solar data pipeline captures three complementary data streams to understand actual solar panel performance, calibrate the PANEL_FACTOR over time, and enable solar-aware energy advisories.

```
Open-Meteo archive API
        │
        ▼
   weather_log (hourly GHI forecast + actual)
        │
        ├──► solar_actuals (daily panel_factor_obs)
        │              ▲
MyEnergi API           │
   /cgi-jday-E{serial} │
        │              │
        ▼              │
myenergi_readings ─────┘
(30-min import_kwh + eddi_kwh)
```

---

## Database Tables

All tables are in the `sparc_energy` PostgreSQL database, `public` schema.

### `weather_log`

Stores hourly GHI (Global Horizontal Irradiance) in Wh/m² for Maynooth (lat 53.38, lon -6.59).

| Column | Type | Notes |
|--------|------|-------|
| `id` | BIGSERIAL PK | |
| `location` | TEXT | Default: `'maynooth'` |
| `hour_utc` | TIMESTAMPTZ | Start of the hour, UTC |
| `ghi_wh_m2` | NUMERIC(8,2) | Wh/m² for this hour |
| `data_type` | TEXT | `'forecast'` or `'actual'` |
| `fetched_at` | TIMESTAMPTZ | When this row was written |

**Unique constraint:** `(location, hour_utc, data_type)` — forecast and actual coexist for the same hour.

**Data sources:**
- `forecast`: written at 20:00 by `morning_advisory.py` (Open-Meteo forecast endpoint, `forecast_days=2`)
- `actual`: written at 23:30 by `myenergi_poller.py` (Open-Meteo archive endpoint for the day just ending)

**Why store both?** To compare forecast vs actual GHI and track advisory accuracy over time. The archive API has a ~1-day lag, so actuals are written the following evening.

---

### `myenergi_readings`

TimescaleDB hypertable. Stores 30-min aggregated data from the MyEnergi hub (serial: 21509692).

| Column | Type | Notes |
|--------|------|-------|
| `hub_serial` | TEXT | MyEnergi hub serial number |
| `interval_start` | TIMESTAMPTZ | Start of 30-min slot, UTC (partition key) |
| `import_kwh` | NUMERIC(8,4) | Grid import in this slot |
| `eddi_kwh` | NUMERIC(8,4) | Eddi hot-water diversion in this slot |
| `sample_count` | SMALLINT | Number of minute samples aggregated (≤30) |
| `fetched_at` | TIMESTAMPTZ | When this row was written |

**Primary key:** `(hub_serial, interval_start)` — composite key required for TimescaleDB partitioning.

**Conversion from MyEnergi raw data:**
```
# MyEnergi /cgi-jday-E{serial} returns fields:
#   imp: instantaneous grid import in centi-Watts
#   hsk: instantaneous Eddi hot-water diversion in centi-Watts
#   (sampled once per minute, ~1441 entries per day)

import_kwh = average(imp samples in slot) * 0.5h / 100 / 1000
eddi_kwh   = average(hsk samples in slot) * 0.5h / 100 / 1000
```

**Important limitations:**
- `imp` is never negative — export data is NOT available from this endpoint
- Export (solar to grid) requires a Harvi CT clamp device (`gen` field) — user purchasing
- House self-consumption from solar is currently not measurable without Harvi
- ESB CSV remains the official source for import/export (meter_readings table)

**Schedule:** Polled daily at **23:30 Europe/Dublin** by `deployment/myenergi_poller.py` via APScheduler.

---

### `solar_actuals`

Daily solar summary, one row per day. Combines export (from ESB CSV) and Eddi diversion (from MyEnergi) to compute observed panel factor.

| Column | Type | Notes |
|--------|------|-------|
| `id` | BIGSERIAL PK | |
| `solar_date` | DATE UNIQUE | The date this row covers |
| `export_kwh` | NUMERIC(8,3) | ESB net export for the day (populated separately) |
| `eddi_kwh` | NUMERIC(8,3) | Eddi diversion total (from MyEnergi `che` field) |
| `ghi_actual` | NUMERIC(8,3) | kWh/m² observed (sum of weather_log actual hours / 1000) |
| `ghi_forecast` | NUMERIC(8,3) | kWh/m² forecast the day before |
| `panel_factor_obs` | NUMERIC(6,4) | Lower bound: `(export_kwh + eddi_kwh) / ghi_actual` |
| `recorded_at` | TIMESTAMPTZ | When this row was last updated |

**Panel factor calibration:**
```
panel_factor_obs = (export_kwh + eddi_kwh) / ghi_actual

This is a LOWER BOUND because:
  Total generation = export + Eddi + house self-consumption
  House SC is not measurable without Harvi CT clamp.

Live calibration (2026-04-29):
  export = 7.4 kWh, Eddi = 2.12 kWh, GHI = 6.712 kWh/m²
  panel_factor_obs = 9.52 / 6.712 = 1.418

PANEL_FACTOR in morning_advisory.py = 1.6 (adds ~13% for estimated house SC)
```

**Self-calibration plan:** Once 30+ days of `solar_actuals` data accumulates, `PANEL_FACTOR` in `morning_advisory.py` should be updated to `median(panel_factor_obs) * 1.1` (10% uplift for house SC). A script for this is not yet written.

---

## Scheduled Jobs (APScheduler in `deployment/app.py`)

| Time (Europe/Dublin) | Function | What it does |
|---------------------|----------|--------------|
| 16:00 | `_run_scheduled_inference` | LightGBM forecast for all households |
| 20:00 | `_run_morning_advisory` | Open-Meteo GHI → SolarAdvisory → Pushover + advisory_log |
| 23:30 | `_run_myenergi_poll` | MyEnergi jday → myenergi_readings + weather_log actual + solar_actuals |

---

## Accessing the Data

### Via psql (direct DB)
```bash
docker compose exec db psql -U sparc -d sparc_energy

# Check last 7 days of MyEnergi readings
SELECT DATE(interval_start AT TIME ZONE 'Europe/Dublin') AS day,
       SUM(import_kwh) AS total_import_kwh,
       SUM(eddi_kwh) AS total_eddi_kwh
FROM myenergi_readings
WHERE interval_start >= NOW() - INTERVAL '7 days'
GROUP BY 1 ORDER BY 1 DESC;

# Check GHI forecast vs actual
SELECT DATE(hour_utc AT TIME ZONE 'Europe/Dublin') AS day,
       data_type,
       ROUND(SUM(ghi_wh_m2) / 1000, 3) AS ghi_kwh_m2
FROM weather_log
GROUP BY 1, 2 ORDER BY 1 DESC;

# Panel factor trend
SELECT solar_date, eddi_kwh, ghi_actual, panel_factor_obs
FROM solar_actuals ORDER BY solar_date DESC LIMIT 30;
```

### Via Grafana Explore (ad-hoc SQL)
1. Open `localhost:3001`
2. Left sidebar → **Explore**
3. Select datasource: `sparc-postgres`
4. Write any SQL query against the tables above

### Via Grafana Dashboard (planned — DAN-127)
A dedicated "Solar Data Pipeline" dashboard will be created (DAN-127) with:
- 30-min MyEnergi import vs Eddi diversion time-series
- GHI forecast vs actual by day
- Panel factor trend
- Poller health (last successful fetch)

---

## Future: Harvi CT Clamp Integration

When the user installs a myenergi Harvi CT clamp on the solar cable:
1. The `/cgi-jday-E{serial}` response will include a `gen` field (generation in centi-Watts)
2. `myenergi_poller.py` needs one new column: `generation_kwh NUMERIC(8,4)` in `myenergi_readings`
3. `solar_actuals` gains: `generation_kwh` and `house_sc_kwh = generation - export - eddi`
4. `panel_factor_obs` becomes exact (not a lower bound)

Migration for this: `infra/db/migrations/004_harvi_generation.sql` (not yet created).
