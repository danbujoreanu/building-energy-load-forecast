# Sparc Energy — Product Engineering Roadmap

**Project:** Building Energy Load Forecast → Sparc Energy Ltd (pre-incorporated)
**Last updated:** 2026-04-15 (Session 40)
**Mission:** Day-ahead electricity load forecasting for Irish residential homes, enabling
demand-response optimisation against dynamic pricing. MSc AI thesis → cleantech startup.

> **Single source of truth.** This file replaces the previous split between root `ROADMAP.md`
> (research diary) and `docs/ROADMAP.md` (commercial roadmap). Both are now archived here.

---

## How to Read This Roadmap

### Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete — date shown in parentheses |
| 🔄 | In progress — active this quarter |
| 🔴 | High priority — next in queue |
| 🟡 | Medium — planned, not yet started |
| 🔵 | Low / exploratory |
| 🎓 | PhD-track (longer-term research) |
| ⏸️ | Deferred — blocked or deprioritised |

### Item Metadata

Each item carries: **Added** (when it entered the backlog) · **Resolved** (when closed) ·
**Owner** (staff persona responsible) · **Priority** · **Depends On** (blockers).

### Ownership Personas

| Persona | Responsibilities |
|---------|-----------------|
| Staff ML Engineer | Models, features, training pipeline, MLOps, registry |
| Staff Data Engineer | Data connectors, preprocessing, schema, provenance |
| Staff Backend Engineer | FastAPI, Docker, AWS, CI/CD |
| Staff Data Scientist | Evaluation, significance tests, paper figures |
| Staff Product Manager | Product vision, PRDs, commercial priorities, Phases A/B/C |
| Staff Product Marketing | Consumer insights, positioning, go-to-market |
| Staff Energy Expert | Tariff modelling, demand-response logic, grid regulations |
| Staff Governance Lead | EU AI Act, GDPR, Model Cards, AIIAs, data lineage |
| Dan (founder) | All of the above — single contributor |

---

## Status Snapshot — Q2 2026

| Track | State | Next Milestone | Deadline |
|-------|-------|---------------|---------|
| Research & Publication | 🔄 Journal paper in draft | Applied Energy submission | TBD |
| Core ML & MLOps | ✅ Production-grade (Session 40) | Quantile registry + SRP refactor | Q2 2026 |
| Product — Consumer App | 🔄 Phase A in flight | BTM asset detection module | Jun 2026 |
| Deployment & Infrastructure | 🔄 Phase 7 started (Dockerfile ✅) | AWS App Runner live endpoint | Q2 2026 |
| Commercial & Regulatory | 🔴 Dynamic pricing trigger 47 days away | ESCO Appendix A draft ready | 1 Jun 2026 |
| PhD | 🔄 Decarb-AI interview Apr 21 | Outcome decision | 21 Apr 2026 |

---

## TRACK 1 — Research & Publication

### R1 — Thesis & Conference Papers

| Status | Item | Added | Resolved | Owner | Notes |
|--------|------|-------|----------|-------|-------|
| ✅ | MSc Thesis — *ML Approaches for Building Energy Load Forecasting in Norwegian Public Buildings* (NCI Dublin) | 2024 | 2025-09 | Staff Data Scientist | Foundation document |
| ✅ | AICS 2025 Full Paper — *Forecasting Energy Demand: The Case for Trees over Deep Nets* (Springer CCIS) | 2025-09 | 2025-12 | Staff Data Scientist | 76/100, 85/100, 78/100 reviewer scores |
| ✅ | AICS 2025 Student Paper — DCU Press Companion Proceedings (dual-track acceptance) | 2025-09 | 2025-12 | Staff Data Scientist | 19/100 student reviewer — accepted trade-off |

### R2 — Journal Paper (Applied Energy / Energy and Buildings)

**Goal:** Extend AICS paper with H+24 paradigm parity, Oslo cross-city, horizon sweep, DM tests, Section 7 Responsible AI.

