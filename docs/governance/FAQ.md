# Sparc Energy — Frequently Asked Questions

**Maintained by:** Claude Code (Engineering Lead)  
**Format:** Questions arising in architecture meetings and engineering sessions — logged for institutional memory.  
**Last updated:** 21 April 2026 (Session 44)

---

## Data & Pipeline

**Q: Why was the Column_N feature name mismatch only caught now?**  
The pipeline always used `.values` (numpy arrays) when calling `SklearnForecaster.fit()`, so LightGBM never stored column names — it silently assigned generic `Column_0..N` names. The HTTP `/predict` API was the first thing that ever tried to match feature names by key (dict-based request body) — that's when the mismatch surfaced. No retraining needed for existing functionality; the fix is forward-looking (next `run_pipeline.py` produces semantic names automatically).

**Q: Do we need to retrain the models after the Column_N fix?**  
Not urgently. `/control`, `run_home_demo.py`, and `live_inference --dry-run` all work correctly. The Drammen/Oslo models in `outputs/models/` are unchanged. When you next run `scripts/run_pipeline.py` for any reason (~30 min), the new models will have semantic feature names and `/predict` will work perfectly with named payloads.

**Q: Which ESB HDF file should I use?**  
`HDF_calckWh_*.csv` (kWh) for forecasting and billing. This is energy *consumed* per 30-minute slot — directly maps to your electricity bill and is the correct input for LightGBM.  
`HDF_kW_*.csv` (kilowatts) is instantaneous power demand — useful for appliance pattern detection and BTM (behind-the-meter) asset inference (see Kazempour et al., arxiv:2501.18017, DAN-100). Keep both files.

**Q: Why is Grafana showing "No data"?**  
The TimescaleDB schema exists and all tables are created, but the database is empty. The missing piece is the `POST /upload` endpoint (DAN-96) — once built, upload the ESB CSV and Grafana fills up immediately. The dashboard (`sparc_overview.json`) is already provisioned and will auto-populate.

**Q: How accurate is the home model?**  
MAE 0.163 kWh/hour on 2 years of Dan's actual ESB data (April 2024–April 2026, 17,496 rows). R² = 0.68. For context: your kettle uses ~0.15 kWh per boil, a shower is ~1 kWh. Predictions are typically within ±160 watt-hours per hour.

---

## Architecture

**Q: Why not Streamlit for Sparc Energy?**  
Sparc is a commercial consumer product targeting mobile users. Streamlit is a data science prototyping tool — it restarts on code changes, can't handle multiple concurrent users, and isn't suited for API-first architecture. Sparc's roadmap is FastAPI backend + React/PWA frontend.  
Greenhouse is different: personal project, one user, rapid iteration on visualisations → Streamlit is the right tool there.

**Q: Why is ChromaDB RAG disabled in Docker?**  
The `intel/` directory is not copied into the container (one Dockerfile line missing: `COPY intel/ ./intel/`). The `/intel/query` endpoint exists in `deployment/app.py` but is unreachable until this line is added and `intel` dependencies are included in `deployment/requirements.txt`. Fix tracked as DAN-90/DAN-91.

**Q: What's the difference between the Drammen/Oslo models and the home model?**  
Drammen/Oslo models were trained on Norwegian apartment building data (multiple households, kWh aggregates). The home model is trained directly on Dan's ESB data — it knows your specific patterns (Eddi boosts at 07:00 and 19:45, solar south-facing, gas heating, weekend vs weekday). The home model is what's used for the Irish consumer product.

**Q: Why does `live_inference --dry-run` use 300 hours of mock history?**  
The largest lag feature in the model is `lag_169h` (same time last week). After `dropna()` removes rows with missing lag values, you need at least ~170 clean rows. With safety margin, 300 hours ensures enough clean data survives. Earlier sessions used 72 hours — all rows dropped as NaN, producing an empty DataFrame and a cryptic error.

**Q: Is the Eddi boost command live or stubbed?**  
`get_status()`, `get_schedule()`, and `get_history_day()` are fully live — confirmed working against hub serial 21509692. The `boost()` and `pause()` commands are stubbed in `deployment/connectors.py` (they log the intent but don't call the API). Wiring these is part of the consumer experience work (DAN-98).

---

## Product & Commercial

**Q: What does "dynamic pricing trigger" mean for the product?**  
From 30 June 2026, CRU mandates that the 5 largest Irish electricity suppliers (BGE, Electric Ireland, Energia, SSE Airtricity, Yuno) must offer time-of-use tariffs with 30-minute intervals and day-ahead prices. Currently zero suppliers offer this. When they do, a consumer needs a system that automatically shifts device usage to cheap slots — that's exactly what Sparc does. The mandate is our product-market fit trigger.

**Q: Does the tariff comparison still hold after the June 2026 changes?**  
The `score_home_plan.py` script uses current BGE Free Time Saturday rates. After June 2026, new dynamic tariff products will need a new scoring function. The modular design (tariff rates in `src/energy_forecast/tariff.py`) makes this straightforward. DAN-97 wraps this as an API endpoint.

**Q: Should I recommend moving the 19:45 Eddi boost to 23:00 (night rate)?**  
No. The 19:45 boost is needed to ensure the tank is hot for the 09:30 shower the next morning. If solar has already heated the tank, the Eddi won't activate anyway. Moving it to 23:00 would risk a cold shower if solar yield was low. The 07:00 boost at end-of-night-rate is already optimal.

**Q: Am I on the right tariff?**  
Score: 62/100. You're leaving ~€178/year on the table — specifically, unused Saturday free electricity (currently ~54% utilisation of the 100 kWh/month cap). Switching to a heat pump or adding an EV charger would dramatically increase Saturday free utilisation and improve the score. When your BGE contract renews June 2026, re-run `score_home_plan.py` against available dynamic tariff products.

---

## Engineering Process

**Q: Why do we have both `register_features()` and `register_model_features()`?**  
`register_features()` is the strict validator — it enforces that API requests match the exact feature names the model was trained on. `register_model_features()` is the lenient variant — it detects when a loaded model has generic `Column_N` names (trained without DataFrames) and suppresses strict validation, preventing misleading 422 errors. Once models are retrained with semantic names, only `register_features()` is needed.

**Q: What is the session close-out checklist?**  
Each session should: (1) commit meeting notes to `docs/governance/MEETING_NOTES_YYYY-MM-DD.md`, (2) update Linear (new issues, status changes), (3) update `MEMORY.md` with key decisions, (4) write an orchestrator brief if cross-project actions exist, (5) seed the next meeting agenda.

**Q: How often do architecture meetings happen?**  
Bi-weekly (every 2 weeks). Each session covers: system status → architecture delta → priority stack → open questions → Dan's questions to raise next time. Notes are committed to `docs/governance/`.

**Q: What is the "priority stack" ordering principle?**  
🔴 URGENT = external deadline (AWS Activate Apr 25, contract renewals)  
🔴 THIS WEEK = highest-leverage build (unblocks Grafana, investor demos)  
🟡 NEXT = next 1–2 weeks, core product functionality  
🟠 MONTH = within the month, automation / UX  
🟢 LATER = no deadline, valuable but non-blocking

---

*FAQ maintained in `docs/governance/FAQ.md` | Add questions after each session*
