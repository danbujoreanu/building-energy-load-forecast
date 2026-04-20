# What We've Built — Plain English Overview
## Sessions 38–44 (Jan–Apr 2026)

**For:** Dan (non-engineer perspective)  
**Purpose:** Understand what exists, why it exists, and what each piece does.

---

## The Big Picture — What Is Sparc Energy?

Sparc Energy is software that:

1. **Learns your electricity habits** from your ESB smart meter history
2. **Predicts** how much electricity your home will use tomorrow, hour by hour
3. **Tells your Eddi water heater** when to run based on solar panels and electricity prices
4. **Saves you money** by shifting electricity use to cheap hours (night rate, Saturday free window)

Think of it as a smart assistant that reads your meter, understands BGE's tariff, and quietly moves your hot water heating to the cheapest time of day.

---

## What's Running Right Now (as of April 2026)

### On Your Laptop (localhost)

| Service | What it does | How to access |
|---------|-------------|---------------|
| **FastAPI** (port 8000) | The brain — runs predictions, receives requests | http://localhost:8000/health |
| **PostgreSQL** (port 5432) | The database — stores your meter readings, forecasts | Used by the API automatically |
| **Redis** (port 6379) | The cache — remembers results so forecasts run faster | Used by the API automatically |
| **Grafana** (port 3001) | The dashboard — graphs your energy data | http://localhost:3001 |
| **Caddy** (port 80/443) | HTTPS proxy — not needed until cloud deployment | Background only |

All five services start with one command: `docker compose up -d`

---

## The AI Model — How It Works

### Training (already done)
- **Input**: 2 years of your actual ESB smart meter data (30-min intervals)
- **Algorithm**: LightGBM — a fast, accurate tree-based model (not a neural network)
- **Features**: Hour of day, day of week, your electricity usage 24h ago, 48h ago, same-time last week, solar irradiance, temperature
- **Output**: A model file saved to `outputs/models/` (~3MB, ready to use)

### Prediction (happens when you run the morning brief)
- The model loads in 2 seconds
- Takes the last 2 weeks of your usage as input
- Produces a 24-hour forecast: how many kWh you'll use each hour tomorrow
- Also produces P10/P50/P90 bands (pessimistic / expected / optimistic)

### Accuracy
- **MAE: 0.163 kWh/hour** on your home data (April 2026 result)
- This means predictions are typically within ±160 watt-hours per hour
- For context: your kettle uses ~0.15 kWh, a shower is ~1 kWh

---

## ESB Smart Meter Data — The Two Files

You downloaded two CSV files from ESB Networks My Account. Here's what they are:

| File | What it contains | Do we use it? |
|------|-----------------|---------------|
| `HDF_calckWh_10306822417_20-04-2026.csv` | Energy consumed each 30 minutes (kWh) | **YES — this is the one** |
| `HDF_kW_10306822417_20-04-2026.csv` | Power demand at each moment (kW) | No |

**Why kWh not kW?**
- kWh = how much energy you *used* in each 30-minute slot (like your electricity bill)
- kW = how fast you were using it *at that instant* (like looking at a speedometer)
- For billing and forecasting we want total energy per slot = kWh

The kWh file has **17,496 hourly rows** covering **April 2024 → April 2026**.

---

## The Control Layer — What "Demand Response" Means

After forecasting, the system decides what to do with your Eddi water heater:

| Decision | Meaning | When it happens |
|----------|---------|-----------------|
| `RUN_NOW` ✓ | Run the Eddi now | Night rate (23c) or free Saturday |
| `DEFER` ↓ | Wait, don't run yet | Peak rate (Mon–Fri 17–19h, 39c) |
| `NORMAL` · | No recommendation | Solar generation expected |

From today's run with your actual data:
- **Est. daily cost**: €2.10
- **Est. daily saving vs doing nothing**: €0.78
- **Annualised**: that's ~€285/year just from timing hot water correctly

---

## Why NOT Streamlit (for Sparc Energy)

Streamlit is a quick way to build data science dashboards in Python — great for research and internal tools. We're NOT using it in Sparc because:

1. **Product vision is a consumer mobile app** — a phone app or PWA (Progressive Web App), not a web page
2. **Streamlit doesn't run as a production service** — it restarts on code changes, can't handle multiple users, not suitable for an API-first product
3. **We already have Grafana** for visualising data — no need for a second dashboard tool
4. **FastAPI + React/mobile** is the right architecture for what this becomes commercially

**Greenhouse is different.** Greenhouse is your personal greenhouse automation project — a Streamlit dashboard makes perfect sense there because:
- It's just for you, not customers
- You want to iterate quickly on visualisations
- One user, no need for mobile app architecture
- No commercial product ambitions (yet)

