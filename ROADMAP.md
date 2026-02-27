# Research Roadmap

**Dan Alexandru Bujoreanu — Building Energy Load Forecast**
*MSc Artificial Intelligence, NCI Dublin 2025 → PhD-track research*

This document tracks completed work and all prioritised future iterations,
drawn directly from the MSc thesis (2025) and the 11 Follow-up Questions
document that maps the research forward.

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

### Codebase & Infrastructure

| Item | Detail | Notes |
|------|--------|-------|
| ✅ Modularisation | Refactored 3 Jupyter notebooks → clean Python package (`src/energy_forecast/`) | **Q11 improvement item — done** |
| ✅ Config-driven design | Single `config/config.yaml` as source of truth for all parameters | Eliminates scattered magic numbers |
| ✅ Cyclical encoding fix | Corrected period: hour=24, day=7 (was 23/6 in thesis notebooks) | **Q11 bug fix — resolved in new code** |
| ✅ Test suite (19 tests) | `pytest tests/` — data, features, models, metrics | CI-validated, no raw data needed |
| ✅ GitHub Actions CI | Lint (ruff, black) + tests on Python 3.10 & 3.11 | Every push/PR |
| ✅ `.gitignore` | Excludes 400MB+ processed CSVs, model checkpoints | Raw data only |

### Models Implemented

| Model | Thesis Rank | MAE (kWh) | R² | Train Time |
|-------|------------|-----------|-----|-----------|
| ✅ Random Forest | 🥇 1 | 3.300 | 0.982 | ~2 min |
| ✅ XGBoost | 🥈 2 | 3.419 | 0.982 | ~3s |
| ✅ LightGBM | 🥉 3 | 3.578 | 0.980 | ~3s |
| ✅ Stacking Ensemble (LGBM meta) | 4 | 3.582 | 0.978 | <1s |
| ✅ Stacking Ensemble (Ridge meta) | 5 | 3.698 | 0.978 | <1s |
| ✅ Lasso Regression | 7 | 4.201 | 0.973 | ~4s |
| ✅ Ridge Regression | 8 | 4.215 | 0.973 | <1s |
| ✅ TFT (Temporal Fusion Transformer) | 11 | 5.114 | 0.952 | ~6h |
| ✅ Persistence (Lag 1h) | 10 | 4.561 | 0.959 | — |
| ✅ Seasonal Persistence (Lag 24h) | 13 | 8.762 | 0.834 | — |
| ✅ LSTM | 15 | 10.132 | 0.862 | ~3h 45m |
| ✅ CNN-LSTM | 16 | 12.435 | 0.807 | ~37m |
| ✅ GRU | Implemented | — | — | — |

### Feature Engineering

| Item | Detail |
|------|--------|
| ✅ Cyclical encoding | sin/cos for hour (24), day_of_week (7), month (12), day_of_year (365) |
| ✅ Lag features | Target + temperature lags: 1h, 2h, 3h, 4h, 5h, 6h, 12h, 24h per building |
| ✅ Rolling statistics | 6h/12h/24h/48h mean & std, applied per building |
| ✅ 3-stage feature selection | Variance → Correlation (ρ>0.99) → LightGBM top-35 |

---

## Phase 2 — Next Iteration 🔴

*These are the highest-impact items identified across all 11 follow-up questions.
Recommended order: start with XAI (Q7) and Probabilistic Forecasting (Q3/Q5) as
these are directly applicable to the current pipeline with minimal architecture change.*

### 2A — Explainability / XAI (Q7) 🔴

The most impactful addition for both research and portfolio value.

| Item | Detail | Effort |
|------|--------|--------|
| 🔴 SHAP beeswarm plot | Global feature importance — shows *direction* of impact (e.g., low temp → high load) | Low |
| 🔴 SHAP force plot | Local explanation for any single prediction, especially peaks | Low |
| 🔴 SHAP Dashboard | Interactive dashboard showing feature contributions | Medium |
| 🟡 Model Card | Mitchell et al. (2019) format — intended use, metrics on peak vs normal days, known limitations | Medium |
| 🟡 Dataset Datasheet | Formal documentation of COFACTOR Drammen dataset provenance | Low |
| 🟡 Per-building actual vs predicted plots | Visual trust-building for building managers | Low |
| 🟡 Error bands by hour of day | Show model accuracy range across the 24-hour cycle | Low |

**Implementation note:** `pip install shap` — works directly on trained RF/XGBoost/LightGBM.

### 2B — Probabilistic Forecasting (Q3, Q4, Q5) 🔴

The single theme that runs through Q2, Q3, Q4, Q5 — flagged explicitly by the thesis
as the primary next iteration area. Referenced work: Jalal Kazempour (Crowley et al. 2024, 2025).

