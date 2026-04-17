# Market Positioning — Strategic Brief
*Building Energy Load Forecast Product*
*Last updated: April 2026*

---

## 1. What Category Are We In?

This is the most important strategic question. Getting it wrong leads to the wrong regulatory obligations, the wrong partner conversations, and the wrong go-to-market.

### What we are NOT:
| Category | Example | Why not us |
|---------|---------|-----------|
| PCW (Price Comparison Website) | Bonkers, Switcher, Power to Switch | Backward-looking; compare tariffs based on past usage; commission model; CRU accreditation applies |
| Advanced PCW | elec-tariffs.ie, saveon.ie, Kilowatt.ie | Still backward-looking; HDF upload for historical comparison only; no forecast, no control |
| Home automation hub | Homey, Climote | No AI, no price forecasting, no demand-response optimisation |
| B2B demand aggregator | Viotas, EpiSensor | Commercial/industrial; not residential |

### What we ARE:
**A residential AI energy optimisation service** — operating one layer above PCWs, in the white space that the CRU has explicitly invited market participants to occupy.

| Layer | What it does | Our implementation |
|-------|-------------|-------------------|
| **Forecast** | Predict tomorrow's consumption at 30-min resolution | LightGBM H+24, MAE 0.171 kWh/hr (home dataset) |
| **Price signal** | Ingest day-ahead market prices (DAM) post-16:00 | Phase 6 CLI; Phase 7 API endpoint |
| **Control** | Shift flexible loads (Eddi, EV, battery) to low-price windows | Eddi API integrated; EV scheduling roadmap |
| **Insight** | BTM asset detection, bill scoring, savings quantification | Home Plan Score (62/100); BTM inference roadmap |
| **Advisory** | Morning brief: what to run today and when | Phase 6 complete; WhatsApp push roadmap |

**The CRU's own language validates this positioning:**
> *"The CRU views the provision of near real time metering data services as a potential market opportunity for suppliers and other energy service providers."*
> *(CRU202579, Section 3.1, p.14–15)*

> *"The CRU encourages suppliers and other potential market participants to consider the market opportunities in providing customers with a near real time data service such as an IHD, or through an application."*
> *(CRU202579, Executive Summary, p.2)*

The CRU has removed the ESB Networks IHD monopoly and created a market. We are one of the intended entrants.

---

## 2. Do We Need CRU PCW Accreditation?

**No. Definitively.**

PCW accreditation (CRU202566) applies to price comparison websites. The requirements:
- Display all tariffs on the market
- Calculate Estimated Annual Bills
- Independence and impartiality principles
- Commission disclosure

Our product does not compare tariffs at point-of-sale. It optimises within a chosen tariff. If we were to pursue PCW accreditation, we would be:
1. Forced into comparison methodology constraints that don't fit our product
2. Subject to annual CRU audit and compliance costs
3. Locked into the backward-looking "who's cheapest?" question rather than "how do I spend less on any tariff?"

**What we DO need (not accreditation — registration):**

The **Smart Meter Data Access Code (SMDAC, CRU202517)** governs third-party access to smart meter data via the Smart Meter Data System (SMDS). We qualify as an **Eligible Party / ESCO**. Once SMDS is live (target mid-2026, at risk of delay — see `docs/regulatory/SMART_METER_ACCESS.md`):
- Register as an Eligible Party by filing Appendix A with ESB Networks
- Receive 30-min interval import/export data for consenting customers
- Cost: **free** (funded through network charges)
- Consent: 3-click "Active Permission" from the customer via ESB Networks portal

**Implication:** ESCO registration, not PCW accreditation, is our regulatory pathway. This is already documented and the draft Appendix A is in `docs/regulatory/`.

---

## 3. RENEW Collaboration — Why, What, and How

### Why RENEW is the right partner

| What RENEW has | What we need | Match |
|----------------|-------------|-------|
| Real Irish households with smart meters | Validation dataset | ✓ |
| €2M NCF active funding (Dec 2025) | Research resource | ✓ |
| Pallonetto + Fahy team = HEMS system | Forecasting engine gap | ✓ — they build the HEMS; we provide the forecasting layer |
| NexSys SFI partnership | Funding pathway to PhD and SEAI RD&D | ✓ |
| Maynooth University base | Local (same county as Dan) | ✓ |
| Academic credibility | Journal paper co-authorship route | ✓ |
| IRESI network | Industry connections for pilot recruitment | ✓ |

### The gap RENEW has that we fill

RENEW is building an **AI- and IoT-enabled Home Energy Management System** (HEMS). The published outputs focus on demand flexibility, device control, and consumer participation. What is consistently described as needed in HEMS systems but not the RENEW project's core competence:

