# Session Log

**Project:** Building Energy Load Forecast
**Author:** Dan Alexandru Bujoreanu (x23309903) — NCI Dublin MSc AI 2025
**GitHub:** https://github.com/danbujoreanu/building-energy-load-forecast
**Local path:** `/Users/danalexandrubujoreanu/building-energy-load-forecast/`

This file records every Claude Code session chronologically.
Each session picks up where the previous one left off.
**Claude Code reads `CLAUDE.md` automatically — this file provides the human-readable history.**

---

## Session 1 — 2026-02 (Initial Build)

### Objective
Transform 3 messy Jupyter notebooks (MSc thesis) into a professional Python package and GitHub portfolio.

### What Was Done
- Explored original thesis artifacts: 3 notebooks (EDA, Feature Engineering, Model Training), Drammen dataset (45 buildings, `.txt`), Oslo dataset (48 buildings, `.csv`), 400MB+ processed CSVs
- Designed **Three-Tier Architecture** (from MSc Engineering & Evaluating AI Systems module): Data → Application → Presentation tiers
- Implemented **Pipe-and-Filter** ML pipeline pattern
- Created full package structure: `src/energy_forecast/` with `data/`, `features/`, `models/`, `evaluation/`, `visualization/`, `utils/`

### Files Created (30 total)
| File | Purpose |
|------|---------|
| `config/config.yaml` | Master config — single source of truth |
| `pyproject.toml` | Installable package definition |
| `requirements.txt` | Core dependencies |
| `requirements-dev.txt` | Dev dependencies (pytest, ruff, black) |
| `.gitignore` | Excludes 400MB+ processed CSVs |
| `CLAUDE.md` | Project memory (auto-loaded by Claude Code) |
| `src/energy_forecast/data/loader.py` | Parses Drammen .txt and Oslo .csv → MultiIndex DataFrame |
| `src/energy_forecast/data/preprocessing.py` | Clean, validate, save model-ready parquet |
| `src/energy_forecast/data/splits.py` | Chronological train/val/test splits (no leakage) |
| `src/energy_forecast/features/temporal.py` | Lag, rolling, cyclical features per building |
| `src/energy_forecast/features/selection.py` | 3-stage selection: Variance→Correlation→LightGBM top-35 |
| `src/energy_forecast/models/base.py` | Abstract `BaseForecaster` interface |
| `src/energy_forecast/models/baselines.py` | Naive, SeasonalNaive, Mean baselines |
| `src/energy_forecast/models/sklearn_models.py` | Ridge, Lasso, RF, LightGBM, XGBoost wrappers |
| `src/energy_forecast/models/deep_learning.py` | LSTM, CNN-LSTM, GRU (TensorFlow/Keras) |
| `src/energy_forecast/models/tft.py` | Temporal Fusion Transformer (PyTorch Forecasting) |
| `src/energy_forecast/models/ensemble.py` | Stacking ensemble (Ridge or LGBM meta-learner) |
| `src/energy_forecast/evaluation/metrics.py` | MAE, RMSE, MAPE, R², per-building |
| `src/energy_forecast/evaluation/explainability.py` | SHAP (beeswarm, waterfall, bar plots) |
| `src/energy_forecast/visualization/plots.py` | 8 plot functions |
| `src/energy_forecast/utils/config.py` | Config loader (walks directory tree) |
| `src/energy_forecast/utils/logging_setup.py` | Structured logging |
| `src/energy_forecast/utils/reproducibility.py` | `set_global_seed(42)` |
| `scripts/run_pipeline.py` | End-to-end orchestrator (eda/features/training/explain stages) |
| `scripts/download_data.py` | Oslo dataset download guide |
| `tests/test_data.py` | 6 data tests |
| `tests/test_features.py` | 5 feature tests |
| `tests/test_models.py` | 8 model/metric tests |
| `tests/test_explainability.py` | 4 SHAP tests |
| `.github/workflows/ci.yml` | GitHub Actions CI (lint + tests, Python 3.10 & 3.11) |
| `README.md` | Portfolio README with Mermaid diagrams |
| `docs/HOW_TO_RUN.md` | Execution guide |

### Errors Fixed
1. `setuptools.backends.legacy:build` → `setuptools.build_meta` (pyproject.toml)
2. LightGBM `libomp.dylib` OSError — `pytest.importorskip` doesn't catch `OSError`, changed to manual try/except
3. GitHub push rejected for workflow file — ran `gh auth refresh -h github.com -s workflow` with device code `163B-285E`

