# Research Roadmap

**Dan Alexandru Bujoreanu — Building Energy Load Forecast**
*MSc Artificial Intelligence, NCI Dublin 2025 → Conference Paper (AICS 2025) → PhD-track research*

This document tracks completed work and all prioritised future iterations,
drawn directly from the MSc thesis (2025), the AICS 2025 conference paper, and
external feedback (AI Studio, AICS reviewers, SINTEF expert).

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Completed |
| 🔄 | In progress |
| 🔴 | High priority — next iteration |
| 🟡 | Medium priority |
| 🔵 | Low priority / exploratory |
| 🎓 | PhD-track (longer term) |

---

## Phase 1 — Completed ✅

### Publication

| Item | Detail |
|------|--------|
| ✅ MSc thesis | *Machine Learning Approaches for Building Energy Load Forecasting in Norwegian Public Buildings* — NCI Dublin, 2025 |
| ✅ AICS 2025 Full Paper | *Forecasting Energy Demand in Buildings: The Case for Trees over Deep Nets* — Springer CCIS Series |
| ✅ AICS 2025 Student Paper | Same paper — DCU Press Companion Proceedings (dual-track acceptance) |

### Codebase & Infrastructure

| Item | Detail | Notes |
|------|--------|-------|
| ✅ Modularisation | Refactored 3 Jupyter notebooks → clean Python package (`src/energy_forecast/`) | Q11 improvement — done |
| ✅ Config-driven design | Single `config/config.yaml` as source of truth for all parameters | Eliminates scattered magic numbers |
| ✅ Cyclical encoding fix | Corrected period: hour=24, day_of_week=7 (was 23/6 in thesis notebooks) | Q11 bug fix — resolved |
| ✅ DST-robust lag features | Added lag_167h/lag_169h (same-time ±1h weekly) to original thesis lags | Improves weekly pattern stability |
| ✅ Min/max rolling stats | Added min/max to rolling statistics (thesis had mean/std only) | Tighter load-range bounds |
| ✅ Temperature interaction features | `temp × hour_sin`, `temp × hour_cos` cross-terms | Captures time-varying thermal sensitivity |
| ✅ Test suite (24 tests) | `pytest tests/` — data, features, models, metrics | CI-validated, no raw data needed |
| ✅ GitHub Actions CI | Lint (ruff, black) + tests on Python 3.10 & 3.11 | Every push/PR |
| ✅ SHAP explainability | Beeswarm, bar, waterfall, heatmap — `--stages explain` | `evaluation/explainability.py` |

### Models — V2 Pipeline Results (H+1, 240,481 test samples, July 2021 – March 2022)

DL models (LSTM/GRU/CNN-LSTM) evaluated on 237,313 samples (72 lookback rows per building excluded).

| Model | V2 MAE (kWh) | V2 R² | Thesis MAE (kWh) | Improvement |
|-------|-------------|-------|-----------------|-------------|
| ✅ Random Forest | **1.711** | 0.9947 | 3.300 | −48% |
| ✅ Stacking Ensemble (Ridge meta) | 1.774 | 0.9953 | 3.698 | −52% |
| ✅ LightGBM | 2.108 | 0.9938 | 3.578 | −41% |
| ✅ XGBoost | 2.228 | 0.9931 | 3.419 | −35% |
| ✅ Lasso Regression | 3.064 | 0.9873 | 4.201 | −27% |
| ✅ Ridge Regression | 3.069 | 0.9874 | 4.215 | −27% |
| ✅ LSTM | 3.582 | 0.9816 | 10.132 | −65% |
| ✅ GRU | 3.947 | 0.9812 | — (new) | — |
| ✅ CNN-LSTM | 4.572 | 0.9767 | 12.435 | −63% |
| ✅ Mean Baseline | 22.691 | 0.4415 | — | — |
| — | TFT | *fix applied, re-run needed* | 5.114 | — |

