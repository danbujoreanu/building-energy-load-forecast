# ADR-002: Stacking Ensemble with Out-of-Fold (OOF) Meta-Features

**Status:** Accepted
**Date:** 2025-Q4

---

## Context

With multiple base models available (LightGBM, XGBoost, Ridge, Random Forest, TFT, GRU), a strategy was needed to combine their predictions. Naive averaging discards information about the relative reliability of each model on different sub-problems. The meta-learner approach allows the system to learn the optimal blend empirically.

The central challenge: how to generate meta-features (base model predictions used to train the meta-learner) without introducing leakage from the validation set into the training of the meta-learner.

---

## Options Considered

| Approach | Leakage risk | Compute cost | Accuracy |
|----------|-------------|-------------|----------|
| Simple average | None | None | Moderate |
| Inverse-MAE weighted average | Low (val set used only for weights) | Low | Good |
| Stacking with fixed validation | Medium (meta-learner sees val-set predictions as training data) | Low | Good |
| **Stacking with OOF (5 folds)** | Low (each fold's val never used to train its own base model) | Medium | Best |
| Stacking with OOF including DL models | Low | Very high (infeasible on CPU) | Highest |

---

## Decision

**Two-tier ensemble approach:**

1. **Intra-paradigm stacking (Setup A — tree models):** `StackingEnsemble` with 5-fold `TimeSeriesSplit` OOF, Ridge meta-learner. Only applies to sklearn-compatible models (LightGBM, XGBoost, Ridge, Random Forest) because they can be cloned and retrained per fold cheaply.

2. **Cross-paradigm grand ensemble (Setup A + C):** `WeightedAverageEnsemble` (inverse-MAE) blends tree ensemble predictions with deep learning predictions (TFT, GRU). Alpha-blending (e.g. 0.9 Setup A + 0.1 Setup C) establishes the trust spectrum between domain-engineered tabular features and raw sequence representations.

**Key implementation details:**
- `TimeSeriesSplit(n_splits=5, gap=168)` — the 168-hour gap prevents boundary leakage from lag_168h and rolling_168h features (which are correlated with the first 168 hours of each validation fold's training window)
- OOF fitting passes only `(X_fold_tr, y_fold_tr)` to base models — never the validation fold. This prevents LightGBM/XGBoost early-stopping from being calibrated on the exact fold being predicted (BUG-C6, documented in `ensemble.py`)
- DL models excluded from OOF stacking — they cannot be efficiently cloned and retrained 5x on CPU

---

## Consequences

**Positive:**
- Ridge meta-learner learns true complementarity between LightGBM and XGBoost on unseen data
- OOF removes meta-leakage: the meta-learner trains on predictions the base models made on data they had not seen during their own training
- Gap=168h handles the temporal correlation at fold boundaries cleanly

**Trade-offs:**
- 5 OOF folds × N base models = N additional training runs. Acceptable for fast tree models, infeasible for DL
- First fold's training rows are never in any validation set (~17% of training data excluded from OOF coverage) — standard OOF practice, documented in `ensemble.py`
- WeightedAverageEnsemble for cross-paradigm blending is less theoretically rigorous than full stacking, but mathematically necessary given compute constraints
