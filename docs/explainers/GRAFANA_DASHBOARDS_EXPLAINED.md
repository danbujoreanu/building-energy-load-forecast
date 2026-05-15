# Grafana Dashboards — Explainer
*What each dashboard shows, why panels may be blank, and what data is needed*

---

## Dashboard URLs (via SSH tunnel → localhost)

All URLs work on Mac via the persistent SSH tunnel (LaunchAgent `com.sparc.nuc-tunnel`).
Full infrastructure architecture: `docs/explainers/INFRASTRUCTURE_EXPLAINED.md`

| Dashboard | URL | Status |
|-----------|-----|--------|
| Sparc Overview | http://localhost:3001/d/sparc-overview | ✅ Live |
| Household Intelligence | http://localhost:3001/d/household-intelligence | ✅ Live (set time range: last 2 years) |
| Solar Data Pipeline | http://localhost:3001/d/solar-pipeline | ⏳ Accumulating (myEnergi data started 2026-05-06) |
| Meter Readings | http://localhost:3001/d/meter-readings | ✅ Live (2 years of ESB data) |
| NUC Monitoring | http://localhost:3001/d/nuc-overview | ✅ Updated 2026-05-07 — shows all 13 containers (Sparc + Gardening) |
| Gardening Grafana | http://localhost:3000 | ✅ Live — 25-panel greenhouse dashboard |
| **Portainer (Docker UI)** | **http://localhost:9000** | ✅ Live 2026-05-07 — manage all NUC containers from browser |
| Prometheus | http://localhost:9090 | ✅ Live — raw metrics explorer |
| Gardening Streamlit | http://localhost:8501 | ✅ Live — LVPD, GDD, harvest log |

---

## Why Is X Blank? — Quick Diagnosis

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Free Saturday / tariff panels blank | Time range is too narrow (default = last 6h) | Set to **Last 2 years** in Grafana top-right |
| H+24 Forecast panels blank | `predictions` table empty — no inference run yet | Run inference: see "Trigger Inference" below |
| MyEnergi panels blank | `myenergi_readings` only has data from 2026-05-06 onwards | Wait for nightly polls (23:30) to accumulate |
| NUC monitoring blank | Prometheus datasource UID was missing | ✅ Fixed — restart Grafana to apply |
| Recommendations table blank | `recommendations` table was missing | ✅ Fixed — migration 005 applied 2026-05-06 |
| Solar actuals panels blank | `solar_actuals` needs ESB export_kwh + myEnergi eddi_kwh | Accumulates after nightly 23:45 solar_actuals sync |

**To trigger inference manually** (populates predictions + recommendations):
```bash
curl -s http://localhost:8000/health  # verify API healthy
# Then trigger via API:
curl -s -X POST http://localhost:8000/control \
  -H "Content-Type: application/json" \
  -d '{"household_id": "082fe72b-3c9c-48b1-9af8-c61875cad37f", "dry_run": false}'
```

**Household ID**: `082fe72b-3c9c-48b1-9af8-c61875cad37f` (your MPRN 10306822417)

---

## 1. Sparc Overview

**Purpose**: Real-time system health — one glance to know everything is running.

| Panel | What it shows | Data source |
|-------|--------------|-------------|
| Households | Count of registered households | `households` table |
| Meter Readings | Total 30-min intervals in DB | `meter_readings` |
| Forecasts Issued | Predictions generated | `predictions` |
| Control Recommendations | ControlEngine decisions issued | `recommendations` |
| 30-Minute Meter Readings | 2-year import/export timeseries | `meter_readings` |
| Latest H+24 Forecast | P10/P50/P90 kWh bands for tomorrow | `predictions` (hourly array) |
| Recent Control Recommendations | Last 10 Eddi schedule decisions | `recommendations` |
| Rolling MAE — 7d vs 28d | Model accuracy: actual vs predicted error | `model_drift_log` |
| Drift Ratio gauge | Red if recent MAE > 25% worse than baseline | `model_drift_log` |
| Drift Alerts table | History of Sunday drift checks | `model_drift_log` |

