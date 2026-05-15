# Sparc Energy — Operations Manual
*If Claude is offline, read this. Everything you need to operate the system yourself.*
*Last updated: 2026-05-09*

---

## The Golden Rules

1. **Edit code on your Mac in VS Code. Deploy to the NUC with rsync. Restart the right container.**
2. **Never edit files directly on the NUC** — changes will be overwritten next time you rsync.
3. **The database lives on the NUC. All queries run via `docker exec sparc-db psql ...`**
4. **If something breaks, check logs first. Don't restart blindly.**

---

## The Stack — What Runs Where

```
Your Mac (192.168.68.xxx)
  └── VS Code — edit code here
  └── rsync — push changes to NUC

NUC (192.168.68.119)  ssh dan@192.168.68.119
  └── Docker Compose: ~/sparc/docker-compose.yml
      ├── sparc-api        FastAPI app (scheduler, poller, advisory, RAG endpoints)
      ├── sparc-db         TimescaleDB (PostgreSQL) — all your data
      ├── sparc-grafana    Dashboards
      ├── sparc-redis      Cache (advisory, predictions)
      └── n8n              Workflow automation (morning briefing)
```

**SSH into NUC:**
```bash
ssh dan@192.168.68.119
```

**See what's running:**
```bash
ssh dan@192.168.68.119 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

---

## The Code Deploy Workflow (Mac → NUC)

This is the pattern for every code change:

```bash
# Step 1: Edit the file on your Mac in VS Code
# e.g. ~/building-energy-load-forecast/deployment/myenergi_poller.py

# Step 2: Rsync to NUC (run from Mac terminal)
rsync -av ~/building-energy-load-forecast/deployment/myenergi_poller.py \
  dan@192.168.68.119:/home/dan/sparc/deployment/myenergi_poller.py

# Step 3: Restart the container that uses the file
ssh dan@192.168.68.119 "docker restart sparc-api"

