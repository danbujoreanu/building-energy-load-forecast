# ADR-010: LightGBM-only Production Model — Stacking Ensemble Non-complementarity

**Status:** Accepted
**Date:** 2026-03-15 (Session 30)

---

## Context

The full research pipeline trains five or more model variants: LightGBM, XGBoost, Random Forest, Ridge (Setup A — tree/linear models with engineered features), plus LSTM, GRU, CNN-LSTM, TFT (Setup B — deep learning with engineered features), and PatchTST (Setup C — deep learning on raw sequences). A stacking ensemble (Ridge meta-learner over LightGBM + XGBoost + Ridge base models with out-of-fold predictions) is also trained.

Choosing the production deployment model required weighing accuracy margin, inference cost, operational complexity, hardware requirements, model artifact size, runtime dependency footprint, and fit with the Irish residential use case. Maintaining multiple model types in production would require versioning multiple large artifacts, multiple runtime environments (PyTorch, TensorFlow, scikit-learn), and more complex A/B testing infrastructure — all of which add risk and cost disproportionate to any marginal accuracy gain.

---

## Options Considered

| Option | Test MAE (Drammen H+24) | R² | Notes |
|--------|------------------------|----|-------|
| **LightGBM** | **4.029 kWh** | **0.9752** | Fast inference (~2ms), no GPU, ~50KB artifact |
| Stacking Ensemble (Ridge meta) | 4.034 kWh | 0.9751 | +0.5 MAE margin (negligible), 10× complexity: 3 base models + meta-learner |
| LightGBM_Quantile | P50 ≈ 4.029 kWh | — | Parallel to point model; used for P10/P50/P90 risk-MPC output |
| LSTM / GRU | ~5.0 kWh (H+24) | ~0.96 | Requires GPU for practical training; lower accuracy than trees on tabular features |
| TFT (Setup B) | 8.770 kWh | 0.8646 | Highest compute cost (5,627s training); best suited to long raw sequences, not engineered features |
| PatchTST (Setup C) | 6.955 kWh | 0.9102 | Raw-sequence DL; +72% MAE vs LightGBM on Drammen, +84% on Oslo |
| Mean Baseline | 22.673 kWh | 0.4424 | Reference only |

---

## Decision

**LightGBM as the sole production model for H+24 inference.** LightGBM_Quantile is run in parallel to provide P10/P50/P90 prediction intervals for risk-aware scheduling (see ADR-007), but is not a separate deployment model — it shares the same feature pipeline and is served from the same FastAPI endpoint.

---

## Reasons

1. **Marginal ensemble gain is negligible at this scale.** The stacking ensemble achieves 4.034 kWh MAE vs LightGBM's 4.029 kWh — a difference of 0.005 kWh (0.1%). This does not justify maintaining out-of-fold meta-learner infrastructure, additional inference latency, and the need to version and load three base-model artifacts plus a meta-learner simultaneously in production.

2. **Deep learning models are outperformed by trees on this tabular feature regime.** This is consistent with Grinsztajn et al. (NeurIPS 2022), who show that tree ensembles outperform DL on tabular data, particularly when features are rotationally non-invariant (as lag and rolling statistics are). Moosbrugger et al. (2025, arXiv:2501.05000) additionally confirm that DL offers no advantage with fewer than six months of building-level training data — a common scenario for Irish residential cold-start. PatchTST's +72% MAE disadvantage on Drammen and +84% on Oslo confirms both findings empirically.

3. **Single-file deployment with minimal runtime dependencies.** The LightGBM production artifact serialises to a `.joblib` file of approximately 50KB. The production Docker image requires only `lightgbm`, `scikit-learn`, and `fastapi` — no PyTorch, no TensorFlow, no GPU driver. This dramatically reduces container build time, image size, attack surface, and cold-start latency on AWS App Runner.

4. **Cross-city generalisation confirmed.** Oslo test results (R²=0.963) confirm that LightGBM's paradigm advantage transfers across cities. The model is not overfitted to Drammen's specific buildings or climate. The DM test versus PatchTST (statistic = −12.17, p < 0.0001) is statistically significant at the full test-set level, not just on mean metrics.

---

## Consequences

**In-scope (production):**
- `deployment/live_inference.py` loads only the LightGBM artifact. No DL runtime is present in the production container.
- Monthly retrain cadence (rolling 24-month window) applies to LightGBM only. Drift trigger: 7-day MAE exceeds 1.5× training MAE.
- The H+1 real-time inference path also uses LightGBM — with full lag features available at H+1, no separate model is needed.
- LightGBM_Quantile (P10/P50/P90) is trained alongside the point model and served from the same endpoint for risk-MPC use cases (ADR-007).

**Out-of-scope (research only):**
- Ensemble and DL models remain in `scripts/run_pipeline.py` as research comparison models. They are not removed from the codebase — they are excluded from production serving only.
- DL models are retrained ad-hoc for research purposes (e.g., updating the journal paper benchmarks). They are not part of the monthly retrain cadence.
- TFT and PatchTST artifacts in `outputs/models/` are retained for reference and reproducibility but are never loaded by the live inference path.

**Risk acknowledged:**
If LightGBM's tabular feature advantage erodes as training data grows (e.g., multi-year Irish residential corpus at scale), this decision should be revisited. The comparison pipeline infrastructure is preserved in `scripts/run_pipeline.py` to make re-evaluation straightforward.