> **V2 improvement sources:** DST-robust lags (167h/169h), min/max rolling stats, temp×hour interaction
> features, and complete dataset (45 buildings vs 43 in thesis). The dominant predictor remains `lag_1h`
> (r ≈ 0.977), which explains why DL models (feeding the same features) also improved substantially.

### Feature Engineering

| Item | Detail |
|------|--------|
| ✅ Cyclical encoding | sin/cos for hour (24), day_of_week (7), month (12), day_of_year (365) |
| ✅ Lag features | Target + temperature at [1, 2, 3, 24, 25, 26, 48, 167, 168, 169] hours per building |
| ✅ Rolling statistics | [mean, std, min, max] over [3, 6, 12, 24, 72, 168]-hour windows, per building |
| ✅ 3-stage feature selection | Variance → Correlation (|ρ|>0.99) → LightGBM top-35 |
| ✅ Correlation tie-breaking | Upper-triangle scan: for pair (A, B), B is always dropped — deterministic, documented |

---

## Phase 2 — Next Iteration

### 2A — Explainability / XAI (Q7) — Partially Complete

| Item | Status | Detail |
|------|--------|--------|
| ✅ SHAP beeswarm, bar, waterfall | Done | Global + local explanation for RF/LightGBM/XGBoost |
| 🟡 Model Card | Planned | Mitchell et al. (2019) format — intended use, metrics on peak vs normal days |
| 🟡 Dataset Datasheet | Planned | Formal COFACTOR Drammen dataset provenance document |
| 🟡 Per-building actual vs predicted | Planned | Visual trust-building for building managers |
| 🟡 Error bands by hour of day | Planned | Show model accuracy range across the 24-hour cycle |

### 2B — H+24 Day-Ahead Evaluation 🔴

The single most impactful research improvement identified by AI Studio and AICS reviewers.
H+1 with lag_1h is "easy mode" — lag_1h alone achieves persistence-level accuracy (r=0.977).
H+24 removes all lags < 24h, forcing models to rely on genuine temporal patterns.

#### 2B.1 — Simple H+24 run (Track A — conference/short paper, 1 week effort)

A fair, apples-to-apples comparison: same 35 features as H+1, minus lags < 24h.
The `forecast_horizon` guard in `temporal.py` already handles this automatically.

| Item | Detail | Effort |
|------|--------|--------|
| 🔴 Config change only | Set `forecast_horizon: 24` + `sequence.horizon: 24` | < 1 min |
| 🔴 Re-run `--skip-slow` | Trees + GRU + LSTM + Stacking evaluated H+24 | ~30 min |
| 🔴 Paper update | Addresses AICS R1 ("H+1 is trivial") and AI Studio critique | Low |

> **Expected outcome:** Tree models still dominate (access to 24h, 48h, 168h lags), but the
> DL vs tree gap will narrow because `lag_1h` oracle is gone. First honest test of whether
> LSTM/GRU add value beyond tree-based methods.

#### 2B.2 — Paradigm-Parity H+24 (Track B — journal paper, 2-3 week effort)

**Designed in collaboration with AI Studio (March 2026).** The key insight: giving DL models
the same engineered tabular features as trees creates a *feature parity trap* — trees are
inherently better at tabular data, so DL will always lose on their own ground.

A proper comparison requires **paradigm parity**: each model family receives its natural input.

**Branch A — Tabular (Trees):**
- Input: engineered features, lags ≥ 24h only (`lag_24h`, `lag_25h`, `lag_26h`, `lag_48h`, `lag_167h`, `lag_168h`, `lag_169h`)
- Rolling statistics anchored at t−24h (not t−0)
- Known future covariates: weather forecast for next 24h (in production: NWP; in experiment: observed temperature used as oracle proxy with disclosure)
- Output: 24 separate regression outputs, one per horizon step
- Benefit: fully exploits feature engineering mastery; trees shine here

**Branch B — Sequential (DL / TFT):**
- Input: raw 72-hour look-back sequences [load, temperature, solar, wind] — NO engineered lags, NO rolling stats
- Known future inputs: weather forecast for the next 24h (temperature, solar — TFT `time_varying_known_reals`)
- Architecture: LSTM/GRU encode 72h history; TFT uses variable-selection + attention on raw sequences
- Output: 24-step multi-horizon prediction (direct or iterative)
- Benefit: DL gets to leverage sequence modelling strength; architecture advantage can emerge

