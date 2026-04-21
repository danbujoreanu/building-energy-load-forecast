# n8n — Shared Workflow Automation
## Sparc Energy + Greenhouse Digital Twin

**n8n is shared infrastructure.** One instance (in the Sparc stack) serves both projects.

| Project | Grafana reaches n8n via | Port |
|---------|------------------------|------|
| Sparc Energy | `http://n8n:5678` (Docker internal network) | 3001 |
| Greenhouse | `http://host.docker.internal:5678` (Mac host bridge) | 3000 |

**Notification channel: Pushover** (primary) — push notification app, €4.99 one-time, 30-day free trial.
CallMeBot WhatsApp credentials are stored in `.env` as a backup.

---

## Part 1 — One-Time Setup: Pushover App Token

Pushover requires two credentials: a **User Key** (identifies you) and an **App Token** (identifies the application).
You already have the User Key. You need to create an App Token.

### Step 1 — Create an application at pushover.net
1. Go to: **https://pushover.net/apps/build**
2. Fill in:
   - **Name**: `Sparc Energy`
   - **Type**: Application
   - **Description**: Energy forecasting & Greenhouse automation alerts
3. Click **Create Application**
4. Copy the **API Token/Key** shown on the confirmation page

### Step 2 — Add to .env
```bash
# Edit ~/building-energy-load-forecast/.env and set:
PUSHOVER_APP_TOKEN=your_token_here

# Then restart n8n to pick it up:
cd ~/building-energy-load-forecast
docker compose up -d n8n
```

### Step 3 — Test it
```bash
source .env
curl -s \
  --form-string "token=${PUSHOVER_APP_TOKEN}" \
  --form-string "user=${PUSHOVER_USER_KEY}" \
  --form-string "title=Sparc Test" \
  --form-string "message=Pushover is working" \
  https://api.pushover.net/1/messages.json
# Expected: {"status":1,"request":"..."}
```
You should get a push notification on your phone within a few seconds.

---

## Part 2 — n8n Workflows (already created via API)

All 5 workflows are already created and **activated** in n8n. They become fully functional
the moment `PUSHOVER_APP_TOKEN` is populated in `.env` and n8n is restarted.

### Workflow 1: Sparc — Grafana Alert Relay
- **Trigger**: Grafana webhook POST to `/webhook/sparc-alert`
- **Action**: Pushover push notification (priority HIGH)
- **Webhook URL for Sparc Grafana**: `http://n8n:5678/webhook/sparc-alert`

### Workflow 2: Greenhouse — Grafana Alert Relay
- **Trigger**: Grafana webhook POST to `/webhook/gh-alert`
- **Action**: Pushover push notification (priority HIGH)
- **Webhook URL for Greenhouse Grafana**: `http://host.docker.internal:5678/webhook/gh-alert`

### Workflow 3: Sparc — Daily Morning Brief (08:00)
- **Trigger**: Cron `0 8 * * *` (Europe/Dublin)
- **Action**: Calls `POST http://api:8000/control` → formats action + estimated saving → Pushover
- **Depends on**: DAN-96 (real meter data in TimescaleDB)

### Workflow 4: Greenhouse — Daily Evening Summary (20:00)
- **Trigger**: Cron `0 20 * * *` (Europe/Dublin)
- **Action**: Queries InfluxDB (Greenhouse) for last-hour canopy + soil readings → Pushover
- **Depends on**: `INFLUXDB_TOKEN` in `.env`

### Workflow 5: Sparc — Weekly Drift Check (Monday 09:00)
- **Trigger**: Cron `0 9 * * 1`
- **Action**: `GET http://api:8000/health` → if `drift_status == CRITICAL` → Pushover (priority HIGH)

---

## Part 3 — Webhook URLs Summary

| Workflow | Webhook URL | Used by |
|----------|-------------|---------|
| Sparc alert relay | `http://n8n:5678/webhook/sparc-alert` | Sparc Grafana (port 3001) |
| Greenhouse alert relay | `http://host.docker.internal:5678/webhook/gh-alert` | GH Grafana (port 3000) |
| Morning brief | — | Cron (no webhook) |
| Evening summary | — | Cron (no webhook) |
| Drift check | — | Cron (no webhook) |

---

## Part 4 — Notification Architecture

```
Sparc Grafana → http://n8n:5678/webhook/sparc-alert → n8n WF1 → Pushover → iOS/Android
GH Grafana    → http://host.docker.internal:5678/webhook/gh-alert → n8n WF2 → Pushover → iOS/Android
08:00 cron    → n8n WF3 → http://api:8000/control → Pushover → iOS/Android
20:00 cron    → n8n WF4 → InfluxDB → Pushover → iOS/Android
Mon 09:00     → n8n WF5 → http://api:8000/health → if CRITICAL → Pushover → iOS/Android
```