- **Day-ahead load forecasting at household level** — required for optimal device scheduling
- **Personalised tariff cost prediction** — required for telling a consumer exactly what switching a load will save tonight
- **BTM asset inference from HDF data** — required for scalable onboarding without a full survey

This is precisely what our pipeline delivers: LightGBM H+24 at 0.171 kWh/hr MAE, calibrated on a real Irish household (Maynooth), with Eddi API integration already working.

### What a collaboration looks like

**Research collaboration (immediate — no funding required):**
1. We provide the forecasting module as an open research component for RENEW's HEMS
2. RENEW provides access to anonymised 30-min HDF data from their pilot households (20–50 households in their Phase 2/3 recruitment)
3. Joint output: a journal paper — *"AI-driven load forecasting for demand flexibility in Irish residential HEMS: validation across dynamic pricing scenarios"* — targeting Applied Energy or Energy and Buildings
4. Dan = lead author or co-author; Pallonetto/Fahy = academic co-authors

**Commercial collaboration (medium-term):**
1. RENEW pilots our device (Pi Zero 2W + P1 adapter) as the data collection layer for their HEMS
2. We integrate our morning brief / advisory layer into the RENEW app UX
3. Joint IP position: RENEW owns the HEMS orchestration; we own the forecasting + advisory layer
4. Revenue: if product goes commercial, negotiate a licensing or referral arrangement

**PhD route (longer-term):**
1. Pallonetto as primary supervisor (School of Business / IRESI)
2. Hamilton Institute probabilist as co-supervisor (Ken Duffy if confirmed, or Nepomuceno)
3. Topic: *"Consumer Flexibility Under Dynamic Electricity Pricing: Stochastic Modelling and Behavioural Response"* (already documented in `HAMILTON_INSTITUTE_RESEARCH.md`)
4. Funding: RENEW Phase 2 PhD capacity, NexSys studentship, or GOIPG 2026

### Status — April 2026

Call completed April 8. PhD/collaboration angle explored. **No response received since (as of April 15).** User decided to wait.

**PhD context changed:** Decarb-AI (UCD-led, €31k/year tax-free, Autumn 2026) is now the **active PhD track**. Interview Apr 21 with Andrew Parnell. If Decarb-AI is successful, pursue Pallonetto/RENEW as **research collaboration only** — no PhD ask. If Decarb-AI unsuccessful, revisit Pallonetto as PhD Route 2.