| Item | Detail | Effort |
|------|--------|--------|
| 🔴 Quantile regression (LightGBM) | Train with `objective='quantile'`, predict P10/P50/P90 intervals natively | Low |
| 🔴 Quantile regression (TFT) | TFT already supports quantile outputs | Low |
| 🔴 Prediction interval metrics | Coverage (does P90 contain truth 90% of time?) + Width (sharpness) | Low |
| 🟡 Custom peak-weighted loss | Higher loss weight for top-10% load hours — improve tail accuracy | Medium |
| 🟡 Tail-aware evaluation metric | MAE computed only on top-10% load hours, alongside global MAE | Low |
| 🟡 Event-based classification | Define threshold (e.g., >250 kWh = "Peak Event"), evaluate Recall + F2-Score | Medium |

### 2C — Missing Weather Data / Data Quality (Q1) 🟡

| Item | Detail | Effort |
|------|--------|--------|
| 🟡 Solar/wind imputation (MICE) | MICE on `Global_Solar_Horizontal_Radiation_W_m2` using Temperature, Hour, Month | Medium |
| 🟡 MET Nordic spatial interpolation | Query MET Nordic API for nearest weather station data for each building | Medium |
| 🔵 ERA5 reanalysis data | Meteorological reanalysis as fallback / synthetic weather source | High |
| 🔵 Google WeatherNext | Probabilistic forecast models as direct weather input | High |
| 🔵 Train on forecast vs observation | Use historical weather *forecasts* rather than observations — simulates real deployment | High |

**Context:** Solar radiation and wind speed had ~18% missing values and were excluded from thesis.
Including them as features (after imputation) may improve model accuracy.

### 2D — Stacking / Ensemble Improvements (Q11) 🟡

| Item | Detail | Effort |
|------|--------|--------|
| 🟡 OOF (Out-of-Fold) stacking | Replace fixed validation set with k-fold OOF meta-features — reduces variance | Medium |
| 🟡 Weighted Average Ensemble | Simple average of top-3 model predictions (was MAE 4.081 in thesis) | Low |
| 🟡 Physics-informed constraints | Monotonic constraints for XGBoost/LightGBM: temperature ↓ → load ↑ (Q4) | Low |

---

## Phase 3 — Architecture Extensions 🟡🔵

### 3A — Oslo Dataset Integration (Q6) 🟡

