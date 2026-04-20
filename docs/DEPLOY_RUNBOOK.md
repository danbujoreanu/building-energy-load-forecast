# Sparc Energy — End-to-End Deployment Runbook

**Purpose:** Exact sequence to go from code on Mac → full working system (local + cloud).  
**Test target:** Maynooth household — myenergi Eddi + ESB Smart Meter HDF CSV upload.  
**Last updated:** 2026-04-20 | **Status:** Phase 7 — App Runner not yet live

---

## Overview

```
LOCAL STACK (docker compose up)          CLOUD (AWS App Runner)
─────────────────────────────────        ──────────────────────
FastAPI :8000                            App Runner (eu-west-1)
PostgreSQL/TimescaleDB :5432       →     RDS PostgreSQL (future)
Redis :6379                              ElastiCache (future)
Grafana :3000                            CloudWatch metrics
Caddy (api.sparc.localhost)              App Runner HTTPS endpoint
ChromaDB (local, data/chromadb/)         S3 (model artefacts, future)
```

---

## STEP 1 — Local Full Stack (30 minutes, one-time)

### 1a. Prerequisites

```bash
# Verify Docker is running
docker --version  # Docker 24+

# Verify .env is populated
cat .env | grep -v '#' | grep '='
# Required: MYENERGI_API_KEY, GEMINI_API_KEY
# Optional: LINEAR_API_KEY, AZURE_OPENAI_API_KEY
```

### 1b. Start the full stack

```bash
cd ~/building-energy-load-forecast
docker compose up -d  # Starts FastAPI + PostgreSQL/TimescaleDB + Redis + Grafana + Caddy

# Wait ~30 seconds for TimescaleDB init, then verify:
docker compose ps  # All should be "running"
curl http://localhost:8000/health  # Should return {"status":"ok","model":"active",...}
```

### 1c. Verify each service

```bash
# FastAPI API
curl http://localhost:8000/health | python3 -m json.tool

# Grafana dashboard
open http://localhost:3001  # Login: admin / your GRAFANA_PASSWORD from .env
# Datasource: PostgreSQL at db:5432, database: sparc_energy (auto-provisioned)

# PostgreSQL
docker exec sparc-postgres psql -U sparc -d sparc -c "\dt"
# Should show: households, meter_readings, predictions, recommendations, outcomes
```

---

## STEP 2 — Ingest Smart Meter Data

### 2a. Upload your ESB HDF CSV

```bash
# Your ESB file path:
ESB_FILE="/Users/danalexandrubujoreanu/Downloads/HDF_calckWh_10306822417_22-10-2025.csv"

# Validate it first (dry run):
~/miniconda3/envs/ml_lab1/bin/python scripts/run_home_demo.py --csv "$ESB_FILE" --dry-run

# Full ingest:
~/miniconda3/envs/ml_lab1/bin/python scripts/run_home_demo.py --csv "$ESB_FILE"
```

### 2b. Run the morning brief

```bash
# Dry run (safe — no Eddi commands sent):
~/miniconda3/envs/ml_lab1/bin/python deployment/live_inference.py --dry-run

# Live run (sends real Eddi API calls if control actions triggered):
~/miniconda3/envs/ml_lab1/bin/python deployment/live_inference.py
```

Expected output:
```
=== Sparc Energy Morning Brief — 2026-04-21 ===
Forecast horizon: 24h (H+1 → H+24)
P50 load: 12.4 kWh | BGE cost: €5.02
Eddi recommendation: DEFER_HEATING (peak rate 17:00–19:00)
Top saving opportunity: Saturday free window 09:00–17:00 (next Sat)
```

### 2c. Check Eddi status

```bash
~/miniconda3/envs/ml_lab1/bin/python -c "
from deployment.connectors import MyEnergiConnector
c = MyEnergiConnector()
print(c.get_status())
"
```

---

## STEP 3 — Intel RAG First Ingestion (5 minutes)

```bash
# Run all RSS/Substack feeds (strategic + research + market tiers):
~/miniconda3/envs/ml_lab1/bin/python scripts/intel_feeds.py --ingest

# Ingest strategic docs if you've added PDFs to intel/docs/strategic/:
~/miniconda3/envs/ml_lab1/bin/python scripts/intel_ingest.py --tier strategic --dir intel/docs/strategic/

# Check all counts:
~/miniconda3/envs/ml_lab1/bin/python scripts/intel_ingest.py --status
```

---

## STEP 4 — n8n Local Setup (optional, zero cloud cost)

