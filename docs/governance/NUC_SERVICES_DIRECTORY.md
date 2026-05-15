# NUC Services Directory
*All services running on Intel NUC at 192.168.68.119*
*Last updated: 2026-05-10 | Tailscale: intelnuc.tailc0b176.ts.net*

---

## Quick Access

**On home WiFi:** use `192.168.68.119:PORT`  
**Anywhere (Tailscale):** use `intelnuc.tailc0b176.ts.net:PORT`  
**📌 Universal bookmark:** http://intelnuc.tailc0b176.ts.net:8501

| Service | Home WiFi | Tailscale (anywhere) | Notes |
|---------|-----------|---------------------|-------|
| **🌿 Streamlit Hub** (Gardening + Sparc Intel) | `:8501` | `intelnuc.tailc0b176.ts.net:8501` | Both projects, sidebar nav |
| **⚡ Sparc Grafana** | `:3001` | `intelnuc.tailc0b176.ts.net:3001` | Energy dashboards |
| **🌱 Gardening Grafana** | `:3000` | `intelnuc.tailc0b176.ts.net:3000` | Greenhouse dashboards |
| **🔧 n8n Automation** | `:5678` | `intelnuc.tailc0b176.ts.net:5678` | Workflows, alerts |
| **📊 Portainer** | `:9000` | `intelnuc.tailc0b176.ts.net:9000` | Docker management |
| **🔌 Sparc API** | `:8000` | `intelnuc.tailc0b176.ts.net:8000` | FastAPI backend |
| **📡 InfluxDB** | `:8086` | `intelnuc.tailc0b176.ts.net:8086` | Gardening sensor DB |
| **📈 Prometheus** | `:9090` | `intelnuc.tailc0b176.ts.net:9090` | NUC metrics (dev) |
| **🖥️ cAdvisor** | `:8082` | `intelnuc.tailc0b176.ts.net:8082` | Container stats (dev) |

---

## Grafana Dashboards (inside Sparc Grafana at :3001)

| Dashboard | Path | Description |
|-----------|------|-------------|
| **Sparc Overview** | `/d/sparc-overview` | Main energy dashboard — import/export, forecasts, recommendations |
| **Solar Pipeline** | `/d/solar-pipeline` | Solar capture vs GHI prediction, Eddi diversion, panel factor calibration |
| **Household Intelligence** | `/d/household-intelligence` | Per-household load, predictions, advisory log |
| **Meter Readings** | `/d/meter-readings` | ESB half-hourly import/export (when CSV uploaded) |
| **NUC Overview** | `/d/nuc-overview` | Container health, CPU, RAM, disk — powered by Prometheus |

---

## Database Access (developer only)

```bash
# PostgreSQL (Sparc energy data)
psql -h 192.168.68.119 -U sparc -d sparc_energy
# Password: in ~/sparc/.env → DB_PASSWORD

# InfluxDB (Gardening sensor data)
# Web UI: http://192.168.68.119:8086

# Redis (cache)
redis-cli -h 192.168.68.119
```

---

## Data Update Schedule

| What | When | Lag |
|------|------|-----|
| MyEnergi (import, Eddi, solar) | 00:15 daily (runs for yesterday) | ~1 day |
| Solar actuals sync | 00:45 daily | ~1 day |
| Weather forecast (7 days) | 06:00 daily | ~0 (updated nightly by Open-Meteo) |
| ESB meter CSV data | Manual upload | Up to 7 days behind |
| Greenhouse sensors | Every 5 min (live) | ~5 min |
| Forecasts (H+24) | 16:00 daily | Day-ahead |

**Practical rule:** If you want to see yesterday's energy data in Grafana, it will appear by 01:00.

---

## API Quick Reference

```bash
# Ask the energy system a question (no Terminal needed — use the chat UI at :8502)
curl -X POST http://192.168.68.119:8000/intel/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "how does the eddi work?"}'

# Check what's indexed in the knowledge base
curl http://192.168.68.119:8000/intel/status

# Health check
curl http://192.168.68.119:8000/health

# Get tomorrow's energy forecast
curl "http://192.168.68.119:8000/forecast/{household_id}"
```

---

## When Something Looks Wrong

| Symptom | Check | Fix |
|---------|-------|-----|
| Grafana shows no data for a day | Is the date < 1 day ago? | Wait until after midnight |
| MyEnergi data missing for a specific day | Check `/health` + container logs | Rerun backfill (see OPERATIONS_MANUAL.md) |
| Intel chat not working | http://192.168.68.119:8502 loads? | Check Portainer → sparc-intel-ui logs |
| n8n workflow not triggering | http://192.168.68.119:5678 | Check workflow is active |
| NUC running hot | Portainer → cAdvisor | Check what container is using CPU |

---

## Related Docs

- `OPERATIONS_MANUAL.md` — backfill procedures, restart commands, 2-week ops guide
- `INTEL_MODULE_DEPLOYMENT_EXPLAINED.md` — how the AI chat (Intel RAG) works
- `DATA_PIPELINE_ARCHITECTURE.md` — how data flows from meters → DB → Grafana
- `HARDWARE_STRATEGY.md` — NUC + Mac Mini M5 plan

---

*Generated from: `docker ps --format '{{.Names}}\t{{.Ports}}'` on NUC 192.168.68.119*
*Caddy reverse proxy (sparc-caddy) runs on :80/:443 — not listed above as it routes to the same services*
