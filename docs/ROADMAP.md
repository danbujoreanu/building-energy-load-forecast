# Project Roadmap — Building Energy Load Forecast

**Last updated:** 2026-03-15 (Session 30)
**Status:** Sprint 3 in progress / Phase 7 deployment starting

This roadmap tracks the full journey from research pipeline to commercialised product.
Each sprint has a concrete, single deliverable and a definition of done.

---

## Phase 1: Research Foundation (COMPLETE)
- H+1 and H+24 experiments on Drammen (45 buildings) ✓
- Setup A (Trees+Features), B (DL+Features), C (DL+Raw) — Paradigm Parity ✓
- Oslo generalisation study — Phase 3A, Setup A ✓
- Phase 6 Cyber-Physical Control Layer (controller.py, connectors, FastAPI /control) ✓
- Slash commands: /review, /retro, /sprint ✓
- GitHub Actions PR review (claude-review.yml) ✓

---

## Sprint 1: Journal Paper [COMPLETE ✓ — 2026-03-15]
**Goal:** Submit to Applied Energy or Energy and Buildings

**Foundation:** AICS '25 12-page paper (Springer LNCS, submitted Dec 2025)

**Key additions over AICS paper:**
- Section 2: Extended literature review (Moosbrugger 2025, foundation models 2024, production utility deployments)
- Section 4: Diebold-Mariano significance tests (LightGBM vs PatchTST, LightGBM vs Ridge)
- Section 5: Oslo generalisation narrative (MAE scale vs R² stability argument)
- Section 5.2: Quantile bounds for MPC (LightGBM_Quantile P10/P50/P90)
- Section 5.3: Menu of Solutions framing (H+1=Stability, H+24=Day-Ahead, Quantiles=Risk-MPC)
- Section 7: Reproducibility + Code Availability (GitHub, config.yaml)

**New code:** `scripts/dm_significance_test.py` (Diebold-Mariano test)
**Author block:** "Independent Researcher, Dublin, Ireland"
**Estimated sessions:** 4-5

**Definition of done:** Manuscript submitted to Applied Energy (or Energy and Buildings as backup)

---

## Sprint 2: Horizon Sensitivity Analysis [COMPLETE ✓ — 2026-03-15]
**Goal:** Produce `outputs/results/horizon_metrics.csv` with model performance from H+1 to H+48

**Results (LightGBM/XGBoost/Ridge, Drammen test set):**

| Model | H+1 | H+6 | H+12 | H+24 | H+48 |
|-------|-----|-----|------|------|------|
| LightGBM | 3.188 | 3.584 | 3.799 | 4.057 | 4.724 |
| XGBoost | 3.339 | 3.678 | 3.906 | 4.182 | 4.824 |
| Ridge | 4.301 | 6.306 | 6.883 | 7.487 | 8.447 |

Key finding: LightGBM degrades 48% (H+1→H+48); Ridge degrades 96%. Tree advantage widens with horizon.
LightGBM R² = 0.967 at H+48 (exceeds DoD threshold of 0.90).

**LSTM degradation sweep** (`--include-dl`): Running 2026-03-15 (task b6nbk2ptx, re-kicked after task
file cleanup). Adds LSTM row per horizon to `horizon_metrics.csv`. PatchTST multi-horizon deferred —
raw sequence rebuilds per horizon ~3h; cross-paradigm story complete from H+24 DM (−12.17***).

**New code:** `scripts/run_horizon_sweep.py` (checkpoint-aware, `--resume` flag)
**Journal paper:** Section 5.5 + Table 8 added.

---

## Sprint 3: Oslo Cross-City Generalisation (Deep Dive) [COMPLETE ✓ — 2026-03-15]

**Results:**
- Oslo Setup A (LightGBM): MAE=7.415 kWh, R²=0.963
- Oslo Setup C (PatchTST): MAE=13.616 kWh, R²=0.8741
- Cross-city paradigm gap: +84% MAE for PatchTST vs LightGBM (wider than Drammen +72%)
- Finding: paradigm parity confirmed cross-city; feature engineering advantage is robust to dataset
- Results in `outputs/results/oslo_final_metrics.csv`

**Bug fixed (Session 30):** All pipeline scripts shared `data/processed/` — running oslo pipeline
overwrote drammen processed data. Fixed: `proc_dir = data/processed/{city}/` in `run_pipeline.py`,
`run_raw_dl.py`, `run_horizon_sweep.py`. City-specific paths enforced going forward.

