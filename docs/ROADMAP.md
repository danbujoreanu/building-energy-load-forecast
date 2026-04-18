# Sparc Energy — Product Roadmap

**Last updated:** 2026-04-18 | **Sync source:** Linear (team DAN)  
**North Star:** € saved per active household per year  
**Q2 2026 target:** Website live · 3 test users · AWS Activate · Journal submitted

> Sync this file at each sprint planning: `python scripts/sync_roadmap.py` (DAN-82)  
> For full issue detail → linear.app (team DAN)

---

## Now — Sprint 1 (2026-04-21 → 2026-05-04)

| Issue | Feature | Track | Status |
|-------|---------|-------|--------|
| DAN-69 | AWS Activate credits application | Commercial | 🔴 **Due April 25** |
| DAN-24 | Ingest full intel corpus (all tiers) | Intel | 🟡 In Progress |
| — | Intel RSS feed connector (DAN-81) | Intel | 🟡 Just built |
| DAN-65 | Supabase project setup (website backend) | Engineering | 🟡 Planned |
| — | Sparc Strategy + Governance docs | Product | ✅ Done this session |

---

## Next — Sprint 2 (2026-05-05 → 2026-05-18)

| Issue | Feature | Track | Status |
|-------|---------|-------|--------|
| DAN-10–14 | Journal paper — final sections + submission | Research | 📋 Planned |
| — | Website landing page (energy.danbujoreanu.com) | Product | 📋 Planned |
| DAN-80 | Azure/LangChain portfolio project | Engineering | 📋 Planned |
| — | LinkedIn posts (2 of 3 from docs/linkedin_posts.md) | Commercial | 📋 Planned |
| — | Roadmap sync script (DAN-82) | Engineering | 📋 Planned |

---

## Q2 2026 Backlog (May–June)

### Engineering
| Issue | Feature | Size |
|-------|---------|------|
| DAN-53 | Mac Mini M4 24GB — receive + migrate (June) | L |
| DAN-80 | Azure dual-stack demo (Container Apps + AI Search) | XL |
| DAN-67 | mySigen / Sigenergy API integration (eval) | M |
| DAN-38 | Eddi schedule optimisation from forecast | M |

### Product
| Issue | Feature | Size |
|-------|---------|------|
| DAN-60 | Consumer app Phase 2 spec | L |
| DAN-22 | Morning brief v2 (personalised, push notification) | M |
| DAN-40 | LLM Energy Advisor (Claude haiku-4-5) | L |

### Commercial
| Issue | Feature | Size |
|-------|---------|------|
| — | CRU ESCO registration research + timeline | M |
| — | saveon.ie collaboration agreement | S |
| — | New Frontiers / SEAI RD&D application | L |

### Research / Intel
| Issue | Feature | Size |
|-------|---------|------|
| DAN-81 | RSS/Substack feed ingestion (just built) | ✅ |
| — | MBA RAG tier (intel_mba) — ingest Grant + Entrepreneurship | M |
| DAN-8 | PhD research track — application prep | L |

---

## Phase 2 — Q3/Q4 2026 (Post Mac Mini)

| Feature | Mandate | Notes |
|---------|---------|-------|
| P1 port hardware adapter (Pi Zero 2W + DSMR) | Commercial | Software activation late 2026 |
| Consumer app mobile (Next.js PWA) | Commercial | DAN-60 |
| SMDS automatic data sync | Commercial | Pending ESB Networks SMDS launch |
| Dynamic pricing integration (BGE, Electric Ireland) | Commercial | CRU June 2026 mandate live |
| Homey integration (distribution) | Commercial | App marketplace listing |
| Multi-household dashboard (B2B) | Commercial | Aggregator / ESCO tier |

---

## North Star Tracking

| Quarter | Households | Avg € saved/year | Notes |
|---------|-----------|-----------------|-------|
| Q2 2026 | 1 (test) | €178 (identified) | Manual CSV, Maynooth |
| Q3 2026 | 3 (target) | TBD | First external users |
| Q4 2026 | 10 (target) | €300+ (target) | P1 or CSV |

---

## Done ✅

| Issue | Feature | Quarter |
|-------|---------|---------|
| DAN-5–8 | LightGBM H+24 pipeline (MAE 4.03, R²=0.975) | Q1 2026 |
| DAN-32–33 | Demand-response control engine | Q1 2026 |
| DAN-20–27 | Energy Intel RAG (LlamaIndex + ChromaDB) | Q1 2026 |
| DAN-79 | Career Intel RAG (job spec analysis) | Q2 2026 |
| DAN-53 | Infrastructure decision (Mac Mini M4 + AWS hybrid) | Q2 2026 |

---

## Connection to Business Model Canvas

| Roadmap track | BMC block |
|--------------|-----------|
| ML pipeline, accuracy | Value Proposition (forecast quality) |
| P1 port, SMDS, CSV onboarding | Channels (data access path) |
| Consumer app, website | Channels (customer acquisition) |
| Eddi, dynamic pricing, Homey | Key Activities (device control) |
| saveon.ie, SEAI, ESB Networks | Key Partnerships |
| AWS Activate, SEAI RD&D | Cost Structure / Funding |

*Full BMC: `docs/STRATEGY.md`*

---

*Rule: this file is a snapshot. Issues move daily — Linear is authoritative for status.  
This file provides the PM-level narrative and interview artefact.*
