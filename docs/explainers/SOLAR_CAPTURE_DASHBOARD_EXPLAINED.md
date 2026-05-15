# Solar Capture Dashboard — How We Measure Real Solar Output Without a Harvi
*What was built, why the first approach was wrong, and how to read the panels.*
*Last updated: 2026-05-09*

---

## The Problem We Were Solving

The original solar dashboard showed `actual_solar_kwh` — a number that looked like real solar generation but was actually just:

```
GHI (Open-Meteo) × 1.6 panel factor
```

That's an **estimate**, not a measurement. On 7 May 2026 it showed 9 kWh — a cloudless-day number when it was actually a mixed day generating perhaps 4 kWh. This triggered the full redesign.

**What we actually wanted:** real measured data from the myenergi Eddi, showing exactly where solar energy went.

---

## Solar Energy Flows in This House

```
                    ┌─────────────────┐
                    │  Solar Inverter  │
                    │  (Attic)        │
                    └────────┬────────┘
                             │ AC output
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌──────────────┐  ┌────────────┐  ┌──────────┐
    │  Grid export  │  │   House    │  │   Eddi   │
    │  (exp) ✓     │  │ loads      │  │ (h1d) ✓  │
    │  Measured    │  │ (estimated)│  │ Measured │
    └──────────────┘  └────────────┘  └──────────┘
```

**What the myenergi API measures:**
| Field | Meaning | Measured? |
|-------|---------|-----------|
| `h1d` | Solar → Eddi (divert mode) | ✓ Exact |
| `h1b` | Grid → Eddi (boost mode) | ✓ Exact |
| `exp` | Solar → Grid (export) | ✓ Exact |
| `imp` | Grid → House | ✓ Exact |

**What it CANNOT measure without a Harvi CT:**
- Total solar generation
- Solar → House (self-consumption)

**Why no Harvi?** The Harvi is a wireless CT clamp that mounts on the AC output cable of the solar inverter in the attic. It measures total generation and sends it wirelessly to the Eddi hub. Without it, the Eddi can only see what it controls directly (divert to hot water) and what goes through the grid meter (import/export).

**How we estimate Solar → House:**
Count the number of 30-minute slots during daylight hours (07:00–20:00) where `import_kwh < 0.005` (effectively zero grid draw). Each such slot means the house was running on solar alone, estimated at 0.15 kWh per slot. This is a rough approximation — the actual figure depends on house loads at the time.

---

## What Was Added to the Database (Migration 011)

Previously `myenergi_readings` only stored `eddi_kwh` (h1b + h1d combined). Two new columns were added:

```sql
-- infra/db/migrations/011_myenergi_solar_capture.sql
ALTER TABLE myenergi_readings
    ADD COLUMN IF NOT EXISTS eddi_divert_kwh  NUMERIC(8,4),  -- h1d only (solar → Eddi)
    ADD COLUMN IF NOT EXISTS export_kwh       NUMERIC(8,4);  -- exp (solar → grid)
```

And `myenergi_poller.py` was updated to capture and store these values on every daily poll. A 1,203-day backfill was run to populate historical data back to January 2023.

---

## The Three Dashboard Panels

### Panel 34 — "Solar: Eddi capture + Grid export vs GHI estimate"

**What it shows:**
- Blue bars: `eddi_divert_kwh` — kWh of solar diverted to hot water each day (h1d)
- Green bars: `export_kwh` — kWh of solar exported to the grid each day (exp)
- Orange line: `gen_est_kwh` — estimated solar generation based on actual measured GHI × 1.6
- Purple dashed line: `forecast_kwh` — forecasted solar generation based on forecast GHI × 1.6

**How to read it:**
- The gap between the orange line and the top of the bars = solar going to house loads (unmeasured)
- If the orange line is below the bars, the estimate is wrong for that day (variable cloud cover)
- On good solar days: bars fill up close to the orange line + blue bar tall = Eddi diverted lots

**SQL (simplified):**
```sql
WITH daily_ghi AS (
  SELECT DATE(hour_utc AT TIME ZONE 'Europe/Dublin') AS day,
    ROUND(SUM(ghi_wh_m2) FILTER (WHERE data_type = 'forecast') / 1000.0 * 1.6, 2) AS forecast_kwh,
    ROUND(SUM(ghi_wh_m2) FILTER (WHERE data_type = 'actual')   / 1000.0 * 1.6, 2) AS gen_est_kwh
  FROM weather_log WHERE location = 'maynooth' GROUP BY 1
),
daily_cap AS (
  SELECT DATE(interval_start AT TIME ZONE 'Europe/Dublin') AS day,
    ROUND(SUM(eddi_divert_kwh)::NUMERIC, 3) AS eddi_kwh,
    ROUND(SUM(export_kwh)::NUMERIC, 3) AS export_kwh
  FROM myenergi_readings GROUP BY 1
)
SELECT g.day::TIMESTAMPTZ AS time, c.eddi_kwh, c.export_kwh, g.gen_est_kwh, g.forecast_kwh
FROM daily_ghi g JOIN daily_cap c ON c.day = g.day
WHERE $__timeFilter(g.day::TIMESTAMPTZ) ORDER BY g.day
```

