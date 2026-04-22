# AI Impact Assessment (AIIA) — LightGBM Energy Demand Forecast
*Framework: adapted from Google AI Impact Assessment + UK ICO AI Auditing Framework + EU AI Act Art. 9 Risk Management*
*Author: Dan Alexandru Bujoreanu · Date: 2026-03-28 · Version: 1.1 (updated 2026-04-22)*

---

## Purpose of This Document

An AI Impact Assessment evaluates the potential effects — benefits and harms — of deploying an AI system before it reaches users. This document assesses the LightGBM H+24 energy demand forecasting model for deployment in the Sparc Energy / Wattpath consumer product targeting Irish residential households.

This document serves as:
- Internal governance record for the product
- Evidence for Enterprise Ireland funding applications
- Foundation for ESCO registration under CRU202517
- Reference template for enterprise AI governance programmes (EU AI Act, ISO/IEC 42001)

---

## System Description

| Field | Value |
|-------|-------|
| **System name** | LightGBM H+24 Building Energy Demand Forecast |
| **Deployment context** | Irish residential households — time-of-use tariff optimisation |
| **Decision type** | Recommendation (advisory) — "charge your EV between 2–4am" |
| **Automation level** | Level 2 — automated recommendations with optional automated execution (user-configured) |
| **Affected population** | Irish electricity consumers on time-of-use or dynamic tariffs |
| **Regulatory context** | CRU June 2026 dynamic pricing mandate; GDPR; EU AI Act |
| **AI Act classification** | Limited risk (Art. 52) — transparency obligations apply. Not high-risk (no safety-critical control). |

---

## Step 1 — Identify Affected Parties

| Party | How affected | Severity |
|-------|-------------|---------|
| **Primary user (household)** | Receives energy recommendations; may automate flexible loads based on forecast | Direct |
| **ESB Networks** | Forecast draws on smart meter data via SMDS API | Indirect |
| **Energy suppliers** | User load-shifting affects supplier demand forecasts and imbalance charges | Indirect |
| **Other grid users** | Mass adoption of coordinated load-shifting could create new demand peaks | Systemic (future) |
| **Vulnerable users** | Households on medical equipment, low-income users with no flexible load | At-risk group |

---

## Step 2 — Identify Potential Harms

### 2a. Direct Harms

| Harm | Likelihood | Severity | Mitigation |
|------|-----------|---------|-----------|
| **Wrong forecast → user charges EV at expensive peak time** | Medium (model R²=0.975 but individual household variance is higher) | Low (financial — €5–20/incident estimate) | Confidence interval display; user override always available |
| **Automated action disrupts user comfort** (e.g., heat pump scheduled off when occupant is cold) | Medium (user misconfiguration) | Low–Medium | Comfort constraints configurable; emergency override button |
| **Flex event auto-response deprives user of hot water** — system defers Eddi boost during a Turn Down event; user needs shower before dinner | Medium (if fully automated without consent) | Medium (discomfort, degraded trust) | **Consent-first model required** — see §Flex Event Consent Model below. Never auto-act on comfort-affecting flex responses without explicit user confirmation. |
| **Model underperforms in extreme weather** (heat wave, cold snap) | Low–Medium (trained on 2018-2022 data) | Medium (missed optimisation opportunity during high-cost periods) | Seasonal retraining; anomaly detection flag |
| **Data breach — smart meter data exposed** | Low (local edge processing; OAuth; encrypted at rest) | High (MPRN + consumption pattern = personal data) | Edge-first architecture; no raw data in cloud; GDPR compliant |
| **Model trained on Norwegian buildings misapplied to Irish residential** | Low (explicitly documented limitation; Irish-specific retraining planned) | Medium (degraded recommendation quality) | Domain validation before production; clearly stated in UI |

### 2b. Systemic Harms (at scale)

| Harm | Likelihood | Severity | Mitigation |
|------|-----------|---------|-----------|
| **Synchronised load-shifting creates new demand peak** (all users charge EVs at 2am simultaneously) | Medium (if >5% grid penetration) | High (grid stability) | Personalised stagger built into scheduling; aligned with CRU demand response guidelines |
| **Market distortion** — coordinated demand response affects wholesale prices | Low (small scale initially) | Low–Medium | Monitor; engage CRU proactively as scale grows |