| Status | Item | Added | Resolved | Owner | Notes |
|--------|------|-------|----------|-------|-------|
| ✅ | H+24 Three-Way Paradigm Parity (Setup A/B/C) | 2026-01 | 2026-03-15 | Staff ML Engineer | LightGBM 4.029 kWh R²=0.975; PatchTST DM=−12.17*** |
| ✅ | Oslo cross-city generalisation (Sprint 3) | 2026-01 | 2026-03-15 | Staff ML Engineer | Oslo LightGBM MAE=7.415 R²=0.963; +84% PatchTST gap |
| ✅ | Horizon sweep H+1→H+48 (Sprint 2) | 2026-01 | 2026-03-15 | Staff ML Engineer | LightGBM +48%; Ridge +96%; results in horizon_metrics.csv |
| ✅ | Diebold-Mariano significance tests | 2026-01 | 2026-03-15 | Staff Data Scientist | vs Ridge −33.52***, XGBoost −5.25***, PatchTST −12.17*** |
| ✅ | Section 7: Responsible AI, Ethics, Deployment Governance | 2026-03 | 2026-03-28 | Staff Governance Lead | EU AI Act Limited Risk (Art. 52); GDPR; 5 subsections |
| 🔄 | Final manuscript review and journal selection decision | 2026-04 | — | Dan | Applied Energy target; Energy and Buildings backup |
| 🔴 | Submit to journal | 2026-04 | — | Dan | Priority once next session scheduled |
| 🟡 | Forecast Uncertainty Penalty (oracle vs NWP weather) | 2026-03 | — | Staff Data Scientist | Swap oracle temperature for NWP forecast archive; measure Δ MAE. "Highly publishable." — AI Studio |
| 🟡 | Daily Peak Error + Time of Peak Error metrics | 2026-03 | — | Staff Data Scientist | Peak metrics = what matters for Demand Response and grid operators |

**Key results (Drammen H+24, 240,481 test samples):**

| Model | MAE (kWh) | R² | Setup |
|-------|-----------|----|----|
| LightGBM | 4.029 | 0.9752 | A — Trees + Features |
| Stacking (Ridge meta) | 4.034 | 0.9751 | A |
| PatchTST | 6.955 | 0.9102 | C — DL + Raw Sequences |
| TFT | 8.770 | 0.8646 | B — DL + Features |
| Mean Baseline | 22.673 | 0.442 | — |

**Oslo cross-city (48 schools):** LightGBM MAE=7.415 R²=0.963; Stacking MAE=7.280 R²=0.9635; PatchTST MAE=13.616 (paradigm gap widens cross-city).

### R3 — PhD Track

| Status | Item | Added | Resolved | Owner | Notes |
|--------|------|-------|----------|-------|-------|
| 🔄 | **Decarb-AI (UCD-led)** — interview Tue 21 Apr 2026 with Andrew Parnell | 2026-03 | — | Dan | €31k/yr tax-free + fees; 4 years; 10 positions; Autumn 2026 start |
| 🟡 | RENEW / Pallonetto research collaboration (Maynooth) | 2026-04 | — | Dan | Call Apr 8 — no response. Pursue as **research-only** once Decarb-AI outcome known. See `docs/PALLONETTO_EMAIL.md` |
| 🎓 | PhD Route 2: Pallonetto (IRESI/MU) if Decarb-AI unsuccessful | 2026-04 | — | Dan | Joint paper on AI-driven load forecasting for Irish residential HEMS |
| 🎓 | Decision-Focused Learning ControlEngine (Favaro arXiv:2501.14708) | 2026-02 | — | Staff ML Engineer | Train with dispatch cost loss not MSE; requires SEMO prices |
| 🎓 | Hierarchical BART — cross-building pooling | 2026-01 | — | Staff ML Engineer | Very high effort; PhD-level |
| 🎓 | OOD generalisation (extreme weather) | 2026-01 | — | Staff ML Engineer | Liu et al. 2023 — applied ML safety research |
| 🎓 | Cross-domain transfer to Data Centre IT/Cooling load | 2026-03 | — | Staff Data Scientist | AI Studio suggestion — proves architecture generalises beyond buildings |
| 🎓 | Energy community dynamic pricing agents (Kazempour/Mitridati) | 2026-01 | — | Staff Energy Expert | RL-based prosumer behaviour; bridges to arXiv:2501.18017 |

---

## TRACK 2 — Core ML & MLOps Engineering

### E1 — Model Pipeline (COMPLETE)

| Status | Item | Added | Resolved | Owner |
|--------|------|-------|----------|-------|
| ✅ | Modularisation — 3 notebooks → `src/energy_forecast/` package | 2025 | 2025-12 | Staff ML Engineer |
| ✅ | Config-driven design — `config/config.yaml` single source of truth | 2025 | 2025-12 | Staff ML Engineer |
| ✅ | 35-feature vector — lags, rolling stats, cyclical encoding, weather interactions | 2025 | 2026-01 | Staff ML Engineer |
| ✅ | Oracle-safe features — only lags ≥ forecast_horizon (no leakage) | 2026-01 | 2026-01 | Staff ML Engineer |
| ✅ | DST-robust lags — lag_167h / lag_168h / lag_169h | 2026-01 | 2026-01 | Staff ML Engineer |
| ✅ | 3-stage feature selection — Variance → Correlation → LightGBM top-35 | 2026-01 | 2026-01 | Staff ML Engineer |
| ✅ | SHAP explainability — beeswarm, bar, waterfall, heatmap | 2026-01 | 2026-02 | Staff Data Scientist |
| ✅ | LightGBM Quantile P10/P50/P90 | 2026-02 | 2026-02 | Staff ML Engineer |
| ✅ | Horizon guard assertion — `forecast_horizon == sequence.horizon` | 2026-02 | 2026-02 | Staff ML Engineer |
| ✅ | BUG-C5 fix — `reshape_dl_predictions()` shared utility | 2026-03 | 2026-04-15 | Staff ML Engineer |
| ✅ | Test suite — 151 tests, 0 failures (CI on Python 3.10 & 3.11) | 2026-01 | 2026-04-15 | Staff ML Engineer |

