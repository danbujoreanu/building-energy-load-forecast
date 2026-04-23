# Sparc Energy — End-to-End Deployment Runbook
*Created: 2026-04-01 (approx) | Last modified: 2026-04-22*

**Purpose:** Exact sequence to go from code on Mac → full working system (local + cloud).  
**Test target:** Maynooth household — myenergi Eddi + ESB Smart Meter HDF CSV upload.  
**Status:** Phase 7 — App Runner deploy in progress | CI/CD active | Branch protection enforced

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
| **Pytest failure alert** | Webhook on CI fail | Extract stack trace → investigate and fix |
| **Drift alert** | Cron weekly | `exec: python scripts/run_drift_check.py --report` |

**Note:** n8n AI workflows require `ANTHROPIC_API_KEY` in docker-compose env vars.

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

---

## INCIDENT RESPONSE (DAN-102)

*Added 2026-04-22 | Equivalent: Standard Operating Procedure (SOP) for GxP/21 CFR Part 11 environments*

### Severity Classification

| Severity | Definition | Target response | Target recovery (MTTR) |
|----------|-----------|----------------|------------------------|
| **P1 — Critical** | System makes wrong automated decision that has been acted on (wrong Eddi command executed) | Immediate | 1 hour |
| **P2 — High** | API down, no predictions served, Eddi on fallback schedule | 30 minutes | 4 hours |
| **P3 — Medium** | Degraded accuracy (drift detected), Grafana unavailable, CI red | Next session | 24 hours |
| **P4 — Low** | Non-blocking: Redis cache miss storm, n8n cron skipped, myenergi API timeout | Next session | 48 hours |

---

### P1 — Wrong Automated Decision Executed

**Trigger:** Eddi received a wrong command (e.g. RUN_NOW during peak rate, or heat deferred when solar available)

```bash
# Step 1: Stop further automated commands immediately
python deployment/live_inference.py --dry-run  # Switch to dry-run mode

# Step 2: Check what command was sent and when
tail -20 outputs/logs/control_decisions.jsonl | python3 -m json.tool

# Step 3: Check Eddi current state
python -c "
from deployment.connectors import MyEnergiConnector
c = MyEnergiConnector()
print(c.get_status())
"

# Step 4: Manual override if needed (via myenergi app)
# myenergi app → Eddi → Boost → Manual

# Step 5: Root cause — check the decision reasoning in the JSONL
# Fields: timestamp, action, confidence, reasoning, forecast_values, price, solar

# Step 6: Document in post-incident review (template below)
```

**Post-incident:** Do not resume automated control until root cause is identified and a regression test added.

---

### P2 — API Down / Predictions Not Serving

**Trigger:** `/health` returns 503 or connection refused

```bash
# Step 1: Check all containers
docker compose ps
# All services should show "running" — identify any "exited" or "restarting"

# Step 2: Restart specific failed service
docker compose restart api    # FastAPI
docker compose restart db     # TimescaleDB
docker compose restart redis  # Redis cache

# Step 3: Check logs for root cause
docker compose logs api --tail 50
docker compose logs db  --tail 50

# Step 4: Verify recovery
curl http://localhost:8000/health | python3 -m json.tool
# Expected: {"status":"ok","model":"active or mock"}

# Step 5: If model is "mock" after restart — model artefact missing
ls outputs/models/  # Should contain .pkl files
# If empty: retrain
python scripts/run_pipeline.py --city ireland --save-predictions
```

**Escalation path:** If TimescaleDB data is corrupted → restore from Docker volume backup (see backup procedure below).

---

### P3 — Model Drift Detected

**Trigger:** `scripts/run_drift_check.py` exits with code 1 (CRITICAL), CI blocks deployment

```bash
# Step 1: Run drift report to understand which features drifted
python scripts/run_drift_check.py --city ireland --report

# Step 2: Check when drift started (compare recent vs training distribution)
# Key features to inspect: lag_24h, temperature, hour_of_day

# Step 3: Decision tree
# If < 7 days of new data look odd → data quality issue (check ESB upload)
# If seasonal → expected; retrain with recent window
# If sudden → check if ESB data format changed (new meter firmware)

# Step 4: Retrain with recent data
python scripts/run_pipeline.py --city ireland --save-predictions
python scripts/run_drift_check.py --city ireland  # Must pass before deploying

# Step 5: Promote new model via registry
python -c "
from src.energy_forecast.registry.model_registry import ModelRegistry
r = ModelRegistry()
r.promote_candidate()  # Only if new model beats current by >5% MAE
"
```

---

### P3 — CI Red / Blocked Deployment

