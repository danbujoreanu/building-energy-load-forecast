# Key Results — All Numbers
*Source of truth for all model performance metrics. Do not duplicate in CLAUDE.md.*

---

## Drammen H+24 (test set, 241,523 observations, 44 buildings)

| Setup | Model | MAE (kWh) | RMSE | R² | Train (s) |
|-------|-------|-----------|------|-----|----------|
| **A** | **LightGBM** | **4.029** | **7.445** | **0.9752** | **13** |
| A | XGBoost | 4.197 | 7.662 | 0.9737 | 7 |
| A | Random Forest | 4.402 | 8.376 | 0.9686 | 360 |
| A | Ridge | 7.460 | 12.856 | 0.9261 | <1 |
| B | LSTM | 34.938 | 47.562 | −0.0039 | 2,872 |
| B | CNN-LSTM | 9.375 | 16.744 | 0.8772 | 681 |
| B | TFT | 8.770 | 17.581 | 0.8646 | 5,627 |
| C | PatchTST | 6.955 | 14.118 | 0.9102 | 3,026 |
| Ens-A | Stacking (Ridge) | 4.034 | 7.508 | 0.9751 | 1,059 |
| Base | Mean Baseline | 22.673 | 35.314 | 0.4424 | — |

**Paradigm gap**: LightGBM beats PatchTST by 42% MAE. Ensemble monotonically degrades.

## Oslo H+24 (48 buildings, 779,423 observations)

| Model | MAE (kWh) | R² |
|-------|-----------|-----|
| Stacking | 7.280 | 0.9635 |
| **LightGBM** | **7.415** | **0.9630** |
| PatchTST | 13.616 | 0.8741 |
| Mean Baseline | 45.3 | — |

**Cross-city gap**: PatchTST +84% MAE vs LightGBM on Oslo (wider than +42% on Drammen).

## Probabilistic Forecasting (LightGBM Quantile P10/P50/P90)

| City | P50 MAE | Winkler Score | Coverage | PI Width |
|------|---------|--------------|---------|---------|
| Drammen | 4.072 | 19.457 | 78.3% | 12.737 |
| Oslo | 7.345 | 35.021 | **80.0%** | 23.603 |

## Horizon Sensitivity (Drammen, MAE kWh)

| Model | H+1 | H+6 | H+12 | H+24 | H+48 | Degradation |
|-------|-----|-----|------|------|------|-------------|
| LightGBM | 3.188 | 3.584 | 3.799 | 4.057 | 4.724 | +48% |
| XGBoost | 3.339 | 3.678 | 3.906 | 4.182 | 4.824 | +45% |
| Ridge | 4.301 | 6.306 | 6.883 | 7.487 | 8.447 | +96% |

## Statistical Significance

| Test | Comparison | Statistic | Significance |
|------|-----------|-----------|------|
| Wilcoxon (n=44 buildings) | LightGBM vs Ridge | Cohen's d = −1.52 | p < 0.0001 *** |
| DM HLN-corrected (n=241,393) | LightGBM vs PatchTST | DM = −12.17 | p < 0.0001 *** |
| DM HLN-corrected | LightGBM vs XGBoost | DM = −5.25 | p < 0.0001 *** |
| DM HLN-corrected | LightGBM vs Ridge | DM = −33.52 | p < 0.0001 *** |

## Home Demo (Dan's ESB data)

| Metric | Value |
|--------|-------|
| Model | LightGBM H+24 |
| MAE | 0.171 kWh/hour |
| Data | 2024-03-15 → 2026-03-05, 17,302 hourly rows |
| BGE plan score | 62/100 |
| Annual saving opportunity | €178.65/year |
