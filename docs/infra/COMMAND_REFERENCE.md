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

## Open Grafana Dashboard

Open a browser, type: **http://localhost:3001**  
Login: `admin` / `grafana_local_2026`

The "Sparc Energy — Overview" dashboard loads automatically.

---

## Open the API Docs (Swagger UI)

Open a browser, type: **http://localhost:8000/docs**

You can test `/health`, `/predict`, and `/control` directly from the browser — no curl needed.

---

## Where Commands Run

| Command type | Where to run | How to open |
|---|---|---|
| `docker compose ...` | Terminal.app | Cmd+Space → "Terminal" |
| `docker compose ps` | Terminal.app | Same window |
| `curl localhost:8000/health` | Terminal.app | Same window |
| `python scripts/...` | Terminal.app | Same window |
| `.env` file editing | TextEdit or VS Code | Right-click → Open With |
| Grafana dashboard | Browser | Type `localhost:3001` |
| API Swagger docs | Browser | Type `localhost:8000/docs` |
| n8n workflow UI | Browser | Type `localhost:5678` (when added) |
| Docker Desktop app | Just for watching | Click menu bar icon |

---

## Updating This Reference

If you run a new command that works and want to remember it — add it here.  
File location: `docs/infra/COMMAND_REFERENCE.md`