**Trigger:** GitHub Actions failure email; merge button disabled for all PRs

```bash
# Step 1: Identify failing check from GitHub Actions UI
# Settings → Actions → All workflows → find failing run

# Step 2: Common causes and fixes
# Tests (3.10 or 3.11) red → run locally: pytest tests/ -v --tb=short
# Code quality red → run locally: black --check src/ && ruff check src/
# Docker build red → run locally: docker build -f deployment/Dockerfile -t test .

# Step 3: Fix on a branch, open PR, verify CI green, merge
# Do NOT push directly to main — branch protection blocks it
```

---

### Rollback Procedure

**Model rollback** (production model degraded after promotion):
```bash
python -c "
from src.energy_forecast.registry.model_registry import ModelRegistry
r = ModelRegistry()
r.rollback()  # Promotes last RETIRED model back to ACTIVE
"
```

**Code rollback** (bug introduced in last merge):
```bash
# Find last known-good commit
git log --oneline -10

# Create a revert PR (do NOT force-push main — branch protection prevents it)
git revert <bad-commit-sha>
git checkout -b fix/revert-bad-commit
git push -u origin fix/revert-bad-commit
# Open PR → CI runs → merge
```

**Full stack rollback** (complete disaster recovery):
```bash
docker compose down
git checkout <last-good-tag-or-sha>
docker compose up -d
# Restore model artefacts if needed
python scripts/run_pipeline.py --city ireland --save-predictions
```

---

### Backup Procedure

TimescaleDB data (meter readings, predictions, outcomes) lives in a Docker named volume.

```bash
# Backup
docker run --rm \
  -v building-energy-load-forecast_pgdata:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/tsdb_$(date +%Y%m%d).tar.gz /data

# Restore
docker run --rm \
  -v building-energy-load-forecast_pgdata:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/tsdb_YYYYMMDD.tar.gz -C /
```

**Backup schedule:** Manual before any schema migration or major upgrade. No automated backup in Phase 7 — add to Phase 8 ops scope.

---

### Post-Incident Review Template

After any P1 or P2 incident, create a file `docs/incidents/YYYY-MM-DD-short-title.md`:

```markdown
# Incident: <title>
**Date:** YYYY-MM-DD
**Severity:** P1 / P2
**Duration:** X hours (detection → resolution)

## What happened
[1–3 sentences: what the system did wrong]

## Impact
[What was affected: predictions, Eddi commands, user experience]

## Root cause
[Single sentence — the actual cause, not a symptom]

## Timeline
- HH:MM — detected
- HH:MM — investigation started
- HH:MM — root cause identified
- HH:MM — fix deployed
- HH:MM — system verified healthy

## Fix
[What was changed]

## Prevention
[What regression test / alert was added to prevent recurrence]
```

---

## STAGE GATE CRITERIA (DAN-103)

*Each phase of the pipeline has explicit entry and exit conditions. No phase proceeds without exit criteria met.*

| Phase | Entry criteria | Exit criteria | Evidence required |
|-------|---------------|---------------|-------------------|
| **Data Ingestion** | Raw CSV available; schema validated | Zero NaN rows in `meter_readings`; DST handling verified; row count matches expected | `DataValidator.validate_features()` passes; TimescaleDB row count |
| **Feature Engineering** | `meter_readings` populated; weather data available | Exactly 35 features produced; no future leakage (lag < forecast_horizon); `build_temporal_features()` assertion passes | `len(X.columns) == 35`; integration test DAN-104.3 passes |
| **Model Training** | Features validated; train/val/test split created with `gap=168` | LightGBM MAE ≤ 5.0 kWh (Drammen), ≤ 8.0 kWh (Oslo); R² ≥ 0.95; DM test vs Ridge p < 0.05 | `final_metrics.csv`; `significance_test.py` output |
| **Model Promotion** | New model trained; `drift_detector.py` passes | New model MAE ≤ 1.05 × current ACTIVE model MAE (regression gate ≤ 5%) | `model_registry.py` promotion log; CI drift check passes |
| **API Deployment** | Docker image builds; `/health` returns ok | All 4 CI checks green; `/predict` returns 24-array; `/control` returns valid ActionDecision | GitHub Actions CI; PR merged to main |
| **Production Deploy** | CI green; Docker image in ECR | App Runner serving `/health` → ok; P50 forecast within ±10% of local; JSONL audit log writing | `curl https://<apprunner-url>/health`; CloudWatch logs |
| **Governance Sign-off** | All 6 governance artefacts complete | Model Card, AIIA, Data Lineage, Data Provenance, System Component Map, System Access Model all present and reviewed | `docs/governance/` directory; last modified dates current |
