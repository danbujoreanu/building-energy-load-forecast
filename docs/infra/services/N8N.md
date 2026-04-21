# n8n — Workflow Automation Hub

**Status:** ✅ Running  
**URL:** http://localhost:5678  
**Container:** `sparc-n8n` (in Sparc Docker stack)  
**Version:** n8nio/n8n:latest (2.17.3 as of April 2026)  
**Linear:** DAN-94 ✅ Done  

---

## What's Running Right Now

All 5 workflows are **active**. They require `PUSHOVER_APP_TOKEN` in `.env` to deliver notifications.

| # | Workflow | Trigger | Action | Status |
|---|----------|---------|--------|--------|
| 1 | Sparc — Grafana Alert Relay | POST webhook | Pushover (priority HIGH) | ✅ Active |
| 2 | Greenhouse — Grafana Alert Relay | POST webhook | Pushover (priority HIGH) | ✅ Active |
| 3 | Sparc — Daily Morning Brief | 08:00 cron → `/control` | Pushover | ✅ Active |
| 4 | Greenhouse — Daily Evening Summary | 20:00 cron → InfluxDB | Pushover | ✅ Active |
| 5 | Sparc — Weekly Drift Check | Mon 09:00 → `/health` | Pushover if CRITICAL | ✅ Active |

For full workflow documentation, configuration details, and webhook URLs:
→ **`docs/infra/services/N8N_WORKFLOWS.md`**

---

## Quick Access

```bash
# Open n8n UI
open http://localhost:5678

# Check n8n container is healthy
docker compose ps | grep n8n

# Tail n8n logs
docker compose logs -f n8n --tail=30

# Verify env vars loaded
docker exec sparc-n8n env | grep -E "PUSHOVER|CALLMEBOT"

# Restart n8n (after .env changes)
docker compose up -d n8n
```

---

## Architecture

```
Sparc Grafana (port 3001) ─── http://n8n:5678/webhook/sparc-alert ──→ n8n WF1 → Pushover
GH Grafana (port 3000)    ─── http://host.docker.internal:5678/webhook/gh-alert ──→ n8n WF2 → Pushover
08:00 cron ───────────────── api:8000/control ──→ n8n WF3 → Pushover
20:00 cron ───────────────── host.docker.internal:8086 (InfluxDB) ──→ n8n WF4 → Pushover
Mon 09:00 ────────────────── api:8000/health ──→ n8n WF5 → Pushover (if CRITICAL)
```

n8n sits on the `sparc` Docker network alongside `api`, `db`, `redis`, `grafana`.  
Greenhouse reaches it via `host.docker.internal` (Mac host bridge between separate Docker stacks).

---

## Credentials (all in `.env`, gitignored)

| Variable | Value | Source |
|----------|-------|--------|
| `N8N_API_KEY` | `eyJ...` | n8n Settings → API → Create key |
| `PUSHOVER_APP_TOKEN` | `ar74vud1m3bz99i23nj57anjqsn8rt` | pushover.net/apps/build |
| `PUSHOVER_USER_KEY` | `usbzw4m19wwcht38mz631ycfnznemg` | pushover.net dashboard |
| `CALLMEBOT_PHONE` | `353863531001` | Backup channel |
| `CALLMEBOT_API_KEY` | `8022840` | Backup channel |

---

## Notification Delivery

**Primary: Pushover**
- Install app: App Store / Google Play → search "Pushover" → log in with account
- Notifications appear within 2–3 seconds of trigger
- Priority HIGH (1) for alerts; normal (0) for scheduled briefs
- Test:
```bash
source ~/building-energy-load-forecast/.env
curl -s \
  --form-string "token=${PUSHOVER_APP_TOKEN}" \
  --form-string "user=${PUSHOVER_USER_KEY}" \
  --form-string "title=Test" \
  --form-string "message=From Sparc n8n" \
  https://api.pushover.net/1/messages.json
```

**Backup: CallMeBot WhatsApp**
```bash
source ~/building-energy-load-forecast/.env
curl "https://api.callmebot.com/whatsapp.php?phone=${CALLMEBOT_PHONE}&text=Sparc+test&apikey=${CALLMEBOT_API_KEY}"
```

---

*File: `docs/infra/services/N8N.md` | Last updated: 21 April 2026*
