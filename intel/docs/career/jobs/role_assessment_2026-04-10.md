---
title: "Irish Life — role_assessment_2026-04-10"
document_type: job_spec
tier: career
company: Irish Life
role_title: role_assessment_2026-04-10
date_added: "2026-04-13"
application_status: evaluating
status: active
---

# Interview Prep Brief — AI Portfolio Architect, Irish Life
**Date:** 2026-04-10
**Status:** Not yet applied — assess and apply

---

## Role Fit Summary

### Why Dan is a strong fit
- **Governance artefacts in production** — The JD lists "model cards, documentation templates, transparency artefacts, audit-ready controls" as *desirable*. Dan has all four built for a live production system (Model Card, AIIA, Data Provenance, Data Lineage). Most candidates will describe these concepts. Dan built them.
- **EU AI Act hands-on** — Article 52 classification applied to his own system. Not theoretical — he understands what a conformity assessment looks like from the inside.
- **Translating governance into operational frameworks** — S003 (Governance Builder): 30+ stakeholders, RACI, VP friction dissolved through structural clarity. This is exactly "translate policy into architectural controls."
- **Published AI research** — AICS 2025, Springer CCIS. LightGBM R²=0.975 at <1% compute cost of LSTM. Ryan-credibility-level technical depth.
- **Cross-functional delivery at scale** — Meta: Engineering, Sales, Legal, Finance, Data Science simultaneously. 15+ years. The JD asks for exactly this profile.
- **MSc AI with governance + ethics module** — Not just a practitioner. Academically grounded in the regulatory framework.

### Weak spots to address proactively
| Gap | How to frame it |
|-----|----------------|
| Azure-specific ecosystem (Azure ML, Azure OpenAI, Fabric) | "Strong Vertex AI / GCP experience; actively exploring Azure equivalents — the concepts transfer directly and I'm a fast mover on tooling" |
| MLOps / LLMOps tooling maturity | "I have ML pipeline experience end-to-end; formalising MLOps discipline is a deliberate next step — the Energy project is the proving ground" |
| Financial services / life assurance | "PayPal (regulatory + compliance data analytics) is adjacent; GDPR, CRU, and EU AI Act are the frameworks I've worked within" |
| "Architect" title | Frame as: "I work at the intersection of governance strategy and operational delivery — I translate frameworks into systems that teams actually use" |

### Salary
Irish Life doesn't publish a range. For a senior architect role at ILG, market is likely **€95k–€120k**. Dan's floor is **€70k** (safety net) but don't anchor there — open at €95k–€110k for this role. If asked early:
> "I'm targeting €95k–€110k based on the seniority and scope of the role — happy to discuss the full package once we've both confirmed fit."

---

## Key Talking Points (Top 5)

### 1. The Four Governance Artefacts
**Claim:** I've built the exact artefacts this role requires — in production, not as templates.
**Evidence:** Model Card (LightGBM forecasting model), AI Impact Assessment (EU AI Act Article 52), Data Provenance chain (5 sources, GDPR + CRU compliant), Data Lineage map (8 stages, raw CSV to actuation).
**Number:** 4 artefacts, 1 live production system, 0 prior examples to copy.
**Maps to:** "Provide architectural artefacts and evidence for the Central AI Register, high-risk classification, and audits."

### 2. Governance Framework That People Actually Use
**Claim:** I've built governance infrastructure that stakeholders adopted voluntarily — not by mandate.
**Evidence:** S003 — Global Ads Testing programme. RACI + quarterly prioritisation sprint + statistical thresholds. VP friction dissolved without a single difficult conversation.
**Number:** 30+ stakeholders, $10M+ quarterly budget, 110+ experiments/quarter.
**Maps to:** "Embed controls into solution designs... translate complex regulatory and technical requirements into clear, business-friendly guidance."

### 3. Published AI Research — Technical Credibility
**Claim:** My AI work is peer-reviewed, not just practitioner-level.
**Evidence:** AICS 2025, Springer CCIS. Compared 8 forecasting approaches across 45 buildings. LightGBM with feature engineering: R²=0.975, <1% compute cost of LSTM.
**Number:** 98% accuracy, <1% compute cost, published 2025.
**Maps to:** "Strong experience delivering complex AI and data-driven solutions... analytics, ML, and enterprise AI."

### 4. Cross-Functional Delivery at Meta Scale
**Claim:** I've coordinated AI governance across Engineering, Legal, Finance, Data Science, and Sales simultaneously — at a company with $100B+ ad portfolio.
**Evidence:** S001 (Scale Architect) + S003 (Governance Builder) combined. Operations scaled 600% with no proportional headcount growth.
**Number:** 2M annual cases, 45% resolution time reduction, 5 FTE capacity unlocked.
**Maps to:** "Excellent collaboration across IS, especially with data science, engineering, and AI governance teams."

### 5. EU AI Act — Practical Not Theoretical
**Claim:** I've classified a live AI system under the EU AI Act and documented it.
**Evidence:** AIIA for energy load forecasting model — Article 52 classification, risk category, transparency obligations, human oversight requirements. Built as a reusable artefact.
**Number:** Article 52 classification, 1 live system, cross-referenced against GDPR and CRU.
**Maps to:** "Practical experience integrating regulatory and compliance frameworks including EU AI Act into AI delivery and supporting audits and conformity assessments."

---

## Project Assets to Reference

