# Journal Paper Outline: Forecasting Energy Demand in Buildings
**Working Title:** Forecasting Energy Demand in Buildings: The Case for Trees over Deep Nets across Multiple Paradigms
**Target:** High-Impact Academic Journal (e.g., Applied Energy, IEEE Transactions)

## 1. Introduction
- **The Context:** Importance of accurate building energy load forecasting for smart grids, energy communities, and reducing carbon emissions.
- **The Problem:** The tension between classical, interpretable Tree-based models on tabular features vs. state-of-the-art Deep Learning (DL) models designed for sequential data.
- **The "Menu of Solutions" Concept:** Framing the forecast problem not as a single winner-takes-all scenario, but mapping model strengths (Real-Time vs Day-Ahead Market vs Demand-Response) to unique operational latency strings.
- **Paper Contributions:** A rigorous three-paradigm (Setup A/B/C) benchmark across multiple physical building portfolios (Drammen & Oslo).

## 2. Methodology & System Architecture
- **2.1 The Pipe-and-Filter Design:** Overview of the complete MICE imputed, reproducible V2 data pipeline, ensuring no future-leakage.
- **2.2 Feature Engineering (The Tabular Pathway):** Defining how domain intelligence is explicitly coded via Cyclical encodings, Interaction features (Temp x Hour), and Rolling Statistics. 
- **2.3 Data Cohorts:** Describing the Drammen (45 mixed buildings) and Oslo (48 schools) datasets.

## 3. The Three Paradigms of Forecasting (Experimental Setup)
- **3.1 Setup A: Tabular Tree Experts (H+24)** LightGBM, XGBoost, Random Forest fed explicitly with engineered features.
- **3.2 Setup B: The Tabular-DL Hybrid (H+24) [Negative Control]** DL Architectures forced to read the Setup A engineered tabular arrays.
- **3.3 Setup C: The Sequential-SOTA (H+24)** Pure Attention models (PatchTST) reading native 3D time-series sequences.

## 4. Results & Benchmarking
- **4.1 The Real-Time Horizon (H+1):** Highlighting the explicit dominance of `lag_1h` and why this forms the 'easy mode' of short-term stability prediction.
- **4.2 The Day-Ahead Market (H+24) - Paradigm Parity Examined:** Detail the rigorous empirical drop-off when `lag_1h` is removed. Proving that LightGBM out-competes PatchTST when evaluating domain-tabular vs sequential representations respectively.
- **4.3 The Grand Ensemble vs Stacking:** Analysis of Out-of-Fold (OOF) Stacking stability for trees compared against Alpha-blended integration of Setup A & C. 
- **4.4 Hardware Acceleration Discovery:** Highlighting the observed speedups utilizing Tanh vs ReLU on optimized macOS Silicon engines. 

## 5. Discussion: Geographic Generalization & Real-World Impact
- **5.1 The Oslo Generalization:** Proving the Setup A methodology is fundamentally robust. Evaluating the absolute Error Metric "Scale vs. Variance" reality: Oslo MAE bounded higher simply due to building scale size (Mean Baseline ~45kWh vs ~22kWh), while structural R² reliably maintained perfectly resilient >0.96 bounds.
- **5.2 Probabilistic Bounds for Control:** Examining Quantile Output (P10/P50/P90) as a risk-aware mechanism for Grid MPC controllers.
- **5.3 Broader Impacts (The Virtual Power Plant):** Extrapolating the methodology to residential contexts. The impact of coordinating millions of predictive local systems (solar boilers, EVs) to smooth national grid loads away from gas-peaker dependency.

## 6. Conclusion
- A formalized summary that while Deep Learning captures sequence dynamics beautifully, specifically tailored Tree architectures leveraging well-engineered temporal heuristics (Setup A) provide the highest stability, fastest deployment, and most explainable variance for day-ahead municipal electrical forecasting.
- Suggested avenues for future research (e.g., Data Center Transfer, Weather Forecast Uncertainty Penalties).
