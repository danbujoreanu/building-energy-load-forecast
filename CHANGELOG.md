# Changelog — Building Energy Load Forecast

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]
- Journal paper submission to Applied Energy / Energy and Buildings
- AWS App Runner deployment (`make ecr-push` pending `aws configure`)
- Mac Mini M4 Pro (24GB) self-hosted inference evaluation
- Audit action items from CODE_AUDIT_2026-04-08 (see `docs/ops/AUDIT_ACTION_ITEMS.md`)

---

## [0.9.0] — 2026-03-31 · Code Quality + Documentation Milestone

### Added
- `src/energy_forecast/tariff.py` — single source of truth for BGE Free Time Saturday tariff rates and `rate_slot()` / `rate_for_slot()` functions
- `deployment/mock_data.py` — shared `MOCK_SOLAR_24H` curve (was duplicated across `app.py` and `live_inference.py`)
- `tests/test_integration.py` — 12 end-to-end integration tests (feature engineering, temporal leakage, horizon assertion guard, E2E LightGBM with positive R²)
- `docs/governance/governance_diagram.png` — 1600×900px visual map of AI governance framework
- `docs/ops/SESSION_INDEX.md` — one-row-per-session table (Sessions 1–38)
- `docs/ops/DECISIONS_MAP.md` — all 81 locked decisions mapped to session + rationale
- `docs/ops/SESSION_INDEX.md` — compact navigable session history
- Horizon assertion guard in `temporal.py` — AssertionError if `features.forecast_horizon ≠ sequence.horizon`
- `/health` endpoint now returns real vs mock model status
- `/control` endpoint validates `target_hours` bounds (raises HTTP 400 if empty)
- LinkedIn architecture diagram 3200×2000px (`docs/marketing/`)
- 3 LinkedIn post drafts (`docs/marketing/linkedin_posts.md`)
- CRU dynamic pricing deep research (June 2026 mandate confirmed, SMDS risk documented)

### Changed
- `docs/` reorganised into 7 semantic subfolders: governance / research / commercial / regulatory / product / ops / marketing
- `MODEL_CARD.md` corrected: wrong function signature in code example, H+1 numbers corrected to Sprint 2 actuals, scaler step added
- `CLAUDE.md`, `knowledge/INDEX.md`, `knowledge/ERRORS.md` updated to Session 38 state
- Both ROADMAPs (root + commercial) updated to reflect completed phases and current priorities

### Fixed
- `pickle.load()` in `live_inference.py` now wrapped in try/except with actionable error message
- `log_eddi.py` line 158: `NameError: date` — added `from datetime import date, timezone`
- `score_home_plan.py` — removed duplicate BGE tariff dict, now imports from `energy_forecast.tariff`
- `run_home_demo.py` — removed inline `rate_for_slot()`, imports from `energy_forecast.tariff`

### Removed
- Inline `_MOCK_SOLAR_24H` definition in `live_inference.py` (moved to `deployment/mock_data.py`)
- Inline BGE tariff dicts in `run_home_demo.py` and `score_home_plan.py` (moved to `tariff.py`)

---

## [0.8.0] — 2026-03-27 · AI Governance Milestone

### Added
- `docs/governance/MODEL_CARD.md` — HuggingFace format; 10-model comparative table; DM significance tests; SHAP; caveats; usage code example
- `docs/governance/DATA_PROVENANCE.md` — 5-source chain (COFACTOR, OpenMeteo, ESB HDF, Eddi API, SINTEF Oslo); GDPR Article 6(1)(b); consent; anonymisation status; regulatory compliance table
- `docs/governance/AIIA.md` — EU AI Act Limited Risk (Article 52); 7 risk categories; home trial harm findings; safeguards table; override mechanism; drift trigger
- `docs/governance/DATA_LINEAGE.md` — 8-stage raw CSV → Eddi physical action flow; bug impact audit table cross-referenced to `knowledge/ERRORS.md`
- `CAREER_CONTEXT.md` — cross-project bridge for career coaching; maps project artefacts to role requirements (enterprise AI governance lead target)
- Docker image size optimised: 1.92GB → 169MB (RandomForest .joblib excluded from COPY layer)