# Step 4: Check it started OK
ssh dan@192.168.68.119 "docker logs sparc-api --tail 20"
```

**Which container to restart:**

| File changed | Restart |
|---|---|
| `deployment/*.py` (poller, advisory, scheduler, routers) | `sparc-api` |
| `infra/grafana/provisioning/dashboards/*.json` | `sparc-grafana` |
| `infra/db/migrations/*.sql` | Apply manually (see below), then `sparc-api` |
| `.env` secrets | `sparc-api` (and any other container that uses them) |

---

## Editing Grafana Panels

### Option A: Edit the JSON in VS Code (recommended)

The dashboard JSON files are at:
```
~/building-energy-load-forecast/infra/grafana/provisioning/dashboards/
  ├── solar_pipeline.json         ← Solar Capture, GHI, advisory
  ├── household_intelligence.json ← Import, tariffs, Eddi
  └── nuc_health.json             ← NUC system metrics
```

**Finding a panel's SQL in VS Code:**
1. Open the JSON file
2. `Cmd+F` → search for the panel title, e.g. `"Daily Solar"`
3. Look for `"rawSql"` a few lines below — that's the SQL
4. Edit it directly
5. Rsync + restart Grafana:
```bash
rsync -av ~/building-energy-load-forecast/infra/grafana/provisioning/dashboards/solar_pipeline.json \
  dan@192.168.68.119:/home/dan/sparc/infra/grafana/provisioning/dashboards/solar_pipeline.json
ssh dan@192.168.68.119 "docker restart sparc-grafana"
```

**The panel JSON structure looks like this:**
```json
{
  "id": 34,
  "type": "timeseries",
  "title": "My Panel Title",
  "targets": [
    {
      "rawSql": "SELECT ... FROM ... WHERE ...",
      "format": "time_series"
    }
  ]
}
```
Only ever edit `rawSql`. Don't touch `id`, `type`, `gridPos` unless you know what you're doing.

### Option B: Edit in Grafana UI directly

1. Open Grafana: http://192.168.68.119:3000
2. Navigate to the dashboard → click the panel title → Edit
3. Change the SQL in the query editor
4. Click Apply / Save dashboard

**Warning:** Grafana UI saves go into the internal Grafana database, NOT back to the JSON file. If you ever re-provision (restart Grafana with `--reset-provisioned-dashboards`), UI edits will be lost. Always copy important SQL changes back to the JSON file in VS Code afterward.

### Testing a SQL query before putting it in a panel

```bash
ssh dan@192.168.68.119 "docker exec sparc-db psql -U sparc -d sparc_energy -c \"
SELECT
  DATE(interval_start AT TIME ZONE 'Europe/Dublin') AS day,
  ROUND(SUM(eddi_divert_kwh)::NUMERIC, 3) AS h1d_kwh
FROM myenergi_readings
WHERE interval_start >= CURRENT_DATE - 7
GROUP BY 1 ORDER BY 1;
\" 2>&1"
```

Paste any SQL between the inner quotes. Use `\"` to escape quotes inside.

---

## Running Database Queries

**Interactive psql session:**
```bash
ssh dan@192.168.68.119 "docker exec -it sparc-db psql -U sparc -d sparc_energy"
# Then type SQL directly, \q to exit
```

**Quick one-liner query:**
```bash
ssh dan@192.168.68.119 "docker exec sparc-db psql -U sparc -d sparc_energy -c \"SELECT COUNT(*) FROM myenergi_readings;\""
```

**Useful diagnostic queries:**

```sql
-- How many myenergi readings do we have?
SELECT MIN(interval_start), MAX(interval_start), COUNT(*) FROM myenergi_readings;

-- Last 7 days solar summary
SELECT DATE(interval_start AT TIME ZONE 'Europe/Dublin') AS day,
       ROUND(SUM(eddi_divert_kwh)::NUMERIC,3) AS h1d,
       ROUND(SUM(export_kwh)::NUMERIC,3) AS exp
FROM myenergi_readings WHERE interval_start >= CURRENT_DATE - 7 GROUP BY 1 ORDER BY 1;

-- What's in solar_actuals?
SELECT * FROM solar_actuals ORDER BY solar_date DESC LIMIT 10;

-- Check advisory_log
SELECT advisory_date, recommendation, ghi_forecast FROM advisory_log ORDER BY advisory_date DESC LIMIT 5;

-- Check if any APScheduler jobs are failing (look in API logs instead)
```

---

## Backfill Operations

### Re-fetch myenergi data for a date range

Use this if: data is missing, columns were added (like `eddi_divert_kwh`/`export_kwh`), or you suspect corrupt values.

```bash
# Step 1: Copy backfill script into the API container
ssh dan@192.168.68.119 "docker cp ~/sparc/scripts/myenergi_backfill.py sparc-api:/app/deployment/myenergi_backfill.py"

# Step 2a: Run for a specific date range (background, logs to /tmp/backfill.log)
ssh dan@192.168.68.119 "docker exec -d sparc-api sh -c \
  'python /app/deployment/myenergi_backfill.py \
   --start-date 2026-05-01 --end-date 2026-05-09 \
   > /tmp/backfill.log 2>&1'"

# Step 2b: Force-rewrite even if data already exists (use after formula/column fixes)
ssh dan@192.168.68.119 "docker exec -d sparc-api sh -c \
  'python /app/deployment/myenergi_backfill.py \
   --start-date 2023-01-20 --force \
   > /tmp/backfill.log 2>&1'"

# Step 3: Watch progress
ssh dan@192.168.68.119 "docker exec sparc-api tail -f /tmp/backfill.log"
# Ctrl+C to stop watching (doesn't stop the backfill)

# Step 4: Check when done
ssh dan@192.168.68.119 "docker exec sparc-api tail -5 /tmp/backfill.log"
# Look for: "Backfill complete — done: X, skipped: Y, failed: Z"
```

**How long does it take?** ~4-5 seconds per day (live API calls to your hub).
- 7 days = ~35 seconds
- 1 year = ~30 minutes
- Full history (2023-01-20 → today, ~1200 days) = ~90 minutes

### Backfill solar_actuals (ghi_forecast from advisory_log)

If `solar_actuals.ghi_forecast` is NULL, run this manually in psql:

```sql
UPDATE solar_actuals sa
SET ghi_forecast = al.ghi_forecast
FROM advisory_log al
WHERE al.advisory_date = sa.solar_date
  AND al.household_id  = '082fe72b-3c9c-48b1-9af8-c61875cad37f'
  AND al.ghi_forecast  IS NOT NULL
  AND sa.ghi_forecast  IS NULL;
```

### Backfill weather actuals (GHI from Open-Meteo)

If `weather_log` is missing actual GHI for past days (this runs automatically at 23:30 via the poller):

Trigger the nightly poller manually for a specific date via the API:
```bash
curl -X POST http://192.168.68.119:8000/admin/run-poll?date=2026-05-07
```
(Or just wait for tonight's 23:30 run to catch up the most recent day.)

---

## Manual Advisory Trigger

Send a Pushover advisory right now (useful for testing or if the 20:00 job missed):

```bash
curl -X POST http://192.168.68.119:8000/advisory/trigger
```

This generates the advisory for tomorrow and sends it to your phone immediately.

**Check what the advisory will say without sending it:**
```bash
curl http://192.168.68.119:8000/advisory/preview
```

---

## Checking Logs

```bash
# API logs (scheduler, poller, advisory errors)
ssh dan@192.168.68.119 "docker logs sparc-api --tail 50"
ssh dan@192.168.68.119 "docker logs sparc-api --tail 100 --since 1h"

# Grafana logs (panel errors, datasource issues)
ssh dan@192.168.68.119 "docker logs sparc-grafana --tail 30"

# n8n logs (workflow runs)
ssh dan@192.168.68.119 "docker logs n8n --tail 30"

# All containers, last 10 lines each
ssh dan@192.168.68.119 "for c in sparc-api sparc-db sparc-grafana; do echo \"=== \$c ===\"; docker logs \$c --tail 5 2>&1; done"
```

**What to look for:**
- `ERROR` or `Exception` in sparc-api logs → a job failed
- `[myenergi_poller] Done for YYYY-MM-DD` → nightly poll ran OK
- `[morning_advisory] Advisory sent` → Pushover was sent

---

## Applying a Database Migration

When a new migration SQL file is added (e.g. `011_myenergi_solar_capture.sql`):

```bash
# Option A: Apply from file
rsync -av ~/building-energy-load-forecast/infra/db/migrations/011_myenergi_solar_capture.sql \
  dan@192.168.68.119:/home/dan/sparc/infra/db/migrations/
ssh dan@192.168.68.119 "docker exec sparc-db psql -U sparc -d sparc_energy \
  -f /home/dan/sparc/infra/db/migrations/011_myenergi_solar_capture.sql"

# Option B: Run SQL directly (for short migrations)
ssh dan@192.168.68.119 "docker exec sparc-db psql -U sparc -d sparc_energy -c \
  \"ALTER TABLE myenergi_readings ADD COLUMN IF NOT EXISTS export_kwh NUMERIC(8,4);\""
```

Migrations are idempotent — they use `IF NOT EXISTS` so safe to re-run.

---

## Asking the AI About the System (RAG)

The `intel/` RAG pipeline is live. You can ask it questions about your system in plain English:

```bash
# Ask a question (replace the query with anything)
curl -X POST http://192.168.68.119:8000/intel/ask \
  -H "Content-Type: application/json" \
  -d '{"tier": "operational", "query": "How do I backfill myenergi data?", "top_k": 5}'

# Check what documents are indexed
curl http://192.168.68.119:8000/intel/status

# See available tiers
curl http://192.168.68.119:8000/intel/tiers
```

**Tiers:**
- `operational` — how-to guides, procedures, this manual
- `research` — ADRs, architecture decisions
- `strategic` — commercial analysis, roadmap docs

**Adding a new document to the index** (so the AI can answer questions about it):
```bash
# Step 1: Put the .md file in the right intel/ folder on your Mac
# e.g. ~/building-energy-load-forecast/intel/operational/OPERATIONS_MANUAL.md

# Step 2: Rsync the intel folder
rsync -av ~/building-energy-load-forecast/intel/ \
  dan@192.168.68.119:/home/dan/sparc/intel/

# Step 3: Re-ingest (triggers re-indexing of changed files)
curl -X POST http://192.168.68.119:8000/intel/ingest
```

The ingest is incremental — it only re-processes files whose content has changed (SHA-256 check). Safe to run anytime.

---

## What Runs Automatically (APScheduler Jobs)

You don't need to do these manually — they run on a schedule:

| Job | Time | What it does |
|-----|------|-------------|
| Morning advisory | 20:00 Dublin | Fetches tomorrow's GHI, sends Pushover |
| Weather forecast | 06:00 Dublin | Updates 7-day GHI forecast in weather_log |
| Nightly poll | 23:30 Dublin | Fetches today's myenergi data + GHI actual |
| Solar actuals sync | 23:45 Dublin | Upserts eddi_kwh + ghi_actual into solar_actuals |
| Panel factor update | 23:50 Dublin | Recalculates panel_factor_seasonal |
| Drift check | Sunday 08:00 | Compares forecast MAE 7d vs 28d |
| LP dispatch | 14:30 Dublin | Runs tomorrow's dispatch schedule |
| SEMO prices | 15:00 Dublin | Fetches day-ahead electricity prices |

**If a job failed**, check logs and trigger it manually if needed (see Advisory Trigger above).

---

## The Intel Folder Structure (RAG Documents)

```
~/building-energy-load-forecast/intel/
  operational/    ← how-to guides, procedures (this file belongs here)
  research/       ← architecture decisions, ADRs
  strategic/      ← commercial analysis, roadmap
  engineering/    ← technical deep-dives
```

**The more good documents in here, the better the AI answers.**

Current explainers live in:
```
~/Personal Projects/Energy (Sparc)/docs/explainers/
```
These are NOT auto-indexed — you need to copy relevant ones to `intel/` for the RAG to find them. Or you could symlink the folder (but keep in mind what goes into git — the intel folder is safe to push; personal explainers are local only).

---

## Emergency Procedures

### "Grafana shows no data"
1. Check sparc-db is running: `docker ps | grep sparc-db`
2. Check datasource: Grafana → Configuration → Data Sources → Test
3. Check the panel SQL manually via psql (copy SQL, run against DB)
4. Check for recent schema changes that broke a column name

### "I'm not getting Pushover notifications"
1. Check advisory job ran: `docker logs sparc-api --tail 50 | grep advisory`
2. Manual trigger: `curl -X POST http://192.168.68.119:8000/advisory/trigger`
3. Check env vars: `docker exec sparc-api env | grep PUSHOVER`

### "API is down"
```bash
ssh dan@192.168.68.119 "docker restart sparc-api && docker logs sparc-api --tail 30"
```

### "NUC is unreachable"
- Check it's powered on and connected to network
- SSH may need a minute after boot: `ping 192.168.68.119`
- If fully rebooted, Docker containers restart automatically (restart policy: unless-stopped)

### "I need to see all tables in the database"
```bash
ssh dan@192.168.68.119 "docker exec sparc-db psql -U sparc -d sparc_energy -c '\dt'"
```

### "I need to see the columns of a specific table"
```bash
ssh dan@192.168.68.119 "docker exec sparc-db psql -U sparc -d sparc_energy -c '\d myenergi_readings'"
```

---

## Key File Locations

| What | Path on Mac |
|------|-------------|
| All deployment code | `~/building-energy-load-forecast/deployment/` |
| Grafana dashboards | `~/building-energy-load-forecast/infra/grafana/provisioning/dashboards/` |
| DB migrations | `~/building-energy-load-forecast/infra/db/migrations/` |
| Backfill scripts | `~/building-energy-load-forecast/scripts/` |
| Explainers (local) | `~/Personal Projects/Energy (Sparc)/docs/explainers/` |
| Sprint tracker | `~/building-energy-load-forecast/docs/SPRINT.md` |
| Secrets (.env) | `~/sparc/.env` on the NUC only — never on Mac, never in git |

---

## Rotating or Adding the Anthropic API Key (Intel RAG)

The NUC RAG system (`/intel/ask`) uses a dedicated Anthropic key named **`Intel_NUC`** stored in `~/sparc/.env`.

**If the key stops working / needs rotating:**
1. Go to [console.anthropic.com](https://console.anthropic.com) → **API Keys** → **+ Create Key** → name it `Intel_NUC`
2. Copy the full `sk-ant-api03-...` key
3. On the NUC:
```bash
ssh dan@192.168.68.119
# Edit .env — replace old key or add new line:
nano ~/sparc/.env
# Add/update: ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE

# Recreate container so it picks up new .env (pip installs will need reinstalling — see below):
cd ~/sparc && docker compose up -d api
```
4. Reinstall intel deps after `docker compose up -d api` (they're not baked into the image yet):
```bash
docker exec sparc-api pip install --quiet chromadb==0.6.3 \
  'llama-index-core==0.12.52.post1' 'llama-index-vector-stores-chroma==0.4.2' \
  'llama-index-embeddings-huggingface==0.5.5' 'transformers==4.57.6' \
  'tokenizers==0.22.0' 'sentence-transformers==3.4.1' \
  'huggingface-hub==0.36.2' 'anthropic>=0.40.0'
docker restart sparc-api
```
5. Verify: `curl http://192.168.68.119:8000/intel/status` → should show `"docs": 18`

**If `/intel/ask` returns raw chunks instead of synthesised answer:**
- Check credit balance at console.anthropic.com → Plans & Billing → Add credits
- `docker logs sparc-api --tail 20 | grep -i claude` shows the exact error
- Raw chunk retrieval still works even with no credits / no key

**Why Claude Pro subscription doesn't work here:**
Claude Pro (€20/month at claude.ai) is a web chat interface. The NUC `/intel/ask` endpoint is *code* calling the Anthropic *API* — a completely separate product billed per token. They don't share a wallet.

**Preferred free alternative — Google Gemini:**
Gemini 2.0 Flash has a free tier (15 RPM, 1M tokens/day — more than enough for personal RAG use). Get a key at [aistudio.google.com](https://aistudio.google.com) → **Get API key**. No credit card required.

**To switch to Gemini (or add if Anthropic credits run out):**
```bash
ssh dan@192.168.68.119
echo 'GEMINI_API_KEY=AIzaSy...' >> ~/sparc/.env
cd ~/sparc && docker compose up -d api
# Reinstall intel deps after compose up (pip installs not yet in Docker image):
docker exec sparc-api pip install --quiet chromadb==0.6.3 \
  'llama-index-core==0.12.52.post1' 'llama-index-vector-stores-chroma==0.4.2' \
  'llama-index-embeddings-huggingface==0.5.5' 'transformers==4.57.6' \
  'tokenizers==0.22.0' 'sentence-transformers==3.4.1' \
  'huggingface-hub==0.36.2' 'anthropic>=0.40.0' 'google-generativeai'
docker restart sparc-api
```

The system tries Gemini first, then Claude, then falls back to raw context. Set whichever key you have.

**API keys summary:**
| Key name | Where stored | Purpose | Cost |
|----------|-------------|---------|------|
| `GitHub Secret` | GitHub → Settings → Secrets | CI/CD AI PR reviewer | Paid (Anthropic account) |
| `Intel_NUC` (`ANTHROPIC_API_KEY`) | `~/sparc/.env` on NUC | `/intel/ask` fallback synthesis | Paid per token |
| `GEMINI_API_KEY` | `~/sparc/.env` on NUC | `/intel/ask` preferred synthesis | **Free tier** |

---

## Going Deeper — The LLM Answer for Everything

Once this manual is indexed in the RAG (`intel/operational/`), you can ask it anything:

```bash
curl -X POST http://192.168.68.119:8000/intel/ask \
  -H "Content-Type: application/json" \
  -d '{"tier": "operational", "query": "How do I fix a missing day of myenergi data?", "top_k": 5}'
```

The response includes the answer plus which document it came from, so you can read the source if you need more depth.

**For questions Claude would normally answer** — the RAG is a reference tool, not a replacement. For complex new problems (bugs, new features, decisions), you still need a dev session. For "how do I do X that we've done before" — the RAG should have it.

---

*Maintained by: Claude (sessions) + Dan (review)*
*Add new procedures here every time a new manual operation is performed in a session.*
