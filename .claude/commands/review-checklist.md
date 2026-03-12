# Review Checklist — Energy Forecast Pipeline

## Two-Pass Structure

**Pass 1 (CRITICAL — blocks deployment):** Data Leakage, Model Trust Boundary
**Pass 2 (INFORMATIONAL — noted in PR body):** Everything else

Output format: `[file:line] Problem. Fix: suggestion.`
Be terse. One problem line, one fix line. No preamble.

---

## Pass 1 — CRITICAL

### Data Leakage & Feature Safety
*(Most dangerous failure mode — causes silent result inflation)*

- `shift(1)` missing before any rolling window on target variable (would use future values)
- Scaler `fit()` called on anything other than the training split
  (inference must use `joblib.load(scaler_path)`, never re-fit)
- Lag features with offset < `forecast_horizon` used in H+24 evaluation
  (`lag_1h` through `lag_23h` must be excluded when `forecast_horizon=24`)
- OOF stacking: `gap` parameter < 168 in `TimeSeriesSplit`
  (lag_168h boundary leakage if gap < 168)
- `fit_transform()` used where `transform()` is correct on val/test data
- Any feature derived from `y_true` accessible at prediction time

### Model Trust Boundary
*(User/external input reaching model without validation)*

- Raw API request fields passed to `build_temporal_features()` without type coercion
- `building_id` from request body used in file path construction without sanitisation
  (`outputs/models/{building_id}.joblib` — path traversal risk)
- Feature count not validated before predict:
  expected `n_features_lgbm: 35` — mismatch should raise `ValueError`, not silently predict
- `city` parameter from request accepted without allowlist check
  (only valid: `drammen`, `oslo` — anything else should 400)

---

## Pass 2 — INFORMATIONAL

### Concurrent Inference Safety
- Shared mutable state in `ControlEngine` instance across `/control` requests
  (threshold attributes modified per-request would be a race condition)
- `model` loaded at module import vs per-request
  (module-level load is correct — flag if changed to per-request)
- `MockDeviceConnector.command_log` is a list appended per request
  (acceptable for demo; flag if moved to production without a lock)

### Config Coupling & Magic Numbers
- Any numeric literal that should come from `config/config.yaml`
  (e.g. `35`, `0.95`, `168`, `24` hardcoded in source — use `cfg['n_features_lgbm']` etc.)
- `solar_threshold=150`, `price_peak=0.28`, `price_offpeak=0.16`, `demand_headroom=80.0`
  in `ControlEngine.__init__` are intentional defaults — do NOT flag these as magic numbers
  unless they appear hardcoded *outside* of the constructor default

### Dead Code & Consistency
- Variables assigned but never read
- `predict=False` removed from TFT config (was a confirmed bug fix — do NOT revert)
- `infer_datetime_format=True` reintroduced to `loader.py` (removed in BUG-C4 — do NOT revert)
- `city=""` param removed from `metrics.evaluate()` (additive, backward-compatible — do NOT flag)
- Comments describing old behaviour after code changed (e.g. references to 13 features
  when the pipeline now uses 35)

### Time Window Safety
*(H+24 horizon boundary is easy to break silently)*

- `_build_y_true_matrix()` returning 1D array instead of 2D `(n_samples, 24)`
  for H+24 evaluation (was BUG-DL-H24 — if re-introduced, CRITICAL)
- `forecast_horizon` in config used inconsistently between feature builder and evaluator
- Oslo generalisation: training on Drammen scaler applied to Oslo features
  (correct behaviour — flag only if a new Oslo scaler is accidentally fit)

### API Boundary Safety
- `/predict` endpoint returning raw numpy arrays (must be serialised to list before JSON)
- HTTP 500 returned for known error conditions (should be 400 for bad input, 501 for stubs)
- `NotImplementedError` raised from `EcowittConnector`, `SEMOConnector`, `MyEnergiConnector`
  reaching the API response as a 500 — these should be caught and return 501 Not Implemented

### Test Gaps
- New connector or model file without a corresponding test in `tests/`
- Edge cases not covered: empty DataFrame, single building, NaN-heavy input,
  `forecast_horizon=1` with H+24 pipeline
- New `/control` logic branch without a test asserting the `ControlAction.action` type

---

## Gate Classification

```
CRITICAL (blocks deployment):        INFORMATIONAL (in PR body):
├─ Data Leakage & Feature Safety     ├─ Concurrent Inference Safety
└─ Model Trust Boundary              ├─ Config Coupling & Magic Numbers
                                     ├─ Dead Code & Consistency
                                     ├─ Time Window Safety
                                     ├─ API Boundary Safety
                                     └─ Test Gaps
```

---

## Suppressions — DO NOT flag these

- `±15% P10/P90 heuristic` in `live_inference.py` — known placeholder, tracked in ROADMAP
- `NotImplementedError` in stub connectors (Ecowitt, SEMO, MyEnergi) — intentional stubs
- `MockDeviceConnector`, `MockPriceConnector` used in dry-run — correct for demo mode
- `accelerator="auto"` in TFT config — intentional Metal GPU compatibility fix
- `min_delta=1.0` in EarlyStopping — intentional Metal GPU hang prevention
- Anything already in the diff being reviewed — read the FULL diff before commenting
- `city=""` default in `metrics.evaluate()` — additive, backward-compatible, intentional