**Normal state**: Meter Readings = 34,885. Forecasts Issued / Recommendations = 0 until first inference run.

---

## 2. Household Intelligence

**Purpose**: Deep energy intelligence for Dan's household — behavioural patterns, tariff analysis, savings opportunities.

**⚠️ Set time range to "Last 2 years"** before looking at this dashboard.

### Layer 0 — Household Summary
| Panel | What it shows |
|-------|--------------|
| Total Import (kWh) | Cumulative grid import over selected period |
| Total Export / Solar (kWh) | Solar export fed back to grid |
| Est. Cost | Approximate electricity bill at BGE Affinity rates |
| Data Quality / Coverage | % of 30-min slots with readings vs gaps |

### Layer 0 — BTM Asset Signals
| Panel | What it shows |
|-------|--------------|
| Import vs Solar Export | Dual-axis: shows solar contribution |
| Monthly Solar Export | Seasonal pattern (south-facing roof signature) |

### Layer 1 — When Do You Use Energy?
| Panel | What it shows |
|-------|--------------|
| Average Load Profile (hour of day) | Typical consumption per hour — identifies morning peak |
| Avg Daily Consumption by Day of Week | Weekend vs weekday patterns |

### Layer 2 — Tariff Slot Analysis
| Panel | What it shows |
|-------|--------------|
| Consumption by Tariff Slot | % of usage in Night / Day / Peak / Free Saturday slots |
| Monthly Cost by Tariff Slot | €/month breakdown — shows if tariff is optimal |

### Free Saturday Utilisation (DAN-132)
Compares your Saturday 09:00–17:00 usage against the 100 kWh monthly free cap.
- **Green**: you're under 100 kWh/month free — not fully utilising the tariff benefit
- **Red**: over 100 kWh — you're paying for excess Saturday usage
- **Business logic**: Use this to decide whether to shift loads to Saturdays (e.g. washing machine, dishwasher)

### Layer — Solar / Shifting Opportunities
| Panel | What it shows |
|-------|--------------|
| Shifting Opportunity — Peak → Night | How many kWh/month you could save by shifting to night rate |
| Morning Boost vs Solar Overlap | Does your Eddi 07:00 boost fire before solar is available? |
| Est. Annual Saving (defer boost to solar) | €/year you'd save by letting solar charge the tank |

### Tariff Cost Intelligence
| Panel | What it shows |
|-------|--------------|
| Monthly Solar Export Revenue (DAN-133) | €/month at 18.5c/kWh export tariff |
| Free Saturday Utilisation (DAN-132) | Saturday slot usage vs 100 kWh free cap |
| Monthly Import — Year-Over-Year (DAN-149) | Consumption trend 2024 vs 2025 vs 2026 |
| Estimated Monthly Bill — YoY (DAN-130) | Bill trajectory — shows impact of Eddi + solar |

---

## 3. Solar Data Pipeline

**Purpose**: Validates the quality of solar + myEnergi data inputs. Engineering/ops dashboard — not for end users.

**⚠️ Many panels will be sparse until myEnergi accumulates data (started 2026-05-06).**

### MyEnergi Readings
| Panel | What it shows |
|-------|--------------|
| MyEnergi 30-min: Grid Import vs Eddi Diversion | Real-time from hub. `import_kwh` (grid CT) + `eddi_kwh` (h1b+h1d) |
| Daily Import vs Eddi Totals | Per-day totals. Will fill in from 2026-05-06 |
| Poller Health — Samples per Day | Should be 48 per full day. Partial days show fewer |

### Weather — GHI Forecast vs Actual
| Panel | What it shows |
|-------|--------------|
| Daily GHI Forecast vs Actual | Open-Meteo forecast (dashed) vs measured actual. Validates weather connector |

