# ADR-001: LightGBM as Primary H+24 Forecasting Model

**Status:** Accepted
**Date:** 2025-Q4 (MSc AI thesis phase)

---

## Context

The system needed a model capable of accurate 24-hour-ahead electricity load forecasting across a multi-building panel of Norwegian public buildings (Drammen and Oslo datasets, ~6,000+ hourly records per building). The model had to:
- Generalise from training to unseen buildings and time periods
- Run inference fast enough for a real-time API (sub-second per request)
- Produce interpretable outputs for the governance artefacts (EU AI Act, AIIA, Model Card)
- Be deployable without GPU infrastructure

---

## Options Considered

| Model | Accuracy | Speed | Interpretability | GPU required | Notes |
|-------|----------|-------|-----------------|-------------|-------|
| **LightGBM** | High (R²=0.975) | Very fast | High (SHAP) | No | Candidate |
| XGBoost | Similar to LGBM | Fast | High (SHAP) | No | Near-identical accuracy to LGBM in experiments |
| Random Forest | Lower | Slow at inference | Medium | No | Weaker on tabular with strong lag features |
| TFT (Temporal Fusion Transformer) | Highest on long sequences | Slow (O(n·T²·H)) | Medium (attention weights) | Yes (practical) | Architecture mismatch: quadratic attention at lookback=72 |
| GRU / LSTM | Medium | Medium | Low | Preferred | Sequential dependency doesn't align with parallel multi-output setup |
| Linear Regression | Low | Very fast | Very high | No | Underfits non-linear load patterns |

---

## Decision

**LightGBM** as the primary model, with XGBoost retained as a base learner for the stacking ensemble (ADR-002).

**Reasons:**
1. **Best accuracy for the tabular feature regime:** The 35-feature engineered vector (lag, rolling, cyclical, interaction features) plays to LightGBM's strengths. Feature engineering encodes the domain knowledge; LightGBM exploits it efficiently.
2. **SHAP compatibility:** Native LightGBM SHAP values enable the explainability layer in `evaluation/explainability.py` — directly used in the Model Card and AIIA governance docs.
3. **Production-ready inference:** Models serialise to small `.joblib` files (~50KB). No GPU, no runtime dependencies beyond `lightgbm`. Suitable for a lightweight FastAPI container.
4. **No oracle leakage by design:** LightGBM on engineered lag features with `forecast_horizon=24` is a clean H+24 setup. TFT would have required additional sequence masking complexity to achieve the same guarantee.

---

## Consequences

**Positive:**
- R²=0.975 (Drammen), R²=0.963 (Oslo) — strong generalisation
- SHAP explainability available throughout the governance documentation
- Fast training: full pipeline runs in minutes on CPU
- Easy deployment: single `.joblib` file

**Trade-offs:**
- Loses deep learning's automatic sequence representation — mitigated by thorough lag/rolling feature engineering
- TFT runs in `models/tft.py` as a comparison model and is included in the grand ensemble, but is not production-primary due to compute cost and OOF infeasibility (see ADR-002)
- Multi-output (all 24 horizons from a single call) is implemented via `MultiOutputRegressor` — adds inference overhead vs direct multi-output; acceptable at this scale
