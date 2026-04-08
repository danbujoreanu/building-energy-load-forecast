# Building Energy Load Forecast

**Electricity consumption forecasting for Norwegian public buildings**
MSc Artificial Intelligence · National College of Ireland · 2025
*Dan Alexandru Bujoreanu*

[![CI](https://github.com/danbujoreanu/building-energy-load-forecast/actions/workflows/ci.yml/badge.svg)](https://github.com/danbujoreanu/building-energy-load-forecast/actions)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Conference Paper — AICS 2025

> **Forecasting Energy Demand in Buildings: The Case for Trees over Deep Nets**
> *Dan Alexandru Bujoreanu*
> 33rd Irish Conference on Artificial Intelligence and Cognitive Science (AICS 2025)

This research was submitted to and presented at **AICS 2025** in two tracks:

- 📄 **Full Paper** — submitted to the [Springer CCIS Series](https://www.springer.com/series/7899) (peer-reviewed archival proceedings) · *awaiting final Springer publication confirmation*
- 📄 **Student Paper** — published in the DCU Press Companion Proceedings (dedicated student research track)

The paper benchmarks tree-based models (Random Forest, LightGBM, XGBoost) against deep learning (LSTM, CNN-LSTM, GRU, TFT) for hourly building electricity load forecasting, and demonstrates that tree-based models consistently outperform deep nets on this tabular, high-autocorrelation time series — at a fraction of the training cost.

See [`docs/research/PAPER_JOURNEY.md`](docs/research/PAPER_JOURNEY.md) for the full story: from 3 Jupyter notebooks to a production package to a peer-reviewed conference paper.

---

## Overview

This repository contains the research code for **short-term electricity load forecasting** across 45 Norwegian public buildings (schools and kindergartens, Drammen municipality). Multiple machine learning approaches are implemented, benchmarked, and compared — from classical regression and tree-based ensembles to deep sequence models (LSTM, CNN-LSTM, GRU) and the Temporal Fusion Transformer.

The goal is to evaluate whether tree-based tabular models can match or exceed deep learning performance for this class of building-level energy forecasting, and to quantify the trade-off between predictive accuracy and computational cost.

A second dataset (48 Oslo buildings) is included in the pipeline and available for transfer learning experiments.

---

## Key Findings

- **Tree-based models outperform deep learning** on single-step-ahead evaluation for this dataset. Random Forest, LightGBM, and XGBoost all achieved substantially lower MAE than LSTM or TFT, while training in seconds rather than hours.
- **Temporal lag features dominate predictive accuracy.** LightGBM importance analysis consistently ranks `lag_1h` as the most influential feature (r ≈ 0.977 with the target), reflecting strong short-range autocorrelation in hourly building electricity consumption.
- **Ensemble methods improve H+1 by 3–5% but plateau at H+24.** At H+1, stacking with a Ridge meta-learner reduces MAE by 3–5% over the best single model (1.74 vs 1.71 kWh). At H+24, the OOF stacking ensemble (4.034 kWh) is essentially equivalent to LightGBM alone (4.029 kWh) — the meta-learner correctly discovers that blending correlated base models offers no margin.
- **Weather × time interactions add signal.** Temperature × sin(hour) and Temperature × cos(hour) cross-terms capture the interaction between outdoor temperature and intra-day load cycles, and are consistently selected in the top-35 feature set.

---

## Results

### Single-step-ahead evaluation (H+1) — Drammen test set, July 2021 – March 2022

All models are evaluated on 240,481 hourly observations across 42 buildings in the held-out test period. This is a **single-step-ahead (H+1) task**: the model predicts electricity consumption for the next hour, with all historical features including lag_1h available.

#### MSc Thesis (2025) — 35 selected features

| Rank | Model | MAE (kWh) | RMSE (kWh) | R² | Train time |
|------|-------|-----------|------------|-----|------------|
| 🥇 1 | **Random Forest** | **3.300** | 6.403 | 0.982 | ~2 min |
| 🥈 2 | XGBoost | 3.419 | 6.443 | 0.982 | ~3 s |
| 🥉 3 | LightGBM | 3.578 | 6.679 | 0.980 | ~3 s |
| 4 | Stacking Ensemble (LGBM meta) | 3.582 | 7.030 | 0.978 | <1 s |
| 5 | Stacking Ensemble (Ridge meta) | 3.698 | 7.051 | 0.978 | <1 s |
| 6 | Weighted Average Ensemble | 4.081 | 7.841 | 0.973 | <1 s |
| 7 | Lasso Regression | 4.201 | 7.880 | 0.973 | ~4 s |
| 8 | Ridge Regression | 4.215 | 7.767 | 0.973 | <1 s |
| 9 | Persistence (Lag 1h) | 4.561 | 9.587 | 0.959 | — |
| 10 | TFT (Comprehensive) | 5.114 | 10.424 | 0.952 | ~6 h |
| 11 | Seasonal Naive (Lag 24h) | 8.762 | 19.383 | 0.834 | — |
| 12 | LSTM | 10.132 | 17.686 | 0.862 | ~3.75 h |
| 13 | CNN-LSTM | 12.435 | 20.930 | 0.807 | ~37 min |

### 2026 H+24 Day-Ahead Evaluation: The Paradigm Parity Experiment

To truly evaluate models for day-ahead market forecasting, the horizon was shifted from H+1 (where `lag_1h` dominated) to **H+24**. This prevents simple autoregression and forces models to learn deeper temporal and weather interactions. 

The evaluation is structured as a **3-Way Paradigm Split**:

*   **Setup A: Classical ML (Tabular)** — Trees/Linear models trained on 35 engineered features.
*   **Setup B: Deep Learning (Tabular - Negative Control)** — DL models trained on the same 35 engineered features, proving DL struggles with tabular tabular representations compared to trees.
*   **Setup C: Deep Learning (Sequential)** — SOTA sequence models (PatchTST) trained dynamically on raw 3D sequences (Load, Temp, Solar) with a 72h lookback bridging the entire paradigm.

| Setup | Paradigm | Rank | Model | MAE (kWh) | R² | Train Time | Activation | Note |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Setup A** | **Classical ML + Features** | 🥇 1 | **LightGBM** | **4.029** | **0.975** | ~13 s | - | **Overall Champion** |
| Setup A | Classical ML + Features | 2 | XGBoost | 4.197 | 0.973 | ~7s | - | - |
| Setup A | Classical ML + Features | 3 | Random Forest | 4.402 | 0.968 | ~6 min | - | - |
| Setup A | Classical ML + Features | 4 | Ridge Regression | 7.460 | 0.926 | <1 s | - | Linear Baseline |
| **ENSEMBLE** | **Intra-A OOF Stacking** | - | **Stacking (Ridge meta)** | **4.034** | **0.975** | ~18 min | - | Best ensemble; ≈ LightGBM standalone |
| ENSEMBLE | Cross-Paradigm (A + C) | - | Weighted Avg (A90/C10) | 4.106 | 0.974 | - | - | Best A+C blend; adding DL degrades slightly |
| **Setup C** | **DL + Raw Sequences** | 1 | **PatchTST** | **6.955** | **0.910** | ~50 min | - | **SOTA Sequence Champion** |
| Setup C | DL + Raw Sequences | 2 | CNN-LSTM | 8.040 | 0.890 | ~11 min | ReLU, Tanh | - |
| Setup C | DL + Raw Sequences | 3 | GRU | 8.080 | 0.880 | ~20 min | Tanh | - |
| Setup C | DL + Raw Sequences | 4 | LSTM | 8.380 | 0.880 | ~19 min | Tanh | - |
| **Setup B** | **DL + Features** | 1 | **CNN-LSTM** | **9.375** | **0.877** | ~11 min | ReLU, Tanh | Best Negative Control |
| Setup B | DL + Features (Negative Control) | 2 | GRU | 9.639 | 0.867 | ~16 min | Tanh | - |
| Setup B | DL + Features (Negative Control) | 3 | LSTM | 34.938 | -0.003 | ~48 min | Tanh | *Convergence Failure* |
| Setup B | DL + Features (Negative Control) | 4 | TFT | 8.770 | 0.865 | ~94 min | GLU | Best Setup B by MAE; still 118% worse than LightGBM |

#### Ensembling: The "Trust Spectrum"

Three ensembling strategies are evaluated:
1. **Intra-Paradigm Stacking (Setup A):** 5-Fold **Out-of-Fold (OOF)** predictions from tree models passed to a Ridge meta-learner.
2. **Cross-Paradigm Grand Ensemble (A + C):** Alpha-blended weighted average between LightGBM and PatchTST. Sweep α = 0–100%.
3. **Cross-Paradigm (A+B):** Inverse-MAE validation-weighted blend of LightGBM + CNN-LSTM_SetupB. Weights: LightGBM=0.88 (val MAE=5.16 kWh), CNN-LSTM_B=0.12 (val MAE=37.81 kWh). Result: MAE=7.120 kWh, R²=0.929. Note: evaluated at H+24 specifically (CNN-LSTM last-step predictions), where CNN-LSTM_B's per-step MAE is ~30 kWh — much worse than its 9.375 kWh full-horizon average.

**Finding:** Pure LightGBM outperforms all ensemble variants. The ordering LightGBM (4.03) < A+C (4.11) << A+B (7.12) confirms paradigm non-complementarity: a weaker DL component (CNN-LSTM Setup B) degrades the ensemble far more than a stronger one (PatchTST Setup C). Adding even a small fraction of Setup B predictions nearly doubles the error.

![Paradigm Parity](docs/figures/fig1_paradigm_parity.png)
*Figure 1 — H+24 Paradigm Parity: Setup A (trees) vs Setup B (DL tabular) vs Setup C (DL raw sequences). LightGBM MAE 4.03 kWh vs PatchTST 6.96 kWh, DM statistic −12.17 (p<0.001).*

#### The Oslo Generalization (Phase 3A)

To answer AICS Reviewer 2's request for out-of-distribution geographical validation, the **Setup A** methodology was evaluated against an entirely new municipal dataset: **Oslo** (48 schools, 2019-2023).

Despite the larger baseline loads in the Oslo dataset naturally translating to higher absolute metrics (MAE ~7.4 kWh), **the geographic generalizability was completely verified**. Setup A tree models retained their exceptionally high explanatory power (R² > 0.95 across all tree-based methods), confirming that the engineered tabular pipeline captures foundational thermodynamic behaviours applicable cross-municipality.

| Rank | Model | MAE (kWh) | RMSE (kWh) | MAPE (%) | R² | Daily Peak MAE |
|------|-------|-----------|------------|----------|----|----------------|
| 🥇 1 | **Stacking Ensemble (Ridge meta)** | **7.280** | 13.437 | 15.72 | **0.9635** | 9.563 |
| 2 | LightGBM | 7.415 | 13.518 | 16.28 | 0.9630 | 9.722 |
| 3 | LightGBM (Quantile P50) | 7.345 | 14.492 | 14.45 | 0.9575 | 10.110 |
| 4 | XGBoost | 7.585 | 13.833 | 16.60 | 0.9613 | 10.118 |
| 5 | Random Forest | 7.708 | 14.634 | 15.56 | 0.9567 | 10.231 |
| 6 | Ridge Regression | 15.174 | 24.432 | 32.58 | 0.8792 | 22.284 |
| 7 | Lasso Regression | 15.159 | 24.430 | 32.51 | 0.8792 | 22.278 |
| — | Mean Baseline | 45.295 | 62.624 | 125.09 | 0.2063 | 60.900 |
| — | Naive (persistence) | 55.343 | 72.514 | 177.11 | −0.064 | 66.135 |
| — | Seasonal Naive (24h) | 73.810 | 101.414 | 101.82 | −1.082 | 119.231 |

*Oslo test set: 779,423 observations across 39 buildings. Models trained from scratch on Oslo data; no Drammen weights transferred.*

![Oslo Generalisation](docs/figures/fig3_oslo_generalisation.png)
*Figure 3 — Oslo generalisation: R² > 0.95 for all tree-based models on a held-out Norwegian city with no model transfer.*

---

### Menu of Solutions — Right Model for the Right Window

The pipeline supports three distinct forecasting horizons, each optimised for a different operational use case:

| Horizon | Operational Use Case | Champion Model | MAE (kWh) | R² |
|---------|---------------------|----------------|-----------|-----|
| **H+1** | Real-time battery / EV charge control | Stacking Ensemble (Ridge meta) | **1.74** | **0.995** |
| **H+24** | Day-ahead electricity market bidding | LightGBM | **4.03** | **0.975** |
| **H+24 + P10/P90** | Risk-aware solar diverter scheduling | LightGBM Quantile | 7.42 | 0.957 |

*H+1 and H+24 are trained as separate, horizon-specific models — not the same model evaluated at multiple steps.*

#### Horizon Sensitivity — H+1 → H+24 Degradation Factor

How much does accuracy degrade as we forecast further ahead?  The table below reveals the key finding: **tree models are as horizon-robust as DL models**, and LSTM suffers catastrophic convergence failure at H+24 when given tabular features.

| Model | Setup | H+1 MAE | H+24 MAE | Degradation | Note |
|-------|-------|---------|----------|-------------|------|
| **LightGBM** | A | 2.11 | **4.03** | **1.91×** | H+24 champion; most horizon-robust |
| XGBoost | A | 2.23 | 4.20 | 1.88× | |
| Random Forest | A | 1.71 | 4.40 | 2.57× | H+1 champion |
| Ridge | A | 3.07 | 7.46 | 2.43× | Linear reference |
| Lasso | A | 3.06 | 7.45 | 2.43× | |
| CNN-LSTM | B | 4.57 | 9.38 | 2.05× | DL negative control |
| GRU | B | 3.95 | 9.64 | 2.44× | |
| LSTM | B | 3.58 | 34.94 | **9.8×** | *Convergence failure at H+24* |

**Key insight:** Setup A trees degrade 1.9–2.6× from H+1 → H+24 (mean 2.24×). Converged DL models (CNN-LSTM, GRU) degrade comparably (2.1–2.4×, mean 2.25×). LSTM's 9.8× collapse confirms tabular feature representations are poorly suited to sequence learning at longer horizons without specialised architectural choices.

![Horizon Sensitivity](docs/figures/fig5_per_horizon_mae.png)
*Figure 5 — Per-horizon MAE: LightGBM degrades +48% from H+1 → H+48 vs Ridge +96%. Tree models are as horizon-robust as deep learning.*

Generated by: `python scripts/run_horizon_sweep.py` → `outputs/results/horizon_metrics.csv`

---

## System Architecture

The project implements a **Three-Tier Architecture** (Data / Application / Presentation) with a **Pipe-and-Filter** ML pipeline, following the design patterns studied in the MSc Engineering & Evaluating AI Systems module.

```mermaid
flowchart TD
    classDef default fill:#1a1a1a,stroke:#4a4a4a,stroke-width:2px,color:#fff;
    classDef highlight fill:#2A5D8A,stroke:#4a4a4a,stroke-width:2px,color:#fff;
    classDef control fill:#6e2b2b,stroke:#4a4a4a,stroke-width:2px,color:#fff;
    classDef text fill:none,stroke:none,color:#fff;

    %% Data Preparation
    subgraph Phase1 [Phase 1: Data Preparation]
        A["Drammen & Oslo Ingestion"] --> B["Merge Metadata & Submeters"]
        B --> C["MICE Imputation (ts.hour, ts.month covariates)"]
        C --> D["Model Ready Data"]
    end

    %% Paradigm Split
    subgraph Phase2 [Phase 2: The Paradigm Split]
        D --> E["Tabular Pathway"]
        E --> F["Feature Engineering (Lags, Rolling, Cyclical)"]
        F --> G["Feature Selection (35 Features)"]
        
        D --> H["Sequential Pathway"]
        H --> I["Raw 3D Windowing (72h Lookback)"]
        I --> J["Feature Scaling"]
        
        G:::highlight
        J:::highlight
    end

    %% Modelling Paradigms
    subgraph Phase3 [Phase 3: Modelling Paradigms H+24]
        G --> K["Setup A: Classical ML (LGBM, XGBoost, RF, Ridge)"]
        G --> L["Setup B: DL Tabular (LSTM, CNN-LSTM, GRU, TFT) — Negative Control"]
        J --> M["Setup C: DL Sequence (PatchTST, LSTM, CNN-LSTM)"]
        
        L:::control
    end

    %% Ensembling & Output
    subgraph Phase4 [Phase 4: Ensembling & Output]
        K --> N["Intra-Paradigm Stacking (OOF Ridge Meta-Learner)"]
        K -.->|"Champion: LGBM"| O["Cross-Paradigm Grand Ensemble (Alpha-blended Weighted Average)"]
        M -.->|"Champion: PatchTST"| O
        
        N --> P["H+24 Forecasts & Metrics (MAE, RMSE, Daily Peak Error)"]
        O --> P
    end

    %% Notes
    Note1["Note: Setup B acts as a Negative Control. Proving DL fails on non-sequential tabular features."]:::text
    Note1 -.- L
```

### Explainability — SHAP Feature Attribution

Model decisions are fully interpretable via SHAP. The pipeline generates beeswarm, bar, waterfall, and heatmap plots for each trained model.

![SHAP Beeswarm](docs/figures/shap_beeswarm.png)
*SHAP beeswarm — top drivers of predicted electricity consumption. `lag_1h` (r≈0.977 with target) dominates at H+1; at H+24, weather interactions and day-of-week features rise in importance as short-range autocorrelation features are excluded.*

```bash
python scripts/run_pipeline.py --city drammen --stages explain
# → outputs/figures/shap/shap_beeswarm_{model}.png
```

---

## Methodology

### Data

- **Drammen dataset:** 45 buildings (schools and kindergartens), hourly resolution, 2018–2022. Each building file contains electricity import/export, optional sub-meters, and site metadata.
- **Oslo dataset:** 48 buildings, 2019–2023. Same pipeline, switch `city: oslo` in config.

### Chronological splits

No data leakage: all splits are based on time boundaries.

| Split | Period | Rows (approx.) |
|-------|--------|----------------|
| Train | 2018-01-01 → 2020-12-31 | 1,144,535 |
| Validation | 2021-01-01 → 2021-06-30 | 188,343 |
| Test | 2021-07-01 → 2022-03-18 | 240,481 |

StandardScaler is fitted on the training set and applied to validation and test — no leakage from future data.

### Feature engineering

| Category | Features | Detail |
|----------|----------|--------|
| Calendar | hour_of_day, day_of_week, month, day_of_year, is_weekend | Raw |
| Cyclical | sin/cos encodings of all calendar features | Avoids ordinal distance bias |
| Interaction | temp × hour_sin, temp × hour_cos | Time-varying temperature sensitivity |
| Lag | target and temperature at 1h, 2h, 3h, 24–26h, 48h, 167–169h | Autocorrelation and weekly patterns |
| Rolling | mean, std, min, max over 3h, 6h, 12h, 24h, 72h, 168h | Short- and long-range context |
| Metadata | floor_area, year_of_construction, number_of_users, central_heating_system | Building characteristics |

Feature selection uses three sequential stages: variance threshold → Pearson correlation filter (ρ > 0.95, upper-triangle scan — the later column in each correlated pair is dropped) → top-35 by LightGBM importance. This reduces ~91 engineered features to 35.

### Models

| Category | Implementations |
|----------|----------------|
| Baselines | Naive (lag_1h persistence), Seasonal Naive (lag_24h), Mean |
| Linear | Ridge, Lasso (sklearn) |
| Tree-based | RandomForest, LightGBM, XGBoost |
| Deep learning | LSTM, CNN-LSTM, GRU (TensorFlow/Keras) |
| Transformer | Temporal Fusion Transformer (PyTorch Forecasting) |
| Ensemble | Stacking (Ridge or LightGBM meta-learner), Weighted Average |

All hyperparameters are centralised in `config/config.yaml`.

---

## Quick Start

### Installation

```bash
git clone https://github.com/danbujoreanu/building-energy-load-forecast.git
cd building-energy-load-forecast

# Recommended: conda environment
conda create -n ml_lab1 python=3.12
conda activate ml_lab1
pip install -e ".[all]"
```

In VS Code, select the interpreter via `Cmd+Shift+P` → *Python: Select Interpreter* → `ml_lab1`. Then activate in the terminal:

```bash
conda activate ml_lab1
```

### Reproducibility

To reproduce published results exactly, set `PYTHONHASHSEED` before starting Python (setting it inside a script only affects child processes, not the current interpreter):

```bash
export PYTHONHASHSEED=42
```

Add this to your `.zshrc` or `.bashrc` for persistent effect. All model random states are pinned via `seed: 42` in `config/config.yaml`.

### Run the pipeline

```bash
# All fast models (Ridge, Lasso, RF, LightGBM, XGBoost, Ensemble) — ~10 min
python scripts/run_pipeline.py --city drammen --skip-slow

# All models including LSTM, CNN-LSTM, TFT — ~4–6 hours total
python scripts/run_pipeline.py --city drammen

# Individual stages
python scripts/run_pipeline.py --city drammen --stages eda
python scripts/run_pipeline.py --city drammen --stages features
python scripts/run_pipeline.py --city drammen --stages training --skip-slow
python scripts/run_pipeline.py --city drammen --stages explain   # SHAP analysis
```

### Generate EDA charts

```bash
# All EDA and results charts
python scripts/generate_eda_charts.py --city drammen

# Include per-building energy profiles (45 figures)
python scripts/generate_eda_charts.py --city drammen --profiles

# Quick mode (skip ACF and seasonal decomposition)
python scripts/generate_eda_charts.py --city drammen --quick
```

### View results

```
outputs/
├── results/final_metrics.csv              Model comparison table
└── figures/
    ├── eda/
    │   ├── metadata_overview.png          Building categories, age, size, energy labels
    │   ├── column_availability.png        Sensor coverage heatmap (buildings × meters)
    │   ├── missing_data_analysis.png      Missing percentage per column and building
    │   ├── temperature_vs_electricity.png Scatter by building category
    │   ├── acf_pacf.png                   Autocorrelation structure (24h, 168h peaks)
    │   ├── seasonal_decomposition.png     Trend / seasonal / residual
    │   └── building_profiles/             Per-building daily and seasonal load patterns
    ├── results/
    │   ├── model_comparison_4panel.png    MAE / RMSE / R² / MAPE comparison
    │   ├── model_comparison_mae_bar.png   MAE bar chart
    │   └── thesis_vs_pipeline.png        Original thesis vs reproduced pipeline
    └── shap/
        ├── shap_beeswarm_{model}.png      Feature impact distributions
        ├── shap_bar_{model}.png           Mean absolute SHAP importance
        └── shap_waterfall_{model}_0.png   Single-prediction explanation
```

---

## Repository Structure

```
building-energy-load-forecast/
│
├── config/config.yaml              All parameters — single source of truth
│
├── data/
│   ├── raw/drammen/                45 building .txt files
│   └── raw/oslo/                   48 buildings (download separately, see below)
│
├── src/energy_forecast/            Python package
│   ├── data/                       Loader, preprocessing, splits
│   ├── features/                   Temporal features, feature selection
│   ├── models/                     Baselines, sklearn, deep learning, ensemble
│   ├── evaluation/                 Metrics, SHAP explainability
│   ├── control/                    Demand-response actions + ControlEngine
│   ├── tariff.py                   BGE rate logic (single source of truth)
│   └── utils/                      Config loader, logging, reproducibility
│
├── scripts/
│   ├── run_pipeline.py             End-to-end pipeline orchestrator
│   ├── run_raw_dl.py               Setup C (PatchTST raw sequence)
│   ├── run_horizon_sweep.py        H+1/6/12/24/48 sweep
│   ├── significance_test.py        Wilcoxon + Diebold-Mariano tests
│   ├── run_home_demo.py            Irish home trial morning brief
│   └── score_home_plan.py          Energy plan optimality scorer
│
├── deployment/
│   ├── app.py                      FastAPI inference + control API
│   ├── connectors.py               OpenMeteo, myenergi Eddi, SEMO stubs
│   ├── live_inference.py           CLI morning brief (dry-run safe)
│   ├── Dockerfile                  Non-root, health-checked container
│   └── apprunner.yaml              AWS App Runner config
│
├── docs/
│   ├── governance/                 MODEL_CARD · DATA_PROVENANCE · AIIA · DATA_LINEAGE
│   ├── figures/                    Paper figures + governance diagram (committed)
│   ├── research/                   Journal paper draft, methodology
│   ├── commercial/                 BMC, competitors, funding, roadmap
│   ├── regulatory/                 CRU202517, smart meter access
│   └── ops/                        Session log, decisions map, audit reports
│
├── knowledge/                      Procedural guides (Eddi API, run commands)
├── tests/                          Pytest test suite (90 tests, CI-validated)
├── CHANGELOG.md                    Semantic versioned history (v0.1.0 → v0.9.0)
├── ROADMAP.md                      Research + commercial roadmap
└── outputs/results/final_metrics.csv  Committed results table
```

---

## Datasets

### Drammen (included)

45 Norwegian public buildings (schools and kindergartens). Hourly electricity consumption with optional PV and sub-metering channels, outdoor weather (temperature, solar radiation, wind speed and direction), and per-building metadata (floor area, year of construction, number of occupants, heating system type, energy label).

### Oslo (download required)

48 public school buildings in Oslo, Norway. Same data format and pipeline configuration.

- **DOI:** [10.60609/2hvr-wc82](https://data.sintef.no/product/dp-679b0640-834e-46bd-bc8f-8484ca79b414)
- **License:** CC BY 4.0
- **Citation:** Lien, S.K. et al. (2025). *Hourly Sub-Metered Energy Use Data from 48 Public School Buildings in Oslo, Norway*. Data in Brief.

To use: place files in `data/raw/oslo/` and set `city: oslo` in `config/config.yaml`.

---

## Responsible AI & Governance

This project implements a production-grade AI governance framework across four living documents. Each document is linked to the pipeline stages it governs.

> **Champion model: LightGBM H+24 · MAE 4.03 kWh · R² 0.975 · Diebold-Mariano vs PatchTST: −12.17 (p<0.001)** — validated on 93 buildings across two Norwegian cities.

![Governance Diagram](docs/figures/governance_diagram.png)

| Document | Governs | Key content |
|----------|---------|-------------|
| [**📄 DATA PROVENANCE**](docs/governance/DATA_PROVENANCE.md) | Raw data → Feature engineering | Dataset licences (CC BY 4.0), ESB Networks legal basis, MICE imputation log, no-PII declaration |
| [**📋 MODEL CARD**](docs/governance/MODEL_CARD.md) | Training → Evaluation | **MAE 4.03 kWh / R²=0.975** (Drammen H+24) · Oslo MAE 7.28 kWh / R²=0.9635 · DM −12.17*** vs PatchTST · horizon sweep H+1→H+48 |
| [**⚖️ AI IMPACT ASSESSMENT**](docs/governance/AIIA.md) | Inference → Control | EU AI Act Art. 52 classification, affected parties, CRU June 2026 compliance, drift trigger: 7d MAE > 1.5× |
| [**🔗 DATA LINEAGE**](docs/governance/DATA_LINEAGE.md) | All stages | End-to-end audit trail: Raw CSV → Parquet → 35 features → StandardScaler → LightGBM → FastAPI → ControlEngine → Eddi command |

Regulatory context:
- **EU AI Act**: Limited risk (Art. 52) — transparency obligations apply; no autonomous safety-critical control
- **GDPR**: Contractual necessity basis (Art. 6(1)(b)); AWS eu-west-1 (Ireland); no raw data to any LLM API
- **CRU202517**: Qualifies as ESCO (Eligible Party) for smart meter data access under Ireland's Smart Meter Data System

---

## Production Deployment — Phase 6 & 7

The pipeline is containerised and production-ready beyond the research phase.

```
FastAPI (/predict · /control · /health)
    └── LightGBM H+24 model (joblib)
    └── ControlEngine → demand-response decisions
    └── Connectors: OpenMeteo (live) · myenergi Eddi (live) · SEMO (stub)

Docker (non-root, health-checked) → ECR → AWS App Runner
make docker-build && make ecr-push && make apprunner-deploy
```

Live integrations confirmed working:
- **myenergi Eddi** — hot water diverter API (HTTP Digest Auth): `get_status()`, `get_schedule()`, `get_history_day()`
- **Open-Meteo** — free weather forecast (no key required): temperature + solar radiation, 7-day window
- **ESB Networks HDF** — Irish smart meter CSV upload (manual MVP path; automatic via SMDS mid-2026)

---

## Reproducibility

All random seeds are controlled via `config/config.yaml`:

```yaml
seed: 42   # Applied to Python, NumPy, TensorFlow, and PyTorch
```

> **Important**: Set `export PYTHONHASHSEED=42` in your shell *before* running — Python's hash randomisation is fixed at interpreter startup and cannot be set from within a script.

The CI pipeline (GitHub Actions) runs all 90 tests against Python 3.10 and 3.11 on every push. GPU is not required; all models support CPU training.

---

## Future Work

See [`ROADMAP.md`](ROADMAP.md) for the full research roadmap, drawn from the 11 follow-up questions in the thesis.

Completed since the conference paper:

- ✅ **H+24 Day-Ahead Evaluation** — 3-Way Paradigm Parity Experiment (Setup A/B/C) completed; LightGBM MAE 4.029, PatchTST MAE 6.955
- ✅ **Oslo Generalisation** — Setup A validated on 48-building Oslo dataset; all tree models R² > 0.95
- ✅ **Out-of-fold stacking** — 5-fold TimeSeriesSplit OOF with gap=168h; Ridge meta-learner trained on held-out fold predictions only
- ✅ **Probabilistic forecasting** — LightGBM quantile objective (P50 reported; P10/P90 intervals available)

Open research directions:

- **Journal paper** — H+24 Paradigm Parity results + Oslo generalisation targeting a peer-reviewed journal
- **Hierarchical models** — partial pooling across buildings using BART or multilevel models (Q6)
- **Solar / wind imputation** — MICE-based imputation for ~18% missing weather features (Q1)
- **Transfer learning** — pre-training on Drammen, fine-tuning on Oslo with frozen lower layers

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=src/energy_forecast
```

---

## Citation

**Conference paper (AICS 2025 — preferred citation):**

*Presented at the 33rd Irish Conference on Artificial Intelligence and Cognitive Science (AICS 2025). Submitted to Springer CCIS — publication pending confirmation.*

```bibtex
@inproceedings{bujoreanu2025trees,
  author    = {Dan Alexandru Bujoreanu},
  title     = {Forecasting Energy Demand in Buildings:
               The Case for Trees over Deep Nets},
  booktitle = {Proceedings of the 33rd Irish Conference on Artificial
               Intelligence and Cognitive Science (AICS 2025)},
  series    = {Communications in Computer and Information Science},
  publisher = {Springer},
  year      = {2025},
  note      = {Publication pending},
}
```

**MSc thesis:**

```bibtex
@mastersthesis{bujoreanu2025energy,
  author  = {Dan Alexandru Bujoreanu},
  title   = {Machine Learning Approaches for Building Energy Load Forecasting
             in Norwegian Public Buildings},
  school  = {National College of Ireland},
  year    = {2025},
  type    = {MSc Artificial Intelligence},
}
```

---

## Author

**Dan Alexandru Bujoreanu**
MSc Artificial Intelligence · National College of Ireland · 2025
