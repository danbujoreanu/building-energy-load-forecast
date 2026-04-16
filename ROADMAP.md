# Sparc Energy — Product Engineering Roadmap

**Project:** Building Energy Load Forecast → Sparc Energy Ltd (pre-incorporated)
**Last updated:** 2026-04-16 (Session 42)
**Mission:** Day-ahead electricity load forecasting for Irish residential homes, enabling
demand-response optimisation against dynamic pricing. MSc AI thesis → cleantech startup.

> **Single source of truth.** Every new item discovered during any session must be added here
> before closing. Reference items by ID (e.g. `E-22`) in conversation, commit messages, and ADRs.

---

## How to Read This Roadmap

### Reference System

Every item has a unique ID: **`{TRACK}-{NN}`** — track letter + two-digit sequence number.
In conversation: say "P-01" and we both know exactly which item is meant. Zero ambiguity.

| Track | Code | Domain |
|-------|------|--------|
| Research & Publication | **R** | Papers, PhD, academic experiments |
| Engineering & MLOps | **E** | Pipeline, models, monitoring, code quality |
| Product & Consumer App | **P** | Features, UX, consumer value |
| Deployment & Infrastructure | **D** | Cloud, hardware, connectors, live system |
| Commercial & Regulatory | **C** | Funding, CRU, GDPR, go-to-market |
| Bug Registry | **BUG** | Active and resolved defects |

### Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete — date in parentheses |
| 🔄 | In progress this quarter |
| 🔴 | High priority — next in queue |
| 🟡 | Medium — planned, not yet started |
| 🔵 | Low / exploratory |
| 🎓 | PhD-track / long-term research |
| ⏸️ | Deferred — blocked or deprioritised |
| 🚨 | Urgent — has a hard deadline |

### Ownership Personas

| Persona | Responsibilities |
|---------|-----------------|
| **Staff ML Engineer** | Models, features, training pipeline, MLOps, registry |
| **Staff Data Engineer** | Data connectors, preprocessing, schema, provenance |
| **Staff Backend Engineer** | FastAPI, Docker, AWS, CI/CD, API contracts |
| **Staff Reliability Engineer** | Retry logic, timeouts, fallbacks, circuit breakers, chaos testing |
| **Staff Data Scientist** | Evaluation, significance tests, paper figures, observability |
| **Staff Product Manager** | Product vision, PRDs, sequencing, commercial priorities |
| **Rory** | Consumer psychology, behavioural economics, product trust, framing. Challenges automation-for-cost thinking. Asks: "Does this feel like a knowledgeable friend, or a cost-reduction FAQ bot?" Applies to every consumer-facing output — morning brief, control actions, LLM advisor. |
| **Staff Product Marketing** | Positioning, go-to-market, consumer segmentation, pricing |
| **Staff Energy Expert** | Tariff modelling, demand-response, CRU regulations, grid mechanics |
| **Staff Governance Lead** | EU AI Act, GDPR, Model Cards, AIIAs, data lineage, audit trails |
| **Dan (founder)** | All of the above — single contributor |

---

## Status Snapshot — Q2 2026

| Track | State | Blocking Item | Hard Deadline |
|-------|-------|--------------|---------------|
| Research | 🔄 Journal paper in draft | R-09: final review + submit | TBD |
| Engineering | ✅ Production-grade as of Session 40/41 | E-17: SRP refactor (pre-Phase 7) | Before D-12 |
| Product | 🔄 Pre-tariff sprint | P-01: BTM detection | Before 1 Jun 2026 |
| Deployment | 🔄 Phase 7 started | D-12: App Runner live | Before C1 market |
| Commercial | 🚨 47 days to CRU mandate | C-07: AWS Activate (apply now) | 1 Jun 2026 |
| PhD | 🔄 Interview 21 Apr | R-12: Decarb-AI outcome | 21 Apr 2026 |

---

## TRACK R — Research & Publication

### R-01 through R-03: Conference & Thesis (COMPLETE)

| ID | Item | Status | Added | Resolved | Owner |
|----|------|--------|-------|----------|-------|
| R-01 | MSc Thesis — *ML Approaches for Building Energy Load Forecasting in Norwegian Public Buildings* (NCI Dublin) | ✅ | 2024 | 2025-09 | Staff Data Scientist |
| R-02 | AICS 2025 Full Paper — *Forecasting Energy Demand: The Case for Trees over Deep Nets* (Springer CCIS) | ✅ | 2025-09 | 2025-12 | Staff Data Scientist |
| R-03 | AICS 2025 Student Paper — DCU Press Companion Proceedings (dual-track acceptance) | ✅ | 2025-09 | 2025-12 | Staff Data Scientist |

### R-04 through R-08: Journal Paper Experiments (COMPLETE)

| ID | Item | Status | Added | Resolved | Owner | Notes |
|----|------|--------|-------|----------|-------|-------|
| R-04 | H+24 Three-Way Paradigm Parity (Setup A/B/C) | ✅ | 2026-01 | 2026-03-15 | Staff ML Engineer | LightGBM 4.029 kWh R²=0.975; PatchTST DM=−12.17*** |
| R-05 | Oslo cross-city generalisation | ✅ | 2026-01 | 2026-03-15 | Staff ML Engineer | LightGBM MAE=7.415 R²=0.963; paradigm gap widens +84% cross-city |
| R-06 | Horizon sweep H+1→H+48 | ✅ | 2026-01 | 2026-03-15 | Staff ML Engineer | LightGBM +48% degradation; Ridge +96%; tree advantage widens with horizon |
| R-07 | Diebold-Mariano significance tests | ✅ | 2026-01 | 2026-03-15 | Staff Data Scientist | vs Ridge −33.52***, XGBoost −5.25***, PatchTST −12.17*** |
| R-08 | Section 7: Responsible AI, Ethics, Deployment Governance | ✅ | 2026-03 | 2026-03-28 | Staff Governance Lead | EU AI Act Art. 52 Limited Risk; GDPR; 5 subsections |

