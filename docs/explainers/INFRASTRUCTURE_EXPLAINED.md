# Infrastructure — Mac Laptop vs Intel NUC
*How the two machines divide responsibilities and why*
*Last updated: 2026-05-07*

---

## Quick Access — All Services

| Service | URL | Credentials |
|---------|-----|-------------|
| ⚡ Energy Grafana | http://localhost:3001 | admin / see NUC `.env` GRAFANA_PASSWORD |
| 🌱 Gardening Grafana | http://localhost:3000 | admin / see Gardening `.env` |
| 🔧 Portainer (Docker UI) | http://localhost:9000 | admin / see NUC `.env` PORTAINER_PASSWORD |
| ⚙️ n8n Automation | http://localhost:5678 | owner account / set on first run |
| 📊 Prometheus | http://localhost:9090 | no auth |
| 🌱 Streamlit Hub | http://localhost:8501 | no auth |
| 🌱 Gardening InfluxDB (NUC v2.7) | http://192.168.68.119:8086 or localhost:18086 | see Gardening `.env` INFLUXDB_GH_TOKEN |
| 🧪 InfluxDB 3 Enterprise (Mac test) | http://localhost:8086 | see Gardening `.env` |
| ⚡ Energy API (local dev) | http://localhost:8000 | no auth |
| NUC SSH | `ssh nuc` | SSH key (`~/.ssh/id_ed25519`) |

> **Credentials file:** All service passwords are in `~/sparc/.env` on the NUC (not in Git). Never commit `.env`.

---

## One-Line Design Principle

**NUC = always-on production server. Mac = development workstation.**

The NUC runs everything that must be available 24/7. The Mac runs nothing that production depends on. This means a laptop lid-close or reboot never breaks a live alert, scheduled advisory, or nightly poll.

---

## Access Map

All NUC services are accessed from the Mac via a persistent SSH tunnel managed by the LaunchAgent `com.sparc.nuc-tunnel` (auto-restarts on login and after crash).

| What you type on Mac | Goes to | Service |
|----------------------|---------|---------|
| `http://localhost:3001` | NUC `sparc-grafana` | Energy Grafana |
| `http://localhost:3000` | NUC `gardening-grafana` | Gardening Grafana |
| `http://localhost:5678` | NUC `sparc-n8n` | n8n automation |
| `http://localhost:9090` | NUC `sparc-prometheus` | Prometheus metrics |
| `http://localhost:9000` | NUC `sparc-portainer` | Portainer Docker UI |
| `http://localhost:8501` | NUC `gardening-streamlit` | Gardening Streamlit hub |
| `http://localhost:18086` | NUC `gardening-influxdb` | Gardening InfluxDB 2.7 |
| `http://localhost:8086` | Mac `influxdb3-enterprise` | InfluxDB 3 test instance (local) |
| `http://localhost:8000` | Mac `sparc-api` | Energy API (local dev) |
| `ssh nuc` | 192.168.68.119 | Direct SSH shell |
| `192.168.68.119:PORT` | NUC direct (LAN only) | Any port — UFW inactive |

**Tunnel management:**
```bash
# Check tunnel is alive
ps aux | grep 'ssh.*192.168.68.119' | grep -v grep

# Restart if needed (LaunchAgent will also auto-restart)
launchctl unload ~/Library/LaunchAgents/com.sparc.nuc-tunnel.plist
launchctl load  ~/Library/LaunchAgents/com.sparc.nuc-tunnel.plist
```

---

## NUC — Intel NUC5PGYHR (192.168.68.119)

**OS:** Ubuntu Server 24.04 LTS · **RAM:** 8 GB · **Storage:** 250 GB SSD  
**Role:** Production server — all 24/7 services run here.

### Running containers (13 total)

#### ⚡ Sparc Energy (8 containers)
| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `sparc-api` | FastAPI + LightGBM | 8000 | H+24 forecast, ControlEngine, Solar Advisory |
| `sparc-db` | TimescaleDB/PG16 | 5432 | Primary database — all relational + time-series |
| `sparc-redis` | Redis 7 | 6379 | Session cache · 256 MB cap |
| `sparc-grafana` | Grafana OSS 11 | 3001 | Energy dashboards |
| `sparc-caddy` | Caddy 2 | 80/443 | Reverse proxy · sparc.localhost |
| `sparc-prometheus` | Prometheus v2.52 | 9090 | Metrics scraper |
| `sparc-node-exporter` | node-exporter v1.8.1 | 9100 | Host metrics |
| `sparc-cadvisor` | cAdvisor v0.49.1 | 8082 | Container metrics (degraded — see note) |

