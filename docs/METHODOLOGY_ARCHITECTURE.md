# Proposed Architecture & Methodology Diagram

Based on the Google AI Studio review, the journey from data to the final Grand Ensemble represents a "Paradigm Split." Below is the visual representation using Mermaid and a text-based layout of how the new architecture diagram should be drawn for the final Master's Thesis or Journal Paper.

## Visual Flowchart (Mermaid)

```mermaid
flowchart TD
    classDef default fill:#1a1a1a,stroke:#4a4a4a,stroke-width:2px,color:#fff;
    classDef highlight fill:#2A5D8A,stroke:#4a4a4a,stroke-width:2px,color:#fff;
    classDef control fill:#6e2b2b,stroke:#4a4a4a,stroke-width:2px,color:#fff;
    classDef text fill:none,stroke:none,color:#fff;

    %% Data Preparation
    subgraph Phase1 [Phase 1: Data Preparation]
        A["Drammen & Oslo Ingestion"] --> B["Merge Metadata & Submeters"]
        B --> C["MICE Imputation <br/> (ts.hour, ts.month covariates)"]
        C --> D["Model Ready Data"]
    end

    %% Paradigm Split
    subgraph Phase2 [Phase 2: The Paradigm Split]
        D --> E["Tabular Pathway"]
        E --> F["Feature Engineering <br/> (Lags, Rolling, Cyclical)"]
        F --> G["Feature Selection <br/> (35 Features)"]
        
        D --> H["Sequential Pathway"]
        H --> I["Raw 3D Windowing <br/> (72h Lookback)"]
        I --> J["Feature Scaling"]
        
        G:::highlight
        J:::highlight
    end

    %% Modelling Paradigms
    subgraph Phase3 [Phase 3: Modelling Paradigms (H+24)]
        G --> K["Setup A: Classical ML <br/> (LGBM, XGBoost, RF, Ridge)"]
        G --> L["Setup B: DL Tabular <br/> (LSTM, CNN-LSTM, GRU, TFT)"]
        J --> M["Setup C: DL Sequence <br/> (PatchTST, LSTM, CNN-LSTM)"]
        
        L:::control
    end

    %% Ensembling & Output
    subgraph Phase4 [Phase 4: Ensembling & Output]
        K --> N["Intra-Paradigm Stacking <br/> (OOF Ridge Meta-Learner)"]
        K -.->|"Champion: LGBM"| O["Cross-Paradigm Grand Ensemble <br/> (Alpha-blended Weighted Average)"]
        M -.->|"Champion: PatchTST"| O
        
        N --> P["H+24 Forecasts & Metrics <br/> (MAE, RMSE, Daily Peak Error)"]
        O --> P
    end

    %% Notes
    Note1["Note: Setup B acts as a Negative Control. <br/> Proving DL fails on non-sequential tabular features."]:::text
    Note1 -.- L
```

---

## Text Blueprint

### Phase 1: Data Preparation
**[Drammen & Oslo Dataset Ingestion]**
      ↓
**[Merge Metadata & Submeters]**
      ↓
**[MICE Imputation]** *(Using `ts.hour` & `ts.month` covariates)*
      ↓
**[Model Ready Data]**

---

### Phase 2: The Paradigm Split
*From `[Model Ready Data]`, the pipeline horizontally forks into two distinct tracks:*

**Track 1: Tabular Features Paradigm**
      ↳ **[Feature Engineering]** *(Lags, Rolling Averages, Cyclical Time)*
            ↓
      ↳ **[Advanced Feature Selection]** *(Variance, Correlation, Importance → Select 35 Features)*

**Track 2: Sequential Raw Paradigm**
      ↳ **[Raw 3D Windowing]** *(72h Lookback of Load, Temp, Solar)*
            ↓
      ↳ **[Feature Scaling]**

---

### Phase 3: Modelling & Evaluation (H+24)

*Track 1 feeds Setup A and Setup B. Track 2 feeds Setup C.*

**[Setup A: Classical ML]** *(Fed by Track 1)*
- LightGBM, XGBoost, Random Forest, Ridge, Lasso
- *Goal: Best engineered-feature baseline.*

**[Setup B: Deep Learning Tabular]** *(Fed by Track 1)*
- LSTM, CNN-LSTM, GRU, TFT
- *Goal: Negative Control (Testing DL on non-sequential tabular features).*

**[Setup C: Deep Learning Sequence]** *(Fed by Track 2)*
- PatchTST, LSTM, CNN-LSTM, GRU
- *Goal: High-latency autonomous representation learning.*

---

### Phase 4: Ensembling & Output

*Two distinct ensembling strategies are employed to respect computational boundaries:*

**[Intra-Paradigm Stacking]**
- **Input:** Predictions from Setup A (LGBM, XGB, RF)
- **Method:** 5-Fold Out-of-Fold (OOF) Stacking
- **Meta-Learner:** Ridge Regression Meta-Model

**[Cross-Paradigm Grand Ensemble]**
- **Input:** [Setup A Champion: LightGBM] + [Setup C Champion: PatchTST]
- **Method:** Alpha-blended Weighted Average Stack

↓

**[Final Output]**
- **[H+24 Point Forecasts]** 
- **[Probabilistic P10/P50/P90 Bounds]** *(Planned)*
- **[Metrics: MAE, RMSE, MAPE, Daily Peak Error]**