---

## Step 3 — Identify Potential Benefits

| Benefit | Quantification (estimate) |
|---------|--------------------------|
| **Direct financial saving per household** | €150–400/year (based on home trial: €178.65/yr found on first analysis) |
| **Carbon reduction** | Load-shifting to high-renewable periods reduces average grid carbon intensity |
| **Dynamic pricing confidence** | Removes consumer anxiety about CRU June 2026 mandatory dynamic pricing rollout |
| **Grid flexibility** | Coordinated demand response supports EirGrid renewable integration targets |
| **Energy literacy** | App builds household understanding of their own consumption patterns |

---

## Step 4 — Risk Rating

| Risk | Rating | Rationale |
|------|--------|-----------|
| Privacy | **Medium** | Smart meter data is personal; mitigated by edge architecture and SMDS OAuth |
| Financial harm to user | **Low** | Worst case is suboptimal scheduling; user always has override |
| Safety | **Very Low** | No safety-critical control; heat pump comfort constraints enforced |
| Fairness | **Medium** | Model trained on Norwegian commercial buildings; Irish residential validation needed |
| Grid stability | **Low** (now) / **Medium** (at scale) | Stagger scheduling built in; monitor as user base grows |
| **Overall AIIA risk level** | **Limited Risk** | Transparency obligations apply per EU AI Act Art. 52 |

---

## Step 5 — Safeguards and Controls

| Control | Implementation status |
|---------|----------------------|
| **User always in control** — no fully automated action without opt-in configuration | ✅ Designed into UX spec |
| **Emergency override** — user can cancel any scheduled action in <2 taps | ✅ Required in MVP |
| **Confidence display** — forecast shown with uncertainty range, not single number | 🔄 Planned for MVP |
| **Anomaly flag** — alert user when forecast confidence is low (unusual weather, data gap) | 🔄 Planned |
| **GDPR consent flow** — explicit opt-in for SMDS data access before any data collected | ✅ Required (CRU202517) |
| **Data minimisation** — only 24-month rolling window retained per CRU202517 | ✅ In data pipeline |
| **Model versioning** — all model versions logged in MLflow / checkpoints/ | ✅ Git-tracked |
| **Audit log** — every automated action logged with timestamp, forecast input, and decision | 🔄 Planned |
| **Human review trigger** — escalate to support if user reports 3+ unexpected actions | 🔴 To design |
| **Retraining cadence** — monthly retraining on rolling 24-month window | 🔴 To implement |
| **Flex event consent gate** — no comfort-affecting action executed without explicit user confirmation | ✅ Design principle locked (DAN-114) |

---

## Step 6 — Transparency Obligations (EU AI Act Art. 52)

This system is classified as **limited risk** under the EU AI Act. Obligations:

| Obligation | Compliance |
|-----------|------------|
| Inform users they are interacting with an AI system | ✅ Disclosed in app onboarding |
| Explain the basis of recommendations (in plain language) | ✅ "This recommendation is based on your usage pattern + tomorrow's weather + your tariff" |
| Provide a model card (Art. 13 equivalent) | ✅ MODEL_CARD.md (this repo) |
| Enable human oversight of automated decisions | ✅ Override built into all automated actions |
| Document training data and provenance | ✅ DATA_PROVENANCE.md (this repo) |

---

## Step 7 — Unresolved Questions / Open Items

| Question | Status | Owner |
|---------|--------|-------|
| What is actual performance on Irish residential (not Norwegian commercial)? | 🔴 Needs Irish dataset | Dan — SMDS access in Phase 2 |
| How does model perform during CRU dynamic pricing volatility (post-June 2026)? | 🔴 Unknown — data doesn't exist yet | Monitor post-launch |
| At what household penetration does grid impact become material? | 🟡 Needs modelling | Engage EirGrid when relevant |
| ESCO registration requirements fully met? | 🟡 Appendix A draft ready — not submitted | Submit when incorporating |

---

## Flex Event Consent Model

*Added 2026-04-22 — triggered by live ESB Networks Turn Down event observed in production.*

