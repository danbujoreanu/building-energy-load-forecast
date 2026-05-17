# TOKEN_EFFICIENCY_ENERGY.md — Sparc Energy Session Reference
*Project-specific token efficiency. Read alongside Orchestrator TOKEN_EFFICIENCY.md.*
*Last updated: 2026-05-17*

---

## 1. Pipeline — RAG Query Sequence

```
scripts/rag_query.py
  └── intel/retrieval.py :: query_tier(tier, question, top_k=5)
        ├── intel/embed.py :: get_embed_model(allow_fallback=True)
        │     └── UniVec API (api.univec.ai) → BGE-M3 1024-dim
        │           └── fallback: all-MiniLM-L6-v2 384-dim (if UniVec offline)
        ├── ChromaDB PersistentClient(CHROMA_PATH)
        │     └── collection: intel_{tier}
        ├── LlamaIndex VectorStoreIndex → top-k chunk retrieval
        └── Synthesis (in priority order):
              1. Gemini Flash Lite  if GEMINI_API_KEY set
              2. Ollama (llama3.2)  if localhost:11434 reachable
              3. Retrieval-only     top-k chunks concatenated, no LLM
```

**Key functions — do not guess names:**
- `query_tier(tier, question, top_k)` → `intel/retrieval.py` line ~104
- `query_all_tiers(question, top_k)` → same file
- **Wrong names that will ImportError:** `query_intel`, `query_rag`, `ask_intel`

**Synthesis model names (exact):**
- Gemini: `models/gemini-flash-lite-latest`
- Ollama fallback: `llama3.2:latest` (check `OLLAMA_MODEL` env var first)

---

## 2. File Map — Mac Source → NUC Deployed

| Purpose | Mac path | NUC path | Sync method |
|---------|----------|----------|-------------|
| RAG module | `intel/` | `/home/dan/sparc/intel/` | `rsync -av intel/ nuc:/home/dan/sparc/intel/` |
| Scripts | `scripts/` | `/home/dan/sparc/scripts/` | volume mount `:ro` |
| Deployment | `deployment/` | `/home/dan/sparc/deployment/` | volume mount `:rw` |
| ChromaDB (Mac) | `outputs/chromadb/` | n/a — Mac only | — |
| ChromaDB (NUC) | n/a | `/home/dan/sparc/outputs/chromadb/` | container volume |
| Config | `config/config.yaml` | not on NUC | Mac-only training |
| docker-compose | `docker-compose.yml` | `/home/dan/sparc/docker-compose.yml` | `rsync docker-compose.yml nuc:/home/dan/sparc/` |
| Grafana dashboard | `infra/grafana/provisioning/dashboards/nuc_overview.json` | `/home/dan/sparc/infra/grafana/provisioning/dashboards/` | `rsync` → auto-reload in 30s |
| Node Exporter metrics | n/a | `/var/node_exporter/textfiles/*.prom` | written by scheduler.py |

**Grafana rule:** rsync the JSON file, never call `/api/dashboards/db`. Provisioning auto-reloads in ≤30s.

**Container path root:** `/app/` inside `sparc-api` container maps to `/home/dan/sparc/` on NUC host.

---

## 3. Schema

### ChromaDB Collections (BGE-M3, 1024-dim — all collections)

| Collection | Owner | Mac chunks | NUC chunks | Source docs |
|------------|-------|-----------|-----------|-------------|
| `intel_operational` | Sparc/Energy | 351 | 327 | `intel/docs/operational/` |
| `intel_strategic` | Sparc/Energy | 49 | 46 | `intel/docs/strategic/` |
| `intel_regulatory` | Sparc/Energy | 42 | 47 | `intel/docs/regulatory/` |
| `intel_market` | Sparc/Energy | 46 | 46 | `intel/docs/market/` |
| `intel_career` | Career (Mac only) | 2,048 | — | `Career/intel/` + `Pipeline/` + `Closed/2026/` + strategy files |

**CHROMA_PATH:**
- Mac (conda ml_lab1): `outputs/chromadb/` (relative to project root)
- NUC (container): `/app/outputs/chromadb/` (env var `CHROMA_PATH`)

