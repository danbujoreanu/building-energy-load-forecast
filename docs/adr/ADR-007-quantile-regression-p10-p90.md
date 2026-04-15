# ADR-007: Quantile Regression for P10/P50/P90 Confidence Intervals

**Status:** Accepted
**Date:** 2026-04-13

---

## Context

The system produces point forecasts (R²=0.975, Drammen; R²=0.963, Oslo). EU AI Act Art. 52 requires transparency obligations for Limited Risk AI systems — specifically, that users can assess confidence and exercise override. A point forecast alone does not satisfy this: a building manager needs to know not just "forecast: 42 kWh at 14:00" but also the range of plausible outcomes.

Additionally, demand-response scheduling decisions are cost-asymmetric: the cost of incorrectly deferring heating when demand turns out high (occupant discomfort) differs from the cost of not deferring when demand is low (missed saving). P10/P50/P90 intervals allow the ControlEngine to use risk-appropriate thresholds for different action types.

---

## Options Considered

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **Bootstrap ensemble** | Re-run model N times with resampled training data, report percentiles | Model-agnostic, honest uncertainty | 10–50× inference cost, not deterministic |
| **Conformal prediction** | Post-hoc calibrated intervals using held-out calibration set | Distribution-free guarantees, rigorous | Requires separate calibration set, complex wiring |
| **LightGBM native quantile regression** | Train 3 separate models: `objective='quantile'`, `alpha=[0.1, 0.5, 0.9]` | Simple, fast, no extra infrastructure, same feature set | Intervals not guaranteed to be calibrated; no crossing constraints by default |
| **Gaussian process** | Principled uncertainty, closed-form | Correct posterior | O(n³) scaling — infeasible at 35K+ row training set |

---

## Decision

**LightGBM native quantile regression with 3 parallel models (P10, P50, P90).**

**Reasoning:**
- Training three LightGBM quantile models is trivial given the existing training pipeline — add `alpha` parameter sweep to `scripts/run_pipeline.py`
- Inference cost is 3× single model — acceptable (sub-second at demo scale)
- Same 35-feature vector as the point forecast model — no feature engineering changes
- P50 quantile model output is directly comparable to the existing point forecast as a sanity check
- Sufficient for EU AI Act Art. 52 transparency display and for ControlEngine risk thresholds

**Implementation:**
```python
# In src/energy_forecast/models/lightgbm_model.py — add quantile variants:
QUANTILE_MODELS = {
    'p10': LGBMRegressor(objective='quantile', alpha=0.1, **base_params),
    'p50': LGBMRegressor(objective='quantile', alpha=0.5, **base_params),
    'p90': LGBMRegressor(objective='quantile', alpha=0.9, **base_params),
}

# Training: fit all 3 on same X_train, y_train
# Inference: return {'p10': pred_p10, 'p50': pred_p50, 'p90': pred_p90}
```

**Interval crossing prevention:** LightGBM quantile models can produce P90 < P50 on individual samples. Apply post-hoc monotonicity correction:
```python
p10 = np.minimum(p10, p50)
p90 = np.maximum(p90, p50)
```

**Display rule (EU AI Act compliance):** All user-facing outputs must show P10/P50/P90. Point forecast alone is not compliant for Art. 52. This is enforced in `deployment/app.py` — the `/predict` endpoint always returns all three.

---

## Consequences

**Positive:**
- EU AI Act Art. 52 transparency obligation satisfied — confidence ranges displayed at all times
- ControlEngine can use P90 for conservative scheduling (never defer if P90 > threshold) and P10 for aggressive scheduling
- Journal paper differentiator — Applied Energy reviewers reward uncertainty quantification
- Governance talking point: "We classify as Limited Risk under Art. 52 and display P10/P90 with every forecast"

**Trade-offs:**
- 3× training and inference compute — acceptable
- P10/P50/P90 from quantile regression are not statistically calibrated (i.e., 90% of actuals may not fall within P10–P90). For production, consider adding a conformal calibration step post-training
- P50 quantile model will have slightly different error characteristics than the original point forecast (MAE-optimal vs MSE-optimal). Keep both in evaluation outputs

**Future work:**
- If Sparc Energy applies for EI HPSU or seeks regulated deployment, upgrade to conformal prediction for statistically guaranteed coverage
- Consider adding a coverage metric to the evaluation dashboard: `empirical_coverage(P10, P90, y_actual)` — target ≥ 80%
