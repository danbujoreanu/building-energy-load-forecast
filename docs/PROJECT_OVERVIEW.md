# EnergyOS — Project Overview
*Residential AI Energy Optimisation for the Irish Smart Meter Market*
*Dan Alexandru Bujoreanu — April 2026*

---

## One-Line Summary

A supplier-agnostic AI device and software platform that forecasts household electricity consumption and automatically optimises device scheduling against dynamic electricity prices — built on a peer-reviewed machine learning pipeline, deployed on Irish smart meter infrastructure, timed for the June 2026 dynamic pricing mandate.

---

## The Problem

Ireland has installed 1.9 million smart meters (CRU202579, Executive Summary). Electricity prices are among the highest in Europe. The CRU has mandated that Ireland's five largest suppliers must offer dynamic 30-minute pricing by June 2026 — meaning the price of electricity will change every half hour based on day-ahead wholesale market prices. The average household will lose money without a system that acts on those signals automatically.

Three structural facts define the gap:

1. **74% of Irish customers are not on time-of-use tariffs** despite evidence that 95% would benefit from switching. *(CRU TOU incentivisation research)*
2. **No supplier will build a supplier-agnostic AI** — Bord Gáis has no incentive to tell you that Energia's night rate would save you €300. A structurally independent product will.
3. **The CRU has explicitly invited market participants to build this.** *"The CRU views the provision of near real time metering data services as a potential market opportunity for suppliers and other energy service providers."* *(CRU202579, Section 3.1, p.14)*

---

## Research Foundation

### What Was Built

A complete energy load forecasting pipeline trained on two real-world datasets: 45 commercial buildings in Drammen, Norway and 48 schools in Oslo, Norway, using 30-minute interval smart meter data.

Three experimental setups compared across a 3-way paradigm parity framework:
- **Setup A** — Gradient-boosted trees (LightGBM, XGBoost, Ridge) with engineered temporal and weather features
- **Setup B** — Deep learning (LSTM, TFT) with engineered features
- **Setup C** — Deep learning on raw sequences (PatchTST), without feature engineering

### Key Results

**Drammen — H+24 Day-Ahead Forecast**

| Model | MAE (kWh) | R² |
|-------|-----------|-----|
| LightGBM | **4.029** | **0.9752** |
| XGBoost | 4.182 | 0.9741 |
| Stacking (Ridge meta) | 4.034 | 0.9751 |
| PatchTST (Setup C) | 6.955 | 0.9102 |
| TFT (Setup B) | 8.770 | 0.8646 |
| Mean Baseline | 22.673 | 0.442 |

**Oslo Cross-City Generalisation (45 → 48 buildings, different country)**

| Model | MAE (kWh) | R² |
|-------|-----------|-----|
| LightGBM | **7.415** | **0.9630** |
| Stacking | 7.280 | 0.9635 |
| PatchTST | 13.616 | 0.8741 |

*Oslo MAE is higher in absolute terms because Oslo school buildings are ~2× the size of Drammen buildings. R² values (0.963 vs 0.975) are consistent — the model quality transfers cross-city. PatchTST's gap widens to +84% MAE vs +72% in Drammen: feature engineering advantage is robust to dataset and geography.*

**Diebold-Mariano Significance Tests (HLN-corrected, H+24)**

| Comparison | DM Statistic | Significance |
|-----------|-------------|-------------|
| LightGBM vs PatchTST | −12.17 | *** |
| LightGBM vs XGBoost | −5.25 | *** |
| LightGBM vs Ridge | −33.52 | *** |

*All three comparisons are statistically significant at p < 0.001. The LightGBM superiority is not noise.*

**Horizon Sensitivity (Drammen, MAE kWh)**

| Model | H+1 | H+6 | H+12 | H+24 | H+48 | Degradation |
|-------|-----|-----|------|------|------|-------------|
| LightGBM | 3.188 | 3.584 | 3.799 | 4.057 | 4.724 | +48% |
| XGBoost | 3.339 | 3.678 | 3.906 | 4.182 | 4.824 | +45% |
| Ridge | 4.301 | 6.306 | 6.883 | 7.487 | 8.447 | +96% |

