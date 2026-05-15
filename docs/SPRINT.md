# Active Sprint — updated 2026-05-15
# Read this instead of calling list_issues. Cost: ~200 tokens vs ~28k.
# Update at every session end: move completed to Done, pull next items in.

## In Progress
- DAN-49   App Runner deploy — blocked until AWS Activate credits (DAN-69)
- DAN-168  Harvi CT install (Dan, this weekend May 10) — P0, fixes 50/50 solar split bug
- DAN-169  Irish training data strategy — ADR-013 written; using Norwegian model + Irish calendar features (CER data ruled out — no heat pumps 2009–2010). Unblocks DAN-167.

## Tier 1 — Next to start
- DAN-167  Build forecast accuracy evaluation pipeline — GHI + load forecast vs actuals
           (renamed from "Train Irish model" — ADR-013). Panels 28–32 ready ~May 21 when
           advisory_log hits 14 days. Norwegian model + Irish calendar = immediate path.
- Grafana accuracy panels 28–32 — build once advisory_log ≥ 14 paired rows (~May 21)
- DAN-171  Advisory scheduler + threshold overhaul [merged DAN-145, DAN-156]:
           (a) Fix APScheduler timezone: CronTrigger(hour=20, minute=0, timezone=_DUBLIN) — fires 21:00 Dublin in BST, should be 20:00
           (b) Open-Meteo 502 resilience: retry × 2 with backoff; fallback Pushover on persistent failure
           (c) Replace peak_hours threshold (SKIP_BOOST_THRESHOLD=5) with est_solar vs TANK_DAILY_KWH — seasonal by design
           (d) Investigate Saturday SKIP_BOOST push: scheduler failed with 502; push came from unknown source (n8n workflow?)
           (e) Review full alert taxonomy: FREE_SATURDAY / SKIP_BOOST / PARTIAL / KEEP_BOOST + future peak-avoidance + night-window alerts
- DAN-153  Generalise plan scoring

## Tier 2 — After Tier 1
- DAN-164 Stream 5  Per-household retraining on myEnergi data (needs 60d production — July+)
- DAN-145  Demand shift recommendation (cheapest 2h window) → merged into DAN-171(e)
- DAN-166  Tank temp inference from Eddi kWh log (improve LP dispatcher initial temp)
- Grafana 13 upgrade — next dashboard sprint (docker image tag change, check breaking changes)
- CRO company registration — register Ltd, apply EI Innovation Voucher (post-thesis)

## Blocked / External
- DAN-165  Gardening Digital Twin on NUC (InfluxDB 3 Enterprise hobbyist) — instructions drafted; install via Docker Compose: https://docs.influxdata.com/influxdb3/enterprise/admin/license/?t=Docker+compose#activate-a-trial-or-at-home-license
- DAN-66   ESCO registration (Dan)
- DAN-54   BGE contract renewal (Dan, ends 15 Jun 2026)
- BGE Free Saturday panels — will fill in as Saturdays accumulate in myenergi_readings

## Recently Completed
- E-25     `intel/context_builder.py` + `/intel/ask` endpoint + 11 tests ✅ 2026-05-08
- DAN-170  "Tank full by HH:MM" in Pushover advisory — `_estimate_tank_full_time()` in morning_advisory.py ✅ 2026-05-08
- POST /advisory/{date}/outcome — feedback endpoint + Pushover deep-link, migration 010 ✅ 2026-05-08
- APScheduler coroutine bug — all 10 jobs fixed (lambda→coroutine, args=[app]) ✅ 2026-05-07
- n8n workflow publishing bug — all 5 active workflows published after Gardening import ✅ 2026-05-07
- EDDI_CT_TROUBLESHOOTING.md — full diagnostic log for electrician ✅ 2026-05-07
- N8N_WORKFLOWS_EXPLAINED.md — publishing gotcha, APScheduler bug, diagnostic checklist ✅ 2026-05-07
- ADR-013  Irish training data strategy — CER ruled out, Norwegian model + Irish calendar ✅ 2026-05-08
- FORECAST_ACCURACY_EXPLAINED.md — day-after verification query, CRU/CER notes ✅ 2026-05-08
- COMMERCIAL_ANALYSIS.md — CRU optional-not-mandatory correction, CRO/funding section ✅ 2026-05-08
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
- N8N_WORKFLOWS_EXPLAINED.md       — n8n publishing gotcha, APScheduler bug, diagnostic checklist
- EDDI_CT_TROUBLESHOOTING.md       — Eddi 50/50 split root cause, fix brief for electrician
- FORECAST_ACCURACY_EXPLAINED.md   — Track 1/2/3 queries, day-after verification, panels 28-32
- DATA_PIPELINE_LIVE_EXPLAINED.md  — full live data pipeline reference
- GRAFANA_DASHBOARDS_EXPLAINED.md  — panel-by-panel guide, blank panel diagnosis
- LP_DISPATCH_EXPLAINED.md         — LP thermal dispatch design, pricing model, tank physics
- SOLAR_ADVISORY_EXPLAINED.md      — morning advisory (20:00), panel_factor_seasonal, InfluxDB vs PG
- MYENERGI_POLLER_EXPLAINED.md     — cgi-jday API, hsk bug, full backfill procedure
