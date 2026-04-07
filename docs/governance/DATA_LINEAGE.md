# Data Lineage — Building Energy Load Forecast
*Author: Dan Alexandru Bujoreanu · Last updated: 2026-03-27 · Version: 1.1*
*Purpose: Trace the complete lifecycle of data from raw source through model inference to physical device action.*
*Standard: Adapted from DAMA DMBOK2 Data Lineage + Google Data Cards.*

---

## Overview

This document maps every transformation step, quality gate, and potential failure point from raw sensor data to a physical control action on a home energy device. It exists to support:
- **Audit readiness** — any model output can be traced back to its source data
- **Debugging** — when a prediction is wrong, this map identifies where in the pipeline the error originated
- **Compliance** — demonstrates data governance required under GDPR and CRU202517

---

## End-to-End Lineage Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 1 — RAW INGESTION                                                │
│                                                                         │
│  COFACTOR CSVs          OpenMeteo API          ESB HDF / Eddi API       │
│  (44 buildings,         (historical weather    (home trial only —       │
│   hourly, Wh)            reanalysis, hourly)    30-min Irish data)       │
│       │                       │                        │                │
│       └───────────────────────┴────────────────────────┘                │
│                               │                                         │
│                     [QUALITY GATE 1 — Schema]                           │
│                     • Timestamp format: "%Y-%m-%dT%H:%M:%S%z"          │
│                     • Timezone: Etc/Gmt-1                               │
│                     • Min completeness: ≥70% non-NaN per building       │
│                     • Column coverage: ≥50% across buildings            │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 2 — NORMALISATION & MERGE                                        │
│                                                                         │
│  src/energy_forecast/data/loader.py                                     │
│                                                                         │
│  • Wh → kWh conversion (÷1000) applied at load time                    │
│  • Weather joined to building data by (timestamp, location)             │
│  • Missing intervals: forward-fill ≤2h gaps; else NaN (excluded later) │
│  • Output: data/processed/{city}/model_ready.parquet                   │
│                                                                         │
│  [QUALITY GATE 2 — Completeness]                                        │
│  • Buildings with <70% data completeness dropped                        │
│  • Drammen: 45 buildings raw → 44 buildings retained                   │
│  • Oslo: 48 buildings all retained                                      │
│                                                                         │
│  ⚠ KNOWN BUG (RESOLVED): proc_dir shared across cities                 │
│    Running Oslo pipeline overwrote Drammen processed data.              │
│    Fix: city-specific paths — data/processed/{city}/                    │
│    Impact: Oslo and Drammen results cannot be conflated.                │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 3 — CHRONOLOGICAL SPLITS                                         │
│                                                                         │
│  src/energy_forecast/data/splits.py → make_splits()                    │
│                                                                         │
│  Drammen split (no overlap, no leakage):                                │
│  • Train: 2018-01-01 → 2020-12-31  (~1.16M rows × 35 features)        │
│  • Val:   2021-01-01 → 2021-06-30  (~188k rows)                        │
│  • Test:  2021-07-01 → 2022-03-18  (~241k rows)  ← never seen in train │
│                                                                         │
│  [QUALITY GATE 3 — Temporal integrity]                                  │
│  • Split boundaries are strictly chronological                          │
│  • No building appears in both train and test                           │
│  • StandardScaler fitted on train only; applied to val/test             │
│    (prevents data leakage via statistics)                               │
│                                                                         │
│  ⚠ GUARD (ACTIVE): src/energy_forecast/features/temporal.py            │
│    AssertionError raised if features.forecast_horizon ≠ sequence.horizon│
│    in config.yaml — prevents silent misconfiguration leakage.           │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 4 — FEATURE ENGINEERING                                          │
│                                                                         │
│  src/energy_forecast/features/temporal.py → build_temporal_features()  │
│                                                                         │
│  Feature categories and their lineage:                                  │
│                                                                         │
│  ┌──────────────────────┬─────────────────────────────────────────┐    │
│  │ Feature              │ Source → Transformation                  │    │
│  ├──────────────────────┼─────────────────────────────────────────┤    │
│  │ hour_sin, hour_cos   │ timestamp → sin/cos(2π·hour/24)         │    │
│  │ dow_sin, dow_cos     │ timestamp → sin/cos(2π·dow/7)           │    │
│  │ month_sin, month_cos │ timestamp → sin/cos(2π·month/12)        │    │
│  │ doy_sin, doy_cos     │ timestamp → sin/cos(2π·doy/365)         │    │
│  │ lag_1h               │ target[t-1]  — H+24: EXCLUDED           │    │
│  │ lag_24h              │ target[t-24] — H+24: EXCLUDED           │    │
│  │ lag_167h             │ target[t-167] — DST-robust prev-day      │    │
│  │ lag_168h             │ target[t-168] — exactly 7 days prior     │    │
│  │ lag_169h             │ target[t-169] — DST-robust prev-day      │    │
│  │ rolling_mean_24h     │ rolling mean over t-24..t-1             │    │
│  │ rolling_std_24h      │ rolling std over t-24..t-1              │    │
│  │ rolling_min/max_24h  │ rolling min/max over t-24..t-1          │    │
│  │ rolling_*_168h       │ same statistics, 168h window            │    │
│  │ temperature          │ OpenMeteo reanalysis, °C                │    │
│  │ solar_radiation      │ OpenMeteo, W/m²                         │    │
│  │ temp × hour_sin      │ interaction term                        │    │
│  │ building_id          │ one-hot encoded integer                 │    │
│  └──────────────────────┴─────────────────────────────────────────┘    │
│                                                                         │
│  Horizon guard — lags < forecast_horizon are zeroed/excluded:          │
│  • H+1:  all lags available (lag_1h r≈0.977 dominant predictor)       │
│  • H+24: lags 1h, 2h, 3h, 24h, 25h, 26h, 48h removed                 │
│          (prevents oracle leakage — model cannot see future target)    │
│                                                                         │
│  Feature selection (post-engineering):                                  │
│  • Variance threshold: 0.0 (remove zero-variance)                      │
│  • Correlation threshold: 0.95 (remove near-duplicates)                │
│  • Top-N by LightGBM importance: N=35                                  │
│                                                                         │
│  ⚠ KNOWN BUG (RESOLVED): build_temporal_features horizon source        │
│    Function was reading horizon from argument, not cfg["features"]      │
│    ["forecast_horizon"]. Risk: mismatched lags vs evaluation horizon.  │
│    Fix: all horizon reading goes through cfg key.                       │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 5 — MODEL TRAINING                                               │
│                                                                         │
│  src/energy_forecast/models/sklearn_models.py                           │
│                                                                         │
│  Primary model: LightGBM (key: "lightgbm" — lowercase)                │
│  Config: n_estimators=500, lr=0.05, max_depth=8, num_leaves=63         │
│  Seed: 42 (reproducible)                                                │
│                                                                         │
│  Training data lineage:                                                 │
│  • Input:  X_train (1.16M × 35), y_train (1.16M,)                     │
│  • Scaler: StandardScaler fitted on X_train → transforms X_val/X_test  │
│  • Output: outputs/models/lightgbm_h24.pkl                             │
│            outputs/models/scaler.pkl                                    │
│                                                                         │
│  [QUALITY GATE 4 — Training integrity]                                  │
│  • OOF gap=168 in stacking to prevent lag_168h boundary leakage        │
│  • TFT NaN rows filtered: finite_mask = ~np.any(np.isnan(preds), axis=1)│
│  • DL OOM guard: batch_size=512 in predict (was causing SIGKILL on MPS)│
│                                                                         │
│  ⚠ KNOWN BUG (RESOLVED): sklearn model keys uppercase                  │
│    Keys must be lowercase: "lightgbm", "xgboost", "ridge"              │
│    Impact: model lookup failure at inference if casing wrong.           │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 6 — INFERENCE                                                    │
│                                                                         │
│  deployment/live_inference.py + deployment/app.py (FastAPI)             │
│                                                                         │
│  Input at inference time:                                               │
│  • Last 168+ hours of building consumption (from smart meter / Eddi)   │
│  • OpenMeteo forecast for next 24h (temperature, solar)                │
│  • Current timestamp (for cyclical encoding)                            │
│                                                                         │
│  Processing:                                                            │
│  1. Same feature engineering as training (no training data seen)        │
│  2. Scaler loaded from outputs/models/scaler.pkl                       │
│     (fitted on train only — prevents train/test leakage)               │
│  3. LightGBM loaded from outputs/models/lightgbm_h24.pkl               │
│  4. Returns: 24-point forecast (kWh/hour) + P10/P50/P90 intervals      │
│                                                                         │
│  [QUALITY GATE 5 — Inference integrity]                                 │
│  • pickle.load() wrapped in try/except — version mismatch = actionable │
│    RuntimeError, not cryptic traceback                                  │
│  • /health endpoint reports real vs mock model status                   │
│  • /control validates target_hours bounds (raises HTTP 400 if empty)   │
│                                                                         │
│  ⚠ KNOWN BUG (RESOLVED): pickle.load() unguarded                       │
│    Model file from different sklearn version caused silent crash.        │
│    Fix: try/except with message "Re-run run_pipeline.py to regenerate" │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 7 — TARIFF OPTIMISATION & CONTROL                                │
│                                                                         │
│  src/energy_forecast/control/controller.py                              │
│  src/energy_forecast/tariff.py (single source of truth for BGE rates)  │
│                                                                         │
│  Input:                                                                 │
│  • 24-hour forecast (kWh/hour) from Stage 6                            │
│  • SEMO/EPEX day-ahead prices (live post-CRU June 2026 mandate)        │
│  • BGE tariff schedule: day/night/peak/free (€/kWh)                   │
│  • User device constraints (comfort hours, max kW, override flags)     │
│                                                                         │
│  Processing:                                                            │
│  1. Identify flexible load windows (hot water, EV, battery)            │
│  2. Score each 30-min slot: forecast load × tariff rate                │
│  3. Shift controllable loads to cheapest slots                         │
│  4. Output: schedule for myenergi Eddi API                             │
│                                                                         │
│  ⚠ KNOWN BUG (RESOLVED): Peak rate logic — all non-Saturday            │
│    Peak rate (49.28c) applies Mon–Fri 17:00–19:00 ONLY.               │
│    Bug: was applying peak rate to all non-Saturday evenings,           │
│    including Sunday. Cost calculation inflated for Sunday peak window. │
│    Fix: weekday() < 5 check in tariff.py rate_slot().                  │
│                                                                         │
│  Tariff data lineage:                                                   │
│  BGE "Free Time Saturday" rates → src/energy_forecast/tariff.py        │
│  (single source of truth, imported by run_home_demo.py + score_home_plan.py)│
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 8 — PHYSICAL ACTION (HOME TRIAL)                                 │
│                                                                         │
│  deployment/connectors.py → myenergi Eddi API                          │
│                                                                         │
│  • POST /cgi-boost-time-E{serial} → sets Eddi boost schedule           │
│  • GET /cgi-jday-E{serial}-{Y}-{MM}-{DD} → logs actual consumption     │
│  • All actions logged to scripts/log_eddi.py                           │
│                                                                         │
│  Feedback loop:                                                         │
│  • Actual consumption (Eddi che field = daily kWh) fed back            │
│  • Compares forecast vs actual for drift detection                     │
│  • Drift trigger: 7d MAE > 1.5× training MAE → triggers retraining    │
│                                                                         │
│  ⚠ KNOWN BUG (RESOLVED): Eddi imp/hsk field misinterpretation          │
│    imp and hsk fields are instantaneous centi-Watts, not cumulative Wh.│
│    Use che field from get_status() for daily total consumption.        │
│                                                                         │
│  ⚠ KNOWN BUG (RESOLVED): log_eddi.py NameError                         │
│    date.today() called but only timezone was imported from datetime.   │
│    Fix: from datetime import date, timezone                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Bug Impact Summary