Both data types stored in `weather_log (data_type='actual'|'forecast')`.

### ESB vs MyEnergi Reconciliation
| Panel | What it shows |
|-------|--------------|
| Daily Import Reconciliation | ESB meter_readings vs myenergi_readings on same dates |
| Import % Difference | Should be within ±5%. > 5% suggests CT calibration issue |
| Reconciliation Summary Stats | Mean ratio, coverage days, anomaly count |

Once Harvi is installed and CT calibrated, this panel validates the measurement chain.

### Solar Self-Sufficiency
Shows what % of your consumption comes from solar (export_kwh / import_kwh).

### Seasonal Panel Factor Calibration (DAN-160)
Used by the `morning_advisory.py` to predict tomorrow's Eddi solar diversion.
`panel_factor = (export_kwh + eddi_kwh) / ghi_actual` per month. Requires 10+ clean days per month.

### Tomorrow's Solar Advisory (panels 25–27)

Three stat panels at y=94 showing what the 20:00 advisory issued for **tomorrow**:
- **Panel 25**: Recommendation (SKIP_BOOST / PARTIAL / KEEP_BOOST) with colour coding
- **Panel 26**: Estimated solar kWh + expected hot-water diversion kWh
- **Panel 27**: GHI forecast (kWh/m²) + peak sun hours

All query `advisory_log WHERE advisory_date = CURRENT_DATE + 1`. Populated each evening after 20:00 runs. First populated manually 2026-05-06.

### Forecast Accuracy Audit (panels 28–32)

Section added 2026-05-06. Scroll to the bottom of the dashboard. See `SOLAR_ADVISORY_EXPLAINED.md` § "Forecast Accuracy Audit" for full detail.

| Panel | Shows | Needs |
|-------|-------|-------|
| 29: GHI Forecast vs Actual | 4-line chart — forecast/actual GHI + forecast/actual Eddi kWh | Data from 2026-05-07 onwards |
| 30: GHI Forecast Error % | (forecast − actual) / actual per day | Same |
| 31: GHI MAPE 30d | Open-Meteo accuracy over rolling 30 days | 30+ advisory days (~2026-06-05) |
| 32: Advisory Accuracy % 30d | SKIP/KEEP recommendations matched outcome | Same |

**Note**: Accuracy panels use `eddi_kwh ≥ 2.0 kWh` as "solar-rich day" proxy. The 2.0 kWh threshold sits above two grid boosts (2 × 0.55 kWh = 1.1 kWh) to avoid false positives. Proper h1d isolation requires DAN-139.

---

## 4. Meter Readings

**Purpose**: Primary consumption view — 2 years of ESB data + H+24 forecast overlay.

| Panel | What it shows |
|-------|--------------|
| Grid Import (30-min intervals) | 34,885 readings, April 2024 → April 2026 |
| Solar Export (30-min intervals) | Solar export (all zeros if no solar) |
| H+24 Forecast — Noon (P10/P50/P90) | Tomorrow's prediction (blank until inference runs) |
| Readings in range | Count of rows in selected time window |
| Total Import kWh | Sum of consumption |
| Total Export kWh | Sum of solar export |
| MyEnergi 30-min: Import vs Eddi *(NEW)* | Live myEnergi data from 2026-05-06 |
| MyEnergi Today — Eddi Diverted *(NEW)* | Today's hot water diversion total (kWh) |

**Useful time ranges**: Last 7 days, Last month, Last year, Custom (2024-05-01 to now).

---

## 5. NUC Monitoring

**Purpose**: Comprehensive infrastructure health — CPU, RAM, disk, temperature, network, per-container metrics.  
**Dashboard UID**: `nuc-overview` | **Prometheus datasource**: `sparc-prometheus`  
**Updated**: 2026-05-06 — full rebuild from 8 broken panels to 20+ working panels across 6 sections.

