# n8n — Shared Workflow Automation
## Sparc Energy + Greenhouse Digital Twin

**n8n is shared infrastructure.** One instance (in the Sparc stack) serves both projects.

| Project | Grafana reaches n8n via | Port |
|---------|------------------------|------|
| Sparc Energy | `http://n8n:5678` (Docker internal network) | 3001 |
| Greenhouse | `http://host.docker.internal:5678` (Mac host bridge) | 3000 |

---

## Part 1 — One-Time Setup: WhatsApp via CallMeBot

CallMeBot is a free service. No Twilio account. No credit card. ~20 minutes total.

### Step 1 — Add the CallMeBot number to your WhatsApp
On your phone, add this number as a contact named "CallMeBot":
```
+34 644 65 21 83
```

### Step 2 — Send the permission message
Open WhatsApp, find CallMeBot, send exactly:
```
I allow callmebot to send me messages
```
You'll get a reply within ~30 seconds with your personal **API key**.

### Step 3 — Save credentials in n8n
1. Open n8n: `http://localhost:5678`
2. Go to **Settings → Credentials → Add credential**
3. Select **Header Auth**
4. Name: `CallMeBot`
5. Save your phone number (international format, no +): `353XXXXXXXXX`
6. Save your API key from Step 2

### Step 4 — Test it
```bash
# Replace PHONE and APIKEY with your values
curl "https://api.callmebot.com/whatsapp.php?phone=353XXXXXXXXX&text=Sparc+test+message&apikey=YOUR_KEY"
```
You should receive a WhatsApp message within 5 seconds.

---

## Part 2 — Start n8n

n8n is now in the Sparc docker-compose. Start it:

```bash
cd ~/building-energy-load-forecast

# If stack is already running — add n8n only:
docker compose up -d n8n

# Or restart everything:
docker compose up -d

# Verify:
docker compose ps        # sparc-n8n should show "running"
open http://localhost:5678
```

Create a local account when prompted (email + password, no external verification).

---

## Part 3 — Workflow 1: Sparc Alert Relay

**Trigger:** Grafana alert fires (API down, drift alarm, price spike, etc.)
**Action:** WhatsApp message to Dan

### In n8n UI:
1. **New Workflow** → name: `Sparc — Grafana Alert Relay`

2. Add **Webhook** node (trigger):
   - HTTP Method: `POST`
   - Path: `sparc-alert`
   - Authentication: None (internal network only)
   - Copy the webhook URL: `http://localhost:5678/webhook/sparc-alert`

3. Add **Code** node (format message):
   ```javascript
   const body = $input.first().json;
   const alertName = body.title || body.ruleName || 'Unknown alert';
   const state = body.state || body.status || 'firing';
   const message = `🚨 Sparc Alert\n${alertName}\nState: ${state}\nTime: ${new Date().toLocaleString('en-IE', {timeZone: 'Europe/Dublin'})}`;
   return [{ json: { message } }];
   ```

4. Add **HTTP Request** node (send WhatsApp):
   - Method: `GET`
   - URL: `https://api.callmebot.com/whatsapp.php`
   - Query parameters:
     - `phone`: `353XXXXXXXXX` (your number)
     - `text`: `={{ $json.message }}`
     - `apikey`: `YOUR_CALLMEBOT_KEY`

5. **Save → Activate**

### In Sparc Grafana (once DAN-96 has data):
- Grafana → Alerting → Contact points → Add contact point
- Type: `Webhook`
- URL: `http://n8n:5678/webhook/sparc-alert`
- (Uses Docker network — `n8n` resolves to the sparc-n8n container)

---

## Part 4 — Workflow 2: Greenhouse Alert Relay

**Trigger:** Greenhouse Grafana alert fires (LVPD red, soil moisture low, etc.)
**Action:** WhatsApp message to Dan

### In n8n UI:
1. **New Workflow** → name: `Greenhouse — Grafana Alert Relay`

2. Add **Webhook** node:
   - Path: `gh-alert`
   - Copy the webhook URL: `http://localhost:5678/webhook/gh-alert`

3. Add **Code** node (format message):
   ```javascript
   const body = $input.first().json;
   const alertName = body.title || body.ruleName || 'Unknown alert';
   const state = body.state || body.status || 'firing';
   const message = `🌿 Greenhouse Alert\n${alertName}\nState: ${state}\nTime: ${new Date().toLocaleString('en-IE', {timeZone: 'Europe/Dublin'})}`;
   return [{ json: { message } }];
   ```

4. Add **HTTP Request** node (same as Workflow 1 — same WhatsApp call)

5. **Save → Activate**