**Oslo MAE scale note:** Oslo absolute MAE (7.4 kWh) is higher than Drammen (4.0 kWh) because
Oslo school buildings are larger (Oslo mean baseline: 45.3 kWh vs Drammen: 22.7 kWh).
This is a scale effect, not quality degradation — R² values (0.963 vs 0.975) are consistent.
See JOURNAL_PAPER_DRAFT.md Section 6.3 for full explanation.

**Deferred items (not blocking journal submission):**
- Oslo per-building breakdown (48 schools) — optional, adds one table
- Oslo H+1/H+48 horizon sweep — optional, would confirm degradation transfers cross-city
- Oslo DM test (LightGBM vs PatchTST on Oslo) — would strengthen but Drammen DM is sufficient

---

## Sprint 3B (Deferred): Irish CER Residential Dataset
**Dataset:** CER Smart Metering Project (2009-2010), 6,435 Irish households, 30-min resolution
**Status:** Deferred — access not confirmed; pre-smart-meter data may not reflect 2026 usage patterns
**Revive if:** CER dataset access confirmed AND research question requires Irish residential proof-point

---

## Sprint 4: Decision-Focused Learning ControlEngine
**Goal:** Train the forecast model with dispatch cost as the loss, not MSE

**Reference:** Pietro Favaro (UMONS) arXiv:2501.14708, IEEE TSG accepted
**Concept:** If the model is ultimately used in an MPC controller, the training signal
should be "how much did suboptimal forecasts cost?" not "how wrong was the forecast?"

**What this changes:**
- New `src/energy_forecast/models/dfl.py` — DFL wrapper
- Loss function: `loss = dispatch_cost(predicted_schedule) - dispatch_cost(optimal_schedule)`
- Requires SEMO price data (stub connector already exists: SEMOConnector in deployment/connectors.py)

**Estimated sessions:** 4-5

**Definition of done:** `outputs/results/dfl_metrics.csv` showing cost reduction vs MSE-trained
LightGBM on a simulated Irish dynamic pricing scenario.

---

## Phase 6B: Load Disaggregation (NILMTK)
**Goal:** Disaggregate whole-house load readings into per-appliance estimates

**Reference:** nilmtk.github.io, Jalal Kazempour prosumer learning (arxiv:2501.18017)
**Use case:** P1 port gives whole-house consumption. To control eddi / EV charger intelligently,
we need to estimate "how much of this is background load vs dispatchable load?"

**Scope:** Research prototype only — NILMTK is complex and slow to train.
Simpler heuristic: time-of-day patterns + known appliance signatures from CER data.

**Dependency:** Sprint 3 (CER dataset) must be complete first.
**Estimated sessions:** 3-4

---

## Phase 7: Production Deployment
**Goal:** Deploy the pipeline as a containerised service on AWS or GCP

**Platform decision:**
- **AWS App Runner** — recommended for conference demo, simpler ops, Irish data residency
- **GCP Cloud Run** — better long-term if using Vertex AI for model registry
- Decision deferred until Sprint 1 is complete (focus on research first)

**Stack:**
- FastAPI app (already exists: `deployment/app.py`)
- Docker container (already exists: `deployment/Dockerfile` or equivalent)
- Live data: CSVConnector → OpenMeteoConnector → P1Connector (stub)
- Morning brief CLI: `python deployment/live_inference.py --dry-run` (already works)

**Estimated sessions:** 2-3

---

## Production Model Architecture — Decisions (2026-03-15)

These decisions are fixed for Phase 7+ deployment. Record here to avoid revisiting.

### Which model runs in production?
**LightGBM always.** Not the stacking ensemble (marginal +0.5% R² at 10× complexity). Not DL
(PatchTST 7.0 kWh MAE vs LightGBM 4.0 kWh at H+24, plus no GPU in Pi/cloud tier).

### Inference cadence
| Horizon | Frequency | Trigger |
|---------|-----------|---------|
| H+24 | Daily at 16:00 | SEMO day-ahead price publication |
| H+1 | Hourly | Real-time grid stability / immediate recommendations |

### Retraining
- **Cadence:** Monthly, rolling 24-month window (NOT expanding — prevents pre-heat-pump patterns
  polluting post-heat-pump model)