Based on `AI_PM_Portfolio_Notes/n8n_ClaudeCode_Integration.md`.  
**Purpose:** Workflow automation, agent telemetry, automated test-failure alerting.  
**Cost:** Zero — runs in Docker on your Mac.

### 4a. Add n8n to docker-compose

Edit `docker-compose.yml` — add this service (after the `grafana` block):

```yaml
  # ── n8n (Workflow Automation + Agent Orchestration) ──────────────────────
  n8n:
    image: n8nio/n8n:latest
    container_name: sparc-n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=localhost
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://localhost:5678
    volumes:
      - n8ndata:/home/node/.n8n
      - .:/home/node/sparc_energy:ro
    depends_on:
      - api
    restart: unless-stopped
    networks:
      - sparc

# Add to volumes section:
  n8ndata:
```

### 4b. Start n8n

```bash
docker compose up -d n8n
open http://localhost:5678  # n8n UI
```

### 4c. First workflows to build

| Workflow | Trigger | Action |
|----------|---------|--------|
| **Daily morning brief** | Cron 08:00 | POST to `http://api:8000/predict` → send WhatsApp/email |
| **Pytest failure alert** | Webhook on CI fail | Extract stack trace → Claude for diagnosis |
| **Intel feeds refresh** | Cron daily 06:00 | `exec: python scripts/intel_feeds.py --ingest` |
| **Drift alert** | Cron weekly | `exec: python scripts/run_drift_check.py --report` |

**Note:** n8n's Claude integration requires `ANTHROPIC_API_KEY` in docker-compose env vars.  
For the custom PR hook pattern, use `.claude/commands/sparc-pr.md` instead (no infra needed).

---

## STEP 5 — AWS App Runner Deploy (Phase 7)

**Prerequisites:** AWS account + AWS CLI configured + ECR repository created.  
See DAN-89 (AWS Activate) — apply at `aws.amazon.com/activate/founders/` first for $1,000 credits.

```bash
# Verify Makefile targets:
cat Makefile | grep -E "^docker|^ecr|^apprunner"

# Build Docker image:
make docker-build

# Push to ECR (requires AWS credentials):
export AWS_PROFILE=sparc-energy  # or set AWS_ACCESS_KEY_ID/SECRET
make ecr-push

# Deploy to App Runner:
make apprunner-deploy

# Smoke test live endpoint:
ENDPOINT=$(aws apprunner list-services --query 'ServiceSummaryList[0].ServiceUrl' --output text)
curl https://$ENDPOINT/health
```

**Expected after deploy:**
- `/health` → `{"status":"ok","model":"active"}`
- `/predict` → 24h forecast JSON
- `/intel/query` → RAG response

---

## STEP 6 — Grafana Dashboard Activation

After Step 1 (docker compose up), Grafana auto-provisions from `infra/grafana/provisioning/`.

**Key panels to verify:**
- Energy load forecast (last 7 days actual vs predicted)
- Drift report (KS statistic per feature)
- Control decisions (JSONL audit log → chart)
- Cost savings tracking (BGE tariff × shifted load)

```bash
# Generate some data first (run morning brief a few times or use historical CSV):
~/miniconda3/envs/ml_lab1/bin/python deployment/live_inference.py --dry-run

# Then open Grafana:
open http://localhost:3000
# Dashboard: "Sparc Energy — Operations"
```

---

## Sequence Priority

| Step | Time | Priority | Blocker |
|------|------|----------|---------|
| 1: docker compose up | 30 min | **Do first** | None |
| 2: Smart meter + morning brief | 10 min | **Do first** | Step 1 |
| 3: Intel RAG feeds | 5 min | **Do this week** (DAN-90) | None |
| 4: n8n local | 1 hour | Nice-to-have Sprint 2 | Step 1 |
| 5: AWS App Runner | 1-2 hours | **This week** (D-12) | AWS Activate credits |
| 6: Grafana review | 15 min | After Step 1 | Step 1 |

---

## What "End-to-End" Looks Like When Done

```
HDF CSV upload → FastAPI API
        ↓
LightGBM forecast (H+24)
        ↓
Morning brief: forecast + BGE cost + Eddi recommendation
        ↓
Grafana: live dashboard showing forecast vs actual, drift, savings
        ↓
(optional) n8n: daily cron triggers brief automatically
        ↓
(optional) App Runner: same API accessible from anywhere
```

The test: upload your ESB HDF file, run the morning brief, see the Eddi recommendation for today, check the Grafana dashboard shows the prediction, verify the JSONL audit log has an entry.