**Dimension lock:** Once a collection is created, its dimension is fixed. Changing embedding model = drop collection first, then re-ingest. Never restart ingest without dropping if model changed.

### Database — PostgreSQL + TimescaleDB (NOT InfluxDB)

Energy is the exception — it uses PostgreSQL, not InfluxDB. All other projects use InfluxDB.

| Table | Key columns | Purpose |
|-------|------------|---------|
| `meter_readings` | `household_id, ts, consumption_kwh, export_kwh` | ESB half-hourly data |
| `myenergi_readings` | `household_id, date, eddi_kwh, solar_kwh` | Daily MyEnergi totals |
| `weather_log` | `ts, ghi, temp_c, cloud_cover, precip_mm` | Open-Meteo 7-day forecast |
| `semo_prices` | `date, hour, price_eur_kwh, source` | Day-ahead SMP |
| `advisory_log` | `household_id, date, advisory_json, outcome` | Morning advisory + feedback |
| `lp_recommendations` | `household_id, date, hour, action` | LP dispatch schedule |
| `model_drift_log` | `household_id, checked_at, mae_7d, mae_28d, alert_sent` | Drift monitoring |

**DB connection:** `postgresql://sparc:${DB_PASSWORD}@db:5432/sparc_energy` (container) or `localhost:5432` (host).

### NUC Port Map (complete)

| Port | Service | Container |
|------|---------|-----------|
| 3000 | Gardening Grafana | gardening-grafana |
| 3001 | NUC Overview Grafana | sparc-grafana |
| 3002 | Health Grafana | health-grafana |
| 5678 | n8n | sparc-n8n |
| 7862 | Gardening RAG API | unified-rag-api |
| 7863 | Career RAG API | career-rag-api *(not built yet)* |
| 8000 | Sparc FastAPI + RAG | sparc-api |
| 8086 | Gardening InfluxDB | gardening-influxdb |
| 8087 | Health InfluxDB | health-influxdb |
| 8501 | Gardening Streamlit | gardening-streamlit |
| 8502 | Energy Streamlit | energy-streamlit |
| 8503 | Health Streamlit | health-streamlit |
| 9000 | Portainer | sparc-portainer |
| 9090 | Prometheus | sparc-prometheus |

---

## 4. Agent Model — 3 Tiers (mandatory)

**Always set `model:` explicitly. Never let it default to Sonnet for bulk work.**

| Tier | Model | Use for | Cost vs default |
|------|-------|---------|----------------|
| 1 | `haiku` | Reading batches of files, counting chunks, scanning logs, extracting patterns from >5 files | ~5× cheaper |
| 2 | `sonnet` | Generating explainers, architecture decisions, code synthesis, anything requiring judgment | default |
| 3 | `opus` | **Never for subagents** | — |

**Energy-specific Haiku tasks:**
- Scanning intel/docs/ for new files to ingest
- Reading multiple JD files for Career RAG ingest (200+ files = Haiku, always)
- Checking chunk counts across collections
- Parsing docker logs for errors

```python
# Correct pattern
Agent(description="scan intel/docs for changed files", model="haiku", prompt="...")
Agent(description="generate RAG_PIPELINE explainer", model="sonnet", prompt="...")
```

---

## 5. Copy-Paste Commands  

### RAG Queries (Mac, conda ml_lab1)
```bash
# Single tier query
python scripts/rag_query.py --tier operational --q "What is the BGE night rate?"

# All tiers
python scripts/rag_query.py --all --q "dynamic pricing obligations June 2026"

# Status — chunk counts per tier
python scripts/rag_query.py --status

# Interactive REPL
python scripts/rag_query.py --tier career --interactive
```

### Ingest Commands (NUC, inside sparc-api container)
```bash
# Changed files only (normal use)
docker exec sparc-api python3 /app/scripts/ingest_changed.py

# Single tier
docker exec sparc-api python3 /app/scripts/ingest_changed.py --tier operational

# Dry run — see what would be ingested
docker exec sparc-api python3 /app/scripts/ingest_changed.py --dry-run

# Force re-embed everything (after model change — drop collection first!)
docker exec sparc-api python3 /app/scripts/ingest_changed.py --force --tier operational
```

