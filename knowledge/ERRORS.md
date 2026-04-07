# Known Errors & Bugs
*Deterministic errors → conclude immediately. Infrastructure errors → log, no conclusion until pattern.*
*Conclusions graduate to the relevant domain/procedural file when resolved.*

---

## Active / Watch

| Error | Type | Status | Conclusion |
|-------|------|--------|------------|
| `imp`/`hsk` units in Eddi history API | Deterministic (ambiguity) | OPEN | Fields are instantaneous centi-Watts, not cumulative. Use `che` from `get_status()` for daily total. |
| MEMORY.md 200-line limit | Infrastructure | OPEN | Still 221 lines (over limit). Trim to ≤150 lines — move CRU/commercial detail to topic files. |
| TF Metal SIGKILL on LSTM predict | Deterministic (platform) | CONCLUDED | Apple MPS + gc.collect() invalidates GPU context. Use CPU or subprocess isolation. LSTM H+24 taken from final_metrics. |

---

## Resolved (graduated to domain/procedural files)

| Error | Resolution | Where documented |
|-------|-----------|-----------------|
| `get_history_day()` returning 404 | Wrong URL format. Correct: `/cgi-jday-E{serial}-{Y}-{MM}-{DD}` | `knowledge/procedural/EDDI_API.md` |
| `get_schedule()` wrong key (`dow` vs `bdd`) | `bdd` is 8-char string, not int bitmask. Position 0 unused, 1–7 = Mon–Sun | `knowledge/procedural/EDDI_API.md` |
| proc_dir shared across cities | Drammen and Oslo both wrote to `data/processed/`. Fixed to `data/processed/{city}/` | `CLAUDE.md` critical bugs |
| Peak rate logic — all non-Saturday | Peak is Mon–Fri 17–19 ONLY. Saturday not peak regardless. | `knowledge/domain/TARIFF.md` |
| sklearn model keys uppercase | Keys are lowercase: `lightgbm`, `xgboost`, `ridge` | `CLAUDE.md` critical bugs |
| TFT NaN boundary rows | `finite_mask = ~np.any(np.isnan(preds), axis=1)` | `src/energy_forecast/models/tft.py` |
| DL batch predict OOM | `batch_size=512` in `model_.predict()` insufficient on MPS. Use `_chunked_predict()` | `src/energy_forecast/models/deep_learning.py` |
| LSTM Setup B R² = −0.004 | Not a bug — expected: DL cannot extract structure from pre-computed tabular stats | Paper Section 4.2, Table 1 |
| `build_temporal_features` horizon source | Reads from `cfg["features"]["forecast_horizon"]` not argument | `src/energy_forecast/features/temporal.py` |
| `date` not imported in `log_eddi.py` (line 158) | `from datetime import date, timezone` — both imports required | Session 36 fix |
| `MOCK_SOLAR_24H` duplicated in app.py + live_inference.py | Moved to `deployment/mock_data.py` — single source of truth | `deployment/mock_data.py` |
| `pickle.load()` no error handling in live_inference.py | Wrapped in try/except — raises RuntimeError with actionable message | `deployment/live_inference.py` |
| BGE tariff rates duplicated across 2 scripts | Moved to `src/energy_forecast/tariff.py` — all scripts import from there | `src/energy_forecast/tariff.py` |
| `features.forecast_horizon` / `sequence.horizon` no guard | Added AssertionError in `temporal.py` — catches config mismatch before training | `src/energy_forecast/features/temporal.py` |
| MODEL_CARD code example — wrong function signature | `horizon=24` → correct `build_temporal_features(df, cfg, target)` + scaler step | `docs/governance/MODEL_CARD.md` |

---

## Infrastructure Errors (log, no conclusion yet)

| Error | Occurrences | Last seen | Pattern? |
|-------|-------------|-----------|---------|
| Open-Meteo timeout | ~3 sessions | 2026-03-14 | Retry with 15s timeout resolves it. No systemic issue. |
| Eddi API auth failure (429) | 0 confirmed | — | Not yet observed |
