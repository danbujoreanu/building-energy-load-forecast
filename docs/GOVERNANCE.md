# Sparc Energy — Program Governance & Sprint Cadence

**Last updated:** 2026-04-18 | **Owner:** Dan Bujoreanu

> Governance at a lean solo/small-team level. Scales to team naturally — roles are defined 
> even while Dan holds all of them, so onboarding a co-founder or engineer is clean.

---

## Sprint Cadence

### Definition
- **Sprint length:** 2 weeks
- **Start day:** Monday
- **Current sprint:** Sprint 1 — 2026-04-21 → 2026-05-04
- **Sprint 2:** 2026-05-05 → 2026-05-18

### Sprint Ceremonies (solo-adapted)

| Ceremony | When | Duration | Output |
|----------|------|----------|--------|
| **Sprint Planning** | Monday morning (sprint start) | 30 min | Top 5–8 issues moved to In Progress in Linear |
| **Daily Check-in** | Every morning | 5 min | 3 bullets: done yesterday / doing today / blockers (Obsidian daily note) |
| **Sprint Review** | Friday EOD (sprint end) | 20 min | What shipped? What didn't? Update Linear statuses |
| **Retrospective** | Friday after review | 10 min | 1 thing to keep / 1 to change (Obsidian note) |
| **Quarterly OKR review** | First Monday of new quarter | 60 min | OKRs scored, new OKRs set, STRATEGY.md updated |

### Definition of Done (DoD)
A Linear issue is **Done** when ALL of the following are true:
- [ ] Code written and tested (unit or integration test exists)
- [ ] `docs/` updated if architecture/behaviour changed
- [ ] Linear issue status set to Done + acceptance criteria checked
- [ ] No new TODO/FIXME introduced without a corresponding Linear issue
- [ ] No secrets or personal data in committed code

### Definition of Ready (for Sprint Planning)
An issue is **ready to be pulled into a sprint** when:
- [ ] Title is clear and actionable
- [ ] Acceptance criteria defined (≥3 bullet points)
- [ ] Dependencies identified (linked in Linear)
- [ ] Size estimate: S (<2h) / M (2–8h) / L (8–16h) / XL (>16h, split it)

---

## Team Roles (current → target)

| Role | Now | Target (Phase 2) |
|------|-----|-----------------|
| Product Owner | Dan | Dan |
| Tech Lead / ML Engineer | Dan | Dan + contractor |
| Designer | Claude Design | Freelance designer |
| Commercial / GTM | Dan | Co-founder or advisor |
| PhD Research track | Dan | Dan + supervisor |

---

## Decision Framework

### ADR (Architecture Decision Record)
Every significant technical decision → `docs/adr/ADR-NNN.md`.

Trigger: any decision that:
- Changes the tech stack
- Affects data schema or storage
- Has security or privacy implications
- Would take >1 sprint to reverse

Format: Context / Decision / Consequences / Status  
Index: `docs/adr/`

### Product Decision Gate
Before building any feature:
1. Does it move the North Star Metric (€ saved/household/year)?
2. Is it in the current quarter's OKRs?
3. Is the acceptance criteria written in Linear?

If no to any → park in Backlog with a note.

### Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| SMDS delay (ESB Networks) | High | Medium | MVP path is manual CSV upload — not blocked |
| AWS credits run out | Medium | High | Apply AWS Activate now (April 25 deadline) |
| CRU registration requirement | Medium | High | Research timeline; register early |
| Tibber/Octopus Irish entry | Low | High | Speed to market + regulatory moat (ESCO) |
| Model drift (Irish data patterns) | Low | Medium | 7-day rolling MAE monitoring (deployed) |
| Key person risk (solo) | High | High | Documentation standard (this repo) + Obsidian backup |

---

## Linear Workflow

### Labels
| Label | Meaning |
|-------|---------|
| `Engineering` | Code, infrastructure, ML pipeline |
| `Product` | Features, UX, specs |
| `Intel` | RAG, market research, knowledge base |
| `Research` | ML experiments, paper, PhD |
| `Commercial` | GTM, funding, partnerships |
| `Bug` | Defects in production |
| `Urgent` | Blocks a sprint or deadline |

### Priority levels
| Linear Priority | Meaning |
|----------------|---------|
| Urgent | Blocks something; do today |
| High | In current sprint |
| Medium | Next sprint candidate |
| Low | Backlog |
| No priority | Ideas, someday/maybe |

### Automation rules
- When an architectural decision is made in a Claude Code session → Linear issue created immediately (Python+GraphQL, no manual step)
- When a doc is created/updated → Linear issue linked or updated
- Sprints tracked via Linear labels: `Sprint N` applied at planning

---

## Roadmap Sync Protocol

`docs/ROADMAP.md` is updated:
- **At sprint planning:** move completed items to Done, pull in new items
- **At quarterly review:** full refresh from Linear export

To regenerate ROADMAP.md from Linear:
```bash
export $(cat .env | grep -v '#' | grep -v '^$' | xargs)
python scripts/sync_roadmap.py  # (planned — DAN-82)
```

---

## Programme Governance — Cross-Project

The Orchestrator Claude session (`Personal Projects/0. Orchestrator Command Centre/`) maintains the cross-project view:
- All projects: Energy Sparc, Career, Digital Twin Gardening, Health, Financials, PhD
- MASTER_DASHBOARD.md = single view of active threads across all projects
- CROSS_PROJECT_RADAR.md = issues that span multiple projects

**Energy Sparc ↔ Orchestrator handoff points:**
- When a Sparc decision has career implications → flag to Orchestrator session
- When MBA RAG is ready → Orchestrator session triggers ingestion (out of Sparc remit)
- PhD application → Career session primary; DAN issues (DAN-8, DAN-10–14) are the Sparc research track

---

## Quarterly Review Template

```markdown
## Q[N] 2026 Review — [Date]

### OKR Scorecard
| Objective | Score (0–1) | Notes |
|-----------|------------|-------|
| O1: ...   | 0.X        | ...   |

### North Star progress
- Previous quarter: €X avg saved/household
- This quarter: €X avg saved/household

### What we shipped
- ...

### What we didn't ship (and why)
- ...

### Key decision for Q[N+1]
- ...

### Updated STRATEGY.md? [ ]
### Updated OKRs? [ ]
```
