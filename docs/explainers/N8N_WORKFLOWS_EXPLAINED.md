# n8n Workflows — Explainer
*Sparc Energy Ltd — automation layer for scheduled notifications and webhook relay*
*Created: 2026-05-07 | Instance: `sparc-n8n` on NUC (shared with Gardening project)*

---

## Overview

`sparc-n8n` runs on the NUC as a shared n8n v2 instance. It is the automation layer for:
- **Scheduled notifications** — Pushover alerts on a daily/weekly cron
- **Webhook relay** — Grafana alert webhooks forwarded to Pushover

Both the Sparc Energy and Gardening projects use this single n8n instance.

---

## Active Workflows

| Workflow ID | Name | Type | Schedule | Project |
|-------------|------|------|----------|---------|
| `IPAbqfpUftTFtoOy` | Sparc — Daily Morning Brief | Schedule | 20:00 Dublin | Energy |
| `ZbrEOQ55EaqtQmLR` | Greenhouse — Daily Evening Summary | Schedule | 20:00 Dublin | Gardening |
| `996nwSOt2x5jS0tx` | Sparc — Weekly Drift Check | Schedule | Mon 08:30 Dublin | Energy |
| `vrcsKrPc3sM1fsEy` | Sparc — Grafana Alert Relay | Webhook | POST `/sparc-alert` | Energy |
| `gJuktIk3Y1OdiBS1` | Greenhouse — Grafana Alert Relay | Webhook | POST `/gh-alert` | Gardening |

> **Note:** `9Nvl4l7VRubEoNo6` (DAN-89 AWS deadline) is inactive and can be deleted.

---

## n8n v2 Workflow Publishing — Critical Gotcha

### The problem

n8n v2 introduced a **draft / published** versioning system. A workflow can be:
- **Active** (`active = 1` in DB) — the toggle is on
- **Published** — a specific version has been explicitly published

**Schedule triggers only fire for published workflows.** A workflow that is `active` but has never been published will not run on its cron schedule. Webhook-type workflows activate regardless.

The startup log confirms this:
```
Finished building workflow dependency index. Processed N draft workflows, 0 published workflows.
```
If you see `0 published workflows`, no schedule-based notifications will fire that day.

### When this breaks

Any operation that **imports workflows** (via the n8n UI Import, backup restore, or `n8n import:workflow` CLI) creates new draft versions without publishing them. After an import:
- All schedule-based workflows silently stop firing
- Webhook workflows continue to work (they only need `active = 1`)
- No error is logged when a schedule is missed — it simply doesn't run

### How to fix (UI — preferred)

1. Open n8n at `http://localhost:5678` (SSH tunnel) or `http://192.168.68.119:5678` (direct LAN)
2. For each schedule-based workflow: open it → click **Publish** (top-right button)
3. Verify the startup log on next restart shows `N published workflows` > 0

### How to fix (DB — emergency, when UI is unavailable)

Stop n8n, patch the SQLite database, restart:

```bash
# Stop n8n
docker stop sparc-n8n

# Copy DB
docker cp sparc-n8n:/home/node/.n8n/database.sqlite /tmp/n8n.sqlite

# Publish latest version of each active workflow
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('/tmp/n8n.sqlite')

rows = conn.execute('''
    SELECT wh.workflowId, wh.versionId
    FROM workflow_history wh
    INNER JOIN (
        SELECT workflowId, MAX(createdAt) AS maxDate
        FROM workflow_history GROUP BY workflowId
    ) latest ON wh.workflowId = latest.workflowId AND wh.createdAt = latest.maxDate
    INNER JOIN workflow_entity we ON we.id = wh.workflowId
    WHERE we.active = 1
''').fetchall()

for workflowId, versionId in rows:
    conn.execute(
        'INSERT OR REPLACE INTO workflow_published_version (workflowId, publishedVersionId) VALUES (?, ?)',
        (workflowId, versionId)
    )
conn.commit()
print(f'Published {len(rows)} workflows')
conn.close()
EOF

# Copy DB back and restart
docker cp /tmp/n8n.sqlite sparc-n8n:/home/node/.n8n/database.sqlite
docker start sparc-n8n
```

**Verify:** on startup, log should say `Start Active Workflows:` followed by activated webhook workflows.

---

## APScheduler vs n8n — What Runs Where

There are **two separate scheduling systems** on the NUC. Do not confuse them:

