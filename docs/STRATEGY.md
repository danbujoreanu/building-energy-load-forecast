# Sparc Energy — Product Strategy

**Version:** 1.0 | **Last updated:** 2026-04-18 | **Owner:** Dan Bujoreanu  
**Review cadence:** Quarterly (aligned to OKR cycle)

---

## North Star Metric

> **€ saved per active household per year**

Everything we build is measured against this. A feature that doesn't reduce cost, shift load, or increase accuracy towards this number is deprioritised.

Current baseline for test household (Maynooth, Co Kildare):
- **Identified opportunity:** €178.65/year from Saturday free-rate optimisation alone
- **Target:** €300–500/year fully optimised (device scheduling + tariff switching + dynamic pricing)

Secondary metric: **% of optimisable load successfully shifted** (technical validation).

---

## The Four Mandates

Sparc Energy serves four interconnected objectives simultaneously:

| # | Mandate | Primary outcome |
|---|---------|----------------|
| 1 | **Commercial / Entrepreneurship** | Revenue, funding, market entry |
| 2 | **Career showcase / Portfolio** | Job interviews, employer credibility |
| 3 | **Market-aligned learning** | Azure dual-stack, LangChain, job-spec-driven tech |
| 4 | **Research / Academic platform** | Journal paper → PhD application |

These form a flywheel: research quality validates commercial claims → commercial traction is the strongest career signal → academic publication unlocks PhD → market-aligned learning feeds back into all four.

---

## Business Model Canvas

*Framework: Osterwalder & Pigneur (MBA Entrepreneurship module)*

| Block | Content |
|-------|---------|
| **Value Proposition** | The only Irish product that forecasts your energy consumption, tells you when to shift loads, and actively controls devices — before the bill arrives. Target: €300–500/year savings per household. |
| **Customer Segments** | (1) Heat pump owners (400k target by 2030, SEAI subsidy recipients); (2) EV owners on TOU tariffs; (3) Solar+battery households; (4) Technically literate early adopters (40–49, primary shifters per CSO data) |
| **Channels** | (1) Direct: energy.danbujoreanu.com landing page → waitlist; (2) Partnership: saveon.ie referral CTA (agreed in principle); (3) Integration: Homey app marketplace (distribution); (4) B2B: ESCOs, demand aggregators |
| **Customer Relationships** | Self-service MVP (CSV upload); freemium consumer app (Phase 2); white-label API for partners |
| **Revenue Streams** | Hardware (€99–149 P1 adapter); Subscription (€3.99/month); B2B API licensing; Commission from tariff switching (like PCWs) |
| **Key Resources** | ML pipeline (LightGBM, R²=0.975); RAG knowledge base; Irish smart meter data expertise; CRU ESCO registration (pending); myenergi Eddi API integration |
| **Key Activities** | Load forecasting; demand-response scheduling; market intel ingestion; household onboarding; regulatory compliance |
| **Key Partnerships** | ESB Networks (SMDS data access — CRU202517); myenergi (Eddi API); SEAI (possible RD&D partner); saveon.ie (co-referral); Homey (distribution) |
| **Cost Structure** | Mac Mini M4 ~€749 (June 2026, capex); AWS managed services ~€20–50/month; Domain + Cloudflare (minimal); Claude API (haiku-4-5, ~€0.04/user/month) |

---

## Competitive Strategy

*Framework: Porter's Five Forces + VRIN (Grant, Contemporary Strategy Analysis — MBA Competitive Strategy module)*

### Porter's Five Forces

| Force | Assessment | Implication |
|-------|-----------|-------------|
| Threat of new entrants | Medium — CRU registration + data partnership barriers | File CRU ESCO registration early |
| Buyer power | Low — no comparable Irish product exists | Pricing power exists at launch |
| Supplier power | Low — open data (ESB HDF), open APIs, open models | Stack independence maintained |
| Substitute threat | Low — no Irish product does forecasting + control | Window: 12–18 months before foreign entry |
| Competitive rivalry | Low — PCWs are backward-looking, no direct competitor | Blue ocean for 2026 launch |

### VRIN Analysis (Sustainable Competitive Advantage)

| Resource | Valuable | Rare | Inimitable | Non-substitutable |
|----------|----------|------|-----------|-------------------|
| Irish smart meter dataset + domain expertise | ✓ | ✓ | ✓ (time to acquire) | ✓ |
| CRU regulatory knowledge + ESCO path | ✓ | ✓ | ✓ | ✓ |
| LightGBM pipeline (R²=0.975, production) | ✓ | ✗ (replicable) | ✗ | ✗ |
| Eddi device integration (myenergi) | ✓ | ✓ (first Irish) | ✓ (short-term) | ✗ |
| Dynamic pricing timing (June 2026 CRU mandate) | ✓ | ✓ (window) | ✗ | ✓ |

**Conclusion:** Core advantage is market timing + regulatory knowledge + dataset. The ML model is necessary but not the moat.

---

## Balanced Scorecard

*Framework: Kaplan & Norton — aligned to four mandates*

