# 🏫 Building Energy Load Forecast

> **24-hour ahead electricity consumption forecasting for Norwegian public buildings**
> MSc Artificial Intelligence thesis — NCI Dublin, 2025
> Dan Alexandru Bujoreanu

[![CI](https://github.com/danbujoreanu/building-energy-load-forecast/actions/workflows/ci.yml/badge.svg)](https://github.com/danbujoreanu/building-energy-load-forecast/actions)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

This project develops and compares multiple machine learning approaches for **next-day electricity load forecasting** across 45 Norwegian public school and kindergarten buildings (Drammen, Norway). Accurate day-ahead predictions are critical for energy grid planning, demand response, and reducing peak load costs.

The codebase is a clean, modular refactoring of the original MSc thesis work — designed for **reproducibility, extensibility, and professional readability**. A second dataset (48 Oslo buildings) is pipeline-ready for future transfer learning experiments.

---

## Key Results

> **Thesis finding:** Classical tree-based models outperformed deep learning on this dataset — a compelling real-world result. Random Forest achieved the best MAE while training in under 2 minutes, compared to 6 hours for the Temporal Fusion Transformer.

| Rank | Model | MAE (kWh) | RMSE (kWh) | CV(RMSE) % | R² | Train time |
|------|-------|-----------|------------|------------|-----|------------|
| 🥇 1 | **Random Forest** | **3.300** | **6.403** | **14.48** | **0.982** | 1m 56s |
| 🥈 2 | XGBoost | 3.419 | 6.443 | 14.57 | 0.982 | 3s |
| 🥉 3 | LightGBM | 3.578 | 6.679 | 15.10 | 0.980 | 3s |
| 4 | Stacking (LightGBM meta) | 3.582 | 7.030 | 15.81 | 0.978 | <1s |
| 5 | Stacking (Ridge meta) | 3.698 | 7.051 | 15.86 | 0.978 | <1s |
| 6 | Weighted Avg Ensemble | 4.081 | 7.841 | 17.63 | 0.973 | <1s |
| 7 | Lasso Regression | 4.201 | 7.880 | 17.81 | 0.973 | 4s |
| 8 | Linear Regression | 4.215 | 7.767 | 17.56 | 0.973 | <1s |
| 9 | Ridge Regression | 4.215 | 7.767 | 17.56 | 0.973 | <1s |
| 10 | Persistence (Lag 1h) | 4.561 | 9.587 | 21.67 | 0.959 | — |
| 11 | TFT | 5.114 | 10.424 | 23.57 | 0.952 | ⏱ 6h 4m |
| 12 | Seasonal Naive (24h lag) | 8.762 | 19.383 | 43.82 | 0.834 | — |
| 13 | Seasonal Naive (168h lag) | 9.621 | 19.259 | 43.54 | 0.836 | — |
| 14 | LSTM | 10.132 | 17.686 | 39.77 | 0.862 | ⏱ 3h 45m |
| 15 | CNN-LSTM | 12.435 | 20.930 | 47.07 | 0.807 | ⏱ 37m |

> *Full results from held-out test set, trained on Apple Silicon (MPS). Classical tree-based models dominated — RF achieves R²=0.982 in under 2 minutes vs 6+ hours for deep learning with worse accuracy. This is the thesis's central finding: for tabular hourly energy data, complexity does not improve accuracy.*

---

## System Architecture

The project implements a **Three-Tier Architecture** with a **Pipe-and-Filter** ML pipeline:

```mermaid
graph TD
    subgraph Presentation["🖥️ Presentation Tier"]
        NB[notebooks/]
        SC[scripts/run_pipeline.py]
    end

    subgraph Application["⚙️ Application Tier — src/energy_forecast/"]
        L[data/loader.py\nParse raw .txt/.csv files]
        P[data/preprocessing.py\nClean · Validate · Merge]
        SP[data/splits.py\nTrain · Val · Test]
        T[features/temporal.py\nLag · Rolling · Cyclical]
        FS[features/selection.py\nVariance · Corr · LightGBM]
        M[models/\nBaselines → sklearn → LSTM/GRU/CNN → TFT → Ensemble]
        E[evaluation/metrics.py\nMAE · RMSE · MAPE · R²]
        V[visualization/plots.py]
    end

    subgraph Data["🗄️ Data Tier"]
        RAW[data/raw/drammen/ · oslo/]
        PROC[data/processed/]
        OUT[outputs/results/ · figures/]
        CFG[config/config.yaml]
    end

    NB --> SC
    SC --> L
    L --> P
    P --> SP
    SP --> T
    T --> FS
    FS --> M
    M --> E
    E --> V
    V --> OUT

    RAW --> L
    CFG -.->|parameters| L
    CFG -.->|parameters| T
    CFG -.->|parameters| M
    SP --> PROC
```

---

## ML Pipeline Detail

```mermaid
flowchart LR
    A[📁 45 Raw\nBuilding Files] --> B[Load &\nParse]
    B --> C[Clean &\nValidate]
    C --> D[Train/Val/Test\nSplit]
    D --> E[Temporal Features\nlags · rolling · cyclical]
    E --> F[Feature Selection\nVariance→Corr→LightGBM]
    F --> G1[Baselines]
    F --> G2[sklearn\nRidge/LightGBM/RF]
    F --> G3[Deep Learning\nLSTM · GRU · CNN-LSTM]
    F --> G4[TFT\nAttention]
    G1 --> H[Stacking\nEnsemble]
    G2 --> H
    G3 --> H
    G4 --> H
    H --> I[📊 Evaluation\nMAE · RMSE · R²]
```

---

## Model Complexity vs Accuracy Trade-off

*Applying the MSc Engineering & AI Systems computational complexity framework:*

```mermaid
quadrantChart
    title Complexity vs Accuracy (actual thesis results)
    x-axis Low Complexity --> High Complexity
    y-axis Low Accuracy --> High Accuracy
    quadrant-1 Best — high accuracy low cost
    quadrant-2 Overkill
    quadrant-3 Avoid
    quadrant-4 Investigate further
    Random Forest: [0.38, 0.92]
    XGBoost: [0.32, 0.90]
    LightGBM: [0.28, 0.88]
    Stacking Ensemble: [0.42, 0.87]
    Ridge Regression: [0.10, 0.72]
    Lasso Regression: [0.12, 0.71]
    TFT: [0.90, 0.65]
    LSTM: [0.70, 0.35]
    CNN-LSTM: [0.78, 0.28]
```

> **Key takeaway:** Tree-based models (top-left quadrant) dominated. Deep learning models consumed far more compute for *lower* accuracy on this dataset — a finding worth exploring further with Oslo data and transfer learning approaches.

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/danbujoreanu/building-energy-load-forecast.git
cd building-energy-load-forecast

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install the package + core dependencies
pip install -e ".[all]"
```

### 2. Run the full pipeline

```bash
# Full pipeline (all models, Drammen dataset)
python scripts/run_pipeline.py --city drammen

# Skip slow models during development (CNN-LSTM, TFT)
python scripts/run_pipeline.py --city drammen --skip-slow

# Run individual stages
python scripts/run_pipeline.py --city drammen --stages eda
python scripts/run_pipeline.py --city drammen --stages features
python scripts/run_pipeline.py --city drammen --stages training --skip-slow
```

### 3. View results

```
outputs/
├── results/final_metrics.csv      ← All model metrics
└── figures/
    ├── model_comparison_mae.png
    ├── building_profiles.png
    ├── temperature_sensitivity.png
    └── seasonal_patterns.png
```

---

## Project Structure

```
building-energy-load-forecast/
│
├── config/config.yaml             ← All hyperparameters (lookback, horizon, etc.)
│
├── data/
│   ├── raw/drammen/               ← 45 building .txt files (included)
│   └── raw/oslo/                  ← 48 buildings (download separately)
│
├── src/energy_forecast/           ← Python package
│   ├── data/                      ← Parsing, preprocessing, train/val/test splits
│   ├── features/                  ← Temporal encoding, lag, rolling, selection
│   ├── models/                    ← Baselines, sklearn, LSTM/GRU/CNN, TFT, ensemble
│   ├── evaluation/                ← MAE, RMSE, MAPE, R² metrics
│   ├── visualization/             ← All plot functions
│   └── utils/                     ← Config loader, logging, reproducibility
│
├── scripts/run_pipeline.py        ← One command to run everything
├── notebooks/                     ← Clean exploratory notebooks (import from src/)
├── tests/                         ← Pytest test suite (CI-validated)
└── outputs/results/               ← Model comparison table (committed)
```

---

## Datasets

### Drammen (45 buildings) — included
- **Source**: COFACTOR Project, Norway
- **Type**: Schools and kindergartens
- **Period**: 2018–2024, hourly resolution
- **Features**: Electricity (imported, PV, sub-metered), weather (temperature, solar, wind)

### Oslo (48 buildings) — download required
- **Source**: SINTEF / Oslobygg KF
- **DOI**: [10.60609/2hvr-wc82](https://data.sintef.no/product/dp-679b0640-834e-46bd-bc8f-8484ca79b414)
- **License**: CC BY 4.0
- **Pipeline**: Ready — switch `city: oslo` in `config/config.yaml`

---

## Feature Engineering

Three categories of features are engineered from raw hourly data:

| Category | Features | Purpose |
|----------|----------|---------|
| **Cyclical** | hour_sin/cos, day_of_week_sin/cos, month_sin/cos | Captures periodicity without ordinal bias |
| **Lag** | target at t-1, t-2, t-6, t-12, t-24 hours | Autocorrelation structure |
| **Rolling** | 6h/12h/24h/48h mean & std of electricity + temperature | Trend and volatility context |

Feature selection reduces ~200 engineered features to the top 35 via:
1. Variance threshold
2. Correlation filter (ρ > 0.99)
3. LightGBM feature importance ranking

---

## Reproducibility

All random seeds are controlled centrally:

```yaml
# config/config.yaml
seed: 42   # Python, NumPy, TensorFlow, PyTorch
```

Experiments are fully reproducible on the same hardware. GPU is not required (CPU training supported for all models).

---

## Future Work

See [`ROADMAP.md`](ROADMAP.md) for the full prioritised research roadmap drawn from the
MSc thesis Follow-up Questions document (11 questions, PhD-track research).

Top priorities for the next iteration:

- 🔴 **SHAP explainability** — beeswarm + force plots for global and local predictions (Q7)
- 🔴 **Probabilistic forecasting** — quantile regression (P10/P50/P90) in LightGBM & TFT (Q3/Q5)
- 🟡 **Oslo dataset integration** — cross-dataset comparison, transfer learning (Q6)
- 🟡 **Solar/wind imputation** — include the 18%-missing weather features via MICE (Q1)
- 🟡 **OOF stacking** — replace fixed-validation ensemble with out-of-fold meta-features (Q11)
- 🔵 **Hierarchical BART** — partial pooling across buildings, building_id embeddings (Q6)
- 🔵 **FastAPI inference endpoint** — real-time predictions for live deployment (Q8/Q9)

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=src/energy_forecast
```

---

## Citation

If you use this code or build on this work, please cite:

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

**Datasets:**
- Lien, S.K. et al. (2025). *Hourly Sub-Metered Energy Use Data from 48 Public School Buildings in Oslo, Norway*. Data in Brief. CC BY 4.0.

---

## Author

**Dan Alexandru Bujoreanu**
- 📧 dan.bujoreanu@gmail.com
- 🎓 MSc Artificial Intelligence, NCI Dublin (2025)
- 💼 [LinkedIn](https://linkedin.com/in/danbujoreanu)

---

*Built with ❤️ and a lot of Norwegian electricity data.*