**Production model decision (locked 2026-03-15):** LightGBM only in production. Not ensemble (+0.5% R² at 10× complexity). H+24 daily at 16:00 post-SEMO prices; H+1 hourly. Monthly retrain, rolling 24-month window. Drift trigger: 7-day rolling MAE > 1.5× training MAE. Cold start: 30 days population average → household-specific.

### E2 — MLOps & Production Readiness (COMPLETE — 2026-04-15, Session 40)

| Status | Item | Added | Resolved | Owner | Notes |
|--------|------|-------|----------|-------|-------|
| ✅ | **ModelRegistry** — CANDIDATE→ACTIVE→RETIRED lifecycle | 2026-04-15 | 2026-04-15 | Staff ML Engineer | Regression gate 1.05×, rollback, atomic writes, git lineage; `src/energy_forecast/registry/` |
| ✅ | **DriftDetector** — KS+PSI per feature, target drift, rolling MAE | 2026-04-15 | 2026-04-15 | Staff ML Engineer | PSI thresholds 0.10/0.20; 7-day window; `src/energy_forecast/monitoring/` |
| ✅ | **DataValidator** — hard fail (empty/NaN/Inf/shape) + solar WARNING | 2026-04-15 | 2026-04-15 | Staff ML Engineer | Wired into SklearnForecaster and LightGBMQuantileForecaster |
| ✅ | **`scripts/run_drift_check.py`** — CLI with CI-compatible exit codes | 2026-04-15 | 2026-04-15 | Staff Backend Engineer | Exit 1 on CRITICAL; auto-discovers training MAE |
| ✅ | **Exception hardening** — `logger.error(exc_info=True)` on all 5 critical paths | 2026-04-15 | 2026-04-15 | Staff ML Engineer | OOM split as MemoryError with actionable hint |
| ✅ | **Timezone config** — `cfg["data"].get("timezone", ...)` in loader + splits | 2026-04-15 | 2026-04-15 | Staff Data Engineer | Enables Irish household data without code changes |
| ✅ | **Monitoring config block** in `config/config.yaml` | 2026-04-15 | 2026-04-15 | Staff ML Engineer | rolling_window_days, mae_threshold_multiplier, PSI thresholds |
| ✅ | ADR-009 — City-specific processed paths (`data/processed/{city}/`) | 2026-04-15 | 2026-04-15 | Staff ML Engineer | Retroactive — Session 30 silent-overwrite bug |
| ✅ | ADR-010 — LightGBM-only production decision | 2026-04-15 | 2026-04-15 | Staff ML Engineer | Full 8-model comparison table |
| ✅ | **Stale docs cleanup** — 10 root-level duplicates deleted | 2026-04-15 | 2026-04-15 | Staff Governance Lead | Canonical versions in `docs/research/` + `docs/governance/` |
| 🔴 | `live_inference.py` registry-aware — replace file-glob with `registry.get_active()` | 2026-04-15 | — | Staff Backend Engineer | **Risk:** any pipeline re-run with worse MAE silently replaces live model |
| 🔴 | `run_pipeline.py` — SRP refactor (634-line monolith) | 2026-04-15 | — | Staff Backend Engineer | Refactor before Phase 7 productionisation — `train_stage.py`, `evaluate_stage.py`, `explain_stage.py` |
| 🔴 | Quantile Forecaster registry-aware | 2026-04-15 | — | Staff ML Engineer | P10/P50/P90 models also need registry lifecycle |
| 🟡 | `run_horizon_sweep.py` — hardcoded `"Europe/Oslo"` timezone | 2026-04-15 | — | Staff Data Engineer | Same fix as loader/splits — one-liner |
| 🟡 | `run_grand_ensemble.py` not registry-aware | 2026-04-15 | — | Staff ML Engineer | Grand ensemble outputs unversioned |
| 🟡 | Per-city timezone config (`data.timezones` map in config.yaml) | 2026-04-15 | — | Staff Data Engineer | Full solution beyond current `get("timezone", fallback)` |
| 🟡 | Integration tests — DriftDetector not exercised | 2026-04-15 | — | Staff ML Engineer | E2E test should assert drift report is written after pipeline run |
| 🟡 | CI rollback test — `ModelRegressionError` assertion | 2026-04-15 | — | Staff ML Engineer | Bad deploy → rollback flow tested end-to-end |
| 🟡 | `/health` endpoint drift status | 2026-04-15 | — | Staff Backend Engineer | Read latest drift report JSON and include in `/health` response |
| 🟡 | `CSVConnector` schema validation on load | 2026-04-15 | — | Staff Data Engineer | Validate column names and dtypes; raises `ValueError` with specifics |

