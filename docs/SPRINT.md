# Active Sprint — updated 2026-05-06
# Read this instead of calling list_issues. Cost: ~200 tokens vs ~28k.
# Update at every session end: move completed to Done, pull next items in.

## In Progress
- DAN-163  Drift monitoring Phase 1 — ✅ migration 005, model_drift_log, scheduler job, 3 Grafana panels
- DAN-164  Intelligence layer — Stream 1 (load disagg) ✅, Stream 2 (solar baseline) ✅
            Stream 4 (SEMO prices) 📋 next, Stream 3 (LP dispatch) blocked on Stream 4
- DAN-49   App Runner deploy — blocked until AWS Activate credits (DAN-69)

## Tier 1 — Next to start
- DAN-164 Stream 4  SEMO price feed — SEMOConnector.get_day_ahead_prices(), migration 006
- DAN-152  Household profile schema (has_ev, has_heat_pump, etc.)
- DAN-156  Morning brief personalisation (07:00 Eddi boost)

## Tier 2 — After Tier 1
- DAN-164 Stream 3  LP thermal dispatch — wire LPThermalDispatcher (blocked: needs Stream 4)
- DAN-164 Stream 5  Per-household retraining (needs 60d production data — July+)
- DAN-153  Generalise plan scoring
- DAN-139  Eddi source split (h1d vs h1b)
- DAN-145  Demand shift recommendation (cheapest 2h window)

## Blocked / External
- DAN-165  Gardening Digital Twin on NUC (InfluxDB 3.x) — awaiting InfluxDB webinar
- DAN-66   ESCO registration (Dan)
- DAN-54   BGE contract renewal (Dan, ends 15 Jun 2026)
- MyEnergi Harvi install (Dan, this week) — enables real-time CT clamp data

## Recently Completed
- DAN-128  Intel NUC5PGYHR full stack live (9 containers, SSH tunnel, Chrome access) ✅ 2026-05-05
- DAN-163  Migration 005, model_drift_log, check_drift_sunday job, 3 Grafana panels ✅ 2026-05-06
- DAN-164 Stream 1  load_disaggregation.py → src/energy_forecast/features/ ✅ 2026-05-06
- DAN-164 Stream 2  solar_baseline.py → src/energy_forecast/features/, cloud_cover wired ✅ 2026-05-06
- ESB data ingested — 34,885 rows (Apr 2024 → Apr 2026) ✅ 2026-05-05
- myEnergi live poll — 19 slots captured today, 24 GHI actuals, scheduler running ✅ 2026-05-06
- DAN-159  MyEnergi vs ESB data quality cross-validation (Layers 1+2+5) ✅
- DAN-77   Regression tests for stacking OOF NaN (BUG-01) ✅
- DAN-42   UX_DESIGN_PRINCIPLES.md ✅