| Job | Where | Trigger | Failure mode |
|-----|-------|---------|--------------|
| Energy evening advisory (Pushover) | `sparc-api` APScheduler | 20:00 Dublin | `RuntimeError: no event loop in thread` — see §APScheduler below |
| Gardening evening summary (Pushover) | `sparc-n8n` | 20:00 Dublin | Workflow in draft state — see §Publishing above |
| Sparc weekly drift check | `sparc-n8n` | Mon 08:30 Dublin | Same as above |
| Sparc myenergi poll / solar actuals / data quality | `sparc-api` APScheduler | 23:30–23:55 | Same as APScheduler below |

---

## APScheduler Coroutine Bug — Fixed 2026-05-07

### The problem

All 10 APScheduler jobs in `deployment/scheduler.py` were registered as sync lambdas:

```python
# BROKEN — do not use this pattern
scheduler.add_job(
    lambda: asyncio.ensure_future(_run_morning_advisory(app)),
    CronTrigger(hour=20, minute=0),
    id="morning_advisory",
)
```

`AsyncIOScheduler` dispatches **sync functions** to a `ThreadPoolExecutor`. Inside that thread there is no asyncio event loop, so `asyncio.ensure_future()` raises:

```
RuntimeError: There is no current event loop in thread 'ThreadPoolExecutor-0_0'.
RuntimeWarning: coroutine '_run_morning_advisory' was never awaited
```

The job fires and is logged as run, but the actual advisory function never executes.

### The fix

Pass the coroutine function directly. `AsyncIOScheduler` detects `async def` functions and schedules them in the event loop correctly:

```python
# CORRECT
scheduler.add_job(
    _run_morning_advisory,
    CronTrigger(hour=20, minute=0),
    id="morning_advisory",
    args=[app],
)
```

Applied to all 10 jobs on 2026-05-07. No other code changes required.

### Affected jobs (all fixed)

| Job ID | Function | Schedule |
|--------|----------|----------|
| `daily_inference` | `_run_scheduled_inference` | 16:00 |
| `morning_advisory` | `_run_morning_advisory` | 20:00 |
| `weather_forecast_poll` | `_run_weather_forecast_poll` | 06:00 |
| `data_gap_check` | `_check_data_gaps` | 09:00 |
| `myenergi_poll` | `_run_myenergi_poll` | 23:30 |
| `solar_actuals_sync` | `_sync_solar_actuals` | 23:45 |
| `data_quality_check` | `_run_data_quality_check` | 23:55 |
| `weekly_quality_report` | `_run_weekly_quality_report` | Mon 08:30 |
| `drift_check_sunday` | `_check_drift_sunday` | Sun 02:00 |
| `semo_price_fetch` | `_fetch_semo_prices` | 14:00 |
| `lp_dispatch` | `_run_lp_dispatch` | 14:30 |

---

## Diagnosing Missing Notifications

Run through this checklist when a Pushover notification is missing:

```bash
# 1. Was the APScheduler job attempted?
ssh nuc "docker logs sparc-api --since 2026-05-07T19:00:00 2>&1 | grep -v 'GET /health'"
# Look for: "Running job" + any ERROR or "raised an exception"

# 2. Did n8n workflows fire?
ssh nuc "docker logs sparc-n8n --tail 30 2>&1"
# Look for: "Processed N draft workflows, 0 published workflows" (= publishing issue)
# Look for: "Task rejected by Runner" (= task runner timing issue)

# 3. Are n8n workflows published?
docker cp sparc-n8n:/home/node/.n8n/database.sqlite /tmp/n8n.sqlite
python3 -c "import sqlite3; conn=sqlite3.connect('/tmp/n8n.sqlite'); print(conn.execute('SELECT COUNT(*) FROM workflow_published_version').fetchone())"
# Should be > 0

# 4. Test advisory manually
docker exec sparc-api python -c "
import asyncio, datetime
from deployment.morning_advisory import build_advisory, send_pushover
tomorrow = datetime.date.today() + datetime.timedelta(days=1)
adv = asyncio.run(asyncio.to_thread(build_advisory, tomorrow, None, None))
print(adv)
send_pushover(adv)
"
```

---

## Import Safety Rule

**Before importing any workflow into `sparc-n8n`:** note that the import will reset that workflow to draft state. After any import affecting schedule-based workflows, immediately go to the n8n UI and click **Publish** on the affected workflows.