**Why this is the publishable journal result:**
- Eliminates the feature parity trap from the AICS paper
- PatchTST / TFT on raw sequences vs RF/LightGBM on engineered features — architecturally fair
- Enables probabilistic output: TFT → P10/P50/P90 per horizon step

| Item | Detail | Effort |
|------|--------|--------|
| 🔴 Branch A: H+24 tabular pipeline | Remove oracle lags, add weather forecast inputs for trees | ~1 day |
| 🔴 Branch B: raw sequence loader | New DataLoader that outputs (72, 4) tensors — no feature engineering | ~2 days |
| 🔴 DL multi-horizon output head | Change output from 1 to 24 units (LSTM/GRU/CNN-LSTM) | ~1 day |
| 🔴 TFT known-future weather inputs | Configure `time_varying_known_reals` = [temperature, solar] for 24h window | ~1 day |
| 🟡 PatchTST implementation | Add PatchTST to Branch B — benchmarks exceed Informer | 2-3 days |
| 🟡 Probabilistic metrics (TFT + LightGBM) | P10/P50/P90 + coverage + sharpness metrics | 1 day |

> **Code change estimate (AI Studio assessment):** ~150-170 new lines across 3 files:
> `temporal.py` (branch-aware feature builder), `dl_models.py` (raw sequence loader +
> multi-output head), `config.yaml` (paradigm parity flags). The forecast_horizon guard
> already exists — this builds on it.

### 2B.3 — Production Deployment Architecture (Track A + B prerequisite)

H+24 is the real deployment scenario: utility companies and data centre operators need
**day-ahead forecasts** to manage grid contracts, demand response bids, and peak shaving.

**Inference tiering for production:**

| Tier | Models | Latency | Use case |
|------|--------|---------|----------|
| Real-time (< 1ms) | LightGBM, RF | Sub-millisecond | Live dashboard, anomaly alert |
| Near real-time (< 10ms) | XGBoost | Milliseconds | Hourly monitoring report |
| Day-ahead batch (nightly) | LSTM, GRU, TFT | Train: hours; Infer: ms | H+24 demand forecast, DR bid |
| Weekly / monthly retrain | All models | Hours | Concept drift correction |

**Rolling window retraining (concept drift):**
Building energy patterns drift over time (new tenants, renovations, EV chargers).
Proposed production loop: retrain RF/LightGBM on last 90 days every 30 days;
retrain LSTM/TFT overnight on schedule; alert if rolling MAE degrades > threshold.

| Item | Detail | Effort |
|------|--------|--------|
| 🔵 Rolling window back-test | Walk-forward expanding window evaluation | Medium |
| 🔵 FastAPI inference endpoint | `POST /predict` with building_id, horizon, model, return_quantiles | High |
| 🔵 Docker deployment | Containerised service + periodic retraining scheduler | High |

---

### 2C — Probabilistic Forecasting (Q3, Q4, Q5) 🔴

| Item | Detail | Effort |
|------|--------|--------|
| 🔴 Quantile regression (LightGBM) | `objective='quantile'`, predict P10/P50/P90 natively | Low |
| 🔴 Quantile regression (TFT) | TFT already supports quantile outputs | Low |
| 🔴 Prediction interval metrics | Coverage (does P90 contain truth 90%?) + Width (sharpness) | Low |
| 🟡 Custom peak-weighted loss | Higher loss weight for top-10% load hours | Medium |
| 🟡 Tail-aware evaluation | MAE computed only on top-10% load hours, alongside global MAE | Low |

### 2D — Stacking / Ensemble Improvements (Q11)

