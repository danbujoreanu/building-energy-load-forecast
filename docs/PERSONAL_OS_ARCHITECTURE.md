# Personal Operating System — Architecture Reference

**Last updated:** 2026-04-18 | **Maintained by:** Dan Bujoreanu

> This document describes how all projects, tools, and knowledge bases connect.
> Rule: Obsidian is the master record for everything. Linear is the public-facing task tracker.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Dan's Personal Operating System                  │
│                                                                         │
│  KNOWLEDGE LAYER           TASK LAYER           INTELLIGENCE LAYER     │
│  ─────────────────         ──────────           ───────────────────    │
│  Obsidian Vault            Linear               ChromaDB + Claude      │
│  (everything private)      (roadmap only)       (RAG queries)          │
│                                                                         │
│  ┌──────────────┐          ┌───────────┐        ┌──────────────────┐   │
│  │ Energy Sparc │──────────│ DAN team  │        │ intel_operational│   │
│  │ Career       │          │           │        │ intel_strategic  │   │
│  │ Gardening    │──────────│ GARDEN    │        │ intel_research   │   │
│  │ Health       │          │ (Digital  │        │ intel_market     │   │
│  │ Financials   │          │ Twin)     │        │ intel_career     │   │
│  │ PhD          │          └───────────┘        └──────────────────┘   │
│  │ Orchestrator │                                                       │
│  └──────────────┘                                                       │
│         │                                                               │
│         ▼                                                               │
│  Claude Code Sessions (per-project context)                            │
│  • Energy Sparc session → reads /building-energy-load-forecast/        │
│  • Career session       → reads /Personal Projects/Career/             │
│  • Gardening session    → reads /Personal Projects/Gardening/          │
│  • Orchestrator session → cross-project radar, briefings               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Obsidian — Master Knowledge Base

**Location:** `~/Personal Projects/` + within each project repo

**Scope:** ALL projects, ALL private information. Obsidian sees everything.

| Vault Section | Contains | Privacy Level |
|--------------|----------|---------------|
| `Energy Sparc/` | Architecture decisions, product specs, research notes | Private |
| `Career/` | Job specs (Obsidian source), research notes, interview preps | Strictly private |
| `Career/Applications/` | Live job applications — auto-ingested to ChromaDB via `career_watch.py` | Strictly private |
| `Career/Research_Intel/` | Company research, LinkedIn profiles of people studied (NEVER in git) | Strictly private |
| `Gardening/` | Garden logs, plant database, seasonal plans | Private |
| `Health/` | Medical, cognitive focus, IVF, medications | Never shared |
| `Financials/` | Degiro, Schwab, budget | Never shared |
| `PhD/` | Applications, research directions, contacts | Private |
| `0. Orchestrator/` | Cross-project radar, daily briefings, master dashboard | Private |

**Rule:** Obsidian is the ONLY system that tracks Health, Financials, and personal life.
Linear is for product/engineering roadmaps only. Nothing personal goes to Linear.

---

## Layer 2: Linear — Public Roadmap Tracker

**URL:** linear.app | **Plan:** Free (max 2 teams)

**What Linear IS:**
- Engineering and product roadmaps
- Sprint planning, feature tracking, bug tracking
- Dependencies between issues
- Public-facing (could be shared with collaborators)

**What Linear IS NOT:**
- Personal life (Health, Financials, Relationships)
- Confidential career intelligence (job specs, interview notes)
- Private research notes

### Current Teams

| Team | Key | Scope |
|------|-----|-------|
| Sparc Energy | DAN | ML pipeline, API, consumer app, intel RAG, commercialisation |
| Digital Twin Gardening | GARDEN | Garden sensor data, plant models, seasonal automation |

### Issue Hierarchy
```
Initiative (company-wide goal, multi-quarter)
  └── Project (time-bound deliverable, cross-team, weeks)
        └── Issue (concrete task, one person, hours-days)
```

**Workflow:** Issues in Linear → linked to docs in Obsidian/docs/ → context in Claude sessions.

---

## Layer 3: ChromaDB — RAG Intelligence Layer

**Location:** `~/building-energy-load-forecast/data/chromadb/`
**Access:** via `intel/retrieval.py` → `query_tier(tier, query)`

### Collection Map

| Collection | Project | Document Types |
|-----------|---------|---------------|
| `intel_operational` | Energy Sparc | Architecture docs, API docs, runbooks |
| `intel_strategic` | Energy Sparc | Market research, competitive analysis, regulatory docs |
| `intel_research` | Energy Sparc | Papers, thesis, academic references |
| `intel_market` | Energy Sparc | Commercial landscape, pricing, go-to-market |
| `intel_career` | Career (private) | Job specs (from Obsidian auto-ingest), Dan's profile |