### E3 — Governance & Documentation (COMPLETE)

| Status | Item | Added | Resolved | Owner |
|--------|------|-------|----------|-------|
| ✅ | `docs/governance/MODEL_CARD.md` — HuggingFace format, 10-model table | 2026-03 | 2026-04-15 | Staff Governance Lead |
| ✅ | `docs/governance/DATA_PROVENANCE.md` — 5-source GDPR chain | 2026-03 | 2026-03-28 | Staff Governance Lead |
| ✅ | `docs/governance/AIIA.md` — EU AI Act Limited Risk (Art. 52) | 2026-03 | 2026-03-28 | Staff Governance Lead |
| ✅ | `docs/governance/DATA_LINEAGE.md` — 8-stage raw CSV → Eddi action | 2026-03 | 2026-03-28 | Staff Governance Lead |
| ✅ | ADR-001 through ADR-010 — all major architectural decisions documented | 2026-02 | 2026-04-15 | Staff ML Engineer |

---

## TRACK 3 — Product: Consumer Energy App

### P1 — Phase A: Pre-Dynamic-Tariff Builds (April–June 2026) 🔄

**Trigger:** CRU dynamic pricing mandate live **1 June 2026**. Build the core product now, flip to live prices on mandate day.

| Status | Item | Priority | Added | Owner | Depends On | Notes |
|--------|------|----------|-------|-------|-----------|-------|
| 🔴 | **BTM Asset Detection** — Kazempour et al. (DTU, arXiv:2501.18017) | HIGH | 2026-04-15 | Staff ML Engineer | HDF data pipeline | Infer solar/EV/HP from 30-min profile; replaces onboarding survey; new `src/energy_forecast/btm/inference.py` |
| 🔴 | **WhatsApp / SMS Push** — extend Phase 6 morning brief | MEDIUM | 2026-04-15 | Staff Backend Engineer | Phase 6 complete | 71% Cost-Driven consumers won't open an app (SEAI BI); WhatsApp Business API or Twilio fallback |
| 🟡 | **Consumer Survey** — WTP for €3.99/month + €99-149 hardware | MEDIUM | 2026-04-15 | Staff Product Marketing | None | 5 questions, ~400 respondents via Pollfish; €200-400 budget; pricing validation before launch |
| 🟡 | **saveon.ie referral integration** | LOW | 2026-04-15 | Staff Product Manager | Written agreement | Step 1 (which tariff?) → Step 2 (optimise within it); shared HDF upload pipeline |

### P2 — Phase B: Dynamic Pricing Loop (June 2026) ⏳

**Trigger:** 1 June 2026 CRU mandate. 5 obligated suppliers: Electric Ireland, Bord Gáis, Energia, SSE Airtricity, Yuno.

| Status | Item | Priority | Added | Owner | Depends On | Notes |
|--------|------|----------|-------|-------|-----------|-------|
| 🔴 | **SEMO DAM price ingestion** — `SEMOConnector` stub → real API | CRITICAL | 2026-04-15 | Staff Energy Expert | ENTSO-E token | Day-ahead prices published ~16:00; 30-min resolution |
| 🔴 | **Dynamic tariff optimisation loop** | CRITICAL | 2026-04-15 | Staff ML Engineer | PB-1 (DAM prices) | H+24 forecast + price vector → device scheduling; extend ControlEngine |
| 🔴 | **ESCO registration** — File Appendix A with ESB Networks | CRITICAL | 2026-04-15 | Staff Energy Expert | SMDS live (at risk) | Free data access once SMDS live; draft Appendix A in `docs/regulatory/` |
| 🟡 | **Heat pump BTM detection variant** | HIGH | 2026-04-15 | Staff ML Engineer | PA-1 BTM complete | HP load signature; SEAI HPSS grant = acquisition channel; 400k HP target by 2030 |

### P3 — Phase C: Scale (H2 2026)

| Status | Item | Priority | Added | Owner | Depends On | Notes |
|--------|------|----------|-------|-------|-----------|-------|
| 🔵 | **Social comparison** — "Homes like yours save 23% more" | MEDIUM | 2026-04-15 | Staff Product Manager | Multi-household data | Blocked until RENEW pilot or first users; aggregate server-side only |
| 🔵 | **P1 hardware MVP** — Pi Zero 2W (€15) + DSMR P1 USB adapter (€8-12) | MEDIUM | 2026-04-15 | Staff Backend Engineer | ESB Networks P1 activation | Customer self-install <5 min; custom PCB only at >1k units/month |
| 🔵 | **Battery storage scheduling** — charge/discharge optimisation | MEDIUM | 2026-04-15 | Staff ML Engineer | PB-2 dynamic loop | New `CHARGE_BATTERY` action in `actions.py` |
| 🔵 | **Commercial beta launch** | HIGH | 2026-04-15 | Staff Product Manager | Phase B + pilot hardware | 10-household pilot; saveon.ie + SEAI HPSS channel |
| 🎓 | **LLM Energy Advisor** — `claude-haiku-4-5`, ~€0.04/user/month | LOW | 2026-03 | Staff ML Engineer | Phase B | Context injection: 30d stats + tariff + forecast; no raw time-series to API |
| 🎓 | **Smart Meter Analyst Agent** — Claude Code + trust hierarchy + CER schema | 2026-03 | — | Staff ML Engineer | CER dataset access | Natural language → Pandas → shareable report; EI Innovation Voucher artefact |