The Oslo pipeline is ready. 48 buildings (schools), SINTEF/Oslobygg KF, CC BY 4.0.
DOI: [10.60609/2hvr-wc82](https://data.sintef.no/product/dp-679b0640-834e-46bd-bc8f-8484ca79b414)

| Item | Detail | Effort |
|------|--------|--------|
| 🟡 Run pipeline on Oslo dataset | Switch `city: oslo` in config, run `--skip-slow` | Low |
| 🟡 Cross-dataset comparison | Does a model trained on Drammen generalise to Oslo? | Medium |
| 🟡 Building_ID embeddings | Replace one-hot encoding with learned dense vectors — capture building similarity | Medium |
| 🔵 Cross-dataset transfer learning | Train on Drammen+Oslo combined, measure generalisation | High |

### 3B — Hierarchical Forecasting (Q6) 🔵🎓

This is the state-of-the-art approach that solves the pooled vs per-building trade-off.
Referenced: Hierarchical BART (Chipman et al. 2010; Bruna 2023, NUI Maynooth PhD).

| Item | Detail | Effort |
|------|--------|--------|
| 🔵 Hierarchical BART | Partial pooling: buildings borrow statistical strength from each other | Very High |
| 🔵 Static building features | Use `floor_area`, `building_category` as static covariates | Medium |
| 🔵 Local + global forecast output | Per-building prediction + portfolio aggregate for policymakers | High |
| 🎓 Probabilistic hierarchical model | Naturally produces P10-P90 intervals at both local and portfolio level | Research-level |

### 3C — Simpler Interpretable Models (Q2) 🟡

Models that offer transparency for operational settings and new buildings with limited data.

| Item | Detail | Effort |
|------|--------|--------|
| 🟡 GAM (Generalised Additive Model) | Upgrade to Linear Regression — captures non-linear effects, more transparent than RF | Medium |
| 🔵 Linear Quantile Regression | Point forecast → prediction interval, risk management | Medium |
| 🔵 Dynamic Harmonic Regression | Automates seasonality handling (replaces manual sin/cos features) | High |

### 3D — Robustness / Production Readiness (Q4, Q8, Q9) 🔵

| Item | Detail | Effort |
|------|--------|--------|
| 🔵 OOD detection (input monitoring) | Validate incoming weather forecast against training distribution — fallback to Linear if OOD | High |
| 🔵 Rolling MAE monitoring | Calculate rolling 24h MAE post-prediction, alert if threshold exceeded | Medium |
| 🔵 Scenario stress-testing | Feed trained model synthetic extreme weather (ERA5 historical anomalies) — find model break points | High |
| 🔵 ONNX model export | Convert trained RF/XGBoost to ONNX for fast, framework-agnostic inference | Medium |
| 🔵 FastAPI inference endpoint | REST API for live building-level predictions | High |
| 🔵 Model quantization (16-bit) | Reduce parameter precision for CPU-efficient deployment | Medium |
| 🔵 Docker deployment | Lightweight containerised service for periodic retraining | High |

---

## Phase 4 — PhD-Track Research 🎓

*Items identified as viable research contributions in a part-time PhD framework.*

| Item | Source | Strategic Value |
|------|--------|----------------|
| 🎓 Hierarchical BART with cross-dataset learning | Q6 | Novel for Norwegian public building portfolio |
| 🎓 Probabilistic forecasting for demand response | Q3/Q5, Crowley et al. 2024 | Bridges to energy community grid services |
| 🎓 OOD generalisation for extreme weather | Q4, Liu et al. 2023 | Applied ML safety research |
| 🎓 Behind-the-Meter feature engineering | Q8 | PV/EV integration in building energy systems |
| 🎓 Energy community dynamic pricing | Crowley et al. 2025 | Direct link to Kazempour/Mitridati research |
| 🎓 RACI + governance framework | Q10 | Responsible AI for utility companies (ESB, EirGrid) |

---

## Known Bugs / Technical Debt

| Bug | Status | Notes |
|-----|--------|-------|
| Cyclical encoding (23/6 vs 24/7) | ✅ Fixed in new code | Original notebooks had wrong period for hour/day — no impact on results as lag features dominated |
| Fixed validation for Stacking | 🟡 Planned fix | OOF stacking is the correct approach; fixed-val was a deliberate training-time trade-off in thesis |
| GRU results not in thesis Table 5 | 🟡 Needs evaluation | GRU is implemented but was not formally evaluated in thesis |
| WeightedAverageEnsemble | 🟡 Planned | Thesis had this (MAE 4.081) but not yet in new codebase |
| Two TFT variants | 🟡 Planned | Thesis ran TFT_MAE_Loss (8.58) and TFT_Comprehensive (5.11) — only one in code |

---

## Full Thesis Results Reference (Appendix 2.1)

*Complete results from held-out test set, Apple Silicon MPS.*

| Model | MAE (kWh) | RMSE (kWh) | CV(RMSE) % | R² | Train Time (s) |
|-------|-----------|------------|------------|-----|----------------|
| **Random Forest** | **3.300** | **6.403** | **14.48** | **0.982** | 116 |
| XGBoost | 3.419 | 6.443 | 14.57 | 0.982 | 3 |
| LightGBM | 3.578 | 6.679 | 15.10 | 0.980 | 3 |
| Stacking (LGBM meta) | 3.582 | 7.030 | 15.81 | 0.978 | <1 |
| Stacking (Ridge meta) | 3.698 | 7.051 | 15.86 | 0.978 | <1 |
| Weighted Avg Ensemble | 4.081 | 7.841 | 17.63 | 0.973 | <1 |
| Lasso Regression | 4.201 | 7.880 | 17.81 | 0.973 | 4 |
| Linear Regression | 4.215 | 7.767 | 17.56 | 0.973 | <1 |
| Ridge Regression | 4.215 | 7.767 | 17.56 | 0.973 | <1 |
| Persistence (Lag 1h) | 4.561 | 9.587 | 21.67 | 0.959 | — |
| TFT (Comprehensive) | 5.114 | 10.424 | 23.57 | 0.952 | 21,831 |
| TFT (MAE Loss only) | 8.576 | 13.442 | 19.51 | 0.948 | 21,831 |
| Seasonal Naive (24h) | 8.762 | 19.383 | 43.82 | 0.834 | — |
| Seasonal Naive (168h) | 9.621 | 19.259 | 43.54 | 0.836 | — |
| LSTM | 10.132 | 17.686 | 39.77 | 0.862 | 13,497 |
| CNN-LSTM | 12.435 | 20.930 | 47.07 | 0.807 | 2,238 |

**Key finding:** Classical tree-based models dominated. DL models consumed 100–7,000× more compute
for significantly worse accuracy on this tabular hourly dataset.

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

*Last updated: 2026-02-27*
*Maintained by: Dan Alexandru Bujoreanu — dan.bujoreanu@gmail.com*