### Drop a ChromaDB collection (before re-ingest with new model)
```bash
docker exec sparc-api python3 -c "
import chromadb
c = chromadb.PersistentClient('/app/outputs/chromadb')
c.delete_collection('intel_operational')
print('dropped')
"
```

### Check collection chunk counts (NUC)
```bash
docker exec sparc-api python3 -c "
import chromadb
c = chromadb.PersistentClient('/app/outputs/chromadb')
for n in c.list_collections():
    print(n, '->', c.get_collection(n).count())
"
```

### Sync files Mac → NUC
```bash
# Intel module
rsync -av intel/ nuc:/home/dan/sparc/intel/

# docker-compose (then recreate container for new volume mounts)
rsync docker-compose.yml nuc:/home/dan/sparc/docker-compose.yml
ssh nuc "cd /home/dan/sparc && docker compose up -d api"

# Grafana dashboard (auto-reload in 30s — no API call needed)
rsync infra/grafana/provisioning/dashboards/nuc_overview.json \
  nuc:/home/dan/sparc/infra/grafana/provisioning/dashboards/nuc_overview.json
```

### Linear (read SPRINT.md instead of list_issues)
```bash
# NEVER: gh issue list → 28k tokens
# ALWAYS: cat docs/SPRINT.md → 200 tokens

# Update a Linear issue status (via API — only when needed)
curl -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { issueUpdate(id: \"ISSUE_ID\", input: {stateId: \"STATE_ID\"}) { success } }"}'
```

### NUC health checks
```bash
# All container CPU/RAM
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'

# NUC temperature
cat /sys/class/thermal/thermal_zone*/temp | awk '{printf "%.1f°C\n", $1/1000}'

# Disk usage
df -h / && docker system df
```

### NUC Diagnosis Sequence (when load is high)
```bash
# Step 1 — which container is hot?
ssh nuc "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' | sort -t$'\t' -k2 -rn"

# Step 2 — what's the actual host-level cause? (builds, runaway process)
ssh nuc "ps aux --sort=-%cpu | head -12"

# Step 3 — temperature + load
ssh nuc "uptime && cat /sys/class/thermal/thermal_zone*/temp | awk '{printf \"%.1f°C\n\", \$1/1000}'"
```

### Dead container blocking new start
```bash
# Symptom: "container is marked for removal and cannot be started"
ssh nuc "until ! docker ps -a --filter 'name=sparc-api' --format '{{.Status}}' | grep -q Dead; do sleep 2; done && docker compose up -d api"
```

---

## 6. Gotchas  