---

## TRACK 4 — Deployment & Infrastructure

### D1 — Phase 7: Cloud Deployment (STARTED — commit a15d297)

**Platform decision (locked):** AWS App Runner, eu-west-1 (Irish data residency).

| Status | Item | Added | Resolved | Owner | Notes |
|--------|------|-------|----------|-------|-------|
| ✅ | FastAPI app — `/predict`, `/control`, `/health` endpoints | 2026-02 | 2026-02 | Staff Backend Engineer | `deployment/app.py` |
| ✅ | Dockerfile — production image, non-root user, HEALTHCHECK | 2026-03 | 2026-03-15 | Staff Backend Engineer | commit a15d297 |
| ✅ | `apprunner.yaml` — App Runner config | 2026-03 | 2026-03-15 | Staff Backend Engineer | commit a15d297 |
| ✅ | `Makefile` — `docker-build` / `ecr-push` / `apprunner-deploy` targets | 2026-03 | 2026-03-15 | Staff Backend Engineer | |
| 🔴 | ECR push + App Runner initial deploy | 2026-04-15 | — | Staff Backend Engineer | AWS account | Smoke test: `/health` → `/predict` → `/control` |
| 🔴 | `live_inference.py` registry-aware | 2026-04-15 | — | Staff Backend Engineer | ModelRegistry | See E2 above — CRITICAL risk |
| 🟡 | `/health` endpoint — drift status from latest report JSON | 2026-04-15 | — | Staff Backend Engineer | DriftDetector | |
| 🟡 | S3 model artefact store — push `outputs/models/*.joblib` to S3 | 2026-04-15 | — | Staff Backend Engineer | AWS account | Replace baked-in Docker model copy |
| 🟡 | AWS Secrets Manager — API keys (SEMO, myenergi, Ecowitt) | 2026-04-15 | — | Staff Backend Engineer | AWS account | Remove `.env` dependency |
| 🔵 | CloudWatch alarm — MAE drift → SNS alert | 2026-04-15 | — | Staff Backend Engineer | App Runner live | |

### D2 — Phase 8: Home Trial Hardware (Pending)

**Hardware decision (locked 2026-04-15):** Mac Mini M5 (~€699) + DSMR P1 USB adapter (~€10) = ~€709 total. Production hardware TBD (<€30 BOM target at >500 units/month).

| Status | Item | Added | Resolved | Owner | Notes |
|--------|------|-------|----------|-------|-------|
| ✅ | ESB CSV ingestion — `scripts/run_home_demo.py` | 2026-03 | 2026-03 | Staff Data Engineer | 30-min pivot, resample, DST-safe |
| ✅ | BGE tariff model — Day/Night/Peak/Free Sat/Export rates | 2026-03 | 2026-03 | Staff Energy Expert | Single source of truth: `src/energy_forecast/tariff.py` |
| ✅ | OpenMeteo live weather connector | 2026-02 | 2026-02 | Staff Data Engineer | Free, no API key required |
| ✅ | Morning brief CLI — `python deployment/live_inference.py --dry-run` | 2026-02 | 2026-02 | Staff Backend Engineer | P10/P50/P90, BGE cost, control actions |
| ✅ | myenergi Eddi live status — `MyEnergiConnector.get_status()` | 2026-03 | 2026-03 | Staff Data Engineer | Hub serial 21509692 |
| ✅ | `scripts/log_eddi.py` — `--once`, `--history N`, `--interval` | 2026-03 | 2026-03 | Staff Data Engineer | |
| ✅ | Home Plan Score — 62/100, €178.65/yr saving identified | 2026-03 | 2026-03 | Staff Product Manager | Oct 2023–Oct 2025, 730 days |
| 🔴 | Mac Mini M5 + P1 adapter setup | 2026-04-15 | — | Dan | Hardware purchase | P1 adapter: DSMR USB, €8-12 from NL |
| 🔴 | **BGE contract renewal** — URGENT (expires 15 Jun 2026) | 2026-04 | — | Dan | — | Renewal window open NOW. Target: dynamic tariff from BGE or switch to dynamic supplier |
| 🟡 | EcowittConnector — personal weather station API | 2026-04 | — | Staff Data Engineer | Hardware | GW1100, api.ecowitt.net/api/v3/device/real_time — stub exists |
| 🔵 | `send_command()` activation — Eddi scheduling via API | 2026-04 | — | Staff Backend Engineer | User approval flow | Monitor → Recommend → Automate. Never send commands without user approval |

