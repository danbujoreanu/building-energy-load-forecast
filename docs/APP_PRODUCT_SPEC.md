# App / Device Product Specification

**Product name (working title):** GridSense (or similar)
**Last updated:** 2026-03-15
**Status:** Pre-product — research pipeline complete; deployment architecture designed

---

## What it is

A smart meter AI device + mobile app for Irish households. The device plugs into the P1 port
of an ESB Networks smart meter. It runs inference locally (Raspberry Pi-class hardware) and
connects to a cloud backend for forecasting, price signals, and recommendations.

**Core promise:** Your home learns when energy is cheap and when solar generation will cover
your demand — and acts on it, or tells you to.

---

## Target user

**Primary:** Irish homeowner, 30-55, on a time-of-use or smart tariff (or about to switch).
Energy-aware but not technically inclined. Owns or is considering: heat pump, EV, solar panels,
immersion heater, dishwasher, washing machine.

**Secondary:** Heat pump early adopter. Electricity bill is high and they need help optimising
when the heat pump runs. CSO 2024 data: 33% of Irish households are already on TOU/smart tariffs;
only 10% actively shift consumption — this is the gap the app closes.

**Tertiary:** Landlord managing multiple properties (small portfolio). Same device, fleet dashboard.

---

## Core features

### 1. Day-Ahead Load Forecast
- **What:** P10/P50/P90 forecast of household electricity consumption for the next 24 hours
- **Model:** LightGBM (Setup A) — 4.0 kWh MAE at H+24, R²=0.975 (public buildings baseline)
- **Input:** 72h historical consumption from P1 port + weather from OpenMeteo API
- **Update cadence:** Once daily at 16:00 (after SEMO day-ahead prices published)
- **Why LightGBM and not DL:** ~2ms inference, no GPU needed, 4.0 kWh MAE vs 7.0 kWh for PatchTST

### 2. Price-Aware Scheduling
- **What:** Given tomorrow's SEMO day-ahead prices + load forecast, recommend optimal schedule
  for heat pump / immersion / EV / dishwasher
- **Example:** "Heat pump cheapest window: 02:00-06:00 (€0.12/kWh). Est. saving: €0.45"
- **Automation:** Direct control via MyEnergi API (eddi), smart plugs (Tapo/Shelly), or
  calendar push to Google Home / Apple Home (for devices without direct API)
- **Manual fallback:** Push notification with recommended action; user taps confirm/dismiss

### 3. Solar Generation Forecast
- **What:** Predicted solar output for next 24h using OpenMeteo direct radiation forecast
- **Integrated with:** Load forecast → net import = load - generation → cheaper when net import low
- **Example:** "Tomorrow 11:00-14:00: solar covers 80% of expected load. Grid draw minimal."
- **Feasibility calculator:** Payback period for installing solar based on current consumption
  profile (uses load forecast + Irish solar irradiance data)

### 4. Energy Plan Recommendation
- **What:** Match user's usage profile against available Irish supplier tariffs
- **Data:** Current tariffs from Electric Ireland, Bord Gáis, Energia, SSE Airtricity, Flogas
- **Output:** "Based on your usage pattern, you'd save €180/year on a night-saver tariff vs your
  current standard rate"
- **Framing:** Data-based compatibility match — not financial advice. Precedent: MoneySavingExpert
  comparison model. Regulatory note: compare as information service, not regulated advice.
- **Update:** Tariff database updated monthly (or scraped/API if suppliers provide)

### 5. Heat Pump / EV Optimisation
- **What:** Specific scheduling logic for high-draw appliances
- **Heat pump:** Pre-heat during off-peak (thermal mass stores heat), coast during peak
- **EV charger:** Smart charging window (off-peak + solar surplus)
- **Context:** Ireland targeting 400,000 heat pumps by 2030 (Climate Action Plan). SEAI grant
  up to €6,500 for heat pump installation. Our device makes heat pump economics better —
  natural upsell / SEAI partnership angle.
- **Benefit:** Household with heat pump + our device = cheaper running cost → supports adoption

### 6. Weekly/Monthly Insights Dashboard
- **What:** Retrospective analysis of actual vs forecast consumption, money saved, carbon avoided
- **Key metrics:** Weekly spend vs. equivalent flat-rate spend; demand response compliance rate;
  renewable % of consumption (based on EirGrid carbon intensity API)
- **Notifications:** "This week you shifted 4 loads to off-peak. Saved €3.20 vs doing nothing."
  "Your consumption is 12% higher than last month — we detected a change in your heat pump pattern."
- **This is the low-friction engagement model** — no nagging real-time nudges, weekly digest instead

### 7. LLM Energy Advisor (Phase 2 feature)
- **What:** Conversational interface where user can ask questions about their energy
- **Examples:**
  - "Why is my bill higher this month?" → LLM gets context (load profile, weather, tariff) + answers
  - "Should I switch to Energia's EV tariff?" → LLM evaluates against usage profile
  - "Is it worth getting solar panels?" → LLM runs payback calculation + explains
  - "What's causing this spike on Tuesday evening?" → LLM identifies likely appliance pattern
- **Implementation:** Claude API (claude-haiku-4-5 for speed/cost) with pre-computed user context
  (last 30d consumption stats, current tariff, forecast for today) injected as system prompt
- **Cost model:** ~€0.002 per query (Haiku). Budget: 20 queries/user/month = €0.04/user/month.
  Viable within €3.99 subscription margin.