| Item | Status | Detail | Effort |
|------|--------|--------|--------|
| 🔄 OOF (Out-of-Fold) stacking | **In progress** | Replace fixed-val with TimeSeriesSplit k-fold OOF meta-features — unbiased meta-learner training | Medium |
| ✅ Weighted Average Ensemble | Done | Implemented in `models/ensemble.py` | Done |
| 🟡 Physics-informed constraints | Planned | Monotonic constraints for XGBoost/LightGBM: temp ↓ → load ↑ (Q4) | Low |

### 2E — Missing Weather / Data Quality (Q1) 🟡

| Item | Detail | Effort |
|------|--------|--------|
| 🟡 Solar radiation feature | Already loaded (`Global_Solar_Horizontal_Radiation_W_m2`); add to feature pool after imputation | Medium |
| 🟡 Solar/wind imputation (MICE) | MICE on solar using Temperature, Hour, Month (18% missing) | Medium |
| 🔵 MET Nordic spatial interpolation | Query MET Nordic API for nearest weather station per building | Medium |
| 🔵 ERA5 reanalysis | Meteorological reanalysis as fallback / synthetic weather source | High |

---

## Phase 3 — Architecture Extensions

### 3A — Oslo Dataset Integration (Q6) 🟡

Pipeline-ready. 48 buildings (schools), SINTEF/Oslobygg KF, CC BY 4.0.
DOI: [10.60609/2hvr-wc82](https://data.sintef.no/product/dp-679b0640-834e-46bd-bc8f-8484ca79b414)

| Item | Detail | Effort |
|------|--------|--------|
| 🟡 Run pipeline on Oslo | Switch `city: oslo` in config, run `--skip-slow` | Low |
| 🟡 Cross-dataset comparison | Does a model trained on Drammen generalise to Oslo? | Medium |
| 🟡 Building_ID embeddings | Replace one-hot with learned dense vectors | Medium |
| 🔵 Transfer learning | Train on Drammen+Oslo combined, measure generalisation | High |

### 3B — Hierarchical Forecasting (Q6) 🔵🎓

| Item | Detail | Effort |
|------|--------|--------|
| 🔵 Hierarchical BART | Partial pooling: buildings borrow statistical strength | Very High |
| 🔵 Static building features | `floor_area`, `building_category` as static covariates | Medium |
| 🔵 Portfolio aggregate | Per-building + portfolio-level forecast for policymakers | High |
| 🎓 Probabilistic hierarchical | P10-P90 at both local and portfolio level | Research-level |

### 3C — Simpler Interpretable Models (Q2) 🟡

| Item | Detail | Effort |
|------|--------|--------|
| 🟡 GAM (Generalised Additive Model) | Upgrade to Linear Regression — non-linear, transparent | Medium |
| 🔵 Linear Quantile Regression | Point forecast → prediction interval | Medium |
| 🔵 Dynamic Harmonic Regression | Automates seasonality (replaces manual sin/cos) | High |

### 3D — Robustness / Production Readiness (Q4, Q8, Q9) 🔵

| Item | Detail | Effort |
|------|--------|--------|
| 🔵 OOD detection | Validate incoming weather against training distribution | High |
| 🔵 Rolling MAE monitoring | Alert if rolling 24h MAE exceeds threshold | Medium |
| 🔵 ONNX export | Convert RF/XGBoost to ONNX for framework-agnostic inference | Medium |
| 🔵 FastAPI inference endpoint | REST API for live per-building predictions | High |
| 🔵 Docker deployment | Containerised service for periodic retraining | High |

---

## Phase 4 — PhD-Track Research 🎓

| Item | Source | Strategic Value |
|------|--------|----------------|
| 🎓 Hierarchical BART with cross-dataset learning | Q6 | Novel for Norwegian public building portfolio |
| 🎓 Probabilistic forecasting for demand response | Q3/Q5, Crowley et al. 2024 | Bridges to energy community grid services |
| 🎓 OOD generalisation for extreme weather | Q4, Liu et al. 2023 | Applied ML safety research |
| 🎓 Behind-the-Meter feature engineering | Q8 | PV/EV integration in building energy systems |
| 🎓 Energy community dynamic pricing | Crowley et al. 2025 | Kazempour/Mitridati research link |
| 🎓 RACI + governance framework | Q10 | Responsible AI for utility companies (ESB, EirGrid) |

---

## Known Bugs / Technical Debt

| Bug | Status | Notes |
|-----|--------|-------|
| Cyclical encoding (23/6 vs 24/7) | ✅ Fixed | Original notebooks had wrong period — no impact on results as lag features dominated |
| Fixed validation for Stacking | ✅ Fixed | OOF stacking with TimeSeriesSplit (5 folds) validated March 1st 2026 — MAE 1.744, RMSE 3.240, R² 0.9953 |
| GRU results not in thesis Table 5 | ✅ Fixed | GRU evaluated in V2 pipeline: MAE 3.947 kWh, R² 0.981 |
| WeightedAverageEnsemble missing | ✅ Fixed | Implemented in `models/ensemble.py` |
| TFT pytorch-lightning import | ✅ Fixed | Changed `pytorch_lightning` → `lightning.pytorch` for 2.x compatibility |
| TFT logger=False silenced all epoch output | ✅ Fixed | `logger=False` suppressed both EarlyStopping verbose + epoch logs; fixed to `logger=True` + `_EpochLogger` callback |
| TFT hidden_size=64 (833K params, ~24h/run) | ✅ Fixed | Corrected to `hidden_size=32` (thesis value, 242K params, ~6-7h/run) |
| tensorflow-metal missing → LSTM/GRU/CNN-LSTM on CPU | ✅ Fixed | Installed `tensorflow-metal 1.2.0`; GPU now visible to TF on Apple Silicon |
| TFT num_workers=0 → GPU underutilised | 🟡 Known | PyTorch DataLoader bottleneck: 1 CPU core loads batches synchronously while GPU waits. Machine appears quiet (vs RF which uses 12 cores at 100%). Fix: `num_workers=4` in TFT + DL DataLoaders. Not yet applied (TFT currently running). |

---

## Full Thesis Results Reference (Appendix 2.1)

*Original held-out test set results, Apple Silicon MPS.*

| Model | MAE (kWh) | RMSE (kWh) | CV(RMSE) % | R² | Train Time (s) |
|-------|-----------|------------|------------|-----|----------------|
| **Random Forest** | **3.300** | **6.403** | **14.48** | **0.982** | 116 |
| XGBoost | 3.419 | 6.443 | 14.57 | 0.982 | 3 |
| LightGBM | 3.578 | 6.679 | 15.10 | 0.980 | 3 |
| Stacking (LGBM meta) | 3.582 | 7.030 | 15.81 | 0.978 | <1 |
| Stacking (Ridge meta) | 3.698 | 7.051 | 15.86 | 0.978 | <1 |
| Weighted Avg Ensemble | 4.081 | 7.841 | 17.63 | 0.973 | <1 |
| Lasso Regression | 4.201 | 7.880 | 17.81 | 0.973 | 4 |
| Ridge Regression | 4.215 | 7.767 | 17.56 | 0.973 | <1 |
| Persistence (Lag 1h) | 4.561 | 9.587 | 21.67 | 0.959 | — |
| TFT (Comprehensive) | 5.114 | 10.424 | 23.57 | 0.952 | 21,831 |
| TFT (MAE Loss only) | 8.576 | 13.442 | 19.51 | 0.948 | 21,831 |
| Seasonal Naive (24h) | 8.762 | 19.383 | 43.82 | 0.834 | — |
| LSTM | 10.132 | 17.686 | 39.77 | 0.862 | 13,497 |
| CNN-LSTM | 12.435 | 20.930 | 47.07 | 0.807 | 2,238 |

**Key finding:** Classical tree-based models dominated. DL models consumed 100–7,000× more compute
for significantly worse accuracy on this tabular hourly dataset.

---

## Key External Feedback Summary

See `docs/AI_STUDIO_FEEDBACK.md` for full detail.

| Source | Key Finding | Priority |
|--------|------------|---------|
| AI Studio | lag_1h is the true performance driver; H+1 = "easy mode"; H+24 is the honest evaluation | 🔴 HIGH |
| AI Studio | Feature parity ≠ paradigm parity — DL needs raw sequences, trees need engineered features | 🔴 HIGH |
| AI Studio | H+24 paradigm parity: Branch A (trees, ≥24h lags) vs Branch B (DL, raw 72h sequences + known future weather) | 🔴 HIGH |
| AICS R1 (Full Paper, 76/100) | DL given engineered features creates feature parity trap; DL should get raw sequences | 🔴 HIGH |
| AICS R2 (Full Paper, 64/100) | Single dataset limits generalisability; add Oslo for transfer learning | 🟡 MEDIUM |
| AICS R3 (Full Paper, 85/100) | Very clear presentation | ✅ Confirmed |
| AICS R4 (Full Paper, 78/100) | Figure 3 not needed | ✅ Fixed |
| AICS Student R2 (19/100) | Limited novelty, bullet-based writing | Accepted trade-off at conference level |
| AICS Student R3 (87/100) | Aligns with trees-over-DL literature | Confirms positioning |
| SINTEF Expert | Tree models validated; solar radiation is a valid Phase 2 feature | 🟡 MEDIUM |

### AI Studio Paradigm Parity Experiment (March 2026)

The detailed experiment design agreed with AI Studio for the journal paper (Track B):

**Branch A — Trees (tabular, causal H+24):**
```
Features: lag_24h, lag_25h, lag_26h, lag_48h, lag_167h, lag_168h, lag_169h
          rolling_mean_24h (anchored at t-24), rolling_mean_168h (anchored at t-168)
          cyclical time features, building_id (one-hot)
          known future: observed temperature t+1..t+24 (oracle proxy for NWP)
Models:   RF, LightGBM, XGBoost, Stacking (OOF)
Output:   24 separate point predictions (multi-output regressor)
```

**Branch B — Deep Learning / TFT (sequential, raw input):**
```
Encoder input: raw 72h look-back sequences → [load_kWh, temp_C, solar_Wm2, wind_ms]
               NO engineered lag features; NO rolling statistics
Known future:  weather forecast for t+1..t+24 → [temp_C, solar_Wm2] (TFT known_reals)
Models:        LSTM, GRU, TFT, PatchTST (planned)
Output:        24-step multi-horizon prediction (direct)
               TFT + LightGBM: P10/P50/P90 probabilistic intervals
```

**Why this is the publishable journal result:**
- Eliminates the feature parity trap criticised by AICS R1 and AI Studio
- Each model family gets its natural input representation
- Enables a fair architectural comparison: can TFT's attention mechanism beat RF's feature engineering when both are on home turf?
- Probabilistic output (P10/P50/P90) adds direct decision-support value for utility operators

---

## References

- Chipman, H.A., George, E.I., McCulloch, R.E. (2010). *BART: Bayesian Additive Regression Trees*. Annals of Applied Statistics.
- Bruna, D.W. (2023). *Feature selection and hierarchical modelling in tree-based ML models*. PhD, NUI Maynooth.
- Crowley, B., Kazempour, J., Mitridati, L. (2024). *How Can Energy Communities Provide Grid Services?* arXiv:2309.05363.
- Crowley, B., Kazempour, J., Mitridati, L., Alizadeh, M. (2025). *Learning Prosumer Behavior in Energy Communities*. arXiv:2501.18017.
- Liu, J. et al. (2023). *Towards Out-Of-Distribution Generalisation: A Survey*. arXiv:2108.13624.
- Mitchell, M. et al. (2019). *Model Cards for Model Reporting*. FAccT 2019.
- Lien, S.K., Walnum, H.T., Sørensen, Å.L. (2025). *COFACTOR Drammen dataset*. Scientific Data 12, 393.

---

*Last updated: 2026-03-01 (Session 11 — AI Studio paradigm parity experiment design added)*
*Maintained by: Dan Alexandru Bujoreanu — dan.bujoreanu@gmail.com*