### Background

On 2026-04-22, ESB Networks sent an SMS Turn Down flex event alert to opted-in customers: *"There will be a flex event today between 5-7pm. Please minimise your electricity usage where possible during this timeframe."* This is a live demand response programme — not a pilot. The 17:00–19:00 window aligns with both the BGE peak rate (49.28c/kWh, Mon–Fri) and EirGrid's tightest grid period.

This event surfaced a critical product design question: **should Sparc Energy automatically act on flex event signals, or should it recommend and wait for user confirmation?**

### The core tension

The case for auto-action: maximum grid benefit, maximum financial saving, no friction for the user.

The case against: a user may have scheduled their shower for 18:30 before a dinner date. If the system automatically deferred the Eddi boost to 16:00, the tank is cold by 18:30. The user has no recourse in the moment. This is a real harm — not hypothetical.

### Design principle: Consent-First for Comfort-Affecting Actions

**Sparc Energy will never automatically execute an action that affects physical comfort or resource availability without explicit user confirmation.**

The consent-first flow for flex events:

> *"There's a flex event 5–7pm today. I suggest shifting your 18:00 hot water boost to 16:00 — saves ~€0.05 and supports grid stability. [Accept] [Decline] [Remind me later]"*

The user confirms → the system executes. If the user declines → the system logs the decline, does not act, and notes it in the weekly digest ("You declined 1 flex event this week — that's fine").

### Tiered Autonomy Model

| Action type | Autonomy level | Rationale |
|---|---|---|
| Defer hot water boost during flex event | **Recommend → User confirms** | Hot water access is a comfort and personal care need |
| Shift EV charge window outside peak | **Recommend → User confirms** (default); auto if user explicitly opts in with override window configured | Low risk if charge time window is wide enough |
| Solar surplus divert to Eddi | **Auto-act** | Purely additive — no comfort impact; only runs when surplus exists |
| Skip 07:00 morning boost | **Never auto** | Hard constraint — 09:30 shower dependency documented in user config |
| Schedule appliance (dishwasher) to off-peak | **Recommend → User confirms** | User knows their schedule; system doesn't |

### EU AI Act alignment

EU AI Act Article 14 requires that high-human-impact AI systems enable **meaningful human oversight**. While Sparc Energy is classified as Limited Risk (Art. 52), the flex event consent model ensures Article 14 compliance by design: no action affecting user comfort, safety, or resource access is taken without an explicit human confirmation signal.

### GDPR Article 22 alignment

Automated decisions that "significantly affect" individuals require either explicit consent, contractual necessity, or legal obligation. Deferring a scheduled hot water boost could plausibly meet the "significantly affects" threshold for a vulnerable user (elderly, medical needs). The consent-first model ensures we are always within the explicit consent basis — the user clicked Accept.

### Open question

ESB Networks' SMS arrived at 14:14 for a 17:00 event — only 3 hours' notice. The consent flow above works for same-day events. For events notified the day before (if ESB moves to day-ahead notification), the flow remains the same but with more time for the user to plan. Monitor ESB's notification lead time as the programme matures. See DAN-114.

---

## Assessment Conclusion

**Decision:** Proceed to MVP with the safeguards listed above.

**Rationale:** The system provides significant financial and environmental benefit to Irish households. Identified harms are low severity and well-mitigated. Privacy risk is controlled by edge-first architecture and SMDS OAuth. No safety-critical functions are automated without explicit user configuration. The model's domain transfer limitation (Norwegian commercial → Irish residential) is documented, disclosed to users, and targeted for remediation in Phase 2.

**Next review date:** At Phase 2 launch (Irish SMDS data integration) or when user base exceeds 1,000 households — whichever comes first.

---

## Document Control

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0 | 2026-03-28 | Initial AIIA — pre-MVP | Dan Bujoreanu |
| 1.1 | 2026-04-22 | Added flex event harm to §2a; flex event consent gate to §5; full Flex Event Consent Model section; DAN-114 | Dan Bujoreanu |

*This document should be updated when: the model is retrained on new data, automated action scope changes, new affected parties are identified, or regulatory guidance changes.*