### R-09 through R-11: Journal Paper — In Progress & Planned

| ID | Item | Status | Priority | Added | Owner | Notes |
|----|------|--------|----------|-------|-------|-------|
| R-09 | Final manuscript review + journal submission (Applied Energy / Energy and Buildings) | 🔄 | HIGH | 2026-04 | Dan | Draft complete. Applied Energy = target; Energy and Buildings = backup |
| R-10 | Forecast Uncertainty Penalty — oracle vs NWP weather Δ MAE | 🟡 | MEDIUM | 2026-03 | Staff Data Scientist | AI Studio: "Highly publishable — proves production-readiness." Swap oracle temperature for archived NWP forecast; measure degradation |
| R-11 | Daily Peak Error + Time of Peak Error metrics | 🟡 | MEDIUM | 2026-03 | Staff Data Scientist | The metrics that matter for Demand Response operators. Peak MAE sells to Viotas, ESB, data centres |

### R-12 through R-18: PhD Track

| ID | Item | Status | Priority | Added | Owner | Notes |
|----|------|--------|----------|-------|-------|-------|
| R-12 | **Decarb-AI (UCD-led) PhD — interview 21 Apr 2026** | 🔄 | HIGH | 2026-03 | Dan | €31k/yr tax-free + fees; 4 years; 10 positions; UCD Statistics supervisor |
| R-13 | RENEW research collaboration (Maynooth University) | 🟡 | MEDIUM | 2026-04 | Dan | Call Apr 8 — awaiting response. Pursue as research-only post Decarb-AI outcome. |
| R-14 | Decision-Focused Learning ControlEngine (Favaro arXiv:2501.14708) | 🎓 | — | 2026-02 | Staff ML Engineer | Train with dispatch cost loss not MSE; requires SEMO prices (D-20) |
| R-15 | Hierarchical BART — cross-building pooling | 🎓 | — | 2026-01 | Staff ML Engineer | Very high effort; PhD-level; Chipman et al. 2010 |
| R-16 | OOD generalisation for extreme weather | 🎓 | — | 2026-01 | Staff ML Engineer | Liu et al. 2023 — applied ML safety research |
| R-17 | Cross-domain transfer to Data Centre IT/Cooling load | 🎓 | — | 2026-03 | Staff Data Scientist | AI Studio suggestion — proves architecture generalises beyond Norwegian buildings |
| R-18 | Energy community dynamic pricing agents (Kazempour/Mitridati) | 🎓 | — | 2026-01 | Staff Energy Expert | RL-based prosumer behaviour; arXiv:2501.18017; bridges to P-01 BTM inference |

---

## TRACK E — Engineering & MLOps

### E-01 through E-16: Model Pipeline & Technical Debt Sprint (COMPLETE)

| ID | Item | Status | Added | Resolved | Owner | Notes |
|----|------|--------|-------|----------|-------|-------|
| E-01 | Core ML pipeline — 35-feature vector, LightGBM, Stacking, SHAP, 153 tests | ✅ | 2025 | 2026-04-15 | Staff ML Engineer | See Appendix A for all results |
| E-02 | ModelRegistry — CANDIDATE→ACTIVE→RETIRED lifecycle | ✅ | 2026-04-15 | 2026-04-15 | Staff ML Engineer | Regression gate 1.05×, rollback, atomic writes, git lineage; `src/energy_forecast/registry/` |
| E-03 | DriftDetector — KS+PSI per feature, target drift, rolling MAE trigger | ✅ | 2026-04-15 | 2026-04-15 | Staff ML Engineer | 7-day window, 1.5× threshold; `src/energy_forecast/monitoring/` |
| E-04 | DataValidator — hard fail on empty/NaN/Inf/shape | ✅ | 2026-04-15 | 2026-04-15 | Staff ML Engineer | >1% negatives = WARNING only (valid solar export); `src/energy_forecast/validation.py` |
| E-05 | BUG-C5 fix — `reshape_dl_predictions()` shared utility | ✅ | 2026-04-15 | 2026-04-15 | Staff ML Engineer | Eliminates H+24 interleaving bug across LSTM/GRU/CNN-LSTM/TFT |
| E-06 | Exception hardening — `logger.error(exc_info=True)` on all 5 critical paths | ✅ | 2026-04-15 | 2026-04-15 | Staff ML Engineer | OOM → MemoryError with actionable hint; atomic metrics writes |
| E-07 | Timezone config — `cfg["data"].get("timezone", ...)` in loader + splits | ✅ | 2026-04-15 | 2026-04-15 | Staff Data Engineer | Per-city timezone map: `data.timezones` in config.yaml |
| E-08 | ADR-001 through ADR-010 — all architectural decisions documented | ✅ | 2026-04-15 | 2026-04-15 | Staff ML Engineer | `docs/adr/` — all committed |
| E-09 | Governance docs — Model Card, AIIA, Data Provenance, Data Lineage | ✅ | 2026-03 | 2026-03-28 | Staff Governance Lead | `docs/governance/` — interview-ready for Okta |
| E-10 | `live_inference.py` registry-aware | ✅ | 2026-04-15 | 2026-04-15 | Staff Backend Engineer | `registry.get_active()` first; file-glob fallback with `logger.warning` |
| E-11 | Per-city timezone config (`data.timezones` map in config.yaml) | ✅ | 2026-04-15 | 2026-04-15 | Staff Data Engineer | drammen/oslo/ireland/default |
| E-12 | `CSVConnector` schema validation — required columns, tz-aware index | ✅ | 2026-04-15 | 2026-04-15 | Staff Data Engineer | `_REQUIRED_COLUMNS` frozenset; `_validate_schema()` classmethod |
| E-13 | `/health` endpoint drift status | ✅ | 2026-04-15 | 2026-04-15 | Staff Backend Engineer | `_load_latest_drift_report(city)` — never raises; exposes severity/recommended_action |
| E-14 | Quantile Forecaster registry-aware | ✅ | 2026-04-15 | 2026-04-15 | Staff ML Engineer | `model_name="lightgbm_quantile"` in `run_pipeline.py` registry block |
| E-15 | DriftDetector integration test | ✅ | 2026-04-15 | 2026-04-15 | Staff ML Engineer | `TestDriftDetectorIntegration` — asserts severity != CRITICAL on identical data; JSON round-trip |
| E-16 | CI rollback test — full bad-deploy→rollback scenario | ✅ | 2026-04-15 | 2026-04-15 | Staff ML Engineer | v1 ACTIVE → v2 raises `ModelRegressionError` → force → rollback restores v1 |

