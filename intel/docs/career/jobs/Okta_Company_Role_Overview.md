---
title: "Okta AI Operations Lead — Okta_Company_Role_Overview"
document_type: job_spec
tier: career
company: Okta AI Operations Lead
role_title: Okta_Company_Role_Overview
date_added: "2026-03-31"
application_status: evaluating
status: active
---

# Okta — Company & Role Overview
*Recruiter screen: Tuesday 31 March 2026, 10:00am | Prep reference for Dan Bujoreanu*

---

## What Okta Does (In Plain English)

Okta is an **identity platform**. Their one job: make sure the right person can access the right system — and the wrong person can't.

Every time you log into Salesforce, Slack, or AWS at work and it just works (SSO), or you're asked for a second factor (MFA), or your account is automatically created when you join a company and deleted when you leave — that's Okta running in the background.

They do this at two layers:

| Layer | Product | Who it's for |
|---|---|---|
| **Workforce Identity** | Okta Identity Cloud | Companies securing their employees' access to tools |
| **Customer Identity** | Auth0 (acquired 2021) | Developers building login/auth into their own apps |

Workforce Identity is the core business. Auth0 is the developer-facing platform — it's what Stripe, JetBlue, and Peloton use to build secure login experiences for their customers.

---

## How Okta Works With Clients — Real Examples

**Enterprise SaaS companies** (e.g., Salesforce, Workday, ServiceNow)
→ Okta federates identity across all their tools. An employee at a 10,000-person company has one login that works across 80+ apps — Okta brokers every authentication event. When someone gets promoted, their access updates automatically. When they leave, one deactivation kills access everywhere.

**Healthcare** (e.g., Banner Health, Bupa)
→ HIPAA-compliant access control. Doctors and nurses access patient records from different devices and locations — Okta enforces context-aware MFA (is this a trusted device? Is this a normal location?). Temporary contractor access expires automatically.

**Financial services** (e.g., FedEx, ING)
→ Zero-trust architecture. Every access request is verified continuously, not just at login. Critical for regulatory compliance (SOC 2, ISO 27001, FCA, DORA).

**SaaS product companies** using Auth0 (e.g., Slack, Zoom, T-Mobile)
→ Use Auth0 SDK to build secure customer login into their own products — social login, passwordless, MFA, bot detection. Okta handles the identity infrastructure so the product team focuses on the product.

**Scale**: 18,000+ customers. 100+ million daily logins secured. 7,000+ pre-built app integrations.

---

## Where AI Fits Into Okta Right Now

Okta is building AI into its own product stack — and buying/deploying AI tools internally. Both create governance risk. Both are this role's responsibility.

**AI in Okta's products:**
- **Okta AI** — launched 2024. Uses LLMs to surface anomalous access patterns, generate natural language identity policy suggestions, and automate identity lifecycle tasks
- **Threat Intelligence** — ML models scoring login risk in real-time (location, device, behaviour, velocity)
- **Identity Security Posture Management** — AI scanning for misconfigurations across the identity estate

**AI tools used internally by Okta employees:**
- GitHub Copilot (engineering)
- AI writing and productivity tools (all teams)
- Internal LLMs for legal, support, and sales workflows
- Third-party AI vendors across every function

The problem: every one of these tools ingests data. Some of it is customer data, some is employee data, some is confidential commercial data. Okta sells trust. If an internal AI tool leaks customer data or violates data residency, the reputational damage is existential.

**That's why this role exists.**

---

## The Role: Internal vs External Focus

### Internal Focus (80% of the job)