Env vars used in every Pushover node:
- `$env.PUSHOVER_APP_TOKEN` — application token (set once in .env)
- `$env.PUSHOVER_USER_KEY` — your Pushover user key

---

## Part 5 — Connecting Grafana Contact Points

### Sparc Grafana (port 3001)
Once DAN-96 has data and alert rules are configured (DAN-101):
1. Grafana → Alerting → Contact points → Add contact point
2. Type: `Webhook`
3. URL: `http://n8n:5678/webhook/sparc-alert`
4. HTTP Method: POST

### Greenhouse Grafana (port 3000)
In the Greenhouse stack's Grafana:
1. Grafana → Alerting → Contact points → Add contact point
2. Type: `Webhook`
3. URL: `http://host.docker.internal:5678/webhook/gh-alert`
4. HTTP Method: POST

---

## Part 6 — Credentials Reference

All credentials live in `~/building-energy-load-forecast/.env` (gitignored).

| Variable | Description | Status |
|----------|-------------|--------|
| `PUSHOVER_USER_KEY` | Your Pushover user key | ✅ Set |
| `PUSHOVER_APP_TOKEN` | Pushover app token — Sparc Energy app | ✅ Set |
| `PUSHOVER_GH_TOKEN` | Pushover app token — DT Greenhouse app (`aewujm4...`) | ✅ Set (Apr 21) |
| `INFLUXDB_GH_TOKEN` | GH InfluxDB token for WF4 daily summary | ✅ Set (Apr 21) |
| `CALLMEBOT_PHONE` | WhatsApp backup (353863531001) | ✅ Set |
| `CALLMEBOT_API_KEY` | CallMeBot API key | ✅ Set |
| `N8N_API_KEY` | n8n REST API key | ✅ Set |

**WF2 and WF4 use `PUSHOVER_GH_TOKEN`** — GH alerts appear as "DT Greenhouse" on phone.
**WF4 uses `INFLUXDB_GH_TOKEN`** to query `http://host.docker.internal:8086` (GH InfluxDB).

---

## Part 7 — Workflow Status (Apr 21 2026)

| Workflow | Status | Notes |
|---|---|---|
| WF1: Sparc — Grafana Alert Relay | ✅ Active | Awaiting DAN-101 (Grafana alert rules) |
| WF2: GH — Grafana Alert Relay | ✅ Active + configured | GH Grafana contact point provisioned, GH token set |
| WF3: Sparc — Daily Morning Brief | ✅ Active | Awaiting DAN-96 (real data) |
| WF4: GH — Daily Evening Summary (20:00) | ✅ Active + configured | InfluxDB GH token set, real sensor parsing in Format Message |
| WF5: Sparc — Weekly Drift Check | ✅ Active | Awaiting DAN-96 |

---

## Troubleshooting

```bash
# n8n won't start
docker compose logs n8n --tail=30

# Verify env vars loaded into n8n container
docker exec sparc-n8n env | grep -E "PUSHOVER|INFLUXDB_GH"

# Test GH alert chain end-to-end (fires Pushover "DT Greenhouse" app)
curl -s -X POST http://localhost:5678/webhook/gh-alert \
  -H "Content-Type: application/json" \
  -d '{"status":"firing","alerts":[{"labels":{"alertname":"Test"},"annotations":{"summary":"Manual test from CLI"}}]}'

# Test Pushover directly (Sparc app)
source ~/building-energy-load-forecast/.env
curl -s --form-string "token=${PUSHOVER_APP_TOKEN}" --form-string "user=${PUSHOVER_USER_KEY}" \
  --form-string "title=Sparc Test" --form-string "message=Direct test" \
  https://api.pushover.net/1/messages.json

# Test Pushover directly (GH app)
curl -s --form-string "token=${PUSHOVER_GH_TOKEN}" --form-string "user=${PUSHOVER_USER_KEY}" \
  --form-string "title=GH Test" --form-string "message=Direct test" \
  https://api.pushover.net/1/messages.json

# Greenhouse Grafana can't reach n8n
docker exec gh_grafana wget -qO- http://host.docker.internal:5678/healthz

# Verify GH Grafana alert rules loaded
curl -s -u admin:maynooth_gh_2026 http://localhost:3000/api/ruler/grafana/api/v1/rules | python3 -m json.tool | head -30
```

---

## Linear Tracking

| Issue | Status | What |
|-------|--------|------|
| DAN-94 | ✅ Done | n8n setup — all 5 workflows active, GH tokens configured Apr 21 |
| DAN-101 | 🟡 Todo | Sparc Grafana alert rules (configure after DAN-96 has data) |
| GARDEN-76 | ✅ Done | GH Grafana alerts + Pushover via n8n — live Apr 21 |

*File: `docs/infra/services/N8N_WORKFLOWS.md` | Last updated: 21 April 2026*
