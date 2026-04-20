# n8n — Local Workflow Automation

**What it is:** Visual workflow builder. Like Zapier or Make, but running entirely on your Mac — zero subscription cost.  
**Port:** 5678 (http://localhost:5678)  
**Status:** Not yet in docker-compose — add it with the steps below (10 minutes).  
**Linear:** DAN-94

---

## What n8n Does for Sparc Energy

| Workflow | Replaces | Benefit |
|----------|----------|---------|
| Daily morning brief at 08:00 | Manual `python deployment/live_inference.py` | Runs automatically while you sleep |
| Intel feeds refresh at 06:00 | Manual `python scripts/intel_feeds.py --ingest` | Always-fresh RAG knowledge |
| Weekly drift report | Manual `python scripts/run_drift_check.py` | Automatic alert if model degrades |
| Pytest failure alert | Checking GitHub manually | Instant notification if tests break |

---

## Step 1 — Add n8n to docker-compose.yml

Open `docker-compose.yml` in a text editor.

Find the `volumes:` section near the bottom (it looks like this):
```yaml
volumes:
  pgdata:
  redisdata:
  grafanadata:
  caddydata:
  caddyconfig:
```

**Add `n8ndata:` to that list:**
```yaml
volumes:
  pgdata:
  redisdata:
  grafanadata:
  caddydata:
  caddyconfig:
  n8ndata:          ← ADD THIS LINE
```

Then find the `grafana:` service block and paste the n8n service **after it** (before the `caddy:` block):

```yaml
  # ── n8n (Local Workflow Automation) ─────────────────────────────────────────
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
      - GENERIC_TIMEZONE=Europe/Dublin
    volumes:
      - n8ndata:/home/node/.n8n
      - ./scripts:/home/node/sparc_scripts:ro
    depends_on:
      - api
    restart: unless-stopped
    networks:
      - sparc
```

---

## Step 2 — Start n8n

```bash
cd ~/building-energy-load-forecast

# Start only n8n (if stack already running):
docker compose up -d n8n

# Or restart the whole stack:
docker compose up -d
```

---

## Step 3 — Open n8n and set up account

```bash
open http://localhost:5678
```

1. Create an account (local only — no email verification needed)
2. You'll see the n8n workflow editor

---

## Step 4 — Build Your First Workflow: Daily Morning Brief

This workflow runs `live_inference.py` every morning at 08:00.

### In the n8n UI:

1. Click **+ New Workflow**
2. Name it: `Sparc — Daily Morning Brief`
3. Add a **Schedule Trigger** node:
   - Mode: `Cron`
   - Cron Expression: `0 8 * * *` (8:00 AM every day)

4. Add an **HTTP Request** node (connected to Schedule Trigger):
   - Method: `POST`
   - URL: `http://api:8000/predict`
   - Body: `{"city": "ireland", "dry_run": false}`

5. Add an **Execute Command** node (optional — for running Python scripts directly):
   - Command: `python3 /home/node/sparc_scripts/intel_feeds.py --ingest`

6. Click **Save** → **Activate**

> The `api:8000` URL works because n8n is on the same `sparc` Docker network as the API.

---

## Useful Workflows to Build

### Intel Feeds Refresh (daily 06:00)
```
Schedule (0 6 * * *) → Execute Command: python3 /home/node/sparc_scripts/intel_feeds.py --ingest
```

### Weekly Drift Check
```
Schedule (0 9 * * 1) → Execute Command: python3 /home/node/sparc_scripts/run_drift_check.py --report
                     → IF drift = CRITICAL → HTTP POST to your email/WhatsApp
```

### Morning Brief + WhatsApp notification
```
Schedule (0 8 * * *) → HTTP POST api:8000/predict
                     → Extract P50 kWh + recommended action from response
                     → HTTP POST to Twilio/WhatsApp API (needs Twilio free account)
```

---

## Connecting to Claude / Anthropic API (optional)

If you want n8n to use Claude for summaries:

1. In n8n, go to **Settings → Credentials**
2. Add **Anthropic API** credential
3. Enter your `ANTHROPIC_API_KEY`
4. Use the **AI Agent** or **HTTP Request** node to call `api.anthropic.com`

---

## Troubleshooting

### n8n won't start
```bash
docker compose logs n8n --tail=20
# Common cause: port 5678 already in use
lsof -i :5678
```

### Workflows don't trigger
- Check the workflow is **Active** (toggle in top-right of workflow editor)
- Check the Schedule Trigger timezone matches `Europe/Dublin`

### Can't reach `api:8000` from n8n
Both services must be on the same Docker network. Verify:
```bash
docker network inspect building-energy-load-forecast_sparc | grep -E "sparc-api|sparc-n8n"
```
Both should appear. If n8n is missing: `docker compose restart n8n`

---

## Data n8n Can Access

Because `./scripts` is mounted as `/home/node/sparc_scripts:ro`, n8n's Execute Command nodes can run:
- `python3 /home/node/sparc_scripts/intel_feeds.py --ingest`
- `python3 /home/node/sparc_scripts/intel_ingest.py --status`
- `python3 /home/node/sparc_scripts/run_drift_check.py --report`

Note: These run inside the n8n container, which uses the n8n Python (not your conda env). For scripts needing `scikit-learn` / `lightgbm`, call the FastAPI endpoints instead of running scripts directly.
