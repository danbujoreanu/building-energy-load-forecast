# Database Migrations

Applied via `docker compose exec -T db psql -U sparc -d sparc_energy < infra/db/migrations/NNN_name.sql`
on the Intel NUC running `~/sparc`.

---

## Migration History

| File | Date | Linear | What it adds |
|------|------|--------|-------------|
| `init.sql` | 2026-04-29 | DAN-128 | Base schema: `households`, `meter_readings`, `predictions`, `recommendations`, `recommendation_outcomes`, `tariff_changes`, `solar_actuals`, `weather_log` |
| `002_advisory_log.sql` | 2026-04-xx | — | `advisory_log` table — morning advisory history |
| `003_solar_pipeline.sql` | 2026-04-xx | — | `solar_actuals` extensions — `eddi_kwh`, `ghi_actual`, `panel_factor_obs`, `panel_factor_seasonal` on `households` |
| `004_data_quality.sql` | 2026-05-04 | DAN-159 | `data_quality_events` table — MyEnergi vs ESB reconciliation log |
| `005_recommendations_drift.sql` | **2026-05-06** | **DAN-163** | `model_drift_log` + missing relational tables (`recommendations`, `recommendation_outcomes`, `tariff_changes`) + `customer_tiers` and `savings_gap` views |
| `006_semo_prices.sql` | **2026-05-06** | **DAN-164 Stream 4** | `semo_prices` — EirGrid day-ahead SMP hourly prices (EUR/kWh) |
| `007_household_profile.sql` | **2026-05-06** | **DAN-152** | `households` additions: `has_eddi`, `heating_type`, `installed_pv_kw`, `panel_factor_seasonal` (JSONB), `panel_factor_obs` |

---

## Why Migration 005 Was Needed

The NUC database was initialised with an older `init.sql` that pre-dated the
`recommendations`, `recommendation_outcomes`, and `tariff_changes` tables.
PostgreSQL's `/docker-entrypoint-initdb.d/` only runs init scripts on first
container start — updating `init.sql` does not re-run it on existing volumes.

Migration 005 backfills these tables so the ControlEngine, Grafana panels, and
`customer_tiers` view all work correctly.

---

## How to Apply a Migration

```bash
# From Mac:
ssh dan@192.168.68.119 "cd ~/sparc && docker compose exec -T db psql -U sparc -d sparc_energy \
  < infra/db/migrations/005_recommendations_drift.sql"

# Or interactively on NUC:
ssh dan@192.168.68.119
cd ~/sparc
docker compose exec db psql -U sparc -d sparc_energy
\i /path/to/migration.sql   # if mounted, else pipe via exec -T
```

**Migrations are idempotent** — all use `CREATE TABLE IF NOT EXISTS` and
`CREATE INDEX IF NOT EXISTS`, so re-running is safe.

---

## Pending Migrations

None currently. All planned migrations applied.
