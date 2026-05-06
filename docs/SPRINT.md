# Active Sprint — updated 2026-05-06
# Read this instead of calling list_issues. Cost: ~200 tokens vs ~28k.
# Update at every session end: move completed to Done, pull next items in.

## In Progress
- DAN-49   App Runner deploy — blocked until AWS Activate credits (DAN-69)
- MyEnergi Harvi install (Dan, this week) — enables real-time CT clamp data
- MyEnergi full backfill running on NUC — 2023-01-20 → present (1,202 days, ~24 min total)
  Monitor: ssh dan@192.168.68.119 "docker exec sparc-api tail -5 /tmp/backfill.log"

## Tier 1 — Next to start
- DAN-167  Train Irish household LightGBM model — wire ESB CSV pipeline for Ireland city,
           run scripts/run_pipeline.py, rsync model artefacts to NUC → populates predictions table
           and unblocks Sparc Overview forecast panels
- DAN-156  Morning brief personalisation (07:00 Eddi boost time)
- DAN-153  Generalise plan scoring
- DAN-139  Eddi source split (h1d vs h1b)

## Tier 2 — After Tier 1
- DAN-164 Stream 5  Per-household retraining on myEnergi data (needs 60d production — July+)
- DAN-145  Demand shift recommendation (cheapest 2h window)
- DAN-166  Tank temp inference from Eddi kWh log (improve LP dispatcher initial temp)

## Blocked / External
- DAN-165  Gardening Digital Twin on NUC (InfluxDB 3 Enterprise hobbyist) — instructions drafted; install via Docker Compose: https://docs.influxdata.com/influxdb3/enterprise/admin/license/?t=Docker+compose#activate-a-trial-or-at-home-license
- DAN-66   ESCO registration (Dan)
- DAN-54   BGE contract renewal (Dan, ends 15 Jun 2026)
- BGE Free Saturday panels — will fill in as Saturdays accumulate in myenergi_readings

## Recently Completed
- NUC dashboard comprehensive rebuild — 8 → 20+ panels, 6 sections, textfile collector workaround ✅ 2026-05-06
- NUC dashboard — Technology Stack panel added (TimescaleDB, Redis, cAdvisor workaround note) ✅ 2026-05-06
- Solar Pipeline — Forecast Accuracy Audit section (panels 28–32): GHI MAPE, advisory accuracy %, h1d caveat ✅ 2026-05-06
- SOLAR_ADVISORY_EXPLAINED.md — Forecast Accuracy Audit section added (panels 28–32 walkthrough) ✅ 2026-05-06
- GRAFANA_DASHBOARDS_EXPLAINED.md — NUC section full rewrite + Solar accuracy audit section ✅ 2026-05-06
- Solar Pipeline dashboard — household_id template fix (ORDER BY created_at → onboarded_at DESC) ✅ 2026-05-06
- Solar Pipeline — Tomorrow's Solar Advisory section added (panels 25-27, advisory_log) ✅ 2026-05-06
- LP dispatch switched to BGE retail tariff (was incorrectly using SEMO wholesale SMP) ✅ 2026-05-06
- Morning advisory Pushover manual trigger tested — SKIP_BOOST, GHI=3.63 kWh/m², 9h sun ✅ 2026-05-06
- SOLAR_ADVISORY_EXPLAINED.md updated: 20:00 schedule, seasonality, panel_factor_seasonal, InfluxDB JOIN note ✅ 2026-05-06
- MYENERGI_POLLER_EXPLAINED.md updated: precise NUC backfill procedure with canonical start date ✅ 2026-05-06
- DAN-128  Intel NUC5PGYHR full stack live (9 containers, SSH tunnel, Chrome access) ✅ 2026-05-05
- DAN-163  Migration 005, model_drift_log, check_drift_sunday job, 3 Grafana panels ✅ 2026-05-06
- DAN-152  Migration 007 — household profile cols + panel_factor_seasonal ✅ 2026-05-06
- DAN-164 Stream 1  load_disaggregation.py → src/energy_forecast/features/ ✅ 2026-05-06
- DAN-164 Stream 2  solar_baseline.py → src/energy_forecast/features/, cloud_cover wired ✅ 2026-05-06
- DAN-164 Stream 3  lp_dispatcher.py — BGE tariff pricing, 19 tests, Pushover at 14:30 ✅ 2026-05-06
- DAN-164 Stream 4  SEMOConnector + semo_prices table + migration 006 ✅ 2026-05-06
- ESB data ingested — 34,885 rows (Apr 2024 → Apr 2026) ✅ 2026-05-05
- myEnergi live poll — backfill tested (May 4-5), scheduler running nightly at 23:30 ✅ 2026-05-06
- DAN-159  MyEnergi vs ESB data quality cross-validation (Layers 1+2+5) ✅
- DAN-77   Regression tests for stacking OOF NaN (BUG-01) ✅
- DAN-42   UX_DESIGN_PRINCIPLES.md ✅

## Key Explainers (docs/explainers/)
- DATA_PIPELINE_LIVE_EXPLAINED.md  — full live data pipeline reference
- GRAFANA_DASHBOARDS_EXPLAINED.md  — panel-by-panel guide, blank panel diagnosis
- LP_DISPATCH_EXPLAINED.md         — LP thermal dispatch design, pricing model, tank physics
- SOLAR_ADVISORY_EXPLAINED.md      — morning advisory (20:00), panel_factor_seasonal, InfluxDB vs PG
- MYENERGI_POLLER_EXPLAINED.md     — cgi-jday API, hsk bug, full backfill procedure