All bugs identified during development are documented here with their data lineage impact — i.e., at which pipeline stage they would have corrupted results if not caught.

| Bug | Stage affected | Data integrity impact | Status |
|-----|---------------|----------------------|--------|
| `proc_dir` shared across cities | Stage 2 (normalisation) | Oslo run overwrites Drammen processed data — cross-city comparison invalid | ✅ Fixed |
| Peak rate logic (Sundays as peak) | Stage 7 (tariff) | Sunday cost estimates inflated; €/year saving calculations wrong | ✅ Fixed |
| Horizon config source mismatch | Stage 3+4 (splits/features) | Wrong lags included at H+24 — oracle leakage risk; R² artificially inflated | ✅ Fixed |
| sklearn keys uppercase | Stage 5+6 (training/inference) | Model lookup failure; inference returns error or wrong model | ✅ Fixed |
| TFT NaN boundary rows | Stage 5 (training) | NaN predictions from boundary windows corrupt metric calculation | ✅ Fixed |
| DL predict OOM (batch size) | Stage 5 (training) | SIGKILL on Apple MPS; LSTM result unavailable | ✅ Fixed |
| `pickle.load()` unguarded | Stage 6 (inference) | Cryptic crash on sklearn version mismatch; user sees unactionable traceback | ✅ Fixed |
| Eddi `imp`/`hsk` misinterpretation | Stage 8 (action/feedback) | Daily consumption logged as instantaneous centi-Watts; MAE calculation wrong | ✅ Active (documented) |
| `log_eddi.py` NameError | Stage 8 (action/feedback) | `date.today()` fails at runtime; device schedule not logged | ✅ Fixed |

