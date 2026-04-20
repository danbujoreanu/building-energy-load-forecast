# Architecture Meeting — Sparc Energy
## Date: 21 April 2026 | Session 44 | Bi-weekly Cadence

**Attendees (personas):**
- 🏗 Solutions Architect
- 🤖 ML Engineer
- 📦 Product Manager
- 📊 Business Analyst
- 👤 Dan Bujoreanu — Product Owner / Founder / Domain Expert

**Facilitator:** Claude Code (Sparc AI Engineering Lead)
**Next meeting:** 5 May 2026

---

## Dan's Role in These Meetings

As Product Owner you bring:
- **Domain expertise** — you understand the Irish energy market, BGE tariffs, CRU regulations better than any model
- **User perspective** — you ARE the first user (your Eddi, your ESB data, your BGE contract)
- **Commercial judgment** — funding timeline, investor narrative, go-to-market sequencing
- **Regulatory radar** — CRU decisions, SMDS progress, Near Real Time Metering consultation

**Questions Dan should always raise:**
1. "Is this demo-ready for an investor in 4 weeks?"
2. "Which feature most directly supports the June 2026 dynamic pricing narrative?"
3. "What would a New Frontiers/SEAI evaluator want to see proof of?"
4. "Does this change the plan comparison story — am I still recommending the right tariff?"
5. "Is consumer behaviour accounted for, or are we still assuming a perfect rational user?"

---

## Agenda

1. System status review
2. Architecture walkthrough (as-built)
3. End-to-end user flow
4. Where RAG plugs in
5. Control layer — Eddi logic review
6. Priority stack & Linear sync
7. Open questions / FAQ

---

## 1. System Status (as of 21 April 2026)

| Component | Status | Evidence |
|-----------|--------|----------|
| Docker stack (5 containers) | ✅ Running | `docker compose ps` — all healthy |
| FastAPI `/health` | ✅ Live | `{"status":"healthy","inference_ready":true}` |
| FastAPI `/control` | ✅ Fixed | HEAT_NOW/DEFER decisions working |
| FastAPI `/predict` | ⚠️ Partial | Accepts semantic names; needs retrain for full validation |
| LightGBM — Drammen/Oslo | ✅ Loaded | `outputs/models/drammen_LightGBM_2026-03-05.joblib` |
| LightGBM — Ireland (home) | ✅ Trained today | MAE 0.163 kWh, run_home_demo.py |
| TimescaleDB | ✅ Running | Schema created; tables empty — needs CSV ingestion endpoint |
| Grafana dashboard | ✅ Provisioned | localhost:3001 — "No data" until DB populated |
| myenergi Eddi API | ✅ Live | Status, schedule, history confirmed working |
| ChromaDB RAG | ✅ Local | 7 tiers; disabled in Docker (intel/ not in container) |
| 178 tests | ✅ Passing | `pytest tests/ -q` — 178 passed, 0 warnings |

**Commits this session (4 bugs fixed):**
- `ffc8ea4` — MOCK_SOLAR_24H 25→24 elements (fixed `/control` 500)
- `a524e15` — dry-run mock history 72→300h (fixed lag_169h warmup)
- `907c019` — Column_N feature name validation (fixed `/predict` 422)
- `5c0f7f0` — Grafana dashboard + ESB demo + command reference

---

## 2. Architecture — As Built

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SPARC ENERGY — AS-BUILT (Apr 2026)               │
│                                                                     │
│  DATA IN              BRAIN                    DATA OUT             │
│  ─────────            ─────                    ────────             │
│  ESB CSV upload  ──►  LightGBM (H+24)  ──►    Morning Brief CLI    │
│  (manual today)       MAE 0.163 kWh            /control API         │
│                                                Grafana dashboard    │
│  Open-Meteo API  ──►  ControlEngine   ──►     Eddi boost command   │
│  (live, free)         4 rules today            (stub — works live)  │
│                                                                     │
│  myenergi API ◄──────────────────────────────── MyEnergiConnector  │
│  (LIVE: status,                                 (stub in API,       │
│   schedule, history)                            works in scripts)   │
│                                                                     │
│  STORAGE LAYER        INTELLIGENCE              AUTOMATION          │
│  ─────────────        ───────────              ──────────           │
│  TimescaleDB  ◄──────  predictions table  ─►   n8n (not wired yet)│
│  (running in          meter_readings           APScheduler (todo)  │
│   Docker, empty)      recommendations                               │
│                                                                     │
│  ChromaDB RAG   ◄──── 7 tiers of docs  ──►    /intel/query API    │
│  (local folder)       (energy, mba,            (disabled in Docker  │
│                        career, etc.)            — intel/ not copied)│
└─────────────────────────────────────────────────────────────────────┘
```

**Key files for the control layer (Eddi logic):**
```
src/energy_forecast/control/
├── actions.py      ← ActionType enum: HEAT_NOW / DEFER_HEATING / PARTIAL_HEAT / ALERT
└── controller.py   ← ControlEngine: 4 decision rules (price × solar × demand)

