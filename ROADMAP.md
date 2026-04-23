# Sparc Energy — Engineering Roadmap
*Created: 2026-04-23 | Last modified: 2026-04-23*

**Project:** Building Energy Load Forecast → Sparc Energy (pre-incorporated)
**Mission:** Day-ahead electricity load forecasting for Irish residential homes, enabling
demand-response optimisation against dynamic pricing. MSc AI thesis → cleantech product.

---

## Status Snapshot — Q2 2026

| Track | State | Next milestone |
|-------|-------|---------------|
| Research | Journal paper in final review | R-09: submit to Applied Energy |
| Engineering | Production-grade MLOps pipeline | E-30: JWT auth before multi-tenant launch |
| Product | Pre-dynamic-tariff sprint | P-01: BTM asset detection |
| Deployment | Phase 7 in progress | D-12: AWS App Runner live |
| Regulatory | CRU dynamic pricing mandate 1 Jun 2026 | C-04: ESCO registration with ESB Networks |

---

## Track R — Research & Publication

### Completed

| ID | Item | Resolved |
|----|------|----------|
| R-01 | MSc Thesis — *ML Approaches for Building Energy Load Forecasting in Norwegian Public Buildings* (NCI Dublin) | 2025-09 |
| R-02 | AICS 2025 Full Paper — *Forecasting Energy Demand: The Case for Trees over Deep Nets* (Springer CCIS) | 2025-12 |
| R-03 | AICS 2025 Student Paper — DCU Press Companion Proceedings (dual-track acceptance) | 2025-12 |
| R-04 | H+24 Three-Way Paradigm Parity (Setup A/B/C): LightGBM 4.029 kWh MAE / R²=0.975; PatchTST DM=−12.17*** | 2026-03 |
| R-05 | Oslo cross-city generalisation: LightGBM MAE=7.415 R²=0.963; paradigm gap widens +84% cross-city | 2026-03 |
| R-06 | Horizon sweep H+1→H+48: LightGBM +48% degradation; tree advantage widens with horizon | 2026-03 |
| R-07 | Diebold-Mariano significance tests (HLN-corrected): vs Ridge −33.52***, XGBoost −5.25***, PatchTST −12.17*** | 2026-03 |
| R-08 | Section 7: Responsible AI, Ethics, Deployment Governance (EU AI Act Art. 52; GDPR; 5 subsections) | 2026-03 |

### In Progress / Planned

| ID | Item | Priority |
|----|------|---------|
| R-09 | Final manuscript review + submission to Applied Energy / Energy and Buildings | HIGH |
| R-10 | Forecast Uncertainty Penalty — oracle vs NWP weather Δ MAE (production-readiness proof) | MEDIUM |
| R-11 | Daily Peak Error + Time of Peak Error metrics (the metrics that matter for demand response operators) | MEDIUM |
| R-14 | Decision-Focused Learning ControlEngine — train with dispatch cost loss, not MSE | Research |
| R-15 | Hierarchical BART — cross-building pooling (Chipman et al. 2010) | Research |
| R-16 | OOD generalisation for extreme weather (Liu et al. 2023) | Research |
| R-17 | Cross-domain transfer: data centre IT/cooling load | Research |
| R-18 | Energy community dynamic pricing agents (RL-based prosumer behaviour) | Research |

---

## Track E — Engineering & MLOps

### Completed

| ID | Item | Notes |
|----|------|-------|
| E-01 | Core ML pipeline — 35-feature vector, LightGBM, Stacking, SHAP, 153 tests | |
| E-02 | ModelRegistry — CANDIDATE→ACTIVE→RETIRED lifecycle, regression gate, rollback | `src/energy_forecast/registry/` |
| E-03 | DriftDetector — KS+PSI per feature, target drift, rolling MAE trigger | 7-day window, 1.5× threshold |
| E-04 | DataValidator — hard fail on empty/NaN/Inf/shape | |
| E-05 | `reshape_dl_predictions()` shared utility — eliminates H+24 interleaving bug | |
| E-06 | Exception hardening — `logger.error(exc_info=True)` on all 5 critical paths | |
| E-07 | Timezone config — per-city timezone map in `config.yaml` | drammen / oslo / ireland |
| E-08 | ADR-001 through ADR-010 — all architectural decisions documented | `docs/adr/` |
| E-09 | Governance docs — Model Card, AIIA, Data Provenance, Data Lineage | `docs/governance/` |
| E-10 | `live_inference.py` registry-aware — `registry.get_active()` first, file-glob fallback | |
| E-12 | `CSVConnector` schema validation — required columns, tz-aware index | |
| E-13 | `/health` endpoint exposes drift status — severity + recommended_action | |
| E-17 | `run_pipeline.py` SRP refactor — 634-line monolith → stage modules | |
| E-19 | Strict Pydantic schemas for FastAPI — model-derived 35-feature `PredictionRequest` | |
| E-20 | ControlEngine JSONL audit log — structured per-decision trail | EU AI Act Art. 52 |
| E-22 | Drift check post-training hook — auto-run after Stage 3 | |
| E-23 | Connector retry / timeout / circuit breaker — all live HTTP connectors | `tenacity`, exp. backoff |
| E-24 | `ControlAction.user_message` — plain-English translation of every action | |
| E-27 | Prediction history store — append each H+24 prediction to `predictions` PostgreSQL table | |
| E-28 | ADR-011 — full consumer app tech stack decision record | `docs/adr/ADR-011-consumer-app-tech-stack.md` |
| E-36 | CI pipeline active — Tests (3.10+3.11), Code quality, Docker build; branch protection on main | 4 required checks before merge |