### E-17 through E-28: Outstanding Engineering Items

| ID | Item | Status | Priority | Added | Owner | Depends On | Source |
|----|------|--------|----------|-------|-------|-----------|--------|
| E-17 | `run_pipeline.py` SRP refactor — 634-line monolith → stage modules | 🔴 | HIGH | 2026-04-15 | Staff Backend Engineer | — | Audit |
| E-18 | `run_grand_ensemble.py` registry-aware | 🟡 | MEDIUM | 2026-04-15 | Staff ML Engineer | — | Audit |
| E-19 | Strict Pydantic schemas for FastAPI — model-derived 35-feature `PredictionRequest` | 🔴 | HIGH | 2026-04-15 | Staff Backend Engineer | — | IBM Skill 2 |
| E-20 | ControlEngine JSONL audit log — structured per-decision trail | 🔴 | HIGH | 2026-04-15 | Staff Data Scientist | — | IBM Skill 6 |
| E-21 | ModelRegistry human review gate — CANDIDATE→ACTIVE requires explicit approval flag | 🟡 | MEDIUM | 2026-04-15 | Staff ML Engineer | — | Screenshot audit |
| E-22 | Drift check post-training hook — auto-run `run_drift_check.py` after Stage 3 | 🔴 | HIGH | 2026-04-15 | Staff ML Engineer | — | Screenshot audit |
| E-23 | Connector retry / timeout / circuit breaker — all live HTTP connectors | 🔴 | HIGH | 2026-04-15 | Staff Reliability Engineer | — | IBM Skill 4 |
| E-24 | `ControlAction.user_message` — plain-English translation of every action | 🔴 | HIGH | 2026-04-15 | Rory + Staff Backend Engineer | — | IBM Skill 7 |
| E-25 | `src/energy_forecast/llm/context_builder.py` — deterministic system-prompt formatter | 🟡 | MEDIUM | 2026-04-15 | Staff ML Engineer | P-13 LLM Advisor | IBM Skill 3 |
| E-26 | LLM output filter / safety guard — block out-of-scope LLM advisor responses | 🟡 | MEDIUM | 2026-04-15 | Staff Governance Lead | P-13 LLM Advisor | IBM Skill 5 |
| E-27 | Prediction history store — append each H+24 prediction to `predictions` PostgreSQL table | 🔴 | HIGH | 2026-04-16 | Staff Data Engineer | D-25 schema | Enables P-16 outcome tracking. Fields: household_id, predicted_at, p10/p50/p90 json, model_version_id |
| E-28 | ADR-011 — tech stack decision (PostgreSQL + Supabase + Redis vs alternatives) | 🟡 | MEDIUM | 2026-04-16 | Staff Backend Engineer | D-23 | Document why Supabase over Firebase, PlanetScale, DynamoDB for this use case |

**Notes on outstanding items:**

- **E-17 (SRP refactor):** `run_pipeline.py` at 634 lines is a single-file monolith. Target: `scripts/stages/train_stage.py`, `evaluate_stage.py`, `explain_stage.py`, each ≤200 lines. `run_pipeline.py` becomes a thin orchestrator. Must be done before D-12 (App Runner deploy) or it ships with the debt baked in.

- **E-19 (Pydantic schemas):** Current `PredictionRequest` accepts `features: dict[str, float]` — any key, any count. The production LightGBM model expects exactly the 35 features selected by the 3-stage process (stored in `model.feature_name_`). The fix: at server startup, load the active model and read its `feature_name_` attribute to build a dynamic Pydantic model. Wrong feature names → 400 error with specific message, not a silent prediction with wrong inputs. New module: `src/energy_forecast/api/schemas.py`.

- **E-20 (JSONL audit log):** Every `ControlAction` decision appended to `outputs/logs/control_decisions.jsonl`. Fields: timestamp, building_id, city, action_type, confidence, reasoning, p50_load_kwh, solar_forecast_wm2, price_eur_kwh, dry_run, user_message. Required for EU AI Act Art. 52 ("every action logged") and for debugging overnight runs. `log_eddi.py` already does this for hardware status — ControlEngine needs the same discipline.