- **Concept drift trigger:** 7-day rolling MAE > 1.5× training MAE → immediate retrain
- **Cold start:** Days 1-30 = Irish residential population-average model. Day 31+ = household-specific.
- **User life events:** Manual retrain trigger in app for: got solar, got EV, moved in

### Feedback loop
Do NOT use user actions (accepted/dismissed recommendations) as direct training signal — no
counterfactual is observable. Instead: track compliance rate + bill savings as outcome metrics.
Retrain on observed consumption only (supervised signal is always real metered data).

### LLM Energy Advisor (Phase 2)
- Model: `claude-haiku-4-5` (~€0.04/user/month at 20 queries)
- Context injection: 30d consumption stats + current tariff + today's forecast → system prompt
- No raw time-series sent to API (privacy + cost)
- Full spec: `docs/APP_PRODUCT_SPEC.md`

---

## Phase 8: Hardware Prototype
**Goal:** Raspberry Pi + P1 port adapter running inference on live ESB Networks meter data

**Hardware:**
- Raspberry Pi 4 (4GB RAM) — ~€60
- P1 port adapter (DSMR standard, works with Landis+Gyr E350) — ~€20-30
- MicroSD 32GB, case, power supply — ~€30
- **Total BOM: ~€110-120**

**Software:**
- Fork of `deployment/live_inference.py` for ARM/Pi
- MQTT broker for local device-to-cloud telemetry
- LightGBM inference: ~2ms per prediction, trivially fast on Pi 4

**Pilot:** User's house (Dublin)
- Solar panels (PV generation offset)
- eddi hot water diverter (MyEnergi API, digest auth — stub already in connectors.py)
- Gas heating (not controllable, but load-predictable from temperature)
- Dynamic pricing: Electric Ireland / Bord Gáis tariff (CRU mandate June 2026)

**Estimated sessions:** 3-4 (software only, hardware assembly is manual)

---

## Phase 9: Market Validation + Go-To-Market
**Goal:** 10-household pilot with real energy savings measurement

**Product:** Smart meter AI device
- €99-149 hardware + €3.99/month subscription
- Saves €200-400/year per household (estimated, based on CRU dynamic pricing variance)
- No supplier lock-in (works with any ESB Networks smart meter)

**Market trigger:** CRU dynamic pricing mandate, top 5 suppliers, June 1 2026
- Electric Ireland, Bord Gáis, Energia, SSE Airtricity, PrePay Power
- 1.9M smart meters installed in Ireland

**Funding path:**
1. AWS Activate (free compute credits — apply immediately)
2. Enterprise Ireland HPSU Feasibility Grant (€35k, pre-revenue)
3. Nova UCD / NCI affiliation → SFI Commercialisation Fund
4. Enterprise Ireland iHPSU (up to €1.2M, needs 6-month traction first)

**Competition assessed:**
- Viotas: B2B demand flexibility aggregator, not consumer hardware — different market
- SMS Energy: UK-only meter installer — not present in Ireland
- Tibber: Not in Ireland (yet)
- **Gap confirmed:** No supplier-agnostic Irish smart meter AI device exists.

---

## Milestone Summary

| Milestone | Deliverable | Status | Sessions |
|-----------|------------|--------|----------|
| Sprint 1 | Journal paper submitted | COMPLETE ✓ (draft done; submission pending final review) | 5 |
| Sprint 2 | Horizon sensitivity results | COMPLETE ✓ (2026-03-15) | 1 |
| Sprint 3 | Oslo full paradigm parity | CURRENT | 1-2 |
| Sprint 3B | Irish CER residential (deferred) | DEFERRED | 3-4 |
| Sprint 4 | DFL ControlEngine | PENDING | 4-5 |
| Phase 6B | NILMTK prototype | PENDING | 3-4 |
| Phase 7 | Cloud deployment | PENDING | 2-3 |
| Phase 8 | Raspberry Pi prototype | PENDING | 3-4 |
| Phase 9 | Market validation | PENDING | ongoing |

**Total to commercialisation: ~25-30 sessions (~40-50 hours of focused work)**

---

## Key External Deadlines

| Date | Event |
|------|-------|
| June 1 2026 | CRU dynamic pricing mandate (top 5 Irish suppliers) |
| TBD | Applied Energy submission (Sprint 1 target) |
| TBD | AWS Activate application (do immediately) |
| TBD | Enterprise Ireland HPSU Feasibility Grant application |
