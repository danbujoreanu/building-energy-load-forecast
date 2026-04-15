# ADR-003: Oracle-Safe Feature Engineering (Lag ≥ Horizon Enforcement)

**Status:** Accepted
**Date:** 2025-Q4

---

## Context

The system targets H+24 forecasting — predicting electricity load 24 hours ahead. Feature engineering for time-series models typically uses lag features (e.g., `lag_1h`, `lag_2h`, `lag_24h`). A critical correctness issue arises: if a model trained for H+24 prediction includes a `lag_1h` feature, it is using data from 1 hour ago to predict 24 hours ahead — information that would not be available in production at prediction time.

This is **oracle leakage**: using future-relative data to inflate training and evaluation metrics in ways that cannot be reproduced in deployment. A model trained with oracle leakage may show R²=0.98 on a test set but fail to generalise when deployed, because the evaluation was dishonest.

---

## Options Considered

1. **Use all available lags** — simpler code, higher apparent accuracy, but dishonest evaluation
2. **Horizon-based lag floor (chosen)** — only include lags ≥ `forecast_horizon` when `horizon > 1`
3. **Separate feature sets per horizon** — complex, error-prone to maintain

---

## Decision

Enforce `forecast_horizon` as a hard constraint in `features/temporal.py`:
- When `horizon=24`, only lags ≥ 24 hours are included (e.g., `lag_24h`, `lag_48h`, `lag_168h`)
- When `horizon=1`, all lags are available (honest for H+1 single-step-ahead evaluation)
- A config guard assertion prevents `features.forecast_horizon` and `sequence.horizon` from diverging (common misconfiguration source)

This is enforced at the feature-building level, not at model level — making it impossible to accidentally train a "H+24" model with H+1 features.

**In `live_inference.py`** the same constraint is applied via the same `build_temporal_features()` call, ensuring training and inference are feature-identical.

---

## Consequences

**Positive:**
- All published metrics (R²=0.975 Drammen, R²=0.963 Oslo) are honest H+24 evaluations — no oracle inflation
- The config guard catches the most common misconfiguration at runtime rather than silently producing wrong results
- Directly cited in the Model Card (`docs/governance/MODEL_CARD.md`) as a key design decision
- Important differentiator vs many published energy forecasting benchmarks that don't enforce this constraint

**Trade-offs:**
- Reduced feature count for H+24 (lag_1h through lag_23h excluded) — accuracy lower than it would be with oracle features
- The honest trade-off: R²=0.975 (H+24, oracle-free) vs potentially R²=0.99+ (oracle-contaminated) — the former is the publishable, production-valid result