### In Progress / Planned

| ID | Item | Priority | Depends On |
|----|------|---------|-----------|
| E-18 | `run_grand_ensemble.py` registry-aware | MEDIUM | — |
| E-21 | ModelRegistry human review gate — CANDIDATE→ACTIVE requires explicit approval | MEDIUM | — |
| E-25 | `src/energy_forecast/llm/context_builder.py` — deterministic system-prompt formatter | MEDIUM | P-13 |
| E-26 | LLM output filter / safety guard — block out-of-scope advisor responses | MEDIUM | P-13 |
| E-29 | `deployment/scheduler.py` — APScheduler daily 16:00 batch per household | MEDIUM | D-25 |
| E-30 | FastAPI auth middleware — JWT `get_current_user` dependency injection | **HIGH** | D-29 |
| E-31 | Redis cache in `/predict` — check cache before running model (TTL 23h) | MEDIUM | D-24 |
| E-32 | Resend email notification — morning brief delivery, free tier (3k/month) | MEDIUM | E-29 |
| E-33 | Grafana alert rules — 5 operational thresholds (night rate, price spike, solar, API health, drift) | MEDIUM | data in DB |
| E-37 | Pytest audit — verify all tests call production functions, not local re-implementations | MEDIUM | — |
| E-38 | Segmented model metrics — MAE by city, season, time-of-day band, forecast horizon | MEDIUM | — |
| E-39 | Prompt eval layer — test LLM advisor prompts against fixed cases without deployment | LOW | P-13 |
| E-40 | Engineering knowledge base — queryable best-practices from high-signal engineering articles | LOW | E-36 |

---

## Track D — Deployment & Infrastructure

### Completed

| ID | Item | Notes |
|----|------|-------|
| D-01 | FastAPI app — `/predict`, `/control`, `/health`, `/upload`, `/intel/query` endpoints | `deployment/app.py` |
| D-02 | Dockerfile — production image, non-root user, HEALTHCHECK | |
| D-03 | `apprunner.yaml` — AWS App Runner config | |
| D-04 | `Makefile` — `docker-build` / `ecr-push` / `apprunner-deploy` targets | |
| D-05 | ESB CSV ingestion — `scripts/run_home_demo.py`, 30-min pivot, DST-safe | |
| D-06 | BGE tariff model — Day/Night/Peak/Free Sat/Export rates | `src/energy_forecast/tariff.py` |
| D-07 | `OpenMeteoConnector` — live weather + solar irradiance | Free, no auth |
| D-08 | Morning brief CLI — `python deployment/live_inference.py --dry-run` | P10/P50/P90, cost, control actions |
| D-09 | myenergi Eddi live status — `MyEnergiConnector.get_status()` | HTTP Digest auth |
| D-11 | Home Plan Score — tariff optimisation scoring for Irish households | `scripts/score_home_plan.py` |
| D-24 | Docker Compose local stack — FastAPI + TimescaleDB + Redis + Grafana + n8n | ADR-011 |
| D-25 | Multi-household database schema — households, predictions, recommendations, outcomes | TimescaleDB hypertables |
| D-28 | n8n workflow orchestrator — 6 workflows, push notifications | localhost:5678 |

### In Progress / Planned