---

### Panel 37 — "Days with myenergi data (last 30d)"

Shows how many days in the last 30 have any myenergi_readings rows. A simple data quality check — if it drops below 28/30, something is wrong with the daily poll.

---

### Panel 38 — "Solar destination breakdown: Eddi / Grid / House"

**What it shows:** A stacked bar chart splitting measured solar into three destinations:
- Blue: `eddi_kwh` (solar to hot water — exact)
- Green: `export_kwh` (solar to grid — exact)
- Orange: `house_kwh` (solar to house — estimated via zero-import slots)

**Important limitation:** The house bar is an approximation. It will undercount on days with partial solar coverage because the 0.005 kWh import threshold may miss slots with light grid draw. It will overcount on days with very low house loads. It's directionally useful but not financially precise.

**Improving this:** Install a Harvi CT clamp on the AC output of the solar inverter in the attic. This will give exact generation measurement, making house self-consumption calculable as:
```
house_kwh = generation - eddi_divert - export
```

---

## Harvi Installation Guide

**What to buy:** myenergi Harvi wireless CT clamp transmitter kit (includes Harvi unit + CT clamp + installation hardware). Available from myenergi.com or Amazon. ~€65.

**Where to install:**
1. Turn off solar inverter (isolator switch in attic or main board)
2. Clip CT clamp around **one** of the AC output cables from the inverter
3. Connect CT clamp to Harvi unit
4. Position Harvi within WiFi range of Eddi hub (or use a Harvi extender)
5. Harvi is self-powered by induction from the cable — no battery/mains needed
6. Pair: in myenergi app → Devices → Add device → Harvi → follow prompts
7. Within 1-2 minutes, the app shows live generation figures

**After installation:**
- `gen` field appears in API responses (total solar generation, Joules/min)
- Self-consumption becomes: `gen - h1d - exp` (exact, not estimated)
- Update Panel 38 to use real `gen` instead of zero-import slot estimate

---

## Why `actual_solar_kwh` Was Wrong

Before this session, `solar_actuals.actual_solar_kwh` was populated from `ghi_actual × 1.6`. This is:

1. **Not measured** — it's a physics estimate based on irradiance × assumed panel efficiency
2. **Wildly wrong on variable days** — a day with 50% cloud cover might show 5 kWh estimate but generate 1.5 kWh measured
3. **Misleading labelling** — "actual" implies measurement, not estimate

After this session:
- Column renamed-in-use to `gen_est_kwh` in Grafana queries to make estimation clear
- Real measurements (`eddi_divert_kwh`, `export_kwh`) displayed as bars, clearly separate from estimate lines
- The gap between estimate and bars is visible, communicating the measurement uncertainty honestly

---

## Backfill Command Reference

If you ever need to re-run the backfill for these new columns:

```bash
# On the NUC, from ~/sparc/
ssh dan@192.168.68.119

# Check how many rows have the new columns populated
docker exec sparc-db psql -U sparc -d sparc -c "
  SELECT COUNT(*) FILTER (WHERE eddi_divert_kwh IS NOT NULL) AS has_divert,
         COUNT(*) FILTER (WHERE export_kwh IS NOT NULL) AS has_export,
         COUNT(*) AS total
  FROM myenergi_readings;"

# Trigger a backfill from a specific date (runs on Mac)
cd ~/building-energy-load-forecast
python scripts/myenergi_backfill.py --start-date 2023-01-20 --force

# The --force flag re-fetches even days already in the DB (needed after adding columns)
# Expected runtime: ~90 minutes for 1200 days
```

---

## Data Quality Notes

**Known gaps:**
- BST transition dates (last Sunday March, last Sunday October): first 2 slots of BST day missing (UTC day boundary issue — these slots' data lives in the previous UTC day's API response)
- Days with API failures: `sample_count` < 30 in a slot means partial data
- Days before the Eddi was installed: no data

**How to check for gaps:**
```sql
-- Days with fewer than 40 of 48 possible slots
SELECT DATE(interval_start AT TIME ZONE 'Europe/Dublin') AS day,
       COUNT(*) AS slots
FROM myenergi_readings
WHERE interval_start > NOW() - INTERVAL '30 days'
GROUP BY 1
HAVING COUNT(*) < 40
ORDER BY 1;
```

---

*Source: deployment/myenergi_poller.py, infra/db/migrations/011_myenergi_solar_capture.sql, infra/grafana/provisioning/dashboards/solar_pipeline.json*
*See also: MYENERGI_POLLER_EXPLAINED.md, MYENERGI_UNITS_BUG.md, OPERATIONS_MANUAL.md*