**If following up:** See `docs/PALLONETTO_EMAIL.md` for post-call template. Do NOT lead with PhD. Lead with research collaboration and the specific technical offer (forecasting layer for RENEW's HEMS).

---

## 4. Consumer Insight → Product Gaps

Based on `CONSUMER_BEHAVIOUR.md` (April 2026), here are the gaps between what the consumer needs and what our current product delivers:

### Gap 1 — BTM Asset Detection (HIGH PRIORITY)
- **Consumer need:** Onboarding must be effortless; asking "what devices do you have?" causes drop-off
- **What exists:** Nothing in current pipeline
- **What's needed:** Implement Kazempour et al. (arxiv:2501.18017) BTM inference on HDF data
- **Effort:** Medium — a new analytical module on top of existing HDF pipeline
- **Output:** User onboarding that says "We detected solar panels and an EV charger — is that right?" instead of a 10-question survey

### Gap 2 — Social Comparison (MEDIUM PRIORITY)
- **Consumer need:** Neighbour benchmarking is the highest-impact nudge (SEAI BI)
- **What exists:** Home Plan Score (62/100) is a start
- **What's needed:** "Homes like yours in Maynooth save 23% more" — requires aggregate data from multiple households
- **Effort:** Blocked until we have multiple users; architectural decision: aggregate stats on server side
- **Dependency:** RENEW collaboration provides the household cohort for this

### Gap 3 — Dynamic Tariff Optimisation (CRITICAL — blocked until June 2026)
- **Consumer need:** Optimise device scheduling against 30-min DAM-linked prices
- **What exists:** Static tariff optimisation (BGE Free Saturday, night rate)
- **What's needed:** DAM price ingestion → forecast → scheduling → device control loop
- **Effort:** High — requires DAM API integration (SEMO) + control loop extension
- **Unblock date:** June 2026 (5 obligated suppliers must offer dynamic tariffs)
- **Interim:** Build the architecture now; mock with synthetic DAM prices

### Gap 4 — WhatsApp/SMS Push (MEDIUM PRIORITY)
- **Consumer need:** 71% Cost-Driven segment will not open an app; push notification required
- **What exists:** Phase 6 CLI morning brief (terminal output)
- **What's needed:** WhatsApp Business API or SMS (Twilio) delivery of the morning brief
- **Effort:** Low–medium — Phase 6 already generates the content; need a delivery channel

### Gap 5 — Primary Consumer Research (MEDIUM PRIORITY)
- **Consumer need:** We don't know willingness-to-pay for €3.99/month or €99–149 hardware
- **What exists:** No data
- **What's needed:** A 5-question online survey (400 respondents via Pollfish or SurveyMonkey Audience); €200–400 cost
- **Output:** Pricing validation before any public launch

### Gap 6 — Heat Pump Owner Segment (HIGH PRIORITY — commercial)
- **Consumer need:** Heat pump owners have the most to gain from dynamic tariff optimisation (heating = biggest electricity load)
- **What exists:** No heat pump-specific feature
- **What's needed:** Heat pump load signature detection in BTM inference; SEAI HPSS grant application integration as an acquisition channel
- **Effort:** Medium — a BTM inference variant; partnership with SEAI HPSS portal

---

## 5. App Development Priorities (Sequenced)

Based on the above, here is the recommended build sequence:

### Phase A — Now (April–June 2026) — Pre-dynamic-tariff
1. **BTM asset detection** — implement Kazempour inference on HDF upload (replaces onboarding survey)
2. **WhatsApp push** — extend Phase 6 morning brief to WhatsApp Business API
3. **Consumer survey** — 5 questions, 400 responses, willingess-to-pay data
4. **RENEW collaboration** — call done April 8; awaiting response; pursue as research collaboration once Decarb-AI PhD outcome is known

### Phase B — June 2026 — Dynamic pricing goes live
5. **DAM price ingestion** — SEMO API integration for day-ahead prices
6. **Dynamic tariff optimisation loop** — extend Phase 6 to use DAM prices rather than static BGE rates
7. **Heat pump load detection** — BTM inference variant for HP signature
8. **ESCO registration** — file Appendix A with ESB Networks when SMDS testing opens

### Phase C — H2 2026 — Scaling
9. **Social comparison** — requires multi-household data (from RENEW pilot or first users)
10. **P1 port hardware MVP** — Pi Zero 2W + DSMR P1 adapter; customer self-install kit
11. **Battery storage scheduling** — charge/discharge cycle optimisation using H+24 forecast
12. **Commercial launch** — limited beta via saveon.ie referral + SEAI HPSS channel

---

## 6. How the App Continues to Be a Great Exercise

The user's stated reason to keep building: *"it's a great exercise for me."*

This is entirely consistent with the commercial and research strategy:
- Each gap above is a discrete, learnable engineering challenge
- BTM inference = time series anomaly detection (new skill, publishable)
- WhatsApp integration = API integration + message design (product skill)
- DAM price ingestion = new data source + financial time series (finance ML skill)
- Dynamic tariff optimisation = stochastic control / reinforcement learning territory (PhD-adjacent)
- Social comparison = privacy-preserving aggregation (research challenge)

The app is not just an exercise — it is the research artefact and the product. Each feature built becomes either a paper section or a demo for investors/supervisors.

---

## 7. The Regulatory White Space We Occupy

The CRU has created this landscape deliberately:

```
PCWs (accredited, backward-looking)
  → elec-tariffs.ie / saveon.ie / Bonkers
      "What tariff should I be on?" ← their question

Our product (market participant, forward-looking)
  → "How do I minimise cost on any tariff?" ← our question
  → "What will I use tomorrow?" ← our forecast
  → "What should my Eddi / EV / battery do today?" ← our control

Enabled by:
  CRU202579: market-led near-real-time data → P1 port (end 2025/2026)
  CRU2024121: dynamic pricing mandate → June 2026 (5 suppliers)
  CRU202517: SMDS ESCO access → mid-2026 (free data with consent)
```

No Irish product currently occupies this space. The CRU has explicitly invited it. The timing is 2026.

---

## Related Documents
- `docs/COMPETITORS.md` — full Porter 5 forces + competitor monitoring list
- `docs/COMMERCIAL_ANALYSIS.md` — BMC, TAM/SAM/SOM, unit economics
- `docs/regulatory/SMART_METER_ACCESS.md` — SMDAC / ESCO registration detail
- `docs/research/CONSUMER_BEHAVIOUR.md` — full consumer insight synthesis with precise citations (CRU202579, CRU202566, SEAI BI)
- `../Personal Projects/Cognitive Focus/HAMILTON_INSTITUTE_RESEARCH.md` — PhD supervisor intelligence
