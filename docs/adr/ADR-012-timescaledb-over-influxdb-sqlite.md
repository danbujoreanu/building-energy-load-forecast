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

---

## Addendum — InfluxDB v3 reassessment (2026-05-05)

InfluxDB v3 (aka InfluxDB 3.0) is a complete rewrite using Apache Arrow + DataFusion + Parquet. It addresses the main weakness cited above: v3 supports full SQL including JOINs via the DataFusion query engine.

**However, the decision is unchanged for the following reasons:**

1. **Two InfluxDB stacks, not one.** The Gardening project runs InfluxDB 2.7. InfluxDB v3 is not backward-compatible with v2.7 (different storage engine, different API). Adopting v3 for Energy would mean running two separate InfluxDB versions simultaneously — more operational complexity, not less.

2. **Processing Engine is not built-in ML.** InfluxDB v3's "predictive capabilities" refer to its Processing Engine — a Python trigger/UDF runtime that executes Python scripts on data writes. The LightGBM model still runs in Python; the artifact still needs to exist somewhere. The Processing Engine replaces APScheduler as a trigger mechanism, which already works.

3. **Data frequency mismatch.** InfluxDB v3's columnar storage and Arrow query engine are optimised for sub-second IoT ingestion at high cardinality. Sparc Energy ingests 30-min ESB meter readings and daily MyEnergi polls — not a high-frequency use case.

4. **TimescaleDB already provisioned.** asyncpg pool, Grafana datasource, migrations, and hypertables are all live. Migration cost is not zero.

**Reconsider v3 if:** sub-minute Eddi or Shelly Plug S current readings are added to the pipeline in future. High-frequency IoT ingestion is the genuine use case where v3's architecture outperforms TimescaleDB.