- **E-21 (Human review gate):** Currently `promote_to_active()` is fully automated (regression gate = only check). For a production system, add a `require_approval: bool = False` parameter. When `True`, new CANDIDATE models wait in registry with status `PENDING_REVIEW` until `registry.approve(version_id)` is called. Default `False` preserves current behaviour. Documented as a deliberate solo-founder trade-off in ADR-011.

- **E-22 (Drift check hook):** After `run_pipeline.py` Stage 3 completes, automatically call `DriftDetector.full_report()` and write JSON to `outputs/results/drift_reports/`. Log severity at INFO/WARNING/ERROR. This closes the gap between "we have drift detection" and "drift detection actually runs".

- **E-23 (Reliability):** Use `tenacity` library. Pattern: `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))` on all live connector `fetch_*` methods. Add `timeout=10` to every `requests.get()`. Fallback: if `OpenMeteoConnector` fails → use last-known cached weather from parquet with `logger.warning`. This is the highest-leverage reliability fix in the system — a 45-minute change that prevents 06:00 morning-brief failures.

- **E-24 (user_message):** Add `user_message: str` field to `ControlAction` dataclass. Populated by a `_format_user_message(action_type, confidence, env_state, forecast)` function. Rory's principle: every automated suggestion explains *why* in the language of the person reading it, not the engineer who wrote it. Examples:
  - `DEFER_HEATING` → "Good morning! Your panels should cover hot water heating after 11am — waiting could save you €0.18 today."
  - `HEAT_NOW` → "Night rate runs until 08:00 — Eddi will boost the tank now at the lower rate."
  - `ALERT_HIGH_DEMAND` → "Heads up: we expect high usage between 17–19h today. Running the dishwasher earlier could help."

---

## TRACK P — Product & Consumer App

### P-01 through P-04: Phase 1 — Pre-Dynamic-Tariff Builds (April–June 2026)

**Context:** CRU dynamic pricing mandate live **1 June 2026**. These items build the core product now so it's ready on mandate day. Phase 1 does not require live SEMO prices — uses static tariff logic.

| ID | Item | Status | Priority | Added | Owner | Depends On | Notes |
|----|------|--------|----------|-------|-------|-----------|-------|
| P-01 | **BTM Asset Detection** — infer solar/EV/HP from 30-min HDF profile | 🔴 | HIGH | 2026-04-15 | Staff ML Engineer | HDF pipeline | Kazempour et al. (DTU, arXiv:2501.18017). Replaces onboarding survey. New: `src/energy_forecast/btm/inference.py` |
| P-02 | WhatsApp / SMS Push — extend morning brief to delivery channel | 🟡 | MEDIUM | 2026-04-15 | Staff Backend Engineer | Phase 6 complete | 71% Cost-Driven consumers won't open an app (SEAI BI). WhatsApp Business API or Twilio SMS fallback |
| P-03 | Consumer Survey — willingness to pay for €3.99/month + €99-149 hardware | 🟡 | MEDIUM | 2026-04-15 | Staff Product Marketing | — | 5 questions, ~400 respondents via Pollfish; €200-400 budget; pricing validation before any public launch |
| P-04 | saveon.ie referral integration | 🔵 | LOW | 2026-04-15 | Staff Product Manager | Written agreement | Step 1: which tariff? (saveon.ie) → Step 2: optimise within it (us). Confirm no forecasting plans first |

### P-05 through P-08: Phase 2 — Dynamic Pricing Loop (June 2026)

**Context:** CRU mandate live. 5 obligated suppliers: Electric Ireland, Bord Gáis, Energia, SSE Airtricity, Yuno. Day-ahead prices published daily ~16:00 at 30-min resolution, capped €0.50/kWh.

| ID | Item | Status | Priority | Added | Owner | Depends On | Notes |
|----|------|--------|----------|-------|-------|-----------|-------|
| P-05 | **SEMO DAM price ingestion** — `SEMOConnector` stub → real ENTSO-E API | 🔴 | CRITICAL | 2026-04-15 | Staff Energy Expert | ENTSO-E token | Stub exists in `deployment/connectors.py`. Unblocks P-06 |
| P-06 | **Dynamic tariff optimisation loop** — H+24 + price vector → device scheduling | 🔴 | CRITICAL | 2026-04-15 | Staff ML Engineer | P-05 | Extend ControlEngine. Mock with synthetic DAM prices until P-05 live |
| P-07 | Heat pump BTM detection variant | 🟡 | HIGH | 2026-04-15 | Staff ML Engineer | P-01 | HP load signature; SEAI HPSS grant = acquisition channel; Ireland 400k HP target by 2030 |
| P-08 | **ESCO / Eligible Party registration** — Appendix A with ESB Networks | 🔴 | CRITICAL | 2026-04-15 | Staff Energy Expert | SMDS live | Free data access. Draft in `docs/regulatory/`. Consent: 3-click "Active Permission" |

### P-09 through P-13: Phase 3 — Scale (H2 2026)