---

## Data Retention and Deletion Policy

| Data | Retention period | Deletion trigger |
|------|-----------------|-----------------|
| COFACTOR/SINTEF raw CSVs | Academic use only — local machine | End of research project |
| Processed parquet files | Indefinite (can regenerate) | Re-run pipeline overwrites |
| Model checkpoints (.pkl) | Rolling — 3 versions retained | Monthly retraining cycle |
| ESB smart meter HDF | Duration of home trial | User request (right to erasure, GDPR Art. 17) |
| Eddi API logs | 90 days rolling | Automatic purge |
| Production user data (future) | 24 months rolling (CRU202517 minimum) | User deactivation + 30 days |

---

## Audit Queries

For any model output, the following questions can be answered from this document:

| Question | Answer |
|---------|--------|
| What buildings contributed to this training run? | 44 Drammen buildings (completeness ≥70%) |
| Was any test data seen during training? | No — strict chronological split, no overlap |
| Was the scaler fitted correctly? | Yes — on X_train only (2018–2020) |
| What weather data source was used? | OpenMeteo reanalysis, non-commercial licence |
| Were oracle features used? | No — lag_1h to lag_48h excluded for H+24 |
| Was the tariff calculation correct? | Yes — peak rate Mon–Fri 17–19 only (bug fixed 2026-03) |
| What device action resulted from this forecast? | Eddi boost schedule, logged to log_eddi.py |

---

## Document Control

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0 | 2026-03-27 | Initial creation | Dan Bujoreanu |
| 1.1 | 2026-03-27 | Added bug impact table, audit queries section | Dan Bujoreanu |

*Update this document when: a new pipeline stage is added, a new data source is integrated, a new bug is found and resolved, or the device integration layer changes.*