| Asset | What it demonstrates | Where to find it |
|-------|---------------------|-----------------|
| **AI Impact Assessment (AIIA)** | EU AI Act Article 52 classification, risk category, transparency obligations | `building-energy-load-forecast/docs/governance/AIIA.md` |
| **Model Card** | Governance artefact for production ML model — intended use, limitations, bias considerations | `building-energy-load-forecast/docs/governance/MODEL_CARD.md` |
| **Data Provenance** | 5-source chain with GDPR and CRU compliance mapped | `building-energy-load-forecast/docs/governance/DATA_PROVENANCE.md` |
| **Data Lineage** | 8-stage map from raw CSV to actuation | `building-energy-load-forecast/docs/governance/DATA_LINEAGE.md` |
| **Published paper (AICS 2025)** | Technical credibility — peer-reviewed ML research | Springer CCIS, presented TAI Conference 2025 |
| **GitHub repo (public)** | Full project visibility — code, governance docs, diagrams | https://github.com/danbujoreanu/building-energy-load-forecast |

---

## Questions to Ask

**Q1 — Governance maturity baseline:**
> "The JD mentions the Central AI Register and high-risk classification — where is Irish Life currently in terms of that classification exercise? Are there systems already classified, or is part of this role building that inventory from scratch?"

*Why: Tells you whether you're inheriting something or building net new. Shapes every answer about your operating model.*

**Q2 — Architecture authority:**
> "The role sits in Customer Solutions but represents portfolio interests at the ILG Architecture and AI Governance Boards. How much architectural authority does this role have versus advisory influence? Is this a decision-making seat or a recommendation seat?"

*Why: Critical for understanding whether this is a builder or a policy role. Your background is builder.*

**Q3 — The EU AI Act timeline pressure:**
> "Given the EU AI Act's compliance timelines, what's the most urgent governance gap you're trying to close in 2026? What's keeping the AI Governance Lead up at night?"

*Why: Shows regulatory awareness, positions you as someone who understands the urgency, gets them talking about the real problem.*

**Q4 — Azure maturity:**
> "The JD mentions Azure AI and cloud-native solutions — how mature is the Azure AI footprint currently? Is this greenfield architecture or rationalising an existing estate?"

*Why: Honest signal-gathering on the Azure gap. If it's greenfield, your learning curve is lower. If it's legacy rationalisation, the gap matters more.*

**Q5 — Definition of success:**
> "At 12 months — what would tell you this role is working? What does the governance landscape look like if we get this right?"

*Why: Closes the conversation strategically. Their answer tells you whether the role is achievable and whether the organisation is serious about AI governance.*

---

## Watch Points

### Salary
No published range. Senior architect at ILG — open at €95k–€110k. Don't anchor below €85k publicly. Floor is €70k (safety net, not the opening). Don't volunteer a number — let them anchor first.

### Azure gap
This is the biggest structural gap. Don't hide it — frame it:
> "My cloud AI work has been on GCP and local deployment. Azure is the next environment I'm actively building in — the concepts transfer directly and I move fast on tooling. I'd want to be honest that Azure-specific depth is something I'd be building in the first 90 days, not something I'm bringing on day one."

Honesty here builds more credibility than overbluffing.

### "Architect" vs "Programme Manager"
The JD uses "Architect" but the responsibilities read like a senior governance programme lead with technical credibility. Your framing:
> "I work at the intersection — I can produce the artefacts and I can drive the adoption. The architecture only matters if the teams actually follow it."

### Prior EirGrid rejection (2026-01)
Irish Life is not EirGrid, but both are Irish semi-state/regulated sectors. The previous EirGrid rejection was "analyst level — Dan is over-qualified in governance, under-qualified in grid ops." This role is the inverse: governance is the core, not the sector. No direct parallel.

### Known rejection patterns to avoid
- Don't lead with "programme management" framing — this role needs technical credibility first
- Don't undersell the governance artefacts — they are the differentiator
- Don't over-explain the employment gap — Q4 answer covers it cleanly

---

## Logistics Checklist
- [ ] Role not yet applied — apply via Irish Life careers portal
- [ ] No salary range published — research ILG compensation via Glassdoor/LinkedIn before screen
- [ ] Interview format unknown — expect: HR screen → technical/governance deep-dive → panel
- [ ] BrightHire opt-out: if video interview uses BrightHire, opt out before joining
- [ ] Tech check if remote: stable connection, professional background, headset
- [ ] Governance artefacts: have GitHub links ready — https://github.com/danbujoreanu/building-energy-load-forecast/tree/main/docs/governance

---

## Cross-Project Flags

**Energy project → Irish Life readiness:**
- Governance artefacts are complete and public ✅
- **Gap to close:** Add MLOps/model monitoring (MAE/RMSE drift dashboard) to the Energy project — this directly addresses the MLOps maturity gap Irish Life will probe
- **Gap to close:** Azure component — consider porting one pipeline element to Azure ML to demonstrate Azure-native capability before interview

**Cognitive Focus / Artefact suggestion:**
- If the RENEW/Fabiano PhD path develops, the regulatory AI classification work overlaps with Irish Life's Central AI Register requirement — worth noting as a research connection

**Priority:** Apply now. Governance artefacts are an exact match. Azure gap is real but bridgeable with honest framing. This role is a better fit than Stripe (sales ops) and EirGrid (market ops).