Think of it this way: Streamlit = whiteboard for thinking. FastAPI + mobile = what you'd ship to customers.

---

## What Sessions 42–44 Actually Did (Technical Summary)

### Session 42 (April 20 — before this doc)
- Analysed 9 documents from Google Antigravity (AI PM portfolio notes)
- Built documentation standards: every Linear issue needs runnable commands
- Created DASME/DMAIC/DMEDI framework guide for interviews
- Created agent capability tier docs (L1/L2/L3 with EU AI Act rationale)

### Session 43 (April 20 — morning/afternoon)
- Got Docker stack running for first time (DAN-92 ✅)
- Fixed Dockerfile: `mock_data.py` was missing from container
- Created beginner guides for all Docker services (Grafana, n8n, Postgres, Redis)
- Added passwords to `.env` (`DB_PASSWORD`, `GRAFANA_PASSWORD`)

### Session 44 (April 20 — evening, this session)
**Bugs found and fixed:**
1. Morning brief dry-run used 72 hours of mock data — not enough to cover 169h lag feature → all rows dropped as NaN. Fixed: increased to 300h.
2. `MOCK_SOLAR_24H` had 25 elements instead of 24 → `/control` endpoint crashed with a 500 error on every request. Fixed: removed the extra element.
3. `/predict` API rejected all requests with semantic feature names (e.g. `lag_24h`) because the Drammen model was trained with numpy arrays (no column names) → got generic `Column_0..N` names. Fixed: new `register_model_features()` function detects generic names and keeps validation lenient. Also fixed the training code to pass DataFrames to LightGBM/XGBoost so the next retrain gives proper semantic names.
4. Grafana had no dashboards (empty provisioning folder) → Created `sparc_overview.json` dashboard. Also fixed Grafana missing `DB_PASSWORD` env var.

**ESB demo (DAN-93, partial):**
- New kWh file loaded: 17,496 hourly rows, April 2024 → April 2026
- Model trained on your actual home data: MAE 0.163 kWh/hour, R² 0.68
- Morning brief: tomorrow's schedule with €0.78/day saving

---

## Do We Need to Retrain the Models?

**Short answer: No, not urgently.**

The existing Drammen/Oslo models in `outputs/models/` work fine for:
- `/control` endpoint (demand-response decisions) ✅
- `live_inference.py --dry-run` (morning brief) ✅
- `run_home_demo.py` (Ireland/home demo) ✅ — trains its own model from your data

The only thing that changed is that if you call `/predict` directly via the API with named features, you now get a helpful error message instead of a confusing rejection. The models themselves are unchanged.

When you next run `scripts/run_pipeline.py` (takes ~30 min for Drammen), the new models will have proper feature names and `/predict` will work perfectly.

---

## Next Actions for You

| Priority | Action | Command |
|----------|--------|---------|
| 🔴 TODAY (Apr 25 deadline) | Submit AWS Activate application | Open `docs/funding/AWS_ACTIVATE_APPLICATION.md` |
| 🟡 This week | Re-download fresh ESB HDF data each month | ESB Networks My Account → My Energy Usage |
| 🟡 This week | Check Grafana dashboard at localhost:3001 | Open browser |
| 🟠 When ready | Set up n8n for automated morning briefs | See `docs/infra/services/N8N.md` |
| 🟢 Backlog | Retrain Drammen pipeline with named features | `python scripts/run_pipeline.py --city drammen` |

---

## Glossary — Terms You'll See in the Code

| Term | Plain English |
|------|--------------|
| **LightGBM** | The AI algorithm used for forecasting. Like a very smart Excel formula that learned from 2 years of your data |
| **MAE** | Mean Absolute Error — average prediction error in kWh |
| **H+24** | 24-hour-ahead forecast (predicting what tomorrow looks like) |
| **lag_24h** | "What was my electricity usage exactly 24 hours ago?" — a feature the model uses |
| **Docker** | Software that runs services in isolated mini-computers on your laptop |
| **Container** | One of those mini-computers (the API, the database, Grafana each run in their own) |
| **TimescaleDB** | A time-aware database — like Excel but for time-series data, can query "last 7 days" efficiently |
| **Redis** | A very fast memory store — like a sticky note for the API. Stores today's forecast so it doesn't recompute every time |
| **Eddi** | Your myenergi hot water diverter — runs on solar or grid, the device we're controlling |
| **MPRN** | Meter Point Reference Number — your ESB smart meter's unique ID (10306822417) |
| **RAG** | Retrieval-Augmented Generation — a way of giving Claude access to your documents so it can answer questions about them |
| **P10/P50/P90** | Low / expected / high forecast bands. Like a weather forecast: "probably 5°C, could be 2°C or 8°C" |
| **Dry-run** | Running a script in safe mode using fake data — nothing real is called, nothing is changed |