### Section 1 — ⚡ System Health at a Glance (stat/gauge row)

| Panel | Metric | Normal range |
|-------|--------|-------------|
| CPU % | N3700 utilisation (all cores avg) | < 20% idle, < 60% normal |
| CPU Temp (°C) | `node_hwmon_temp_celsius{chip="platform_coretemp_0"}` | < 65°C idle, < 80°C load |
| RAM Used / Total | Used GB + Total GB | ~1.2 GB used of 6.4 GB |
| Disk Used % | Root filesystem `/` | < 70% (NUC has 107 GB SSD) |
| Disk Free (GB) | Free space on `/` | ~88 GB |
| Total Docker RAM | Combined RSS of all 9 sparc-* containers | < 900 MB normal |

### Section 2 — 📊 CPU & RAM Trend (timeseries)

- **CPU %** — rolling 2-minute rate, blue fill. Spikes at 16:00 (inference) and 23:30 (myenergi poll).
- **RAM Breakdown** — Used (red) / Cached (yellow) / Free (green). Cached memory is not "used" — Linux reclaims it instantly. Watch the Used line.

### Section 3 — 🐳 Container Memory & CPU

Three panels showing per-container resource usage across all 9 `sparc-*` containers:

| Panel | Type | Shows |
|-------|------|-------|
| Container RAM (MB) — sorted | Horizontal bar gauge | Current RSS per container, sorted desc |
| Container CPU % (current) | Horizontal bar gauge | Current CPU per container, sorted desc |
| Container RAM trend (MB) | Timeseries | RAM over time per container — shows if any container has a memory leak |

**Typical top consumers**:
- `sparc-n8n`: ~320 MB (Node.js runtime, largest consumer)
- `sparc-db`: ~120 MB (TimescaleDB — PostgreSQL 16 + TimescaleDB extension)
- `sparc-api`: ~100 MB (FastAPI + LightGBM model in memory)
- `sparc-grafana`: ~90 MB
- `sparc-prometheus`: ~80 MB

**Metric source**: `docker_container_memory_bytes{name=~"sparc-.+"}` — written by `scripts/docker_stats_prom.sh` cron → node_exporter textfile collector. **Not** cAdvisor (see cAdvisor workaround below).

### Section 4 — 🟢 Container Running Status

Stat panel: each of the 9 sparc-* containers shows **🟢 UP** (green) or **🔴 DOWN** (red). Refreshes every 30s. Any container missing from the panel (not just red) means the cron script hasn't scraped it — check `docker ps` on the NUC.

### Section 5 — 🌡️ Temperature & Network

| Panel | What it shows |
|-------|--------------|
| CPU Temperature | Package max (orange, thicker) + Core 0 + Core 1. Alert threshold: 80°C |
| Network In/Out | WiFi `wlp2s0` RX/TX KB/s. Spikes during myenergi poll (23:30) and Grafana refreshes |

### Section 6 — 💾 Disk I/O

| Panel | What it shows |
|-------|--------------|
| Disk Read/Write throughput | `sda` (SATA SSD) read/write KB/s |
| Disk I/O Utilisation % | `node_disk_io_time_seconds_total` — % of time disk was busy. Alert: > 75% |

### Section 7 — 🗄️ Technology Stack

Static reference panel showing what is running on the NUC:

| Service | Technology |
|---------|-----------|
| Primary database | **TimescaleDB** (PostgreSQL 16 extension) |
| Cache | Redis 7 (AOF persistence, 256 MB cap, allkeys-lru) |
| Monitoring | Prometheus v2.52 → Grafana OSS 11 |
| Reverse proxy | Caddy 2 (auto-TLS, HTTP/3) |
| Automation | n8n (webhook + Pushover notifications) |
| API | FastAPI + LightGBM H+24 model |
| Container metrics | node_exporter v1.8.1 textfile collector (not cAdvisor) |

