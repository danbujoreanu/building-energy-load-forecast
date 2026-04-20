# Grafana — Operator Dashboard

**What it is:** Open-source dashboard tool. Think of it as the "cockpit" — it reads data from PostgreSQL and shows charts.  
**Port:** 3001 (http://localhost:3001)  
**Requires:** docker compose running (sparc-db must be healthy first)

---

## Open Grafana

```bash
# Make sure stack is running:
docker compose up -d

# Open in browser:
open http://localhost:3001
```

**Login:** `admin` / your `GRAFANA_PASSWORD` from `.env`

---

## What's Auto-Provisioned

When docker compose starts, Grafana automatically reads:
- `infra/grafana/provisioning/datasources/` — connects to PostgreSQL
- `infra/grafana/provisioning/dashboards/` — loads pre-built dashboard JSON files

You don't configure anything manually. It's all wired up.

---

## Key Panels (once data flows in)

| Panel | Data source | What you'll see |
|-------|------------|----------------|
| 24h forecast vs actual | `predictions` table | LightGBM P50 line vs real consumption |
| Drift status | `drift_reports` table (via JSON logs) | KS statistic per feature, severity |
| Control decisions | `outcomes` table | Every HEAT_NOW / DEFER_HEATING with reasoning |
| Savings tracker | `recommendations` + `outcomes` join | Projected vs actual saving |
| Eddi activity | `meter_readings` table | Solar diversion, grid consumption |

---

## To See Data: Run the Morning Brief First

Grafana has nothing to show until your API writes predictions to the database.

```bash
# Step 1: Ensure stack is running
docker compose up -d

# Step 2: Run morning brief (this writes a prediction to the DB)
~/miniconda3/envs/ml_lab1/bin/python deployment/live_inference.py --dry-run
```

Then refresh Grafana — the forecast chart should appear.

---

## Add a New Panel

1. Open http://localhost:3001
2. Click **Dashboards** (left sidebar) → open the Sparc Energy dashboard
3. Click **Edit** (top right) → **Add panel**
4. In the query editor, write SQL against your tables:

```sql
-- Example: last 24h of predictions
SELECT
  forecast_date as time,
  p50_kwh as "Forecast kWh"
FROM predictions
WHERE household_id = 'ireland_main'
  AND forecast_date > NOW() - INTERVAL '24 hours'
ORDER BY forecast_date;
```

5. Choose chart type (Time series, Bar chart, Stat)
6. Click **Save dashboard**

---

## Save Your Dashboard Changes Back to the Repo

If you add panels you want to keep:

1. Grafana → Dashboard → **Share** → **Export** → **Save to file**
2. Replace `infra/grafana/provisioning/dashboards/sparc_energy.json`
3. Commit: `git add infra/grafana/provisioning/dashboards/ && git commit -m "feat: update Grafana dashboard"`

Next time you run `docker compose up`, the updated dashboard loads automatically.

---

## Useful Database Tables

Connect via any SQL client (TablePlus, DBeaver) to `localhost:5432`, database `sparc_energy`, user `sparc`, password from `.env`:

| Table | What's in it |
|-------|-------------|
| `households` | One row per household (id, city, timezone) |
| `meter_readings` | 30-min interval electricity consumption (TimescaleDB hypertable) |
| `predictions` | LightGBM H+24 forecasts (P10/P50/P90 per household per day) |
| `recommendations` | Eddi schedule recommendations (show, approve, execute) |
| `outcomes` | Actual savings vs predicted |
| `tariff_changes` | BGE tariff history |

---

## Troubleshooting

### "Datasource not found" error
```bash
docker compose restart grafana
# Wait 10 seconds, refresh browser
```

### Dashboard is empty / no data
```bash
# Run morning brief to generate data:
~/miniconda3/envs/ml_lab1/bin/python deployment/live_inference.py --dry-run

# Check the database has data:
docker exec sparc-db psql -U sparc -d sparc_energy -c "SELECT COUNT(*) FROM predictions;"
```

### Forgot Grafana password
```bash
# Reset to a new password:
docker exec sparc-grafana grafana-cli admin reset-admin-password newpassword123
# Update GRAFANA_PASSWORD in .env to match
```