| ID | Item | Status | Priority | Added | Owner | Depends On | Notes |
|----|------|--------|----------|-------|-------|-----------|-------|
| P-09 | Social comparison — "Homes like yours save 23% more" | 🔵 | MEDIUM | 2026-04-15 | Staff Product Manager | Multi-household data | Blocked until RENEW pilot or first users. Aggregate server-side only (privacy) |
| P-10 | P1 hardware MVP — Pi Zero 2W (€15) + DSMR P1 USB adapter (€8-12) | 🔵 | MEDIUM | 2026-04-15 | Staff Backend Engineer | ESB Networks P1 activation | Customer self-install <5 min; custom PCB only at >1k units/month |
| P-11 | Battery storage scheduling — charge/discharge optimisation | 🔵 | MEDIUM | 2026-04-15 | Staff ML Engineer | P-06 | New `CHARGE_BATTERY` action in `actions.py` |
| P-12 | Commercial beta launch — 10-household pilot | 🔵 | HIGH | 2026-04-15 | Staff Product Manager | D-12 + P-06 + P-08 | saveon.ie referral + SEAI HPSS channel |
| P-13 | LLM Energy Advisor — **Gemini Flash** (user has Gemini Pro subscription), ~€0.04/user/month | 🎓 | LOW | 2026-03 | Staff ML Engineer | E-25 + E-26 | Context injection: 30d stats + tariff + forecast; no raw time-series to API. Rory's principle: conversation, not query. Use Gemini Flash (not Claude API) — user has Gemini Pro; see ADR-011 |
| P-14 | Smart Meter Analyst Agent — Claude Code + CER trust hierarchy | 🎓 | LOW | 2026-03 | Staff ML Engineer | CER dataset | Natural language → Pandas → shareable report; EI Innovation Voucher artefact |

### P-16 through P-19: Customer Intelligence (New — 2026-04-16)

**Context:** Tracking whether recommendations were acted on, and segmenting users by engagement behaviour. Primary value: (1) only feed Tier 1 user behaviour back as model signal — dormant users' non-actions are noise. (2) tariff switching rate is the North Star investor metric. (3) the potential-vs-actual savings gap is the strongest retention message.

| ID | Item | Status | Priority | Added | Owner | Depends On | Notes |
|----|------|--------|----------|-------|-------|-----------|-------|
| P-16 | **Prediction outcome tracking** — link each recommendation to its real outcome | 🔴 | HIGH | 2026-04-16 | Staff Data Scientist | D-25 + E-27 | `recommendation_outcomes` table: was_shown, was_acted_on, actual_kwh, potential_saving_eur, actual_saving_eur. Source: ESB CSV re-ingestion next day matches actuals to predictions |
| P-17 | **Customer intelligence dashboard** — potential savings gap, tariff switching rate, engagement score | 🟡 | HIGH | 2026-04-16 | Staff Data Scientist | P-16 | Three metrics per household: (a) potential_saving_eur - actual_saving_eur = "left on table"; (b) tariff_switched boolean; (c) engagement_rate = acted_on / shown. Display to user: "You saved €28 this month. You could have saved €47." |
| P-18 | **Customer tier segmentation engine** — 4-tier behavioural classification | 🟡 | MEDIUM | 2026-04-16 | Staff Product Manager | P-16 | Tier 1 Optimisers (≥70% acceptance, active ≤14d); Tier 2 Trackers (regular, <70% acceptance); Tier 3 Switchers (changed tariff — high commercial value); Tier 4 Dormant (no activity 30+d). Tiers inform notification frequency, re-engagement, and model feedback loop |
| P-19 | **Tiered prediction frequency** — Tier 4 weekly batch, Tier 1-3 daily | 🔵 | LOW | 2026-04-16 | Staff ML Engineer | P-18 | Primary value is not compute (2ms × 1000 users = 2s) — it is signal quality. Tier 4 non-actions are noise in the feedback loop. Only Tier 1 behaviour feeds model improvement. At 100k+ users this also reduces daily batch cost materially |
| P-20 | **Geographic demand heatmap** — household consumption density map for ESCO reporting | 🔵 | LOW | 2026-04-16 | Staff Data Scientist | D-25 + P-12 | GeoJSON + Leaflet.js (or Grafana Geomap panel). Shows aggregate anonymised consumption by postcode. Use case: ESCO reporting to ESB Networks, investor demo, heat pump adoption hotspot identification for SEAI partnership |

### P-15: Rory Design Principle (Cross-Cutting)

| ID | Item | Status | Priority | Added | Owner | Notes |
|----|------|--------|----------|-------|-------|-------|
| P-15 | **Rory design principle** — every consumer-facing output explains itself in plain human language | 🔴 | HIGH | 2026-04-15 | Rory + Staff Product Manager | Codified in `docs/APP_PRODUCT_SPEC.md`. Applies to: `ControlAction.user_message` (E-24), LLM Advisor framing (P-13), morning brief text, WhatsApp push copy (P-02). The principle: an AI that says "run dishwasher at 23:00" without explanation is a cost-reduction FAQ bot. An AI that says "your tariff drops to night rate at 23:00 — running it then saves you €0.40 tonight" is a knowledgeable friend. Trust is the product, not the automation. |

---

## TRACK D — Deployment & Infrastructure

### D-01 through D-11: Phase 7 (Cloud) + Phase 8 (Home Trial) Started