### Changed
- `CLAUDE.md` — career hook added to session-start protocol (line 34)
- `deployment/app.py` — `PredictionResponse` includes `inference_mode: str`; `/health` distinguishes real vs mock models

---

## [0.7.0] — 2026-03-16 · Home Trial + Eddi Integration Live

### Added
- Live myenergi Eddi API integration: `get_status()`, `get_schedule()`, `get_history_day()` — all endpoints confirmed working
- `scripts/score_home_plan.py` — BGE Free Time Saturday plan scoring; 730-day analysis on ESB smart meter data
- `scripts/log_eddi.py` — daily Eddi consumption logging
- CRU202517 ESCO application template (`docs/regulatory/CRU202517_APPENDIX_A_DRAFT.md`)
- `docs/regulatory/SMART_METER_ACCESS.md` — regulatory analysis, P1 port, GDPR, go-to-market
- 54 connector tests added
- Phase 6 Cyber-Physical Control Layer: `src/energy_forecast/control/actions.py`, `controller.py`; `deployment/connectors.py` (CSVConnector, OpenMeteoConnector, EddiConnector stubs)

### Key Findings
- **Plan score: 62/100** — significant room for tariff optimisation
- **€178.65/year** opportunity identified on first analysis of 2 years of home data
- **Model MAE: 0.171 kWh/hour** on 17,302 hourly home readings (Mar 2024 – Mar 2026)

---

## [0.6.0] — 2026-03-15 · Sprint 3 Complete + Production Model Locked

### Added
- Oslo cross-city generalisation: LightGBM MAE=7.415 kWh, R²=0.963 (48 buildings, 779,423 test samples)
- PatchTST Oslo Setup C: MAE=13.616 kWh (+84% gap vs LightGBM — wider than Drammen +72%)
- Cross-paradigm DM test: LightGBM vs PatchTST DM=−12.17 (p<0.0001 ***)
- Production model architecture formally locked (see `knowledge/domain/DECISIONS.md`)
- AWS App Runner deployment config: `Dockerfile`, `apprunner.yaml`, `Makefile` (`make docker-build`, `make ecr-push`)
- `deployment/app.py` lifespan model caching, `/control` POST endpoint, `/health` status

### Fixed
- **CRITICAL**: `proc_dir` shared across cities — Oslo pipeline was overwriting Drammen processed data. Fixed to `data/processed/{city}/` in all three pipeline scripts. Oslo data migrated.

### Production Model Decisions (locked 2026-03-15)
- **Inference model**: LightGBM only (not ensemble, not DL)
- **Cadence**: H+24 at 16:00 daily; H+1 hourly
- **Retraining**: Monthly, rolling 24-month window; drift trigger: 7d MAE > 1.5× training MAE
- **Cold start**: 30 days population-average → household-specific

---

## [0.5.0] — 2026-03-15 · Sprints 1 & 2 Complete — Core Research Done

### Added
- Sprint 1: Cross-paradigm Diebold-Mariano significance tests
  - LightGBM vs Ridge: DM=−33.52 (p<0.0001 ***)
  - LightGBM vs XGBoost: DM=−5.25 (p<0.0001 ***)
  - LightGBM vs PatchTST [C]: DM=−12.17 (p<0.0001 ***)
- Sprint 2: Horizon sensitivity sweep H+1 → H+48 (LightGBM/XGBoost/Ridge on Drammen)
  - LightGBM: 3.188 → 4.724 kWh MAE (+48%); R²=0.967 at H+48
  - Ridge: 4.301 → 8.447 kWh MAE (+96%) — tree advantage widens with horizon
- `scripts/run_horizon_sweep.py` — checkpoint-aware with `--resume` flag
- `scripts/significance_test.py` — Wilcoxon + Diebold-Mariano tests; HLN correction
- Journal paper Section 5.5 (horizon sensitivity) + Table 8
- DM test Table 2b added to paper

---

## [0.4.0] — 2026-03-07 · Three-Way Paradigm Parity Complete