*The LightGBM advantage over Ridge widens at longer horizons. R² remains 0.967 at H+48 — well above the 0.90 threshold used for MPC applications.*

**Irish Home Validation (Dan's home, Maynooth)**

The pipeline was retrained on a real Irish residential smart meter dataset (17,302 hourly rows, 2024-03-15 to 2026-03-05, ESB Networks HDF format). Achieved **MAE 0.171 kWh/hour** — well below the ±0.5 kWh threshold needed for practical bill optimisation.

### Core Research Insight

> **Paradigm parity confirms that gradient-boosted trees with temporal and meteorological features consistently outperform deep learning models** — including purpose-built architectures (TFT, PatchTST) — on building-level energy load forecasting. The computational advantage of tree models (13s training vs 45min for PatchTST) further reinforces their suitability for edge deployment on low-power hardware.

This finding directly contradicts the prevailing narrative in applied ML that deep learning should always be the first choice. It is the core thesis of the submitted AICS 2025 paper and the journal paper in preparation.

---

## The Product

### What It Does

EnergyOS is a three-layer system:

```
┌─────────────────────────────────────────────────────────────┐
│  DATA LAYER                                                  │
│  P1 port (30-min real-time) + ESB HDF (30-min historical)   │
│  Open-Meteo weather API + SEMO day-ahead prices             │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│  INTELLIGENCE LAYER                                          │
│  LightGBM H+1 (real-time balancing)                         │
│  LightGBM H+24 + P10/P90 quantile bounds (day-ahead)        │
│  BTM asset inference (solar, EV, heat pump detection)       │
│  Tariff scoring and bill optimisation                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│  CONTROL LAYER                                               │
│  myenergi Eddi API (hot water scheduling)                    │
│  EV charger scheduling (Zappi / OCPP)                        │
│  Battery charge/discharge optimisation (roadmap)            │
│  Morning brief push notification (WhatsApp / SMS roadmap)   │
└─────────────────────────────────────────────────────────────┘
```

### Home Plan Score — Live Demo

The pipeline has been validated on Dan's own home. Key output:

- **Plan score: 62/100** (Bord Gáis Free Time Saturday, October 2023 – October 2025)
- Free Saturday utilisation: 54% of 100 kWh/month cap
- **€178.65/year left on table** — unused Saturday free generation window
- Eddi schedule already optimal for the current tariff; improvement requires switching tariff or adding battery

The system correctly identifies that the evening Eddi boost (19:45) cannot be moved to night rate without sacrificing hot water availability at 09:30 — a nuance a generic "save money" recommendation would miss.

### Control Layer (Phase 6 — Complete)

```python
# From deployment/live_inference.py — Phase 6 morning brief
IF solar_forecast[h] > 200 W/m² AND P10[h] < 3 kWh:
    → Divert solar surplus to hot water (free heat)
IF dynamic_price[h] < off_peak_threshold AND EV.needs_charge:
    → Schedule EV charge in this slot
IF P90[h] > peak_demand AND flexible_load.active:
    → Defer dishwasher / washing machine to off-peak
```

FastAPI `/control` endpoint validates `target_hours` bounds, connects to myenergi Eddi via authenticated digest API, and returns a JSON schedule. The Eddi API integration is confirmed live (hub serial confirmed working, API key in `.env`).

### Deployment Stack

- **API:** FastAPI (`deployment/app.py`) — `/predict`, `/control`, `/health` endpoints
- **Model:** LightGBM serialised to pickle; `/health` shows real vs mock model status
- **Infrastructure:** Docker container → AWS ECR → AWS App Runner (eu-west-1, Irish data residency)
- **Hardware MVP:** Raspberry Pi Zero 2W (€15) + DSMR P1 USB adapter (€8–12) + case
- **Makefile targets:** `make docker-build` / `make ecr-push` / `make apprunner-deploy`

---

## The Market

### The June 2026 Trigger

| Event | Date | Source |
|-------|------|--------|
| CRU dynamic pricing mandate | **June 2026** | CRU Decision CRU2024121 |
| Smart meters installed (nationwide) | 1.9M+ | CRU202579, Exec Summary p.2 |
| P1 port software activation | End of 2025 / 2026 | CRU202579, Section 1.2, p.9 |
| SMDS ESCO third-party access | Mid-2026 (target) | CRU202517 SMDAC |
| Five obligated suppliers | BGE, Electric Ireland, Energia, SSE Airtricity, Yuno | CRU2024121 |

Dynamic pricing means the cost of electricity changes every 30 minutes (linked to day-ahead market). A household that can shift 3 kWh of flexible load per day (EV charging, hot water, dishwasher) from peak periods (€0.35–€0.50/kWh) to off-peak (€0.05–€0.12/kWh) saves **€200–400/year**. EnergyOS automates that shift without the consumer needing to do anything.

### Consumer Behaviour Reality

*(Sources: SEAI Behavioural Insights on Energy Efficiency; CRU202566; CRU202579; CSO HEBEU 2024)*

- **71% of Irish homeowners** are "Cost-Driven" — they will not proactively engage with energy apps. The product must work automatically. *(SEAI BI, p.8, Figure 3)*
- Only **10% intend to undertake home energy improvements** in the near future. *(SEAI BI, p.12)*
- **Over 70% identify "not having sufficient funds"** as the primary barrier to energy investment. *(SEAI BI, p.15)*
- **90% rate "comfort improvement"** as the most important factor in any energy investment decision — above financial savings. *(SEAI BI, p.19, Figure 14)*
- **45% of Irish customers** used a PCW in 2022. This figure is increasing year on year. *(CRU202566, Exec Summary, p.1)*
- **No Irish product currently combines** load forecasting with active device control. The entire PCW space is backward-looking. *(CONSUMERS_BEHAVIOUR.md; COMPETITORS.md)*

**Product design implication:** For the dominant Cost-Driven segment, automation — not engagement — is the answer. EnergyOS schedules the Eddi, the EV charger, and eventually the battery automatically, every day. The user does nothing after onboarding.

### Regulatory Positioning

EnergyOS is **NOT a Price Comparison Website**. PCW accreditation (CRU202566) applies to backward-looking comparison tools. We are an **ESCO (Energy Service Company) / Eligible Party** under the Smart Meter Data Access Code (CRU202517):

- Free access to 30-min interval import/export data for consenting customers via SMDS
- Consent: 3-click "Active Permission" via ESB Networks portal
- Application: Appendix A to ESB Networks when SMDS testing opens (mid-2026)
- No commission dependency; no comparison methodology constraints

This is the regulatory white space the CRU has deliberately created.

---

## Competitive Position

**No product exists in the Irish market combining:**
1. Irish smart meter compatibility (ESB Networks, P1 port)
2. Building-level ML load forecasting (LightGBM H+24, R²=0.975)
3. Supplier-agnostic dynamic price optimisation (SEMO DAM integration)
4. Automated device control (myenergi Eddi, Zappi, EV charger)

| Feature | Loop (UK) | Tibber (not in Ireland) | Supplier apps | EnergyOS |
|---------|-----------|------------------------|--------------|---------|
| Works in Ireland | No | No | Yes (own customers) | **Yes** |
| Supplier-agnostic | Partial | No (Tibber contract required) | No | **Yes** |
| ML load forecast | No | No (price-only) | No | **Yes (LightGBM R²=0.975)** |
| P10/P90 uncertainty bounds | No | No | No | **Yes** |
| Automated device control | No | EV only | No | **Yes (EV + hot water + deferral)** |
| Dynamic tariff integration | No | Yes (Nordpool) | No (not yet) | **Yes (SEMO DAM, June 2026)** |
| Academic validation | No | No | No | **Yes (AICS 2025, journal in prep)** |
| Hardware + software | No | Yes (Pulse dongle) | No | **Yes (P1 adapter + cloud)** |

**The first-mover data advantage is compounding.** Every week of personalised P1 data per household makes the household-specific model more accurate. A competitor arriving in 2027 starts cold. Every EnergyOS household starts warm from day one (population model) and improves continuously.

**Why utilities cannot replicate this:**
Bord Gáis has no incentive to tell you that Energia's night rate is better for your EV. Electric Ireland has no incentive to tell you to reduce peak usage if that reduces their margin. A supplier-agnostic independent product has full alignment with consumer savings. No utility can replicate this structurally.

---

## Commercial Model

### Revenue and Unit Economics

| Stream | Price | Notes |
|--------|-------|-------|
| Hardware (device + P1 adapter) | €99–€149 | One-time; Pi Zero 2W (€15) + P1 adapter (€8–12) BOM |
| Software subscription | €3.99/month (€47.88/year) | Model updates, SEMO price feed, advisory |
| **Average household saving** | **€200–400/year** | Flexible load shift: EV + hot water + peak deferral |
| **Customer payback period** | **3–6 months** | At €300 avg saving / €149 hardware + €48 subscription |

**Year 1 unit economics (per household):**
- Revenue: €149 (hardware) + €47.88 (subscription) = **€196.88**
- COGS: ~€30 (hardware BOM + shipping) + ~€12 (cloud hosting) = **~€42**
- **Gross margin: ~79%**

### Market Sizing

- Irish smart meter households with P1-capable meter: ~950,000 (50% of 1.9M installed)
- EV owners (highest-value segment): ~80,000 in Ireland (growing rapidly)
- Heat pump owners (highest-savings potential): ~60,000 and growing toward 400k by 2030 target
- **Conservative SAM (Year 1–2):** 50,000 EV/HP early adopter households = €9.9M hardware + €2.4M/year subscription
- **TAM (post-P1 activation):** All 1.9M smart meter households = €380M+ addressable (5-year view)

### Launch Phases

| Phase | When | Product | Revenue model |
|-------|------|---------|---------------|
| **Phase 0** | Now | Research pipeline + home demo | None (validation) |
| **Phase 1** | Q2 2026 | Software-only: ESB HDF upload → morning brief → manual MyEnergi scheduling | €2.99/month SaaS |
| **Phase 2** | Q3 2026 | Add automated MyEnergi cloud API scheduling (no hardware needed) | €3.99/month |
| **Phase 3** | Q1 2027 | P1 hardware device — real-time, full automation, solar diversion | €99–149 device + €3.99/month |
| **Phase 4** | 2027 | Social comparison, battery optimisation, SEAI/CRU partnerships | Scale |

*Phase 1 requires no hardware, no manufacturing, no P1 port — just the existing deployment stack.*

### Funding Path

| Stage | Programme | Amount | When |
|-------|-----------|--------|------|
| 1 | **AWS Activate** (no company needed; conference demo qualifies) | $5–25k credits | Now — apply immediately |
| 2 | **Enterprise Ireland HPSU Feasibility Grant** | €35k | Q3 2026 |
| 3 | **New Frontiers Phase 2** (via NCI or Maynooth) | €15k stipend + 6 months | Q4 2026 |
| 4 | **SEAI RD&D Call** (May–July 2026; NCI or Maynooth as academic partner) | €200k–500k | Q2 2026 application |
| 5 | **Enterprise Ireland iHPSU** | Up to €1.2M | 2027 (requires 6-month traction) |
| 6 | **Dogpatch Labs 2050 Accelerator** (ESB partner, equity-free) | Acceleration + network | Jan 2027 cohort |

---

## Research and Academic Track

### Published

**AICS 2025 — Springer CCIS** *(submitted December 2025, in press)*
*"Paradigm Parity in Building Energy Load Forecasting: Gradient-Boosted Trees vs. Deep Learning at Multiple Horizons"*

- 12-page full paper (Springer Lecture Notes in Computer Science format)
- Three-setup experimental framework; H+1 and H+24 horizons; Drammen dataset
- Foundation for all subsequent work

### In Preparation

**Journal Paper — target: Applied Energy or Energy and Buildings**
- Extended results: DM significance tests, Oslo cross-city generalisation, horizon sweep H+1→H+48
- New sections: responsible AI / deployment governance, quantile bounds for MPC applications
- Section 7: Responsible AI, Ethics, and Deployment Governance (added Session 32)
- Status: Draft complete in `docs/JOURNAL_PAPER_DRAFT.md`; submission pending final review

### Potential Paper 3 — RENEW Collaboration

Target output from a proposed research collaboration with Prof. Fabiano Pallonetto (IRESI / Maynooth University, RENEW project):
*"AI-driven household load forecasting for demand flexibility under dynamic electricity pricing: an Irish residential validation"*

- Validates residential generalisation (vs current commercial buildings dataset)
- Real Irish household HDF data from RENEW pilot network
- Connects academic pipeline to live product deployment
- Collaboration email ready to send: `docs/PALLONETTO_EMAIL.md`

### PhD Route

Based in Maynooth, the strongest PhD pathway is:
- **Primary supervisor:** Prof. Fabiano Pallonetto (IRESI, Maynooth / DCU)
- **Topic:** *"Consumer Flexibility Under Dynamic Electricity Pricing: Stochastic Modelling and Behavioural Response"*
- **Funding route:** RENEW Phase 2 PhD capacity, NexSys SFI studentship, or GOIPG 2026
- **Strategy:** Establish RENEW research collaboration first → PhD emerges naturally from collaboration
- Full supervisor intelligence: `Personal Projects/Cognitive Focus/HAMILTON_INSTITUTE_RESEARCH.md`

---

## Key Partnerships

### saveon.ie
Dan's friend has built a polished Irish PCW with HDF upload and tariff comparison. Collaboration agreed in principle:
- saveon.ie = Step 1: "Which tariff should I be on?"
- EnergyOS = Step 2: "Now optimise within it"
- Proposed: referral CTA from saveon.ie results page → EnergyOS onboarding
- Formalise with a written agreement; confirm no forecasting/control plans on their side

### myenergi (Eddi / Zappi)
EnergyOS is not a hardware company. myenergi makes the best solar diversion and EV charging hardware in the Irish market. Positioning: *"The AI forecast layer for your myenergi system."*
- EnergyOS calls the myenergi cloud API to schedule boost timers based on H+24 forecast
- myenergi hardware handles physical switching; EnergyOS handles the intelligence
- This is faster to market than custom hardware

### RENEW / IRESI (Maynooth)
Proposed research collaboration with Prof. Pallonetto. RENEW is building an AI-enabled HEMS; we provide the forecasting module. They provide household pilot data. Joint journal paper output.

### SEAI (potential)
SEAI's Heat Pump Support Scheme (HPSS) is the primary acquisition channel for the highest-value user segment. A device that optimises heat pump operating costs directly improves the economics of SEAI's flagship scheme. Potential for SEAI channel partnership or grant-in-aid.

---

## Outstanding Items

### Research

| Item | Priority | Status | Estimated effort |
|------|----------|--------|-----------------|
| Journal paper submission | Critical | Draft complete; final review needed | 1 session |
| RENEW collaboration initiation | High | Email ready to send | Send today |
| Primary consumer survey (willingness-to-pay) | High | Not started | 1 session to design + €200–400 to run |
| CER Irish residential dataset validation | Medium | Access not confirmed | 3–4 sessions once confirmed |
| BTM asset detection (Kazempour approach) | High | Not started | 3–4 sessions |
| Decision-focused learning (Sprint 4) | Medium | Spec complete | 4–5 sessions |

### Product / Engineering

| Item | Priority | Status | Estimated effort |
|------|----------|--------|-----------------|
| Phase 7 AWS deployment | High | Dockerfile + apprunner.yaml exist; ECR push pending | 1–2 sessions |
| WhatsApp Business API push | High | Phase 6 content exists; delivery channel missing | 1 session |
| DAM/SEMO price ingestion | High — blocked until June 2026 | SEMOConnector stub exists | 2 sessions |
| Dynamic tariff optimisation loop | Critical — June 2026 | Architecture designed; implementation pending | 3–4 sessions |
| BTM asset inference module | High | Design phase | 3–4 sessions |
| Heat pump BTM detection | High | Dependent on BTM module | 1–2 sessions |
| Consumer survey + in-app onboarding | Medium | Not started | 2 sessions |
| Social comparison features | Medium | Blocked until multi-household data | Post-RENEW |
| P1 hardware MVP (Pi Zero 2W + adapter) | Medium | BOM identified; assembly manual | 1 session setup |
| Battery storage scheduling | Medium | Forecast exists; control logic needed | 2–3 sessions |

### Commercial / Regulatory

| Item | Priority | Status |
|------|----------|--------|
| AWS Activate application | Critical | Apply immediately — no company required |
| ESCO Appendix A draft | High | Template exists in `docs/regulatory/`; file when SMDS opens |
| saveon.ie referral agreement | High | Agreed in principle; formalise in writing |
| SEAI RD&D application (May–July 2026) | High | Needs NCI or Maynooth academic partner confirmed first |
| EI HPSU Feasibility Grant | Medium | Q3 2026 — needs 6 weeks of product demo evidence |
| New Frontiers application | Medium | Q4 2026 — requires 1-page business concept |

### Immediate Next Actions (in order)

1. **Send journal paper** — final check + submit to Applied Energy
2. **Send Pallonetto email** — `docs/PALLONETTO_EMAIL.md` is ready
3. **Apply for AWS Activate** — takes 20 minutes; no company required
4. **Push Phase 7 Docker container to ECR** — the deployment exists; needs ECR push + apprunner config
5. **Design BTM inference module** — highest-leverage engineering task for product

---

## The Two-Track Summary

```
RESEARCH TRACK                         COMMERCIAL TRACK
──────────────                         ────────────────
AICS 2025 (published)          →       Technical credibility established
Journal paper (in prep)        →       Peer-reviewed validation for SFI/EI
RENEW collaboration            →       Real household data + journal paper 3
PhD (Pallonetto, 2026–)        →       Structured research programme

PIPELINE (built)               →       Production-ready backend
Phase 6 control layer (built)  →       Eddi/EV scheduling works today
Phase 7 deployment (WIP)       →       Live service endpoint
BTM inference (roadmap)        →       Frictionless onboarding
WhatsApp push (roadmap)        →       Cost-Driven segment served

JUNE 2026: CRU dynamic pricing mandate
  └── 5 obligated suppliers
  └── 30-min DAM-linked prices
  └── 1.9M smart meters ready
  └── P1 port activation
  └── PRODUCT-MARKET FIT TRIGGER
```

Both tracks are necessary. Neither substitutes for the other. The journal paper provides the peer-reviewed validation that makes SEAI RD&D and SFI applications competitive. The commercial product provides the real-world deployment evidence that makes the second and third papers original contributions rather than incremental ones.

---

## About the Researcher

**Dan Alexandru Bujoreanu**
MSc in Artificial Intelligence, NCI Dublin (2025) | BSc in Mathematics
15+ years in product management and AI at Meta, eBay, and PayPal (international markets)
Based in Maynooth, Co. Kildare (W23H7T1)

*Independent researcher building at the intersection of machine learning, energy systems, and consumer behaviour.*

---

*Full technical documentation: `building-energy-load-forecast/` GitHub repository*
*Commercial plan: `docs/COMMERCIAL_ANALYSIS.md` | `docs/FUNDING_AND_MONETISATION.md`*
*Consumer research: `Thesis WIP/Aditional resources/Consumer insights and studies/CONSUMER_BEHAVIOUR.md`*
*Regulatory analysis: `docs/regulatory/SMART_METER_ACCESS.md`*
*Strategic positioning: `docs/MARKET_POSITIONING.md`*
