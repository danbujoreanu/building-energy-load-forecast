# Experiment Status & Tidy-Up Summary

## 1. Paradigm Status (H+24 Day-Ahead)

| Setup | Paradigm | Models Completed | Models Pending | Goal |
| :--- | :--- | :--- | :--- | :--- |
| **Setup A** | Classical ML + Features | LightGBM, XGB, RF, Ridge, Lasso | None | Best engineered-feature baseline |
| **Setup B** | DL + Features | LSTM | CNN-LSTM, GRU, TFT | Best deep representation with engineered features |
| **Setup C** | DL + Raw Sequences | PatchTST | None | High-latency sequential learning |
| **Ensemble** | Cross-Paradigm | A + C | None | Testing if features + sequences > either |

## 2. Champion Comparison (H+24 MAE)
*Evaluation performed on consistent 2024 test split*

| Model Family | Setup | MAE | R² | Note |
| :--- | :--- | :--- | :--- | :--- |
| **LightGBM** | Setup A | **4.054** | **0.9754** | **Current Project Champion** |
| Grand Ensemble | A + C | 4.106 | 0.9749 | Weighted (0.9 LGBM / 0.1 PatchTST) |
| PatchTST | Setup C | 6.921 | 0.9118 | State-of-the-art Transformer |

## 3. The Grand Ensemble Strategy
The Grand Ensemble is a **Weighted Average** stack between the champion of Setup A (LightGBM) and Setup C (PatchTST).
- **Finding:** Currently, simple ensembling does not outperform Setup A alone.
- **Hypothesis:** The explicit domain knowledge in Setup A features (lags, rolling averages) is more robust for the H+24 point forecast task than the current implicit representations in PatchTST.

## 4. Engineering Stewardship & Execution Plan
To ensure system stability and scientific rigour:
1. **SEQUENTIAL DL RUNS:** We are running Setup B models (CNN-LSTM, GRU, TFT) one at a time.
2. **STRICT ENVIRONMENT:** All processes use `ml_lab1` specifically to avoid dependency conflicts.
3. **LOG CLEANLINESS:** Removed verbose epoch logs in favor of high-level status reporting.

## 5. Pending Tasks
1. 🔄 **Finish Setup B Sequential Run:** CNN-LSTM, GRU, and TFT (Running in background).
2. 🔄 **Update Master Comparison Table:** Populate the final results in README.md once Setup B finishes.
3. 🔄 **Oslo Generalization:** Final step to prove the pipeline works across different climates/datasets.