| ID | Item | Priority | Notes |
|----|------|---------|-------|
| D-12 | ECR push + AWS App Runner initial deploy | **HIGH** | Smoke test: `/health` → `/predict` → `/control` |
| D-13 | S3 model artefact store | MEDIUM | Replace Docker-baked model with runtime S3 pull |
| D-14 | AWS Secrets Manager — rotate all credentials out of `.env` | MEDIUM | |
| D-15 | CloudWatch alarm — MAE drift → SNS alert | LOW | |
| D-20 | `SEMOConnector` real implementation — ENTSO-E day-ahead prices API | **HIGH** | Stub exists; unblocks dynamic pricing |
| D-22 | `P1Connector` — real-time ESB smart meter via P1 port | LOW | Pending ESB P1 software activation |
| D-23 | Consumer app tech stack — Next.js PWA + FastAPI + Supabase + Redis | **HIGH** | See `docs/adr/ADR-011` |
| D-26 | APScheduler batch prediction pipeline — daily 16:00 per registered household | MEDIUM | |
| D-29 | Supabase project setup — EU region, run `infra/db/init.sql` | **HIGH** | |

---

## Track C — Regulatory & Compliance

| ID | Item | Status | Notes |
|----|------|--------|-------|
| C-01 | EU AI Act Limited Risk (Art. 52) classification | ✅ | Transparency: confidence shown, override always available, every action logged |
| C-02 | GDPR compliance — Art. 6(1)(a) consent for household meter data | ✅ | AWS eu-west-1 (Ireland). No raw time-series to external API |
| C-03 | CRU PCW accreditation — confirmed NOT required | ✅ | We qualify as ESCO/Eligible Party under CRU202517, not a PCW |
| C-04 | ESCO registration — Appendix A with ESB Networks | 🔴 | Draft in `docs/regulatory/`. File when SMDS opens mid-2026 |
| C-05 | SMDS status tracking — ESB Networks smart meter data access | 🟡 | CRU202517 published 19/02/2025. Technical infrastructure under construction |
| C-06 | GDPR privacy policy — 30-min data reveals occupancy patterns | 🟡 | Required before Phase 7 public launch |

---

## Bug Registry

### Active

| ID | Description | Severity |
|----|-------------|----------|
| BUG-01 | Stacking OOF drops rows when `LightGBM_Quantile` included — sklearn `clone()` incompatibility | MEDIUM |
| BUG-02 | TFT `num_workers=0` — GPU underutilised on macOS DataLoader bottleneck | LOW |

### Resolved (selected)

| ID | Description | Resolved |
|----|-------------|----------|
| BUG-C5 | DL H+24 predictions flattened incorrectly — `reshape_dl_predictions()` | 2026-04-15 |
| BUG-C6 | Stacking OOF early stopping leakage | 2026-03 |
| BUG-DL-H24 | DL H+24 evaluation length mismatch | 2026-03 |
| BUG-LOC | `data/processed/` shared across cities — oslo clobbers drammen | 2026-03-15 |
| BUG-PEAK | Peak rate logic applied all days instead of Mon–Fri only | 2026-03 |
| BUG-OOM | DL predict out-of-memory — `batch_size=512` required | 2026-03 |

---

## Appendix — Experiment Results

### H+24 Paradigm Parity — Drammen (240,481 test samples)

| Model | MAE (kWh) | R² | Setup |
|-------|-----------|----|----|
| LightGBM | 4.029 | 0.9752 | A — Trees + Engineered Features |
| Stacking (Ridge meta) | 4.034 | 0.9751 | A |
| PatchTST | 6.955 | 0.9102 | C — DL + Raw Sequences |
| TFT | 8.770 | 0.8646 | B — DL + Engineered Features |
| Mean Baseline | 22.673 | 0.442 | — |

### Oslo Cross-City Validation (48 buildings)

| Model | MAE (kWh) | R² | Note |
|-------|-----------|----|----|
| LightGBM | 7.415 | 0.9630 | Oslo buildings ~2× larger than Drammen |
| Stacking | 7.280 | 0.9635 | |
| PatchTST | 13.616 | 0.8741 | +84% gap vs LightGBM — widens cross-city |

### Horizon Sweep — LightGBM Drammen (MAE kWh)

| H+1 | H+6 | H+12 | H+24 | H+48 | Degradation |
|-----|-----|------|------|------|-------------|
| 3.188 | 3.584 | 3.799 | 4.057 | 4.724 | +48% |

Ridge degradation H+1→H+48: +96%. **Tree advantage widens with forecast horizon.**

### Diebold-Mariano Significance Tests (HLN-corrected, H+24)

| Comparison | DM statistic | Significance |
|-----------|-------------|-------------|
| LightGBM vs PatchTST | −12.17 | *** |
| LightGBM vs XGBoost | −5.25 | *** |
| LightGBM vs Ridge | −33.52 | *** |