| Gotcha | What happens | Fix |
|--------|-------------|-----|
| **BGE-M3 dimension mismatch** | Ingest after model upgrade fails with `InvalidDimensionException` — ChromaDB collection is dimension-locked | Drop the collection first: `c.delete_collection('intel_X')`, then re-ingest |
| **`docker compose restart` doesn't reload `.env`** | New env vars (e.g. UNIVEC_API_KEY) absent → MiniLM fallback fires → 384-dim vectors written silently | Always use `docker compose up -d <service>` (container recreation) when env vars change |
| **SPRINT.md not `list_issues`** | `list_issues` = 28k tokens, `docs/SPRINT.md` = 200 tokens | Read file, never call API without `--filter` |
| **UniVec rate limiting (Errno 61)** | Concurrent ingest calls → `Connection refused` after ~3 files | `ingest_changed.py` has 0.5s sleep between files — don't bypass it |
| **`query_intel` / `query_rag` ImportError** | These function names don't exist | Correct names: `query_tier(tier, question)` and `query_all_tiers(question)` in `intel/retrieval.py` |
| **Grafana dashboard Grafana API vs rsync** | Calling `/api/dashboards/db` via Python-over-SSH = 3 tool calls + escaping hell | `rsync` JSON to provisioning dir → auto-reload in 30s. Only use API for datasources/folders |
| **`intel_career` lives on Mac, not NUC** | Querying `intel_career` via NUC sparc-api returns empty (collection not deployed) | Query from Mac conda env, or build Career NUC service (see `CAREER_NUC_RAG_SETUP.md`) |
| **Shared `.env` path** | NUC `.env` is at `~/sparc/.env` (not in repo). Mac `.env` at project root. Both needed separately. | Never commit `.env`. Append new vars: `echo "KEY=val" >> ~/sparc/.env` on NUC |
| **Grafana provisioned dashboard edit in UI** | Changes made in Grafana UI don't auto-save to the JSON file — diverges from repo within one session | Edit JSON on Mac → rsync → let provisioning reload. Never edit live and forget to save. |
| **`docker stats` sort cuts containers** | `head -10` on sorted output hides lower-CPU containers that may still be problematic | Remove `head` or sort by memory: `sort -t$'\t' -k3 -rn` |
| **Concurrent Docker builds on NUC** | Two simultaneous builds (e.g. Health + Gardening sessions both rebuild) → NUC load 9.7 on 4 cores, swap thrashing, both builds crawl | Check `ps aux \| grep 'docker.*build'` before triggering any build. Never build when load > 2.0. |
| **Python multiline over SSH** | `ssh nuc "python3 -c '...complex code...'"` — 3 escaping layers, hard to debug | Write script to `/tmp/check.py` via heredoc, then `docker exec ... python3 /tmp/check.py`. One round-trip, no escaping. |
| **`export_to_nuc.py` references purged collections** | Script still exports `intel_mba` + `intel_career` — both purged from Gardening on 2026-05-17 | Do not run this script without updating `EXPORT_COLLECTIONS` first. Stale as of 2026-05-17. |
| **Dropping a collection is not data loss** | ChromaDB collections are vector indexes only — source `.md` files on Mac are untouched | Any collection can be rebuilt by running `ingest_changed.py` against the source directory. Drop freely. |

---

## 7. Explainers Index — What to Read and When

| Situation | Read this |
|-----------|-----------|
| RAG pipeline not returning results / wrong tier | `docs/explainers/RAG_PIPELINE_EXPLAINED.md` |
| ChromaDB flush issues, HNSW errors on NUC | `docs/explainers/RAG_ON_NUC_EXPLAINED.md` |
| Morning advisory not sending / solar advisory logic | `docs/explainers/SOLAR_ADVISORY_EXPLAINED.md` |
| MyEnergi poller failing / BST timezone issue | `docs/explainers/MYENERGI_POLLER_EXPLAINED.md` |
| LP dispatch schedule questions | `docs/explainers/LP_DISPATCH_EXPLAINED.md` |
| Grafana dashboard panels / Prometheus queries | `docs/explainers/GRAFANA_DASHBOARDS_EXPLAINED.md` |
| ESB CSV upload pipeline / meter_readings table | `docs/explainers/METER_UPLOAD_PIPELINE_EXPLAINED.md` |
| End-to-end data flow from ESB CSV → Eddi | `docs/explainers/DATA_PIPELINE_LIVE_EXPLAINED.md` |
| Model drift alerts / Sunday scheduler | `docs/explainers/MLOPS_OBSERVABILITY_EXPLAINED.md` |
| n8n workflow publishing / WhatsApp alerts | `docs/explainers/N8N_WORKFLOWS_EXPLAINED.md` |
| Docker / container architecture overview | `docs/infra/DOCKER_BEGINNER_GUIDE.md` |
| NUC multi-project RAG ownership and architecture | `0. Orchestrator Command Centre/NUC_INFRASTRUCTURE.md` |
| Career NUC RAG setup (not yet built) | `0. Orchestrator Command Centre/CAREER_NUC_RAG_SETUP.md` |
| Why TimescaleDB not InfluxDB | `docs/adr/ADR-012-timescaledb-over-influxdb-sqlite.md` |
| Why LightGBM, not deep learning | `docs/adr/ADR-001-lightgbm-primary-model.md` |
| Tariff rates / BGE night/day/peak/free-sat | `intel/docs/operational/ENERGY_QUICK_REFERENCE.md` — RAG Pipeline section |