deployment/
└── connectors.py   ← MyEnergiConnector (boost/pause — STUB needs wiring)
```

---

## 3. End-to-End User Flow — Every Step, Every Technology

```
STEP 1 — USER UPLOADS DATA
  Today:  Manual CSV from ESB Networks My Account (30-min kWh intervals)
  File:   HDF_calckWh_*.csv  ← USE THIS ONE (not kW)
  2026:   P1 port adapter (Pi Zero 2W + DSMR cable, ~€23)
  2027:   SMDS API (ESB Networks, CRU202517 — automatic sync)
  STATUS: ❌ No POST /upload endpoint yet — this is DAN-96
         ↓
STEP 2 — STORAGE (TimescaleDB)
  Tables: households · meter_readings · predictions · recommendations · outcomes
  Running: ✅ sparc-db container, port 5432
  Data:    ❌ empty until DAN-96 is built
         ↓
STEP 3 — PLAN ANALYSIS (runs once on onboarding + when contract renews)
  Script:  scripts/score_home_plan.py
  Output:  BGE day/night/peak breakdown, Saturday utilisation, €/year savings
  Today:   Dan's score = 62/100, €178/year on table (unused Saturday free)
  Missing: API endpoint + UI — DAN-97
         ↓
STEP 4 — FORECASTING (LightGBM)
  Input:   Last 168h of consumption + weather (lag_24h, lag_168h, hour_of_day, solar, temp)
  Model:   LightGBM H+24, trained on 2 years of your home data
  Output:  P10/P50/P90 for 24 hours ahead
  MAE:     0.163 kWh/hour (your home, April 2026)
  Running: ✅ in API + scripts/run_home_demo.py
  Weather: Open-Meteo (free, no API key, live)
         ↓
STEP 5 — CONTROL ENGINE (ControlEngine)
  File:    src/energy_forecast/control/controller.py
  Rules:   price < 0.16 EUR/kWh          → HEAT_NOW (night rate cheap)
           solar > 150 W/m² + price high  → DEFER (wait for panels)
           moderate solar + mid price      → PARTIAL_HEAT
           P90 > demand headroom           → ALERT_HIGH_DEMAND
  Missing: consumer override, tank temp, time-of-need — DAN-98
         ↓
STEP 6 — EDDI CONTROL (myenergi API)
  File:    deployment/connectors.py — MyEnergiConnector
  Live:    get_status(), get_schedule(), get_history_day() ✅
  Stub:    boost/pause commands (needs wiring) 
  Hub:     Serial 21509692, confirmed working
         ↓
STEP 7 — DELIVERY TO USER
  Today:   CLI morning brief (Terminal command)
           /control API (JSON response)
           Grafana (operator dashboard, local)
  Roadmap: n8n scheduled push notification (DAN-94)
           Consumer PWA/mobile app (DAN-99, Claude Design)
           WhatsApp/Telegram bot (quick win)