### D3 — Connectors & Data Access

| Status | Item | Added | Resolved | Owner | Notes |
|--------|------|-------|----------|-------|-------|
| ✅ | `CSVConnector` — demo/test mode from parquet | 2026-02 | 2026-02 | Staff Data Engineer | |
| ✅ | `OpenMeteoConnector` — live weather + solar irradiance | 2026-02 | 2026-02 | Staff Data Engineer | |
| ✅ | `SEMOConnector` stub — day-ahead prices | 2026-02 | 2026-02 | Staff Energy Expert | ENTSO-E API token needed |
| ✅ | `MockDeviceConnector` — CI/demo safe command logging | 2026-02 | 2026-02 | Staff Backend Engineer | |
| 🟡 | `CSVConnector` schema validation — column names, dtypes, DatetimeTz index | 2026-04-15 | — | Staff Data Engineer | |
| 🟡 | `SEMOConnector` — real ENTSO-E API implementation | 2026-05 | — | Staff Energy Expert | ENTSO-E token | Unblocks Phase B dynamic pricing |
| 🔵 | `MQTTConnector` — industrial sensor feeds | 2026-03 | — | Staff Data Engineer | MQTT broker | B2B use case |
| 🔵 | P1Connector — real-time ESB smart meter via P1 port USB | 2026-03 | — | Staff Data Engineer | P1 hardware | Same DSMR P1 standard as NL/BE/LU/ES |

---

## TRACK 5 — Commercial & Regulatory

### C1 — Regulatory & Compliance

| Status | Item | Added | Resolved | Owner | Notes |
|--------|------|-------|----------|-------|-------|
| ✅ | EU AI Act classification — Limited Risk (Art. 52) | 2026-03 | 2026-03-28 | Staff Governance Lead | Transparency obligations: confidence range always shown, always an override, every action logged |
| ✅ | GDPR compliance — Art. 6(1)(a) consent for own meter data | 2026-03 | 2026-03-28 | Staff Governance Lead | |
| ✅ | CRU PCW accreditation — definitively NOT needed | 2026-04 | 2026-04-15 | Staff Energy Expert | We are ESCO / Eligible Party under CRU202517, not a PCW |
| 🔴 | ESCO / Eligible Party registration — Appendix A with ESB Networks | 2026-04-15 | — | Staff Energy Expert | SMDS live (mid-2026 target, at risk) | Draft ready in `docs/regulatory/` |
| 🟡 | SMDS status tracking — ESB Networks near-real-time data access | 2026-03 | — | Staff Energy Expert | ESB Networks decision | P1 port hardware already installed on all Irish meters; software activation pending |
| 🟡 | GDPR privacy policy — 30-min data reveals occupancy | 2026-04-15 | — | Staff Governance Lead | Phase 7 live | On-device inference preferred long-term; disclose in privacy policy |

### C2 — Funding & Go-to-Market

| Status | Item | Priority | Added | Owner | Notes |
|--------|------|----------|-------|-------|-------|
| 🔴 | **AWS Activate** — free compute credits (no company needed) | HIGH | 2026-04-15 | Dan | Apply immediately |
| 🟡 | **SEAI RD&D** — research funding call (May–Jul 2026) | HIGH | 2026-04-15 | Dan | NCI partner route |
| 🟡 | **Enterprise Ireland HPSU Feasibility Grant** — €35k pre-revenue | MEDIUM | 2026-04-15 | Dan | Requires company formation first |
| 🟡 | **New Frontiers** programme — via Orla Byrne (NCI) | MEDIUM | 2026-04-15 | Dan | Pre-incorporation pathway |
| 🔵 | **EI iHPSU** — up to €1.2M, needs 6-month traction | LOW | 2026-04-15 | Dan | Phase C |
| 🔵 | **Dogpatch 2050 Accelerator** — ESB partner, equity-free | LOW | 2026-04-15 | Dan | Jan 2027 cohort |
| 🔵 | Heat pump angle — SEAI HPSS grant as acquisition channel | MEDIUM | 2026-04-15 | Staff Product Marketing | BTM HP detection | Ireland 400k HP target by 2030 |
| 🔵 | RENEW collaboration (Pallonetto/MU) — research-only | LOW | 2026-04-15 | Dan | Decarb-AI outcome | 20-50 household pilot network; joint paper |

---

## Known Issues & Debt Registry

### Active Bugs