| ID | Item | Status | Added | Resolved | Owner | Notes |
|----|------|--------|-------|----------|-------|-------|
| D-01 | FastAPI app — `/predict`, `/control`, `/health` endpoints | ✅ | 2026-02 | 2026-02 | Staff Backend Engineer | `deployment/app.py` |
| D-02 | Dockerfile — production image, non-root user, HEALTHCHECK | ✅ | 2026-03 | 2026-03-15 | Staff Backend Engineer | commit a15d297 |
| D-03 | `apprunner.yaml` — AWS App Runner config | ✅ | 2026-03 | 2026-03-15 | Staff Backend Engineer | commit a15d297 |
| D-04 | `Makefile` — `docker-build` / `ecr-push` / `apprunner-deploy` targets | ✅ | 2026-03 | 2026-03-15 | Staff Backend Engineer | |
| D-05 | ESB CSV ingestion — `scripts/run_home_demo.py`, 30-min pivot, DST-safe | ✅ | 2026-03 | 2026-03 | Staff Data Engineer | |
| D-06 | BGE tariff model — Day/Night/Peak/Free Sat/Export rates | ✅ | 2026-03 | 2026-03 | Staff Energy Expert | `src/energy_forecast/tariff.py` — single source of truth |
| D-07 | `OpenMeteoConnector` — live weather + solar irradiance | ✅ | 2026-02 | 2026-02 | Staff Data Engineer | Free, no API key required |
| D-08 | Morning brief CLI — `python deployment/live_inference.py --dry-run` | ✅ | 2026-02 | 2026-02 | Staff Backend Engineer | P10/P50/P90, BGE cost, control actions. Always dry_run safe |
| D-09 | myenergi Eddi live status — `MyEnergiConnector.get_status()` | ✅ | 2026-03 | 2026-03 | Staff Data Engineer | Hub 21509692 |
| D-10 | `scripts/log_eddi.py` — `--once`, `--history N`, `--interval` modes | ✅ | 2026-03 | 2026-03 | Staff Data Engineer | |
| D-11 | Home Plan Score — 62/100, €178.65/yr saving identified | ✅ | 2026-03 | 2026-03 | Staff Product Manager | Oct 2023–Oct 2025, 730 days |

### D-12 through D-26: Outstanding Deployment Items

| ID | Item | Status | Priority | Added | Owner | Depends On | Notes |
|----|------|--------|----------|-------|-------|-----------|-------|
| D-12 | **ECR push + AWS App Runner initial deploy** | 🔴 | HIGH | 2026-04 | Staff Backend Engineer | AWS account | Smoke test: `/health` → `/predict` → `/control` against mock. Must precede D-13 market launch |
| D-13 | S3 model artefact store — push `outputs/models/*.joblib` to S3 | 🟡 | MEDIUM | 2026-04-15 | Staff Backend Engineer | D-12 | Replace Docker-baked model copy with runtime pull |
| D-14 | AWS Secrets Manager — API keys (SEMO, myenergi, Ecowitt) | 🟡 | MEDIUM | 2026-04-15 | Staff Backend Engineer | D-12 | Remove `.env` file dependency |
| D-15 | CloudWatch alarm — MAE drift → SNS alert | 🔵 | LOW | 2026-04-15 | Staff Reliability Engineer | D-12 | |
| D-16 | **Mac Mini M5 + P1 adapter home setup** | 🔴 | HIGH | 2026-04-15 | Dan | Hardware purchase | Mac Mini M5 ~€699 + DSMR P1 USB ~€10 = ~€709. P1 adapter: DSMR USB from NL |
| D-17 | **BGE contract renewal** | 🚨 | URGENT | 2026-04 | Dan | — | Expires **15 June 2026**. Renewal window open NOW. Evaluate switching to dynamic tariff supplier |
| D-18 | `EcowittConnector` — personal weather station | 🟡 | LOW | 2026-03 | Staff Data Engineer | GW1100 hardware | `api.ecowitt.net/api/v3/device/real_time` — stub exists |
| D-19 | `send_command()` activation — Eddi scheduling via myenergi API | 🔵 | LOW | 2026-04 | Staff Backend Engineer | User approval flow | Monitor → Recommend → Automate. Never without explicit user approval. `user_approved=True` parameter required (E-23 safety boundary) |
| D-20 | `SEMOConnector` real implementation — ENTSO-E API | 🔴 | HIGH | 2026-03 | Staff Energy Expert | ENTSO-E token | Stub exists. Unblocks P-05 |
| D-21 | `MQTTConnector` — industrial sensor feeds | 🔵 | LOW | 2026-03 | Staff Data Engineer | MQTT broker | B2B use case |
| D-22 | `P1Connector` — real-time ESB smart meter via P1 port | 🔵 | LOW | 2026-03 | Staff Data Engineer | D-16 + ESB P1 activation | Same DSMR P1 standard as NL/BE/LU/ES |
| D-23 | **Full consumer app tech stack** — Next.js PWA + FastAPI + PostgreSQL/Supabase + Redis | 🔴 | HIGH | 2026-04-16 | Staff Backend Engineer | — | See `docs/TECH_STACK.md`. Handles auth, multi-tenancy, notification delivery, account management |
| D-24 | **Docker Compose local stack + Cloudflare Tunnel** — Mac Mini M5 beta hosting | 🔄 | HIGH | 2026-04-16 | 2026-04-16 | Staff Backend Engineer | D-23 | `docker-compose.yml` + Caddy + Grafana provisioning + `infra/db/init.sql` + `.env.example`. Run: `docker compose up -d`. ADR-011 |
| D-25 | **Multi-household database schema** — households, predictions, recommendations, outcomes, tariff_changes | ✅ | HIGH | 2026-04-16 | 2026-04-16 | Staff Data Engineer | D-23 | Schema in `infra/db/init.sql`. Views: `customer_tiers`, `savings_gap`. TimescaleDB hypertables on `meter_readings` + `predictions`. |
| D-26 | **APScheduler batch prediction pipeline** — daily 16:00 per registered household | 🟡 | MEDIUM | 2026-04-16 | — | Staff ML Engineer | D-23 + D-25 | Single shared LightGBM model per city; per-household: tariff config + consumption history only. Redis cache (TTL 23h) |
| D-27 | **Vega-Lite custom panels in Grafana** — energy-native operator chart specs | 🔵 | LOW | 2026-04-16 | — | Staff Backend Engineer | D-24 | Use Grafana's Vega-Lite panel plugin for: P10/P50/P90 forecast bands, drift severity heatmap, household consumption fingerprint. More expressive than default Grafana charts. |
| D-28 | **n8n workflow orchestrator** — replace APScheduler + notification code (Phase 2) | 🔵 | LOW | 2026-04-16 | — | Staff Backend Engineer | D-23 | Self-hosted, open-source (runs in Docker). Handles: CSV upload → process → notify; WhatsApp/email dispatch; P1 port webhook triggers. Add to docker-compose.yml alongside API. Eliminates custom notification code. |

