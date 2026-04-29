# ADR-012: TimescaleDB (PostgreSQL extension) as the time-series store

**Status:** Accepted
**Date:** 2026-04-29

---

## Context

The Sparc Energy pipeline needed a time-series database to store:
- 30-min interval smart meter readings from ESB CSV uploads (`meter_readings`)
- Daily energy forecasts from the LightGBM model (`predictions`)
- Morning solar advisory log (`advisory_log`)
- Hourly weather GHI forecast + actuals (`weather_log`)
- 30-min MyEnergi import and Eddi diversion (`myenergi_readings`)
- Daily solar actuals for panel-factor calibration (`solar_actuals`)

Two other databases were already present in the developer's environment:
- **InfluxDB** — used by the Gardening / Greenhouse digital twin project for sensor time-series
- **SQLite** — suggested as a lightweight option by the Gardening project

---

## Options Considered

| Database | Type | Concurrent writes | SQL / JOINs | Time-series compression | Already in stack |
|----------|------|-------------------|-------------|------------------------|-----------------|
| **TimescaleDB** | PostgreSQL extension | Full ACID | Full SQL | Yes (automatic) | Added (Docker Compose) |
| InfluxDB | Purpose-built TSDB | Good | InfluxQL / Flux (limited) | Yes | Yes (Gardening project) |
| SQLite | Embedded relational | No (write lock) | Full SQL | No | No |
| Plain PostgreSQL | Relational | Full ACID | Full SQL | No | No |

---

## Decision

**TimescaleDB on PostgreSQL**, running as a single Docker service (`sparc-db`), co-located with the FastAPI container.

---

## Reasons

### 1. SQL and JOIN capability
The core value of Sparc is *joining* meter data, forecasts, tariff slots, and advisory logs. Queries like "forecast error by tariff slot" or "panel factor trend vs weather" require multi-table JOINs. InfluxDB's Flux/InfluxQL cannot do this without exporting to a separate store. TimescaleDB is PostgreSQL — any SQL query works.

### 2. One database, not two
Adding InfluxDB would mean two separate time-series databases in the Docker Compose stack, two connection pools in the API, two backup strategies, and two mental models for the engineer. TimescaleDB consolidates everything into the existing `sparc_energy` database.

### 3. asyncpg compatibility
The FastAPI service already uses `asyncpg` (async PostgreSQL driver) for the `households` and `predictions` tables. `myenergi_readings` and `weather_log` use the same pool — zero new dependencies.

### 4. TimescaleDB hypertables for `myenergi_readings`
`myenergi_readings` is expected to accumulate ~48 rows/day continuously. TimescaleDB auto-partitions by `interval_start` into time chunks, keeping query performance flat as the table grows. Plain PostgreSQL would need manual partitioning at scale.

### 5. Grafana PostgreSQL datasource already provisioned
The `sparc-postgres` Grafana datasource is already configured and working for all existing dashboards. All new tables are immediately queryable in Grafana — no new datasource, no new credentials.

### 6. Separation from Gardening project
The Gardening / Greenhouse digital twin is a separate project with its own InfluxDB instance. Keeping Sparc on TimescaleDB maintains clean separation:
- Different retention policies (Sparc: 3+ years meter history; Gardening: rolling sensor data)
- Different schemas and access patterns
- No cross-project dependency or shared infrastructure risk

### 7. SQLite ruled out immediately
SQLite has a write lock on the whole database file — incompatible with concurrent APScheduler jobs (16:00 inference, 20:00 advisory, 23:30 MyEnergi poll) all writing simultaneously.

---

## Consequences

- **Positive:** Full SQL, JOINs, asyncpg, Grafana out of the box, hypertable compression
- **Positive:** Single Docker service; existing backup / restore procedures apply
- **Negative:** TimescaleDB Docker image is ~400MB larger than plain PostgreSQL
- **Negative:** `create_hypertable()` requires the partition column to be part of the PRIMARY KEY (discovered when `id BIGSERIAL PRIMARY KEY` was initially used for `myenergi_readings` — fixed by using composite `PRIMARY KEY (hub_serial, interval_start)`)
- **Watch out for:** TimescaleDB version must match the extension version inside the container. Always use `timescale/timescaledb-ha` image tag pinned to a specific version in `docker-compose.yml`.

---

## Relationship to Gardening project

The Gardening project (`/Users/danalexandrubujoreanu/Personal Projects/Gardening/`) uses the same free Open-Meteo API for weather data and stores it in InfluxDB. This is intentional duplication — the two projects serve different purposes and should remain independently deployable. Do NOT attempt to share a database between them.
