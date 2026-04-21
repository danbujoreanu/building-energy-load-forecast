# Sparc Energy — Command Reference

**One place for every command you'll ever type.**  
Rule of thumb: anything starting with `docker`, `python`, `curl`, or `git` → Terminal.app. Anything visual → browser.

---

## How to open Terminal

Press **Cmd + Space**, type **Terminal**, press Enter.  
Then navigate to the project: `cd ~/building-energy-load-forecast`

---

## Docker Stack Commands

| What you want to do | Command |
|---------------------|---------|
| Start everything | `docker compose up -d` |
| Stop everything (data preserved) | `docker compose down` |
| Check what's running | `docker compose ps` |
| See live API logs | `docker compose logs -f api` |
| See all logs | `docker compose logs --tail=50` |
| Restart API after code change | `docker compose restart api` |
| Rebuild API image after code change | `docker compose build api && docker compose up -d api` |
| Wipe everything and start fresh | `docker compose down -v && docker compose up -d` |

---

## Verify the API is Up

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "inference_ready": true, "models": {"LightGBM": "real"}}
```

---

## Run the Home Energy Demo (Your ESB Data)

```bash
cd ~/building-energy-load-forecast
~/miniconda3/envs/ml_lab1/bin/python scripts/run_home_demo.py \
  --csv "data/ESB Smart Meter Data/HDF_calckWh_10306822417_20-04-2026.csv"
```

What it does: loads 2 years of your smart meter data, trains a LightGBM model on your actual consumption, and prints tomorrow's schedule with BGE tariff savings.

---

## Run the Morning Brief (Dry-run / No real data needed)

```bash
cd ~/building-energy-load-forecast
PYTHONPATH=src:. ~/miniconda3/envs/ml_lab1/bin/python -m deployment.live_inference --dry-run
```

---

## Run the Test Suite

```bash
cd ~/building-energy-load-forecast
PYTHONPATH=src ~/miniconda3/envs/ml_lab1/bin/python -m pytest tests/ -q
```

Expected: `178 passed` in ~10 seconds.

---

## Run the Full ML Pipeline (Norwegian data — ~30 min)

```bash
cd ~/building-energy-load-forecast
~/miniconda3/envs/ml_lab1/bin/python scripts/run_pipeline.py --city drammen
~/miniconda3/envs/ml_lab1/bin/python scripts/run_pipeline.py --city oslo
```

Only needed if you want to retrain models. Existing models in `outputs/models/` still work.

---

## Intel RAG Commands

```bash
cd ~/building-energy-load-forecast

# First-time ingest of energy market intelligence docs
~/miniconda3/envs/ml_lab1/bin/python scripts/intel_feeds.py --ingest

# Check status (how many docs/chunks in each tier)
~/miniconda3/envs/ml_lab1/bin/python scripts/intel_ingest.py --status

# Ingest a folder into a tier
~/miniconda3/envs/ml_lab1/bin/python scripts/intel_ingest.py \
  --tier strategic --dir intel/docs/strategic/
```

---

## Git Commands

```bash
# See what changed
git status
git diff

# Save your work
git add -p          # review changes interactively
git commit -m "your message"