**Key rule:** `intel_career` is local-only and gitignored. Job specs and personal profiles 
never appear in git or any public system. See `intel/docs/career/` → `**/.gitignore`.

**Future:** `intel_garden` tier for Digital Twin Gardening (plant databases, grow guides).

---

## Layer 4: Claude Code — Per-Project Sessions

Each project has its own Claude Code session with relevant context pre-loaded.

### Session Architecture

```
/building-energy-load-forecast/      ← Energy Sparc session
  CLAUDE.md                          ← project-specific rules (gitignored)
  docs/README.md                     ← knowledge navigation hub
  
~/Personal Projects/Career/          ← Career session  
  CLAUDE.md                          ← career-specific rules

~/Personal Projects/Gardening/       ← Gardening session
  CLAUDE.md                          ← garden-specific rules
  
~/Personal Projects/0. Orchestrator/ ← Orchestrator session
  CLAUDE.md                          ← cross-project rules
  CROSS_PROJECT_RADAR.md             ← active issues across all projects
  DAILY_BRIEFING.md                  ← morning brief template
```

### Cross-Project Connections

Some items belong to multiple projects. The convention:

| Issue Type | Primary Home | Cross-Reference |
|-----------|-------------|-----------------|
| PhD Decarb-AI | Career → Obsidian | DAN-8 (Sparc research track) |
| Mac Mini M4 | DAN-53 (Sparc infra) | Links to Career (portfolio) + Garden (local hosting) |
| Azure portfolio | Career (job market) | DAN-80 (Sparc tech debt / dual-stack) |
| journal paper | DAN-10–14 (Sparc) | PhD application (Career) |
| P1 port hardware | DAN (Sparc product) | No career link |

---

## Data Flow: Job Application → Interview Brief

```
Obsidian vault
  └── Career/Applications/{Company}/{Role}.md (you write/paste JD)
        │
        ▼ (career_watch.py polls every 2 seconds)
  Auto-enriched with YAML frontmatter (company, role, date inferred)
        │
        ▼ (ingest_job_spec() → ingest_file(tier="career"))
  ChromaDB intel_career collection (local only, gitignored)
        │
        ▼ (career_ingest.py --match "Company Role")
  Gemini Flash generates:
    • Fit summary (strengths / gaps vs Dan's profile)
    • Resume tailoring notes
    • Tech stack gaps for Sparc portfolio
        │
        ▼
  Claude Code Career session → interview prep brief
```

---

## Data Flow: Energy Market Research → Sparc Decisions

```
Source doc (PDF / web article / regulatory notice)
        │
        ▼ (intel_ingest.py --tier strategic --file doc.pdf)
  ChromaDB intel_strategic collection
        │
        ▼ (FastAPI /intel/query endpoint OR direct query_tier())
  LlamaIndex retrieval → Gemini Flash synthesis
        │
        ▼
  Gradio Intel interface (port 7861) OR Claude Code session
        │
        ▼ → Linear issue + docs/ update
```

---

## Token Efficiency Rules

These rules keep Claude Code sessions fast and cheap:

| Rule | Implementation |
|------|---------------|
| Direct API over MCP | Linear via Python+GraphQL (10-50× fewer tokens than MCP tool schema loads) |
| Known path → Read tool | Only use Agent for open-ended multi-file search |
| Batch mutations | All Linear updates in one Python script |
| Cache context | CLAUDE.md in each project keeps session context warm |
| Gitignore private data | intel/docs/career/ never in git; avoids accidental sharing |

---

## What Each System Owns (Hard Rules)

```
System          Owns                                    Never Has
─────────────── ──────────────────────────────────────  ────────────────────────
Obsidian        ALL knowledge (every project)           Nothing excluded
Linear          Engineering/product roadmaps only       Personal life, Health, PII
ChromaDB        RAG-queryable knowledge (all projects)  Raw PII of other people
Claude Code     Active session context + code           Nothing persisted between sessions
Git/GitHub      Code, docs, configs                     Career intel, personal profiles, secrets
```

---

## Future: Digital Twin Gardening

When the Gardening project matures to need RAG:
- New collection: `intel_garden`
- Source documents: plant database .md files, grow guides, seasonal calendar
- Session: `~/Personal Projects/Gardening/` with `CLAUDE.md`
- Linear team: GARDEN (already created)
- Sensor integration: TBD (Mac Mini M4 as hub, June 2026)

The same LlamaIndex + ChromaDB infrastructure as Sparc. Zero new dependencies.