- **Privacy:** No raw usage data sent to API — only computed statistics and aggregates

### 8. Learning / Adaptive Model (Phase 2 feature)
- **What:** Model retrains on individual household data as it accumulates
- **Cadence:** Monthly retrain on rolling 24-month window of actual consumption
- **Trigger events:** Automatic on calendar + manual on life events (got solar, got EV, moved in)
- **Cold start:** First 30 days = population average model (Irish residential baseline)
  After 30 days = household-specific model takes over
- **Sliding window vs expanding:** Rolling 24-month (prevents stale pre-heat-pump data polluting
  post-heat-pump model)
- **Concept drift detection:** Rolling 7-day MAE > 1.5× training MAE → auto-retrain triggered
- **Note:** This is the "learning phase" Jalal Kazempour mentioned — the system needs ~30 days
  to learn a new household's patterns. Communicate this to users at onboarding.

---

## What we deliberately do NOT do (Phase 1)

- Real-time (<5min) inference — adds complexity, minimal value vs hourly
- Per-appliance disaggregation (NILMTK) — deferred to Phase 6B
- Multi-household aggregation / community energy — deferred (requires ESB/utility partnership)
- Battery/BESS scheduling — requires 2-way hardware control, different liability model
- Directly commanding appliances without explicit user confirmation for first 30 days

---

## Technical architecture (production)

```
[P1 Port Adapter] → [Raspberry Pi 4 / Pi Zero 2W]
                         ↓ (MQTT or HTTPS)
                   [AWS / GCP Backend]
                    ├── FastAPI inference endpoint (already exists: deployment/app.py)
                    ├── LightGBM model (already trained, deployment/live_inference.py)
                    ├── OpenMeteo weather connector (already implemented)
                    ├── SEMO price connector (stub, needs ENTSO-E API token)
                    ├── MyEnergi eddi connector (stub, needs hardware + API key)
                    └── Claude API (LLM advisor — Phase 2)
                         ↓
                   [Mobile App — React Native or PWA]
```

**Inference latency:** LightGBM H+24 prediction: ~2ms. Full pipeline (weather fetch + features + predict): <500ms. Suitable for hourly batch.

---

## Opportunities

| Opportunity | Detail |
|------------|--------|
| Heat pump adoption wave | Ireland targeting 400k heat pumps by 2030; our device reduces running cost → supports SEAI grant programme |
| CRU dynamic pricing mandate | Top 5 suppliers mandated to offer TOU tariffs by June 2026; creates natural demand for optimisation tool |
| Climate Action Plan alignment | Direct alignment with Ireland's legally binding 51% emissions reduction target; eligible for government co-funding |
| SEAI partnerships | SEAI runs Home Energy Saving Kits programme; our device is a natural evolution |
| Viotas model (precedent) | Viotas pays LEAP customers to reduce demand during peaks (grid flexibility). Our device enables the same residential behaviour without requiring a utility intermediary |
| No direct competitor | Tibber not in Ireland; Climote (smart thermostat, ~€100) has no AI forecasting or solar integration |
| ESB Networks P1 port | Physical access point on every modern smart meter — no supplier permission required |

---

## Risks

| Risk | Mitigation |
|------|-----------|
| ESB Networks changes P1 port spec / access | Open standard (DSMR), unlikely; monitor ESB announcements |
| Suppliers don't publish API for price signals | Use SEMO/ENTSO-E public API (already planned) |
| Regulatory: recommending tariffs = financial advice | Frame as "usage compatibility match" not "best deal"; legal review before launch |
| User fatigue with notifications | Weekly digest model instead of real-time nudges (see §6) |
| Model accuracy on residential load (vs public buildings) | Norwegian public buildings are well-behaved; residential is noisier. Target R²>0.80 (vs 0.975 for buildings). Need residential validation dataset before claiming accuracy in marketing. |
| Utility backlash (losing high-margin peak customers) | Product is supplier-agnostic. Utilities are incentivised to reduce peak demand (Eirgrid constraint costs). Frame as demand flexibility enabler, not disruptor. |
| Users with irregular schedules | Weekly insights model is schedule-agnostic. Real-time nudges are opt-in only. |

---

## PhD alignment

The product generates multiple novel research questions:
- **Q1:** Does an adaptive household-level model outperform a population-level model?
  (personalisation vs. data volume trade-off)
- **Q2:** Can BTM asset inference (Kazempour 2025) identify when a user adds a heat pump/EV
  from load curve changes alone?
- **Q3:** What is the optimal decision loss function for demand response recommendations?
  (DFL — Decision-Focused Learning, Sprint 4)
- **Q4:** Does the paradigm parity finding (trees > DL) hold for residential loads?
  (answer: likely no — residential loads are more irregular, DL may close the gap)

These questions are each publishable papers and a coherent PhD thesis.

---

## Funding path

1. **AWS Activate** — free cloud credits ($5-25k). Apply with GitHub repo + pitch deck.
2. **Enterprise Ireland HPSU Feasibility Grant** — €35k pre-revenue for market validation.
   Requires: Irish company, identifiable market, prototype or proof-of-concept.
3. **SEAI Research & Innovation funding** — aligned with Climate Action Plan.
4. **NCI / Nova UCD** — SFI Commercialisation Fund requires academic partner.
   Existing MSc = seed IP. NCI MSc project = eligible origin story.
5. **Enterprise Ireland iHPSU** — up to €1.2M after 6-month traction.

