# Architecture and Thesis-to-Production Comparison

This document serves as the foundation for the Methodology section of the journal paper. It details the transition from the original Jupyter Notebook thesis to the production-ready Python package (V2), and provides a comprehensive breakdown of the new architecture.

## Section 1: The Engineered File Structure & Pipeline (V2 Pipeline)

The project has been refactored from three monolithic Jupyter Notebooks into a clean, modular Python package following a **Three-Tier Architecture** (Presentation, Application, Data) and a **Pipe-and-Filter ML pipeline** pattern.

### 1.1 The Application Tier (`src/energy_forecast/`)

The core engine is contained within the `src/energy_forecast/` package, adhering strictly to Single Responsibility Principles. The pipeline executes sequentially through these modules:

1. **`data/loader.py` (Ingestion):** Handles the raw reading of `.csv` or `.txt` building matrices. Ensures dataset completeness, standardizes column names, and concatenates individual building data into uniform Pandas structures.
2. **`data/preprocessing.py`:** Cleans the raw data. Handles anomalies in target consumption, resamples to strictly hourly resolution, and aligns the global chronological timestamp index.
3. **`data/imputation.py` (MICE):** A critical upgrade. Implements Multiple Imputation by Chained Equations (MICE) utilizing temporal covariates (`hour`, `month`) and correlated weather variables to realistically fill gaps in weather matrices (e.g., Solar Radiation) without forward-fill distortion or Look-Ahead leakage.
4. **`features/temporal.py`:** Computes strictly deterministic calendar features (`hour`, `day_of_week`), and their Cyclical transformations (sine/cosine encodings) to eliminate boundary biases.
5. **`features/engineering.py`:** Calculates complex, domain-specific predictors:
   - **Lag Features:** Memory states representing historical target or temperature variables (e.g., `lag_24h` for daily seasonality, `lag_168h` for weekly).
   - **Rolling Statistics:** Computes short-term (3h) to long-term (168h) bounds (Mean, Min, Max, Std), creating dynamic, smoothed contexts of recent operations.
   - **Interaction Features:** Multiplicative pairs between temperature and cyclical encodings capturing the time-varying sensitivity of loads.
6. **`features/selection.py`:** Automatically identifies target-centric value via a multi-stage funnel: Variance Threshold → Absolute Pearson Correlation ($|\rho| > 0.99$ filter) → Top 35 LightGBM Feature Importance mapping.
7. **`data/raw_sequence.py`:** Distinct to **Setup C** experiments. Formats raw matrices into overlapping 3D tensors (`[samples, sequence_length, features]`) suitable to feed directly into deep attention networks and Recurrent layers.
8. **`models/` (The Interfaces):** Wrappers for `sklearn_models.py`, `deep_learning.py` (Keras integration), and advanced logic like `ensemble.py`, centralizing `fit()` and `predict()` methods for automated pipeline iterations.

### 1.2 The Pipe-and-Filter Data Flow

The control script (`scripts/run_pipeline.py`) orchestrates the pipeline:
**Data Loader** → **Preprocessing** → **Time-Splits (Train/Val/Test)** → **Feature Engineering** → **Feature Selection** → **Model Training** → **Evaluation / Metrics Generation** (`final_metrics.csv`).

Every stage acts as a pure function: DataFrames enter safely indexed; transformed DataFrames exit. This allows the pipeline to decouple training logic from data representation, making it trivially simple to seamlessly switch between the **Drammen** and **Oslo** contexts entirely via standard config triggers.

---

## Section 2: Old Thesis vs. New Production Pipeline
The transition from the MSc academic implementation to the production-ready package crystallized several pivotal methodological upgrades.

### 2.1 The H+1 vs H+24 Horizon Realization
**Old Thesis:** Evaluated models natively on **H+1 (Real-Time Balancing)**. Because the highly-correlated `lag_1h` variable ($r=0.977$) is present at H+1, Tree Models were essentially operating on "easy mode," rendering Deep Learning structurally redundant for this short latency.
**Production V2:** Evaluated via **H+24 (Day-Ahead Market)**. The `lag_1h` oracle was explicitly dropped from the training arrays, forcing all models to forecast strictly 24 hours out. This provided a rigorously honest Day-Ahead evaluation frame for the Journal, and proved that even stripped of recent memory, tabular logic still surpassed native sequences on this dataset.

### 2.2 Paradigm Parity (Setup A vs B vs C)
**Old Thesis:** Attempted a "Feature Parity" logic, forcing DL architectures like LSTM to process the exact same engineered tabular features as Random Forest (creating high structural redundancy).
**Production V2:** Shifted to true "Paradigm Parity".
- **Setup A (Trees):** Allowed its natural domain of tabular engineered features.
- **Setup B (DL on Tabular):** Formed the explicitly measured Negative-Control benchmark revealing representational degradation.
- **Setup C (DL Sequential):** Allowed DL models native, un-engineered 3-dimensional 72-hour `raw_sequence.py` matrices, evaluating Attention Networks fundamentally accurately on their "home turf."

### 2.3 System Accelerations and Engineering Integrity
**Hardware Alignment (ReLU to Tanh):** The Thesis broadly utilized standard ReLU for DL models, causing training epochs exceeding 15+ hours. V2 refactored LSTMs to exclusively utilize `Tanh` activations. This seamlessly tied into Apple Silicon and optimized CUDA RNN kernels, resulting in a **10x speedup** making iterative DL training feasible on regular timelines.

**Ensembling (OOF vs. Grand):** The original notebook aggregated results simplistically. The V2 package explicitly distinguished between **Intra-Paradigm Out-of-Fold (OOF) Stacking** (which allowed Ridge Meta-Learners robustly un-biased CV combinations for Tree models) and the **Cross-Paradigm Grand Ensemble**, relying mechanically on Alpha-weighted blending due to the high computational constraints of bootstrapping Transformer Models like PatchTST.