### In Greenhouse Grafana:
- Grafana (port 3000) → Alerting → Contact points → Add contact point
- Type: `Webhook`
- URL: `http://host.docker.internal:5678/webhook/gh-alert`
- (`host.docker.internal` bridges from the Greenhouse Docker network to your Mac's localhost)

---

## Part 5 — Workflow 3: Sparc Morning Brief (08:00 daily)

**Trigger:** 08:00 every day (Europe/Dublin)
**Action:** Calls `/control` endpoint → formats → WhatsApp

### In n8n UI:
1. **New Workflow** → name: `Sparc — Daily Morning Brief`

2. Add **Schedule Trigger** node:
   - Mode: Cron
   - Expression: `0 8 * * *`
   - Timezone: `Europe/Dublin`

3. Add **HTTP Request** node (get control decision):
   - Method: `POST`
   - URL: `http://api:8000/control`
   - Body (JSON):
     ```json
     {
       "city": "ireland",
       "dry_run": false,
       "target_hours": [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6]
     }
     ```

4. Add **Code** node (format WhatsApp message):
   ```javascript
   const data = $input.first().json;
   const action = data.action_type || 'UNKNOWN';
   const msg = data.user_message || 'No message';
   const saving = data.estimated_daily_saving_eur || 0;
   
   const emoji = {
     'HEAT_NOW': '🔥',
     'DEFER_HEATING': '☀️',
     'PARTIAL_HEAT': '⚡',
     'ALERT_HIGH_DEMAND': '⚠️'
   }[action] || '📊';
   
   const message = `${emoji} Good morning! Sparc Brief\n${msg}\nEst. saving today: €${saving.toFixed(2)}\n\nRun: curl localhost:8000/control for full detail`;
   return [{ json: { message } }];
   ```

5. Add **HTTP Request** node (send WhatsApp) — same as Workflows 1 & 2

6. **Save → Activate**

---

## Part 6 — Workflow 4: Greenhouse Evening Summary (20:00 daily)

**Trigger:** 20:00 every day (Europe/Dublin)
**Action:** Queries latest InfluxDB readings → formats → WhatsApp

### In n8n UI:
1. **New Workflow** → name: `Greenhouse — Daily Evening Summary`

2. Add **Schedule Trigger** node:
   - Cron: `0 20 * * *`
   - Timezone: `Europe/Dublin`

3. Add **HTTP Request** node (query InfluxDB Flux API):
   - Method: `POST`
   - URL: `http://host.docker.internal:8086/api/v2/query?org=maynooth`
   - Headers:
     - `Authorization`: `Token YOUR_INFLUXDB_TOKEN`
     - `Content-Type`: `application/vnd.flux`
   - Body (raw Flux):
     ```flux
     from(bucket: "greenhouse")
       |> range(start: -1h)
       |> filter(fn: (r) => r._measurement == "greenhouse_canopy" or r._measurement == "soil_moisture")
       |> last()
     ```

4. Add **Code** node (parse and format):
   ```javascript
   const records = $input.first().json;
   // Parse Flux CSV response — extract LVPD, soil north, soil south, temp
   // n8n returns raw CSV from Flux API — parse the values
   const message = `🌿 Greenhouse Evening Summary\n` +
     `LVPD: check Grafana for latest\n` +
     `http://localhost:3000\n` +
     `Time: ${new Date().toLocaleString('en-IE', {timeZone: 'Europe/Dublin'})}`;
   return [{ json: { message } }];
   ```
   > **Note:** The Flux CSV format is complex to parse in n8n Code node. Simpler alternative: query Ecowitt API directly (HTTP GET with your API keys) — returns clean JSON. See Greenhouse `GH_DIGITAL_TWIN_ARCHITECTURE.md` for Ecowitt API credentials.

5. Add **HTTP Request** node (WhatsApp) — same as above

6. **Save → Activate**

---

## Part 7 — Workflow 5: Weekly Drift Check (Monday 09:00)

**For Sparc Energy only.** Runs the drift detector and alerts if the model is degrading.

### In n8n UI:
1. **New Workflow** → name: `Sparc — Weekly Drift Check`

2. Add **Schedule Trigger**: `0 9 * * 1` (Monday 09:00)

3. Add **HTTP Request** node:
   - Method: `GET`
   - URL: `http://api:8000/health`

4. Add **IF** node:
   - Condition: `{{ $json.drift_status }}` equals `CRITICAL`

5. True branch → **HTTP Request** (WhatsApp):
   ```
   ⚠️ Sparc drift CRITICAL
   Model accuracy degrading — retrain needed.
   Run: python scripts/run_drift_check.py --city ireland
   ```

6. False branch → no action (or a green weekly summary if you want one)

7. **Save → Activate**

---

## Summary: What Each Webhook URL Is

| Workflow | Webhook URL | Used by |
|----------|-------------|---------|
| Sparc alert relay | `http://n8n:5678/webhook/sparc-alert` | Sparc Grafana (port 3001) |
| Greenhouse alert relay | `http://host.docker.internal:5678/webhook/gh-alert` | GH Grafana (port 3000) |
| *(Morning brief is scheduled — no webhook)* | — | Cron |
| *(Evening summary is scheduled — no webhook)* | — | Cron |
| *(Drift check is scheduled — no webhook)* | — | Cron |

---

## Troubleshooting

```bash
# n8n won't start
docker compose logs n8n --tail=30

# Port conflict
lsof -i :5678

# Greenhouse Grafana can't reach n8n
# Test from inside the GH Grafana container:
docker exec -it gh_grafana wget -qO- http://host.docker.internal:5678/healthz

# Sparc Grafana can't reach n8n
docker exec -it sparc-grafana wget -qO- http://n8n:5678/healthz

# CallMeBot not delivering
# Check: is the number in international format without +? (353XXXXXXXXX not +353...)
# Retry the curl test from Part 1, Step 4
```

---

## Linear Tracking

| Issue | Status | What |
|-------|--------|------|
| DAN-94 | 🟠 Backlog | n8n setup — DONE (docker-compose.yml updated) |
| DAN-101 | 🟡 Todo | Grafana alert rules (configure after DAN-96 has data) |
| P-02 | 🟡 Todo | WhatsApp push notification |

*File: `docs/infra/services/N8N_WORKFLOWS.md` | Last updated: 21 April 2026*