---

## TRACK C — Commercial & Regulatory

### C-01 through C-06: Regulatory & Compliance

| ID | Item | Status | Priority | Added | Resolved | Owner | Notes |
|----|------|--------|----------|-------|----------|-------|-------|
| C-01 | EU AI Act Limited Risk (Art. 52) classification | ✅ | — | 2026-03 | 2026-03-28 | Staff Governance Lead | Transparency: confidence always shown, always an override, every action logged |
| C-02 | GDPR compliance — Art. 6(1)(a) consent for own meter data | ✅ | — | 2026-03 | 2026-03-28 | Staff Governance Lead | AWS eu-west-1 (Ireland). No raw time-series to LLM API |
| C-03 | CRU PCW accreditation — definitively NOT needed | ✅ | — | 2026-04 | 2026-04-15 | Staff Energy Expert | We are ESCO/Eligible Party under CRU202517, not a PCW |
| C-04 | ESCO registration — Appendix A with ESB Networks | 🔴 | CRITICAL | 2026-04-15 | — | Staff Energy Expert | SMDS live mid-2026 (at risk of delay). Draft in `docs/regulatory/` |
| C-05 | SMDS status tracking — ESB Networks near-real-time data access | 🟡 | MEDIUM | 2026-03 | — | Staff Energy Expert | P1 hardware already on all Irish meters; software activation pending. Track ESB comms |
| C-06 | GDPR privacy policy — 30-min data reveals occupancy | 🟡 | MEDIUM | 2026-04-15 | — | Staff Governance Lead | Disclose before Phase 7 live. On-device inference preferred long-term |

### C-07 through C-14: Funding & Go-to-Market

| ID | Item | Status | Priority | Added | Owner | Notes |
|----|------|--------|----------|-------|-------|-------|
| C-07 | **AWS Activate** — free compute credits | 🔴 | HIGH | 2026-04-15 | Dan | Apply immediately. No company formation required |
| C-08 | SEAI RD&D funding call | 🟡 | HIGH | 2026-04-15 | Dan | May–July 2026 window. NCI partner route |
| C-09 | Enterprise Ireland HPSU Feasibility Grant — €35k pre-revenue | 🟡 | MEDIUM | 2026-04-15 | Dan | Requires company formation |
| C-10 | New Frontiers — via NCI programme | 🟡 | MEDIUM | 2026-04-15 | Dan | Pre-incorporation pathway |
| C-11 | EI iHPSU — up to €1.2M | 🔵 | LOW | 2026-04-15 | Dan | Needs 6 months of traction first |
| C-12 | Dogpatch 2050 Accelerator — ESB partner, equity-free | 🔵 | LOW | 2026-04-15 | Dan | January 2027 cohort |
| C-13 | Heat pump angle — SEAI HPSS as acquisition channel | 🟡 | MEDIUM | 2026-04-15 | Staff Product Marketing | Depends P-07 | Ireland 400k HP target by 2030. Device makes HP economics viable |
| C-14 | RENEW collaboration (Maynooth University) — research-only | 🟡 | LOW | 2026-04-15 | Dan | Post Decarb-AI outcome. 20-50 household pilot network; joint paper opportunity |

---

## Bug Registry

### Active Bugs

| ID | Description | Severity | Added | Owner | Fix Plan |
|----|-------------|----------|-------|-------|---------|
| BUG-01 | Stacking OOF drops rows when `LightGBM_Quantile` included — NaN from sklearn `clone()` incompatibility | MEDIUM | 2026-03 | Staff ML Engineer | Add `LightGBM_Quantile` to exclusion list in `run_pipeline.py` before `StackingEnsemble` |
| BUG-02 | TFT `num_workers=0` — GPU underutilised on macOS (PyTorch DataLoader bottleneck) | LOW | 2026-03 | Staff ML Engineer | Known trade-off. `num_workers=4` fix deferred — macOS spawn overhead may offset gain |

### Resolved (selected — full history in git log)

| Old ID | Description | Resolved | Session |
|--------|-------------|----------|---------|
| BUG-C5 | DL H+24 predictions flattened incorrectly — `reshape_dl_predictions()` | 2026-04-15 | 40 |
| BUG-C6 | Stacking OOF early stopping leakage | 2026-03 | — |
| BUG-DL-H24 | DL H+24 evaluation length mismatch | 2026-03 | — |
| BUG-C3 | TFT `timestamp` in `time_varying_known_reals` → OOD saturation | 2026-03 | — |
| BUG-C4 | Rolling window target leakage — missing `shift(1)` | 2026-03 | — |
| BUG-LOC | `data/processed/` shared across cities — oslo clobbers drammen | 2026-03-15 | 30 |
| BUG-PEAK | Peak rate logic applied all days (should be Mon–Fri only) | 2026-03 | 31 |
| BUG-OOM | DL predict out-of-memory — `batch_size=512` required | 2026-03 | 31 |

---

## Deferred / Long-Term Research