#### 🌱 Gardening Digital Twin (4 containers)
| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `gardening-influxdb` | InfluxDB 2.7-alpine | 8086 | Sensor time-series (soil, LVPD, temp, humidity) |
| `gardening-grafana` | Grafana OSS 11 | 3000 | 25-panel greenhouse dashboard |
| `gardening-streamlit` | Streamlit custom | 8501 | Live hub — LVPD, GDD, harvest log, RAG |
| `gardening-poller` | Python custom | — | Ecowitt API → InfluxDB every 5 min |

#### 🔧 Shared Infrastructure (2 containers)
| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `sparc-n8n` | n8n 2.19 | 5678 | Automation — **5 active workflows** (see below) |
| `sparc-portainer` | Portainer CE | 9000 | Docker management UI for all NUC containers |

### n8n workflows on NUC (5 active)

| Workflow | Trigger | Action |
|----------|---------|--------|
| Sparc — Grafana Alert Relay | Grafana webhook | Format → Pushover (Sparc app token) |
| Greenhouse — Grafana Alert Relay | Grafana webhook | Format → Pushover (GH app token) |
| Sparc — Daily Morning Brief | 20:00 schedule | Call `/control` API → Pushover |
| Greenhouse — Daily Evening Summary | 20:00 schedule | Query InfluxDB → Pushover |
| Sparc — Weekly Drift Check | Sunday schedule | Call `/health` → Pushover if MAE critical |

Credentials: all via `$env.PUSHOVER_APP_TOKEN`, `$env.PUSHOVER_GH_TOKEN`, `$env.PUSHOVER_USER_KEY` — set in `~/sparc/.env` and passed through `docker-compose.yml`.

> **Note on cAdvisor:** cAdvisor fails to read container metrics on Ubuntu 24 due to overlay2 filesystem incompatibility. Workaround: `docker_stats_prom.sh` cron runs every 30s and writes container CPU% and RAM to node_exporter textfile collector. This is what the Grafana container panels read.

---

## Mac Laptop (development workstation)

**Role:** Code editing, testing, git push. Nothing production depends on this machine.

### Running containers (4, dev only)
| Container | Port | Purpose |
|-----------|------|---------|
| `sparc-api` | 8000 | Local dev API — test changes before push to NUC |
| `sparc-db` | 5432 | Local dev database — schema experiments, migration testing |
| `sparc-redis` | 6379 | Local dev cache |
| `influxdb3-enterprise` | 8086 | InfluxDB 3 Enterprise test instance for Gardening v3 migration (DAN-165) |

### Stopped containers (moved to NUC)
- `sparc-grafana` — stopped 2026-05-07 (NUC is authoritative)
- `sparc-n8n` — stopped 2026-05-07 (workflows migrated to NUC, NUC n8n is canonical)
- `sparc-caddy` — stopped 2026-05-07 (not needed on dev machine)

> **Why keep db/redis/api on Mac?** Local dev loop: edit code → `docker compose up sparc-api` → test at localhost:8000 → push to NUC. Avoids touching production during active development.

---

## Why Two Databases?

| Project | Database | Reason |
|---------|----------|--------|
| Sparc Energy | **TimescaleDB** (PostgreSQL) | `recommendations`, `households`, `tariff_changes` need `UPDATE`, FK constraints, sequences — impossible in any InfluxDB version (append-only) |
| Gardening | **InfluxDB 2.7** → **InfluxDB 3 Enterprise** (planned) | Pure append-only sensor streams — no relational model needed. Processing Engine plugins replace Grafana alert rules. |

See `docs/adr/ADR-012` for full decision record.

---

## Docker Desktop — What You See

Docker Desktop on Mac **only shows Mac-local containers** (sparc-api, sparc-db, sparc-redis, influxdb3-enterprise). NUC containers are invisible to Mac's Docker daemon.

**To see NUC containers:**
- **Terminal:** `ssh nuc "docker ps"`
- **Browser:** `http://localhost:9000` — Portainer (full web UI with logs, stats, exec, restart)

---

## Verify Everything Is Running
```bash
# NUC containers (all 13)
ssh nuc "docker ps --format 'table {{.Names}}\t{{.Status}}'"

# SSH tunnel (should show one ssh process with all port forwards)
ps aux | grep 'ssh.*192.168.68.119' | grep -v grep

# n8n workflows active
ssh nuc "docker exec sparc-n8n n8n export:workflow --all 2>/dev/null | python3 -c \"
import sys,json; data=json.load(sys.stdin)
[print(f'  {[\\\"paused\\\",\\\"active\\\"][w[\\\"active\\\"]]}: {w[\\\"name\\\"]}') for w in data]\""

# Portainer
curl -s http://localhost:9000/api/status | python3 -c "import sys,json; d=json.load(sys.stdin); print('Portainer:', d.get('Version','?'))"
```