| Responsibility | What it actually means |
|---|---|
| **AI Asset Library** | Maintain the living registry of every AI model, workflow, and third-party AI tool running inside Okta. Who owns it, what data it touches, what risk tier it's in. |
| **AIIA & Model Cards** | Before any AI tool goes live internally, run an impact assessment. Document the model. Classify the risk. This is the operational governance gate. |
| **Vendor Gatekeeper** | When a team wants to use a new AI tool (say, an AI meeting summariser that processes sales calls), you audit it first. Data retention policy? Opt-out mechanism? EU data residency? Pass → approved. Fail → blocked or negotiated. |
| **Policy-to-Playbook** | Okta's legal and privacy team sets the AI policy. You translate it into a practical runbook engineers and PMs can actually follow. Policy lives in Legal. Operations lives with you. |
| **Incident Response** | When something goes wrong (AI tool accesses data it shouldn't, a model behaves unexpectedly), Legal and Security need the data map fast. You own that map. |
| **Stakeholder navigation** | You sit between Legal (who sets the rules), Engineering (who builds), Privacy (who owns GDPR/CCPA), and Sales (who needs deals unblocked). No formal authority. Outcome ownership. |

### External Focus (20% of the job)

| Responsibility | What it actually means |
|---|---|
| **Customer-facing AI messaging** | Enterprise customers — especially in financial services, healthcare, government — will ask Okta: "What AI do you use, and how do you govern it?" This role ensures Okta's AI governance story is accurate, consistent, and credible externally. |
| **Sales unblocking** | A customer's security team has a question about how Okta uses AI in its product. The answer exists in your Asset Library and policy documents. You're the source of truth that turns a stalled procurement into a closed deal. |
| **Regulatory readiness** | EU AI Act, GDPR, CCPA, DORA (for financial services customers) — as regulations evolve, Okta needs to demonstrate its AI governance posture to auditors and enterprise buyers. You maintain the evidence. |

---

## Why You Want This Role — Dan's Authentic Motivation

Use this as a prompt for the call — don't recite it, but know the genuine answer:

**The role is where governance becomes product.**
Most governance roles are reactive — policies written after the risk materialises. Okta's AI Operations Lead is proactive: you build the system that lets the company ship AI features at speed without hitting regulatory or reputational walls. That's not compliance overhead — it's the infrastructure that makes velocity possible.

**It's the identity layer at the exact moment AI is breaking it.**
AI agents are making autonomous decisions — accessing systems, taking actions, impersonating humans. The identity question ("is this the right entity doing the right thing?") is suddenly one of the hardest problems in enterprise technology. Okta sits at that intersection. Being inside Okta when that problem is being solved is a genuinely interesting place to be.

**The governance work you've done maps directly.**
You've built an AIIA, a Model Card, a Data Provenance chain, and a Data Lineage document — not because a company required you to, but because you applied the right framework to your own system. That's not a career pivot. It's evidence that you already think this way.

**The role reports to Legal, not Engineering.**
That's unusual for an ops role — and deliberate. It signals that Okta takes AI governance seriously enough to put it inside Legal, not as an afterthought inside an engineering function. For someone with your operational + governance background, reporting line into Legal gives you the authority to actually enforce standards, not just recommend them.

---

## One Line for the Recruiter: Why Okta, Why Now

> *"Okta is solving the identity problem at exactly the moment AI is making it harder — agents acting autonomously, AI tools accessing data at scale, the regulatory environment tightening. The governance infrastructure this role builds isn't overhead; it's what makes Okta's AI product story credible to enterprise customers. That combination — technical governance + cross-functional delivery + trust as a competitive advantage — is where I've spent the last decade, and it's exactly where I want to operate."*

---

## Your Governance Artefacts — What They Are & Why They Matter Here

These four documents live at `/building-energy-load-forecast/docs/governance/`. They are direct evidence of the operational patterns Okta needs this role to build and scale.

---

### 1. MODEL_CARD.md
**What it is:** A standardised factsheet for the LightGBM H+24 forecasting model, following the Mitchell et al. (2019) / Hugging Face format.

**What it documents:**
- Model architecture, task, version, author, publication (AICS 2025 Springer)
- Intended use and explicitly out-of-scope uses
- Training data: COFACTOR Drammen — 45 Norwegian buildings, Jan 2018–Mar 2022, ~3.9M readings
- Performance: H+1 R²=0.9947 (RF), H+24 R²=0.975 (Drammen), R²=0.963 (Oslo cross-city validation); home trial MAE=0.171 kWh/hr
- Ethical considerations: privacy (building-level only, no occupant identification), fairness (tested on Norwegian data — Irish generalisation caveat documented), environmental impact (LightGBM chosen in part for <1% compute cost vs LSTM)
- Known limitations and caveats

**Why it matters for Okta:** Every AI tool in Okta's Asset Library needs a document like this. The Model Card is the entry in the library — without it, you don't know what the model does, who's accountable, or what its failure modes are. You've built one from scratch for a production system.

---

### 2. DATA_PROVENANCE.md
**What it is:** A source-by-source record of where every dataset came from, under what terms it's used, and how it was handled.

**What it documents (5 sources):**

| Source | Type | Consent basis |
|---|---|---|
| COFACTOR Drammen | Norwegian building AMR data | Academic research licence, NCI Dublin |
| SINTEF Oslo | Cross-city validation set | Academic, no redistribution |
| OpenMeteo | Weather reanalysis | Open-source, CC attribution |
| ESB Networks smart meter | Personal home trial data | GDPR Art. 6(1)(a) — own data, explicit consent |
| myenergi Eddi API | Personal device telemetry | OAuth token, personal device |

Also includes: full GDPR compliance table per source, data residency decisions, audit trail, regulatory coverage (EU AI Act Art. 10, CRU202517).

**Why it matters for Okta:** When a vendor AI tool processes Okta customer data, someone has to document: what data did it touch, under what licence, with what retention policy? This document is the template for that audit. You've done it for five heterogeneous sources with different regulatory frameworks. That's the audit skill.

---

### 3. AIIA.md
**What it is:** An AI Impact Assessment for the LightGBM H+24 system — adapted from Google's AI Impact Assessment template, UK ICO AI Auditing Framework, and EU AI Act Article 9.

**What it documents:**
- EU AI Act classification: **Limited Risk (Article 52)** — transparency obligations apply; not High Risk
- Affected parties: primary users, ESB Networks, energy suppliers, grid-level systemic effects
- Direct harms table (5 harms with likelihood, severity, and mitigation status for each)
- Systemic harms (mass load-shifting, grid effects at scale)
- Benefits quantified: €150–400/yr household saving, carbon reduction estimate
- Risk rating table
- 13 safeguards with implementation status (✅ / 🔄 / ⬜)
- Transparency obligations (EU AI Act Art. 52): disclosure requirements, user notification
- Assessment conclusion: **Proceed to MVP** with documented conditions

**Why it matters for Okta:** This is the exact artefact the JD calls "AIIAs" — the operational workflow Bullet 4 describes. You haven't just heard of an AIIA; you built one with a real harms table using actual home trial data. When the recruiter asks "have you worked with AI impact assessments?" — this is a concrete, specific answer.

---

### 4. DATA_LINEAGE.md
**What it is:** A complete 8-stage map of data movement from raw source to physical device action, including quality gates, failure modes, and audit query templates.

**What it documents:**

```
Stage 1 — Raw Ingestion (COFACTOR CSVs, OpenMeteo API, ESB/Eddi API)
    ↓ Quality Gate 1: schema, timestamp format, completeness ≥70%
Stage 2 — Normalisation & Merge (Wh→kWh, weather join, gap-fill)
    ↓ Quality Gate 2: buildings <70% completeness dropped
Stage 3 — Feature Engineering (23 features: lag, rolling, calendar, weather)
    ↓ Quality Gate 3: feature variance check, NaN threshold
Stage 4 — Model Training (LightGBM, time-series cross-validation)
    ↓ Quality Gate 4: R² ≥ 0.95 on validation set
Stage 5 — Inference (H+1 to H+24 multi-step forecasting)
Stage 6 — Decision Engine (if/then logic: forecast + tariff → schedule recommendation)
Stage 7 — Actuation (WFC01 smart valve / Eddi diverter command)
Stage 8 — Audit Trail (JSON log: timestamp, inputs, forecast, decision, action)
```

Also includes: bug impact table (bugs found in ERRORS.md mapped to pipeline stage and effect on outputs), audit query section for incident investigation.

**Why it matters for Okta:** Bullet 3 of the JD — "Data Provenance & Lineage Architecture: Map and document the entire lifecycle of data, from source origins to final usage, ensuring every AI output is explainable, audit-ready, and legally sound." This document is that, for a live system. You can say: "I've built an 8-stage lineage document with quality gates, failure mode mapping, and audit queries — for a production system I built myself. That's the capability I'd bring to Okta's AI Asset Library."

---

## Summary: What These Four Documents Prove

| Okta JD Bullet | Your Governance Artefact |
|---|---|
| AI Asset Library (source of truth for all models) | MODEL_CARD.md — the entry format for any model in the library |
| Data Provenance & Lineage Architecture | DATA_PROVENANCE.md + DATA_LINEAGE.md — built for a 5-source, 8-stage pipeline |
| Operationalizing Ethics at Scale (AIIAs & Model Cards) | AIIA.md — EU AI Act classified, harms table with real data, 13 safeguards |
| Rigorous Third-Party Auditing (data retention, opt-out) | DATA_PROVENANCE.md — per-source compliance table including GDPR, consent, residency |

Most candidates will describe having seen these frameworks. You built them last week.

---

*Document created 2026-03-31. Okta screen: Tuesday 31 March 2026, 10:00am.*