### Financial Perspective
| Objective | Measure | Target (Q4 2026) |
|-----------|---------|-----------------|
| Achieve early revenue | Paying subscribers | 10 households |
| Secure non-dilutive funding | AWS Activate + SEAI grant awarded | €25k+ |
| Control unit economics | Monthly burn rate | <€200/month |

### Customer Perspective
| Objective | Measure | Target (Q4 2026) |
|-----------|---------|-----------------|
| Demonstrate real savings | € saved per household tracked | >€200 avg |
| Grow awareness | Website visitors + waitlist signups | 500 unique, 50 waitlist |
| Enable easy onboarding | Time to first forecast | <10 min (CSV upload) |

### Internal Processes Perspective
| Objective | Measure | Target (Q4 2026) |
|-----------|---------|-----------------|
| Maintain model quality | H+24 MAE on live Irish data | ≤4.5 kWh |
| Reliable API uptime | Weekly uptime % | >99% |
| Ship features predictably | Sprint completion rate | >80% |

### Learning & Growth Perspective
| Objective | Measure | Target (Q4 2026) |
|-----------|---------|-----------------|
| Build Azure portfolio | Azure working demo endpoint | Live by Q3 |
| Publish journal paper | Submitted to Applied Energy | Q2 2026 |
| PhD application | Application submitted | Q3 2026 |
| Market intelligence | ChromaDB corpus freshness | <7 days stale |

---

## OKRs — Q2 2026 (April – June)

### Objective 1: Launch Sparc publicly with measurable household savings
| Key Result | Owner | Due |
|-----------|-------|-----|
| KR1: Website live at energy.danbujoreanu.com with case study page | Dan | May 31 |
| KR2: 3+ active test users with real ESB CSV data uploaded | Dan | June 30 |
| KR3: AWS Activate application submitted | Dan | April 25 |
| KR4: Journal paper submitted to Applied Energy | Dan | May 31 |

### Objective 2: Establish commercial foundation
| Key Result | Owner | Due |
|-----------|-------|-----|
| KR1: CRU ESCO registration research complete + timeline defined | Dan | May 15 |
| KR2: saveon.ie collaboration formalized (written agreement or MOU) | Dan | June 15 |
| KR3: Mac Mini M4 received and production services migrated | Dan | June 30 |

### Objective 3: Build dual-stack portfolio for job market
| Key Result | Owner | Due |
|-----------|-------|-----|
| KR1: Azure portfolio working demo live (Container Apps + AI Search) | Dan | June 30 |
| KR2: 2 LinkedIn posts published (technical + market framing) | Dan | May 15 |
| KR3: GitHub public snapshot clean with README leading with numbers | Dan | May 31 |

---

## Strategic Positioning Statement

> **For** Irish homeowners with smart meters who want to reduce electricity costs,  
> **Sparc Energy** is the only demand-response platform  
> **that** combines load forecasting, price intelligence, and real-time device control  
> **unlike** price comparison websites (backward-looking, no control) and smart home hubs (no forecasting, no price optimisation).

---

## Ansoff Matrix — Growth Path

| | Existing Markets (Ireland) | New Markets |
|--|---------------------------|-------------|
| **Existing Products** | Deepen: heat pump + EV owners in Ireland | Expand: UK (if Tibber/Octopus doesn't enter) |
| **New Products** | Extend: B2B aggregation / ESCO services | Diversify: Nordic/EU via Homey integration |

**Current focus:** Market Penetration (bottom-left). Nail Ireland before expanding.

---

## Funding Roadmap

| Stage | Vehicle | Amount | Timing |
|-------|---------|--------|--------|
| Now | AWS Activate | $5–25k credits | April 2026 — APPLY NOW |
| Q2 | New Frontiers (EI/Orla Byrne) | Non-dilutive + mentoring | Via NCI |
| Q2–Q3 | SEAI RD&D | Research grant | May–July 2026 window |
| Q3 | EI PSSF | €50–100k | Post-launch traction |
| 2027 | iHPSU / Dogpatch 2050 | Up to €1.2M | Jan 2027 cohort |

---

## MBA Knowledge Base

The UCD MBA at `/Users/danalexandrubujoreanu/UCD/` contains the strategic frameworks underpinning this document. Key resources:

| Module | File | Frameworks |
|--------|------|-----------|
| Competitive Strategy | `Contemporary Strategy Analysis - Robert M. Grant.pdf` | Porter 5 Forces, VRIN, Value Chain |
| Entrepreneurship | `2. Entrepreneurship/Lectures pdf/` | BMC, GEM data, pitching |
| Global & Corporate Strategy | `3. Global and Corporate Strategy/` | Corporate strategy, M&A |
| Digital Transformation | `2. Digital Transformation/` | Platform economics, digital disruption |
| Operations | `2. Operations and Innovation Management/` | Process optimisation |

**RAG tier:** `intel_mba` (planned — see DAN-81). Embeddings are local (zero cost); ingestion can proceed any time.  
**Query:** `python scripts/intel_ingest.py --tier mba --dir ~/UCD/"1. Competitive Strategy"` (start with priority modules)

---

*This document should be reviewed at the start of each quarter. Decisions that change strategic direction → ADR in `docs/adr/` + update here.*