### Git State at End
- Repo: `https://github.com/danbujoreanu/building-energy-load-forecast`
- Commits: `0c330f3` (initial), `b16c4ab` (docs update with real thesis results)
- Tests: 19/19 passing

---

## Session 2 — 2026-02-28

### Objective
Answer user questions, add XGBoost, read Follow-up Questions PDF, create ROADMAP, implement SHAP.

### Context (start of session)
Continued from context-compacted session. Last commit was `b16c4ab`.

### Questions Answered
1. **Results copied or run?** → Results copied from thesis Appendix 2.1. New code not yet executed end-to-end. Todo: run `python scripts/run_pipeline.py --city drammen --skip-slow` to verify.
2. **Claude Code vs VS Code?** → Use Claude Code as primary (reads CLAUDE.md, fast multi-file edits). Keep VS Code for running pipeline, viewing plots, debugging.
3. **Update original architecture diagram?** → No. Original stays in thesis. New Mermaid diagrams in README reflect what was built. No conflict.

### Work Done

#### XGBoost Added
- `src/energy_forecast/models/sklearn_models.py` — added `_build_xgboost()` + early stopping support + docstring updated
- `config/config.yaml` — added `xgboost:` block with thesis-matched hyperparameters

#### Follow-up Questions PDF — Key Findings
11 questions with future work items extracted into ROADMAP.md. Key themes:
- **Probabilistic forecasting** is the #1 next research area (Q3, Q4, Q5) — quantile LightGBM, prediction intervals
- **SHAP explainability** is highest-impact/lowest-effort next step (Q7)
- **Hierarchical BART** is the long-term PhD-track model (Q6)
- **Cyclical encoding bug** (23/6 vs 24/7) was in original notebooks — **already fixed** in new code (periods: hour=24, day=7)
- **OOF stacking** should replace fixed-validation ensemble (Q11)

#### Files Created/Updated
| File | Change |
|------|--------|
| `ROADMAP.md` | NEW — full PhD-track research roadmap, 50+ items, 4 phases, drawn from all 11 follow-up questions |
| `README.md` | Full 15-model results table (was 8), added Lasso/Ridge/baselines/Weighted Ensemble, ROADMAP link |
| `docs/SESSION_LOG.md` | NEW — this file |
| `src/energy_forecast/evaluation/explainability.py` | NEW — SHAP module (beeswarm, waterfall, bar, heatmap) |
| `tests/test_explainability.py` | NEW — 4 SHAP tests |
| `scripts/run_pipeline.py` | Added `explain` stage |
| `requirements.txt` | Added `shap>=0.44`, `xgboost>=2.0` |

#### Session 2 Commits
- `0a237d7` — Add XGBoost, full results table, and PhD-track ROADMAP
- (next) — Session log, SHAP implementation, pipeline explain stage

### Git State at End
- All changes pushed to `main`
- Tests: target 23+/23+ passing (after SHAP tests added)

### Next Session — Recommended Starting Point
1. **Run the pipeline end-to-end** — `cd /Users/danalexandrubujoreanu/building-energy-load-forecast && python scripts/run_pipeline.py --city drammen --skip-slow`
2. **Debug any pipeline issues** — data loading, feature engineering, model training
3. **Verify SHAP plots** — run `python scripts/run_pipeline.py --stages explain` after training
4. **Probabilistic forecasting** — quantile regression in LightGBM (next ROADMAP item)

---

## Pending Technical Debt

| Issue | Priority | Notes |
|-------|----------|-------|
| Pipeline not yet run end-to-end on real data | 🔴 HIGH | All code written from scratch — needs validation |
| GRU has no thesis benchmark result | 🟡 | Implemented, not formally evaluated in thesis Table 5 |
| WeightedAverageEnsemble not in code | 🟡 | Thesis had it (MAE 4.081), easy to add to ensemble.py |
| OOF stacking (fixed-val used instead) | 🟡 | Q11 improvement — deliberate thesis trade-off |
| Two TFT variants (only one in code) | 🔵 | Thesis ran TFT with MAE Loss (8.58) and Comprehensive (5.11) |

---

*Session log maintained by Claude Code. Always update this file at the end of each session.*