**Why TimescaleDB?** It's a PostgreSQL extension, not a separate database. `sparc-db` runs a single PostgreSQL 16 container with TimescaleDB extension enabled. This gives native SQL JOINs across time-series (`myenergi_readings`, `weather_log`) and relational tables (`advisory_log`, `recommendations`) — impossible in InfluxDB 2.x Flux. See `docs/adr/ADR-012-timescaledb-over-influxdb-sqlite.md`.

---

### cAdvisor Workaround — Why the Textfile Collector

**Problem**: cAdvisor v0.49 on Ubuntu 24.04 with Docker `overlay2` storage driver cannot resolve container names. It looks for `/rootfs/var/lib/docker/image/overlayfs/layerdb/mounts/` which does not exist on `overlay2`. All container labels come through as empty strings, so per-container metrics are unaddressable in Grafana.

**Solution**: Bypass cAdvisor entirely for container-level metrics. Use the **node_exporter textfile collector** pattern:

```
scripts/docker_stats_prom.sh   (runs every 30s via cron)
        │
        └── docker stats --no-stream
                │
                └── writes /var/node_exporter/textfiles/docker_stats.prom
                        │
                        └── node_exporter (--collector.textfile.directory)
                                │
                                └── Prometheus scrapes → Grafana
```

**Crontab on NUC** (`crontab -e`):
```
* * * * * /home/dan/sparc/scripts/docker_stats_prom.sh
* * * * * sleep 30 && /home/dan/sparc/scripts/docker_stats_prom.sh
```

**Metrics exposed**:
- `docker_container_memory_bytes{name="sparc-api"}` — RSS in bytes
- `docker_container_cpu_percent{name="sparc-api"}` — CPU % (0–100 per core)
- `docker_container_running{name="sparc-api"}` — 1 if running

**Important**: The `.prom` file must be world-readable for the node_exporter container to read it. `docker_stats_prom.sh` uses `chmod 644 "$TMP"` before `mv` to ensure this — without it, `node_textfile_scrape_error` = 1 and all container metrics disappear.

**To verify metrics are flowing**:
```bash
ssh dan@192.168.68.119 "cat /var/node_exporter/textfiles/docker_stats.prom | head -20"
# Should show all 9 sparc-* containers with memory_bytes and cpu_percent values
```

**To verify no scrape errors**:
```bash
# In Grafana Explore on sparc-prometheus:
node_textfile_scrape_error
# Should return 0 for all instances
```

---

## Scheduler — When Does Data Arrive?

| Time | Job | What it writes |
|------|-----|---------------|
| 09:00 daily | `check_data_gaps` | Pushover if ESB data stale > 72h |
| 16:00 daily | `daily_inference` | `predictions` + triggers ControlEngine |
| 20:00 daily | `morning_advisory` | `advisory_log`, Pushover notification |
| 23:30 daily | `myenergi_poll` | `myenergi_readings` (48 slots), `weather_log` (GHI actuals) |
| 23:45 daily | `solar_actuals_sync` | `solar_actuals` (export_kwh aggregated from ESB) |
| 23:55 daily | `data_quality_check` | `data_quality_events`, Pushover if anomaly |
| Mon 08:30 | `weekly_quality_report` | Pushover weekly summary |
| Sun 02:00 | `drift_check_sunday` | `model_drift_log`, Pushover if drift > 1.25× |

---

## The "Old Grafana" vs This One

The old Grafana on Mac (localhost:3000) was running against a different database — either
mock data or an older PostgreSQL instance. The NUC Grafana (localhost:3001 via SSH tunnel)
connects to the real TimescaleDB with your actual ESB data.

If you saw rich solar pipeline panels before, they were either:
- Mock/generated data in the old setup
- Or a previous home server configuration

The NUC setup shows real data only. As myEnergi data accumulates nightly and inference
runs daily from 16:00, all panels will populate over the next 2–4 weeks.