### Added
- Setup C (PatchTST raw sequences): MAE=6.955 kWh, R²=0.9102 on Drammen H+24
- Setup B results confirmed: TFT MAE=8.770, CNN-LSTM 9.375, LSTM 34.938 kWh (negative control)
- MICE weather imputation module for sparse OpenMeteo data
- Phase 6 control layer foundation: `deployment/connectors.py` skeleton
- Morning brief CLI: `deployment/live_inference.py --dry-run`
- `docs/research/JOURNAL_PAPER_DRAFT.md` — 8 sections, all figures generated
- Section 7: Responsible AI, Ethics, and Deployment Governance

### Key Finding
- **Paradigm Parity result**: LightGBM (4.029 kWh) beats PatchTST (6.955 kWh) by 42% MAE at H+24 — confirms tree models with engineered features outperform DL raw-sequence models on this building dataset

---

## [0.3.0] — 2026-03-01 · OOF Stacking + H+24 Evaluation Framework

### Added
- `TimeSeriesSplit` OOF stacking (5 folds, timestamp-split, not row-split) — eliminates fold contamination
- Stacking Ensemble H+24: MAE=4.034 kWh, R²=0.9751 (marginal vs LightGBM alone — later confirmed insufficient to justify complexity)
- 3-way Paradigm Parity framework defined: Setup A (Trees+Features), B (DL+Features), C (DL+Raw)
- H+24 as primary evaluation horizon — removes oracle leakage from lag_1h (r=0.977 autocorrelation)
- `scripts/run_raw_dl.py` — Setup C PatchTST pipeline
- DL models retrained with uniform H+24 target (not multi-step H+1-evaluated-at-step-0)
- `import lightning.pytorch as pl` — pytorch-forecasting 1.3+ compatibility fix

---

## [0.2.0] — 2026-02-28 · First Honest H+24 Pipeline

### Added
- Forecast horizon enforced as H+24; all lags < 24h excluded from feature set (oracle leakage prevention)
- OOF stacking foundation (fixed-val → OOF methodology decision)
- SHAP explainability: beeswarm, bar, waterfall, heatmap — `evaluation/explainability.py`
- XGBoost model with early stopping
- `docs/research/JOURNAL_PAPER_OUTLINE.md` and `PAPER_JOURNEY.md`
- README rewritten as clean academic project page

### Fixed
- Oracle leakage: `lag_1h` removed from H+24 feature set
- MAPE: rows where y_true < 0.1 kWh excluded (not epsilon-denominator approach)
- `number_of_users` imputation: category-density method matching original thesis EDA

---

## [0.1.0] — 2026-02-08 · Initial Release

### Added
- Full package structure: `src/energy_forecast/` with data, features, models, evaluation, visualization, utils
- `config/config.yaml` — single source of truth for all pipeline parameters
- Models: Ridge, Lasso, Random Forest, LightGBM, XGBoost, LSTM, GRU, CNN-LSTM, TFT, Stacking Ensemble, Mean/Naive/SeasonalNaive baselines
- `scripts/run_pipeline.py` — end-to-end orchestrator (eda/features/training/explain stages)
- `tests/` — 19 tests (data, features, models, explainability); GitHub Actions CI
- Three-Tier Architecture (Data / Application / Presentation) + Pipe-and-Filter ML pipeline
- Cyclical encoding fix: hour period=24, day_of_week period=7 (was 23/6 in thesis notebooks)
- DST-robust lag features: lag_167h, lag_169h (same-time ±1h weekly)
- Correlation tie-breaking: upper-triangle scan, deterministic B-drop rule
- `column_min_coverage: 0.50` filter — prevents sparse optional-meter columns from wiping all rows

---

[Unreleased]: https://github.com/danbujoreanu/building-energy-load-forecast/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/danbujoreanu/building-energy-load-forecast/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/danbujoreanu/building-energy-load-forecast/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/danbujoreanu/building-energy-load-forecast/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/danbujoreanu/building-energy-load-forecast/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/danbujoreanu/building-energy-load-forecast/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/danbujoreanu/building-energy-load-forecast/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/danbujoreanu/building-energy-load-forecast/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/danbujoreanu/building-energy-load-forecast/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/danbujoreanu/building-energy-load-forecast/releases/tag/v0.1.0
