# PostgreSQL + TimescaleDB — Data Store

**What it is:** PostgreSQL is a relational database (like Excel but for code). TimescaleDB is an extension that makes it fast at time-series data (energy readings over time).  
**Port:** 5432 (localhost:5432 from your Mac)  
**Container:** `sparc-db`  
**Data survives:** Yes — stored in the `pgdata` Docker volume

---

## You Don't Need to Do Anything

The database starts automatically with `docker compose up -d`.  
The schema (all tables) is created automatically from `infra/db/init.sql` on first run.  
You don't need to connect to it directly unless you want to inspect data.

---

## What's in the Database

| Table | What it stores | Populated by |
|-------|---------------|-------------|
| `households` | One row per home (id, city, timezone, postcode) | Manual insert / API |
| `meter_readings` | 30-min electricity readings — TimescaleDB hypertable | ESB CSV upload |
| `predictions` | LightGBM H+24 forecasts (P10/P50/P90) | Morning brief / API `/predict` |
| `recommendations` | Eddi scheduling recommendations | Control engine |
| `outcomes` | Actual savings vs predicted | Next-day reconciliation |
| `tariff_changes` | BGE rate history | Manual / feed |

Plus views: `customer_tiers` (segments households by usage), `savings_gap` (what's been left on the table).

---

## Connecting from Your Mac (optional — for data exploration)

### Option A: TablePlus (free, visual)
1. Download TablePlus: https://tableplus.com/
2. New Connection → PostgreSQL
3. Host: `localhost`, Port: `5432`
4. Database: `sparc_energy`, User: `sparc`
5. Password: whatever you set as `DB_PASSWORD` in `.env`

### Option B: Terminal
```bash
docker exec -it sparc-db psql -U sparc -d sparc_energy
```

Once in:
```sql
-- See all tables:
\dt

-- See latest predictions:
SELECT household_id, forecast_date, p50_kwh, estimated_cost_eur
FROM predictions
ORDER BY created_at DESC
LIMIT 10;

-- Count meter readings:
SELECT COUNT(*) FROM meter_readings;

-- See savings gap:
SELECT * FROM savings_gap;

-- Exit:
\q
```

---

## TimescaleDB — What Makes it Special

The `meter_readings` table is a **hypertable** — TimescaleDB automatically chunks it by time. This means:
- Querying "last 30 days" is fast even with millions of rows
- Compression can be applied to old data automatically
- Time-series aggregations (`time_bucket`) are optimised

Example query using TimescaleDB functions:
```sql
-- Hourly average consumption last 7 days
SELECT
  time_bucket('1 hour', reading_time) AS hour,
  AVG(import_kwh) AS avg_kwh
FROM meter_readings
WHERE household_id = 'ireland_main'
  AND reading_time > NOW() - INTERVAL '7 days'
GROUP BY hour
ORDER BY hour;
```

---

## Backup Your Database

```bash
# Create a backup file:
docker exec sparc-db pg_dump -U sparc sparc_energy > ~/sparc_backup_$(date +%Y%m%d).sql

# Restore from backup:
docker exec -i sparc-db psql -U sparc sparc_energy < ~/sparc_backup_20260420.sql
```

---

## Troubleshooting

### Database won't start
```bash
docker compose logs db --tail=30
# Common cause: pgdata volume is corrupted (rare)
# Nuclear option (loses all data):
docker compose down -v
docker compose up -d
```

### "password authentication failed"
Your `DB_PASSWORD` in `.env` doesn't match what the database was created with.

```bash
# If first run: just update .env and:
docker compose down -v  # wipes DB (it's empty anyway)
docker compose up -d

# If DB has data: don't wipe. Connect as postgres superuser:
docker exec -it sparc-db psql -U postgres
ALTER USER sparc WITH PASSWORD 'new_password';
\q
# Update .env to match
```

### Check database is healthy
```bash
docker compose ps db
# Should show: running (healthy)
```
