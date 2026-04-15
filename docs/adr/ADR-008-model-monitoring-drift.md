# ADR-008: Model Monitoring and Drift Detection

**Status:** Accepted
**Date:** 2026-04-13

---

## Context

The LightGBM H+24 model achieves R²=0.975 (Drammen), R²=0.963 (Oslo) on the held-out test set. These are static evaluation numbers from the training period (2016–2022 data). Once deployed, model performance can degrade due to:

1. **Data drift** — input feature distributions shift (climate change, building usage changes, occupancy patterns change)
2. **Concept drift** — the relationship between features and target changes (e.g., post-COVID occupancy patterns differ from pre-COVID training data)
3. **Infrastructure drift** — upstream data sources change format, introduce NaNs, or change update frequency

Without monitoring, performance degradation is invisible until user complaints or anomalous control decisions surface it. For EU AI Act Art. 52 compliance, the system must maintain transparency obligations over time — which implies knowing when model performance has degraded to the point where confidence intervals are no longer reliable.

The evaluation infrastructure (`metrics.py`) already computes MAE, RMSE, MAPE, R² and Daily Peak MAE. The gap is a scheduled drift detection pass that runs against recent actuals and flags anomalies.

---

## Options Considered

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **MLflow Model Registry** | Full MLOps platform: experiment tracking, model versioning, staging/production promotion | Industry standard, rich UI, integrates with most clouds | Significant setup overhead, overkill for single-model single-site deployment |
| **Lightweight drift script** | Python script: load model + recent actuals, compute rolling weekly MAE, compare to baseline, write report | Zero infrastructure, uses existing metrics.py, runs in 2 seconds | No UI, manual review of report file |
| **Evidently AI** | Open-source drift detection library with HTML report generation | Rich statistical tests (PSI, KL-divergence), nice reports | Adds dependency, more than needed for current scale |
| **File-based model registry + drift script** | Date-stamped .joblib files (already in place) + drift script + structured JSON report | Leverages existing pattern, auditable, schedulable via CCR | Requires discipline to maintain naming convention |

---

## Decision

**File-based model registry (already in place) + lightweight drift script (`scripts/monitor_drift.py`).**

Rationale:
- The model registry pattern is already implemented: `outputs/models/drammen_LightGBM_2026-03-05.joblib` — date-stamped, reproducible, one file per training run
- `metrics.py` already computes all required metrics — drift detection is a thin wrapper
- A JSON drift report (`outputs/monitoring/drift_report_YYYY-MM-DD.json`) is auditable and schedulable
- MLflow adds value at scale (multiple models, multiple environments, A/B testing). At current scale (two buildings, one production model), it is infrastructure debt, not infrastructure value. **Re-evaluate when Sparc Energy has 3+ active model versions or adds a second deployment site.**

**Model registry conventions (formalised):**
```
outputs/models/
  {city}_{model}_{YYYY-MM-DD}.joblib     # production models
  {city}_{model}_{YYYY-MM-DD}_p10.joblib # quantile models (ADR-007)
  {city}_{model}_{YYYY-MM-DD}_p90.joblib
```

**Drift thresholds (initial, calibrate after 3 months of live data):**
| Metric | Warning threshold | Critical threshold |
|--------|------------------|-------------------|
| MAE (weekly vs baseline) | +20% | +40% |
| RMSE (weekly vs baseline) | +25% | +50% |
| R² (weekly vs baseline) | -0.05 | -0.10 |

---

## Consequences

**Positive:**
- Model degradation is detected before it affects demand-response control decisions
- EU AI Act Art. 52 transparency: can state "model performance is monitored weekly with automated drift alerts"
- Career talking point: "I implemented drift monitoring as part of MLOps lifecycle management"
- Schedulable via CCR as a weekly task once live data is flowing

**Trade-offs:**
- No UI — drift report is a JSON file, reviewed manually or via the daily-morning-briefing agent
- Statistical sophistication is low (threshold-based, not PSI/KL-divergence) — sufficient for current scale
- Requires actual recent predictions and actuals to be logged; currently the morning brief script (`live_inference.py`) does not persist predictions to a log file

**Required prerequisite:**
Predictions from `live_inference.py` must be persisted to `outputs/monitoring/predictions_log.jsonl` for drift detection to work. Add this logging to `live_inference.py` before enabling drift monitoring.

---

## Related Files
- `scripts/monitor_drift.py` — implementation
- `src/energy_forecast/evaluation/metrics.py` — metrics infrastructure
- `deployment/live_inference.py` — predictions must be logged here first
- `docs/adr/ADR-007-quantile-regression-p10-p90.md` — P10/P90 also need drift monitoring
