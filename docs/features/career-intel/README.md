# Feature: Career Intelligence RAG

**Status:** ✅ Production
**Linear:** DAN-79, DAN-80
**Owner:** Dan Bujoreanu

---

## What it does

Two-way intelligence between job search and product development:
1. **Career → Energy**: extracts tech requirements from job specs; flags which to implement in Sparc
2. **Energy → Career**: uses Sparc's technical architecture as evidence in applications/interviews

## Key commands

```bash
# Ingest all Obsidian job specs (run after adding a new JD)
python scripts/career_ingest.py --all-obsidian

# Analyse fit for a specific role
python scripts/career_ingest.py --match "PartnerRe Senior AI Architect"

# Technology frequency across all job specs
python scripts/career_ingest.py --tech-eval

# Watch folder for new specs (run on Mac Mini startup)
python scripts/career_watch.py
```

## Cross-portfolio tech gaps (as of 2026-04-18)

| Technology | Mentions | Priority | Action |
|-----------|---------|---------|--------|
| Azure | ×46 | CRITICAL | TECH_STACK.md §15 has mapping; build Azure portfolio |
| n8n | ×13 | HIGH | DAN-64 in backlog |
| React | ×9 | MEDIUM | Next.js (DAN-60) covers this |
| dbt | ×9 | LOW | Not relevant to Sparc |
| Vertex AI | ×8 | LOW | GCP equivalent; cover in interview framing |
| LangChain | ×7 | HIGH | DAN-80 — dedicated portfolio project |
| Snowflake | ×6 | MEDIUM | TECH_STACK.md has Azure equivalence mapping |

## Obsidian folder convention

```
Career/Applications/
  {CompanyName}/
    {Job Title}.md             ← no date
    2026-04-18 {Job Title}.md  ← date prefix (stripped automatically)
```

Metadata auto-generated from folder/filename if no YAML frontmatter.

## Ingested job specs (as of 2026-04-18)

- **Active:** Anthropic, CITI, Delve Deeper, EirGrid, Irish Life, Okta, PartnerRe, PhD Decarb-AI, Red Hat, Revolut, Storyblok, Zendesk, dbt Labs
- **Closed:** VIOTAS AI Solutions Lead (assessment materials ingested)
- **Rejected:** SSE Airtricity Business Product Owner AI (Christina + Claire profiles ingested)

## SSE Airtricity rejection — lesson learned

Rejection reason: could not provide strong examples of working with Design teams.

Interviewers ingested:
- **Christina Geoghegan** (Product Designer) — key interviewer, asked Design collaboration question
- **Claire Melady-Bell** (Product Manager) — PM interviewer

**What we did about it in Linear:** DAN-28 (BTM Detection), DAN-42 (Rory Design System), DAN-48 (UI Prototyping) all have explicit Design collaboration sections.

## Key files

- `intel/career.py` — match_job_spec(), evaluate_tech_stack(), ingest_obsidian_jobs()
- `scripts/career_ingest.py` — CLI
- `scripts/career_watch.py` — Obsidian folder watcher
- `intel/docs/career/jobs/` — ingested job specs
- `intel/docs/career/profile/DAN_BUJOREANU_PROFILE.md` — skills/experience profile