| ID | Item | Severity | Added | Owner | Status |
|----|------|----------|-------|-------|--------|
| BUG-E1 | Stacking Ensemble OOF drops rows when `LightGBM_Quantile` is included — NaN generation from missing sklearn `clone()` compatibility | MEDIUM | 2026-03 | Staff ML Engineer | Open — fix: add `LightGBM_Quantile` to exclusion list in `run_pipeline.py` before `StackingEnsemble` |
| BUG-D1 | `run_horizon_sweep.py` hardcodes `"Europe/Oslo"` timezone | LOW | 2026-04-15 | Staff Data Engineer | Open — one-line fix |
| BUG-D2 | TFT `num_workers=0` — GPU underutilised on macOS | LOW | 2026-03 | Staff ML Engineer | Known — `num_workers=4` fix deferred (macOS spawn overhead) |

### Resolved Bugs (selected — full history in git log)

| ID | Item | Resolved | Session |
|----|------|----------|---------|
| BUG-C5 | DL H+24 predictions flattened incorrectly — `reshape_dl_predictions()` | 2026-04-15 | 40 |
| BUG-C3 | TFT BUG — `timestamp` in `time_varying_known_reals` → OOD saturation | 2026-03 | — |
| BUG-C6 | Stacking OOF early stopping leakage — val data leaked into fold fitting | 2026-03 | — |
| BUG-DL-H24 | DL H+24 evaluation length mismatch — `_build_y_true_matrix()` | 2026-03 | — |
| BUG-C4 | Rolling window target leakage — `shift(1)` before rolling | 2026-03 | — |
| BUG-LOC | `data/processed/` shared across cities — oslo clobbers drammen | 2026-03-15 | 30 |
| BUG-PEAK | Peak rate logic applied all days — Mon–Fri only | 2026-03 | 31 |
| BUG-DL-OOM | DL predict OOM — `batch_size=512` required | 2026-03 | 31 |

### Strategic Debt (documented, time-bounded, no reckless items)

| ID | Item | Severity | Plan |
|----|------|----------|------|
| DEBT-1 | `run_pipeline.py` SRP violation — 634-line monolith | MEDIUM | Refactor into stage modules before Phase 7 productionisation |
| DEBT-2 | `live_inference.py` file-glob model loading | HIGH | Replace with `registry.get_active()` — CRITICAL before App Runner deploy |
| DEBT-3 | No CI gate on model regression | MEDIUM | Add `ModelRegressionError` assertion to CI test suite |
| DEBT-4 | Per-city timezone map not yet in config.yaml | LOW | Needed before adding second non-Norwegian city |

---

## Deferred / Long-Term Research (🎓 PhD-Track)

| Item | Source | Concept | When to Revive |
|------|--------|---------|---------------|
| Automated Market Maker integration | Shaun Sweeney 2025 | Modeling load agents in AMM pricing framework | PhD research |
| Price-responsive load agents (RL) | Sweeney / Crowley | RL-based agents reacting to dynamic grid pricing | PhD research |
| Asymmetric settlement risk loss | Sweeney | Penalise under-procurement differently from over-procurement | PhD research |
| Hierarchical BART cross-building | Q6, Chipman 2010 | Partial pooling across 45 buildings | PhD — very high effort |
| NILMTK load disaggregation | Phase 6B | Per-appliance load from whole-house signal | After BTM detection (PA-1) |
| ERA5 reanalysis weather | 2026-01 | Meteorological fallback / synthetic weather source | Journal paper extension |
| ONNX export | 2026-01 | Framework-agnostic LightGBM/XGBoost inference | Commercial scaling |
| Irish CER residential dataset (2009-2010) | Sprint 3B | 6,435 households, 30-min, pre-smart-meter | Revive if CER access confirmed and research question requires it |
| Walk-forward rolling window back-test | 2026-01 | Concept drift simulation across production months | PhD / journal extension |

---

## Appendix A — Experiment Results Archive

### V2 Pipeline — H+1 (240,481 test samples)

| Model | MAE (kWh) | R² | Thesis MAE | Δ |
|-------|-----------|----|-----------|----|
| Random Forest | 1.711 | 0.9947 | 3.300 | −48% |
| Stacking (Ridge meta) | 1.774 | 0.9953 | 3.698 | −52% |
| LightGBM | 2.108 | 0.9938 | 3.578 | −41% |
| XGBoost | 2.228 | 0.9931 | 3.419 | −35% |
| LSTM | 3.582 | 0.9816 | 10.132 | −65% |
| GRU | 3.947 | 0.9812 | — | — |
| CNN-LSTM | 4.572 | 0.9767 | 12.435 | −63% |
| Mean Baseline | 22.691 | 0.4415 | — | — |

### H+24 Paradigm Parity — Drammen (2026-03-15)