# See recent commits
git log --oneline -10
```

---

## All Dashboards & Services — Quick Access

| Service | URL | Login | What it shows |
|---------|-----|-------|---------------|
| **Grafana** | http://localhost:3001 | admin / grafana_local_2026 | Model drift, consumption, API health, alert rules |
| **FastAPI docs** | http://localhost:8000/docs | — (no auth) | Swagger UI — test /health /predict /control |
| **FastAPI health** | http://localhost:8000/health | — | JSON: model status, drift, inference ready |
| **n8n workflows** | http://localhost:5678 | (your account) | 5 active workflows — view, edit, execution logs |
| **PostgreSQL** | localhost:5432 | sparc / sparc_local_2026 | TablePlus or psql — raw time-series data |
| **Redis** | localhost:6379 | — | redis-cli for cache inspection |

---

## Open Grafana Dashboard

Open a browser, type: **http://localhost:3001**  
Login: `admin` / `grafana_local_2026`

The "Sparc Energy — Overview" dashboard loads automatically.

---

## Open the API Docs (Swagger UI)

Open a browser, type: **http://localhost:8000/docs**

You can test `/health`, `/predict`, and `/control` directly from the browser — no curl needed.

---

## n8n Workflow Automation

Open: **http://localhost:5678**

### What's running (5 active workflows):
| Workflow | Trigger | What it does |
|----------|---------|-------------|
| Sparc — Grafana Alert Relay | Grafana webhook | Sends Pushover alert when Grafana fires |
| Greenhouse — Grafana Alert Relay | GH Grafana webhook | Same for Greenhouse |
| Sparc — Daily Morning Brief | 08:00 every day | Calls `/control` → sends energy forecast to phone |
| Greenhouse — Daily Evening Summary | 20:00 every day | Queries InfluxDB → sends GH summary |
| Sparc — Weekly Drift Check | Mon 09:00 | Calls `/health` → alerts if model drift is CRITICAL |

### Operating n8n day-to-day:
```bash
# View all workflow execution logs
open http://localhost:5678/executions

# Restart n8n (after .env changes or updates)
docker compose up -d n8n

# View n8n logs
docker compose logs -f n8n --tail=30

# Check env vars are loaded
docker exec sparc-n8n env | grep -E "PUSHOVER|CALLMEBOT"
```

### Webhook URLs for Grafana contact points:
- **Sparc Grafana** → `http://n8n:5678/webhook/sparc-alert`
- **Greenhouse Grafana** → `http://host.docker.internal:5678/webhook/gh-alert`

### To add a new workflow:
1. Open http://localhost:5678 → New Workflow
2. Or create via API: see `docs/infra/services/N8N_WORKFLOWS.md` for the Python script pattern used to create all 5 current workflows

Full reference: `docs/infra/services/N8N_WORKFLOWS.md`

---

## Pushover Push Notifications

Pushover delivers real-time push notifications from n8n to your phone.

**First time:** Install the **Pushover** app (App Store / Google Play) → log in with your account. You'll start receiving notifications immediately.

### Test Pushover manually:
```bash
source ~/building-energy-load-forecast/.env
curl -s \
  --form-string "token=${PUSHOVER_APP_TOKEN}" \
  --form-string "user=${PUSHOVER_USER_KEY}" \
  --form-string "title=Sparc Test" \
  --form-string "message=Pushover is working" \
  https://api.pushover.net/1/messages.json
# Expected: {"status":1,"request":"..."}
```

### Test a Grafana alert relay manually:
```bash
# Simulate what Grafana sends to n8n → gets forwarded to your phone
curl -s -X POST http://localhost:5678/webhook/sparc-alert \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Alert","state":"firing","ruleName":"Manual test"}'
```

---

## Where Commands Run

| Command type | Where to run | How to open |
|---|---|---|
| `docker compose ...` | Terminal.app | Cmd+Space → "Terminal" |
| `docker compose ps` | Terminal.app | Same window |
| `curl localhost:8000/health` | Terminal.app | Same window |
| `python scripts/...` | Terminal.app | Same window |
| `.env` file editing | TextEdit or VS Code | Right-click → Open With |
| Grafana dashboard | Browser | http://localhost:3001 |
| API Swagger docs | Browser | http://localhost:8000/docs |
| n8n workflow UI | Browser | http://localhost:5678 |
| n8n execution logs | Browser | http://localhost:5678/executions |
| Docker Desktop app | Just for watching | Click menu bar icon |

---

## Updating This Reference

If you run a new command that works and want to remember it — add it here.  
File location: `docs/infra/COMMAND_REFERENCE.md`