```

---

## 4. Where RAG Plugs In

The RAG system (ChromaDB + 7 tiers) upgrades the product from "smart thermostat" to "energy advisor".

| Tier | Contents | Consumer use case | Operator use case |
|------|----------|-------------------|-------------------|
| `energy` | CRU regulations, SEAI reports, dynamic pricing rules | "Why should I switch plan?" | Regulatory compliance check |
| `intel` | Market feeds, competitor moves, EirGrid data | — | Weekly intelligence briefing |
| `mba` | Porter, BMC, Lean Canvas, UCD strategy cases | — | Fundraising prep, investor Q&A |
| `career` | DASME/DMAIC frameworks, interview transcripts | — | Dan's personal use |
| `strategic` | Product roadmap, tech decisions | — | Session context, decision audit |
| `garden` | Greenhouse project docs | — | Digital Twin Gardening project |
| `operational` | GDPR guidance, CRU202517, data access codes | Privacy policy answers | Compliance queries |

**Current status:** 7 tiers running locally. The `/intel/query` API endpoint exists in code but is **disabled in Docker** — `intel/` directory not copied into the container (one Dockerfile line fix).

**Next step:** Add `COPY intel/ ./intel/` to Dockerfile and install intel dependencies in `deployment/requirements.txt`. Enables the "energy advisor" LLM layer.

**Technical stack:** ChromaDB (vector store) + LlamaIndex (orchestration) + MiniLM-L6-v2 (embeddings) + Gemini Flash (synthesis, ~€0.04/user/month).

---

## 5. Eddi Logic Review — What Needs Improving

**Current state (4 rules, controller.py lines 220–310):**
```
Rule 1: P90 > demand headroom → ALERT (safety)
Rule 2: solar ≥ 150 W/m² AND price ≥ 0.28 → DEFER
Rule 3: price < 0.16 → HEAT_NOW (cheap rate)
Rule 4: moderate solar + mid price → PARTIAL_HEAT
Default: HEAT_NOW (safe baseline)
```

**What it's missing (consumer behaviour):**

| Gap | Problem | Fix |
|-----|---------|-----|
| User override | User showers at 9:30am — can't defer indefinitely | `earliest_need_time` parameter → must heat before deadline |
| Tank temperature | If tank already hot (solar heated it), Eddi won't run anyway | Read Eddi `tmp` field from `/cgi-jstatus-E{serial}` |
| Consumer trust | "Why is it doing that?" — no explanation shown to user | `user_message` field already in ControlAction — needs UI |
| Battery advice | "Should I get a battery?" — pattern-based recommendation | Phase 2 — needs generation vs consumption delta |
| Plan comparison | "Am I on the right tariff?" | score_home_plan.py → needs API endpoint + UI |

**DAN-98** captures the consumer override work.

---

## 6. The kW File — Appliance Detection

The `HDF_kW_10306822417_20-04-2026.csv` file (instantaneous power at 30-min intervals) is valuable for appliance inference — referenced in Kazempour et al. (arxiv:2501.18017) on BTM asset detection.

**What 30-min kW data reveals for your home:**

| Pattern | Inference |
|---------|-----------|
| Regular 0.5–0.7 kW spikes at 07:00 and 19:45 | Eddi boost (confirmed) |
| ~3.5 kW sustained, winter mornings | Would indicate heat pump (you have gas — verify absence) |
| Near-zero daytime + negative export | Solar + low occupancy (confirms south-facing) |
| 7–22 kW overnight spike | EV charging (not present in your data) |

**Decision: keep both files.** kWh for forecasting and billing. kW for appliance validation and BTM inference.

---

## 7. Priority Stack (Linear Synced)

| Priority | Issue | What | Effort | Linear |
|----------|-------|------|--------|--------|
| 🔴 URGENT | DAN-89 | Submit AWS Activate (deadline Apr 25) | 30 min | In Progress |
| 🔴 THIS WEEK | DAN-96 | `POST /upload` CSV → TimescaleDB | 2–3h | **New** |
| 🟡 NEXT | DAN-97 | Plan comparison API + Grafana panel | 1 day | **New** |
| 🟡 NEXT | DAN-98 | Consumer override in ControlEngine | 4h | **New** |
| 🟡 NEXT | DAN-90 | Intel feeds first ingestion | 5 min | Todo |
| 🟠 MONTH | DAN-94 | n8n morning brief automation | 2h | Backlog |
| 🟠 MONTH | DAN-99 | Claude Design — 3 consumer app screens | Design | **New** |
| 🟠 MONTH | DAN-100 | kW appliance detection analysis | 2h | **New** |
| 🟢 LATER | DAN-91 | Ingest strategic docs into RAG | 1h | Todo |
| 🟢 LATER | Retrain | Run pipeline with named features | 30 min | — |

**Completed this session:**
- ✅ DAN-92 — Docker stack first run
- ✅ DAN-93 — ESB HDF upload + morning brief (home demo ran, MAE 0.163 kWh)

---

## 8. Open Questions / FAQ

See `docs/governance/FAQ.md` for the full reference. Key items from this meeting:

**Q: Why was Column_N only caught now?**
The pipeline always used `.values` (numpy arrays) so LightGBM never stored column names. The HTTP API was the first thing that ever tried to match feature names by key — that's when the mismatch surfaced. No retraining needed for existing functionality.

**Q: Do we need to retrain?**
Not urgently. `/control` and the home demo work perfectly. When you next run `run_pipeline.py` (any reason), the fix is already in place and the new model will have semantic feature names automatically.

**Q: Why not Streamlit for Sparc?**
Sparc = commercial consumer product → mobile app / PWA architecture. Streamlit is a data science prototyping tool, not production software. Greenhouse = personal project, one user, Streamlit is perfect there.

**Q: Which ESB file to use?**
`HDF_calckWh_*.csv` (kWh) for forecasting and billing. `HDF_kW_*.csv` (kilowatts) for appliance pattern analysis. Keep both.

**Q: Why is Grafana blank?**
The database schema exists but is empty. The missing piece is `POST /upload` (DAN-96) — once built, upload the ESB CSV and Grafana fills up immediately.

---

## 9. Governance Notes

**Meeting cadence:** Bi-weekly (every 2 weeks). Meeting notes committed to `docs/governance/`.

**Format:** Each meeting covers: system status → architecture delta → priority stack → open questions → Dan's questions to raise next time.

**Session close-out checklist (always):**
- [ ] Meeting notes committed to `docs/governance/MEETING_NOTES_YYYY-MM-DD.md`
- [ ] Linear updated (new issues, status changes)
- [ ] MEMORY.md updated with key decisions
- [ ] Orchestrator brief written if cross-project actions exist
- [ ] Next meeting agenda seeded

---

*Notes compiled by Claude Code (Engineering Lead) | Committed: `docs/governance/MEETING_NOTES_2026-04-21.md`*