This affects both the Sparc Energy and Gardening projects sharing this instance.

---

## Reviewing All Alerts and Their Logic

### Alert flow end-to-end

```
Grafana (evaluates every 5 min)
  → rule condition met for pending duration
  → fires POST to n8n webhook URL
  → n8n WF2/WF5 formats and forwards
  → Pushover → iOS notification
```

### Gardening Grafana alert rules

Defined in: `Greenhouse/digital_twin/grafana/provisioning/alerting/alert_rules.yaml`
Datasource: InfluxDB 2.7 NUC (`greenhouse-influxdb`, Flux queries)
Evaluation group: `greenhouse-climate`, interval: 5m

| Rule UID | Title | Condition | Pending | Severity |
|---|---|---|---|---|
| `botrytis-risk` | Botrytis Risk | LVPD mean (10m) **< 0.4 kPa** | 10m | critical |
| `heat-stress` | Heat Stress | Canopy temp mean (10m) **> 32°C** | 10m | critical |
| `water-stress` | Water Stress | LVPD mean (20m) **> 1.5 kPa** | 20m | warning |
| `dry-soil-gh4n` | Dry Soil GH4 North | Soil moisture GH4N last (15m) **< 25%** | 15m | warning |
| `dry-soil-gh4s` | Dry Soil GH4 South | Soil moisture GH4S last (15m) **< 25%** | 15m | warning |

**Note:** rules fire on *sustained* breaches — e.g. heat-stress requires 32°C for a full 10 minutes before alerting.

### Sparc Energy Grafana alert rules

Defined in Sparc Grafana provisioning. Webhook URL: `http://192.168.68.119:5678/webhook/sparc-alert`.

### Check current alert state

```bash
# View all firing/pending alerts in Gardening Grafana
curl -s http://localhost:3000/api/alertmanager/grafana/api/v2/alerts \
  -u admin:maynooth_gh_2026 | python3 -c "
import sys, json
alerts = json.load(sys.stdin)
if not alerts:
    print('No active alerts')
for a in alerts:
    labels = a.get('labels', {})
    status = a.get('status', {}).get('state', '?')
    print(f\"[{status.upper()}] {labels.get('alertname','?')} | {labels.get('zone','')}\")
"

# View alert rule evaluation state
curl -s http://localhost:3000/api/prometheus/grafana/api/v1/rules \
  -u admin:maynooth_gh_2026 | python3 -c "
import sys, json
d = json.load(sys.stdin)
for group in d.get('data', {}).get('groups', []):
    for rule in group.get('rules', []):
        print(f\"{rule['state']:10} {rule['name']}\")
"
```

### Test the webhook relay end-to-end

```bash
# Send a test alert payload to the Greenhouse n8n webhook
curl -s -X POST http://localhost:5678/webhook/gh-alert \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {"alertname": "TestAlert", "severity": "warning"},
      "annotations": {"summary": "Test from curl — ignore"}
    }]
  }'
# Expected: {"message":"Workflow was started"}
# Expected outcome: Pushover notification in "DT Greenhouse" app within ~5 seconds

# Same for Sparc relay
curl -s -X POST http://localhost:5678/webhook/sparc-alert \
  -H "Content-Type: application/json" \
  -d '{"alerts": [{"status": "firing", "labels": {"alertname": "TestAlert"}, "annotations": {"summary": "Test"}}]}'
```

### Check n8n execution history

```bash
# View recent workflow executions via API
curl -s "http://localhost:5678/api/v1/executions?limit=10" \
  -H "X-N8N-API-KEY: $(grep N8N_API_KEY ~/building-energy-load-forecast/.env | cut -d= -f2)" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
for e in d.get('data', []):
    print(e['id'], e['status'], e.get('workflowId','?'), e.get('startedAt','?')[:19])
"
```

### Why alerts fire but Pushover is silent — quick checklist

1. **n8n workflow in draft state** — check startup log: `docker logs sparc-n8n --tail 20 | grep -i draft`
2. **Webhook not registered** — test with curl above; if 404, deactivate/reactivate workflow via n8n UI
3. **Grafana contact point wrong URL** — check `grafana/provisioning/alerting/contact_points.yaml`
4. **Alert in pending, not firing** — rule fires after pending duration (10–20 min), not immediately
5. **Poller not writing** — no sensor data = no alert evaluation; check `docker logs gardening-poller --tail 5`
