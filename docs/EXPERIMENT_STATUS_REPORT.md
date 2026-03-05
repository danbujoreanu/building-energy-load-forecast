# Experiment Status & Tidy-Up Summary

## 1. Paradigm Status (H+24 Day-Ahead)

| Setup | Paradigm | Models Completed | Models Pending | Goal |
| :--- | :--- | :--- | :--- | :--- |
| **Setup A** | Classical ML + Features | LightGBM, XGB, RF, Ridge, Lasso | None | Best engineered-feature baseline |
| **Setup B** | DL + Features | LSTM, CNN-LSTM, GRU | TFT (Running) | **Negative Control:** Prove DL fails on tabular features |
| **Setup C** | DL + Raw Sequences | PatchTST | None | High-latency sequential representation learning |
| **Ensemble** | Cross-Paradigm | A + C | None | Testing if representation (C) + tabular signal (A) is optimal |

## 2. Champion Comparison (H+24 MAE)
*Evaluation performed on consistent 2024 test split*

| Model Family | Setup | MAE | R² | Note |
| :--- | :--- | :--- | :--- | :--- |
| **LightGBM** | Setup A | **4.054** | **0.9754** | **Current Project Champion** |
| Grand Ensemble | A + C | 4.106 | 0.9749 | Weighted Stack (0.9 LGBM / 0.1 PatchTST) |
| PatchTST | Setup C | 6.921 | 0.9118 | State-of-the-art Sequence Transformer |

## 3. The Grand Ensemble Strategy
The Grand Ensemble is an **Alpha-Blended Weighted Stack** between the champion of Setup A (LightGBM) and Setup C (PatchTST). Out-of-Fold (OOF) Stacking was correctly reserved strictly for Setup A (Intra-Paradigm), as building OOF folds for models like PatchTST is computationally infeasible. Let me know if you would like me to tune the alpha hyperparameter dynamically or if the static weights used perfectly demonstrated the trust spectrum.
- **Finding:** Currently, simple ensembling does not outperform Setup A alone.
- **Hypothesis:** The explicit domain knowledge in Setup A features (lags, rolling averages) is more robust for the H+24 point forecast task than the current implicit representations in PatchTST.

## 4. Pending Tasks
1. 🔄 **Finish Setup B Sequential Run:** The final "Negative Control" model, TFT, is currently epoching.
2. ✅ **Category-Level Analytics:** `analyze_building_types.py` generated `category_level_metrics.csv` to prove Drammen Schools' performance (Targeting Reviewer 2).
3. 🔄 **Migration Tidy-Up:** Move `lightning_logs` and outputs from `Thesis WIP 2026/` to `building-energy-load-forecast/` when TFT releases its file lock.
4. 🔄 **Oslo Generalization:** Final experiment to prove model climate/building transferability using the new category grouping.