| ID | Item | Why Deferred | Revive When |
|----|------|-------------|-------------|
| — | Automated Market Maker integration (Sweeney 2025) | PhD-level research | PhD programme |
| — | Price-responsive load agents (RL-based) | PhD-level research | PhD programme |
| — | Asymmetric settlement risk loss function | PhD-level research | PhD programme |
| — | NILMTK load disaggregation | Complex; superseded by P-01 BTM inference | After P-01 ships |
| — | ERA5 reanalysis weather source | Low priority while OpenMeteo works | R-10 uncertainty penalty |
| — | ONNX model export | Commercial scaling need | >1k active users |
| — | Irish CER residential dataset (2009-2010) | Pre-smart-meter; may not reflect 2026 patterns | CER access confirmed + research need |
| — | Walk-forward rolling back-test | Research extension | Journal paper extension |

---

## Key External Deadlines

| Date | Event | Track | ID | Status |
|------|-------|-------|-----|--------|
| **21 Apr 2026** | Decarb-AI PhD interview — UCD Statistics | Research | R-12 | 🔄 ACTIVE |
| **15 Jun 2026** | BGE contract renewal deadline | Deployment | D-17 | 🚨 URGENT |
| **1 Jun 2026** | CRU dynamic pricing mandate — 5 Irish suppliers | Product | P-05/P-06 | KEY TRIGGER |
| **Mid-2026** | ESB Networks SMDS live — ESCO Appendix A filing | Commercial | C-04 | AT RISK |
| **May–Jul 2026** | SEAI RD&D funding call (NCI partner route) | Commercial | C-08 | TRACK |
| TBD | Applied Energy journal submission | Research | R-09 | Draft ready |
| TBD | AWS Activate (apply immediately — no company needed) | Infrastructure | C-07 | APPLY NOW |
| TBD | EI HPSU Feasibility Grant (€35k, pre-revenue) | Commercial | C-09 | Post-formation |
| Jan 2027 | Dogpatch 2050 Accelerator — ESB partner, equity-free | Commercial | C-12 | TRACK |

---

## Appendix A — Experiment Results Archive

### H+24 Paradigm Parity — Drammen (2026-03-15, 240,481 test samples)

| Model | MAE (kWh) | R² | Setup |
|-------|-----------|----|----|
| LightGBM | 4.029 | 0.9752 | A — Trees + Engineered Features |
| Stacking (Ridge meta) | 4.034 | 0.9751 | A |
| PatchTST | 6.955 | 0.9102 | C — DL + Raw Sequences |
| TFT | 8.770 | 0.8646 | B — DL + Engineered Features |
| Mean Baseline | 22.673 | 0.442 | — |

### Oslo Cross-City (48 schools, 2026-03-15)

| Model | MAE (kWh) | R² | Note |
|-------|-----------|----|----|
| LightGBM | 7.415 | 0.9630 | Scale effect — Oslo buildings 2× larger than Drammen |
| Stacking | 7.280 | 0.9635 | |
| PatchTST | 13.616 | 0.8741 | +84% gap vs LightGBM — widens cross-city |

### Horizon Sweep — Drammen LightGBM (MAE kWh)

| H+1 | H+6 | H+12 | H+24 | H+48 | Degradation |
|-----|-----|------|------|------|-------------|
| 3.188 | 3.584 | 3.799 | 4.057 | 4.724 | +48% |

Ridge degradation H+1→H+48: +96%. **Tree advantage widens with horizon.**

### DM Significance Tests (HLN-corrected, H+24)

| Comparison | Statistic | p |
|-----------|-----------|---|
| LightGBM vs PatchTST | −12.17 | *** |
| LightGBM vs XGBoost | −5.25 | *** |
| LightGBM vs Ridge | −33.52 | *** |

---

## Appendix B — IBM Agent Engineering Skills: Project Mapping

*Source: IBM YouTube — "The 7 Skills You Need to Build AI Agents"*
*Applied to Sparc Energy by: Staff ML Engineer + Staff Reliability Engineer + Rory*

| Skill | Status in Project | Action Items |
|-------|------------------|-------------|
| **1. System Design** — structure not spaghetti | ✅ Strong — layered architecture (DataConnector → FastAPI → ControlEngine → DeviceConnector) | E-17 (SRP refactor) — last structural debt |
| **2. Tool & Contract Design** — airtight schemas | ⚠️ Gap — `PredictionRequest` accepts `dict[str, float]` (any keys) | E-19: strict Pydantic schema derived from model's `feature_name_` at startup |
| **3. Retrieval Engineering** — context quality = answer ceiling | 🟡 Pre-MVP — no RAG yet | E-25: `context_builder.py` for LLM Advisor. Key principle: pre-computed stats, not raw time-series |
| **4. Reliability Engineering** — one failure doesn't bring down the house | 🔴 Gap — no retry/timeout on any live connector | E-23: `tenacity` retry + `timeout=10` + fallback to cached weather on all HTTP connectors |
| **5. Security & Safety** — your agent is an attack surface | ✅ Good foundations — `dry_run=True` default, `DataValidator`, EU AI Act Art. 52 | E-26: LLM output filter for when P-13 ships |
| **6. Evaluation & Observability** — vibes don't scale | ✅ DriftDetector + ModelRegistry. Gap: no ControlEngine decision trail | E-20: JSONL audit log per decision |
| **7. Product Thinking** — design for humans | ⚠️ Gap — `ControlAction.reasoning` is engineer-readable, not consumer-readable | E-24: `user_message` field. P-15: Rory principle codified in product spec |