| Model | MAE (kWh) | R² | Setup |
|-------|-----------|----|----|
| LightGBM | 4.029 | 0.9752 | A |
| XGBoost | 4.197 | 0.9740 | A |
| Random Forest | 4.402 | 0.9690 | A |
| Stacking (Ridge meta) | 4.034 | 0.9751 | A |
| Ridge | 7.460 | 0.9260 | A |
| PatchTST | 6.955 | 0.9102 | C |
| TFT | 8.770 | 0.8646 | B |
| CNN-LSTM | 9.375 | — | B |
| Mean Baseline | 22.673 | 0.442 | — |

### Horizon Sweep — Drammen LightGBM (MAE kWh, 2026-03-15)

| H+1 | H+6 | H+12 | H+24 | H+48 | Degradation |
|-----|-----|------|------|------|-------------|
| 3.188 | 3.584 | 3.799 | 4.057 | 4.724 | +48% |

Ridge H+1→H+48 degradation: +96%. **Tree advantage widens with horizon.**

### DM Significance Tests (HLN-corrected, H+24, 2026-03-15)

| Comparison | Statistic | p |
|-----------|-----------|---|
| LightGBM vs PatchTST | −12.17 | *** |
| LightGBM vs XGBoost | −5.25 | *** |
| LightGBM vs Ridge | −33.52 | *** |

### Oslo Cross-City (48 schools, 2026-03-15)

| Model | MAE (kWh) | R² | vs Drammen gap |
|-------|-----------|----|----|
| LightGBM | 7.415 | 0.9630 | Scale effect (Oslo buildings 2× larger) |
| Stacking | 7.280 | 0.9635 | |
| PatchTST | 13.616 | 0.8741 | +84% (widens cross-city vs +72% Drammen) |

**R² values consistent (0.963 vs 0.975) — scale effect, not quality degradation.**

### Original Thesis Results (NCI 2025)

| Model | MAE (kWh) | RMSE | R² | Train (s) |
|-------|-----------|------|-----|-----------|
| Random Forest | 3.300 | 6.403 | 0.982 | 116 |
| XGBoost | 3.419 | 6.443 | 0.982 | 3 |
| LightGBM | 3.578 | 6.679 | 0.980 | 3 |
| Stacking (Ridge meta) | 3.698 | 7.051 | 0.978 | <1 |
| TFT (Comprehensive) | 5.114 | 10.424 | 0.952 | 21,831 |
| LSTM | 10.132 | 17.686 | 0.862 | 13,497 |
| CNN-LSTM | 12.435 | 20.930 | 0.807 | 2,238 |

---

## Appendix B — Key External Feedback

| Source | Finding | Priority | Status |
|--------|---------|----------|--------|
| AI Studio | H+1 = "easy mode" (lag_1h r=0.977); H+24 is the honest evaluation | 🔴 HIGH | ✅ Applied |
| AI Studio | Feature parity ≠ paradigm parity — DL needs raw sequences, trees need engineered features | 🔴 HIGH | ✅ Applied (Setup C) |
| AI Studio | "Menu of Solutions" framing: H+1=Stability, H+24=Day-Ahead, Quantiles=Risk-MPC | 🔴 HIGH | ✅ Applied |
| AI Studio | Add Daily Peak Error + Time of Peak Error — the metrics that matter for DR operators | 🟡 MEDIUM | Pending |
| AI Studio | Forecast Uncertainty Penalty (oracle vs NWP weather) — highly publishable | 🟡 MEDIUM | Pending |
| AI Studio | Cross-domain transfer to Data Centre IT/Cooling load | 🎓 PhD | Pending |
| AICS R1 | DL given engineered features = feature parity trap; DL needs raw sequences | 🔴 HIGH | ✅ Applied |
| AICS R2 | Single dataset limits generalisability | 🟡 MEDIUM | ✅ Applied (Oslo) |
| SINTEF Expert | Tree models validated; solar radiation is a valid Phase 2 feature | 🟡 MEDIUM | Partial |

---

## Key External Deadlines

| Date | Event | Track | Status |
|------|-------|-------|--------|
| **21 Apr 2026** | Decarb-AI PhD interview — Andrew Parnell (UCD) | Research | ACTIVE |
| **15 Jun 2026** | BGE contract renewal deadline | Product | URGENT |
| **1 Jun 2026** | CRU dynamic pricing mandate — 5 Irish suppliers | Product | KEY TRIGGER |
| **May–Jul 2026** | SEAI RD&D funding call (NCI partner route) | Commercial | TRACK |
| **Mid-2026** | ESB Networks SMDS live — ESCO Appendix A | Regulatory | AT RISK |
| TBD | Applied Energy journal submission | Research | Draft ready |
| TBD | AWS Activate (free credits — apply now, no company needed) | Infrastructure | APPLY IMMEDIATELY |
| TBD | EI HPSU Feasibility Grant (€35k, pre-revenue) | Commercial | PENDING LAUNCH |
| Jan 2027 | Dogpatch 2050 Accelerator — ESB partner, equity-free | Commercial | TRACK |
