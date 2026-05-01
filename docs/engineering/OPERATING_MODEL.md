# Operating Model — Sparc Energy
# Full protocol detail moved here from CLAUDE.md (2026-05-01 restructuring)
# Load this file when: setting up Linear issues, reviewing session protocol, career loop work

---

## Linear Issue Quality Standard

### Every issue must contain:

**1. Document References (mandatory)**
Every issue description must reference relevant documents **by name** (not path):
```
References: MODEL_CARD.md · DATA_LINEAGE.md · N8N_WORKFLOWS.md
```

**2. Sub-issues for multi-step work**
Any issue with >2 implementation steps must have sub-issues:
```
DAN-96: POST /upload endpoint                         ← parent
  └─ DAN-96.1: Schema validation + CSV parser         ← sub-issue
  └─ DAN-96.2: TimescaleDB insert + idempotency       ← sub-issue
  └─ DAN-96.3: Integration test + To verify: command  ← sub-issue
```
Sub-issues use the GraphQL `createIssue` mutation with `parentId` set to the parent issue ID.

**3. Labels**

| Label | When to use |
|-------|-------------|
| `ml-pipeline` | Model training, evaluation, drift, features |
| `infra` | Docker, Grafana, Redis, TimescaleDB, n8n, Pushover |
| `deployment` | FastAPI endpoints, Dockerfile, connectors, CLI |
| `governance` | Model Card, AIIA, Data Lineage, Provenance, ADRs |
| `product` | Consumer app, control engine, UX, notifications |
| `urgent` | Deadline < 1 week or blocking another issue |
| `blocked` | Cannot proceed — note what it's blocked on |

**4. Dependencies**
- Use `issueRelationCreate(issueId: A, relatedIssueId: B, type: blocks)`
- State in description: "Blocked by DAN-96 (no meter data in DB)"

**5. Estimates**

| Points | Meaning |
|--------|---------|
| 1 | < 1 hour |
| 2 | 1–3 hours |
| 3 | Half day |
| 5 | Full day |
| 8 | 2–3 days |
| 13 | Full sprint (break it down first) |

**6. Priority**

| Priority | When |
|----------|------|
| Urgent | Deadline this week or production down |
| High | This sprint must ship |
| Medium | Next sprint or blocking product progress |
| Low | Nice-to-have, no deadline |
| No priority | Research / exploration / backlog |

### `To verify:` command standard
```
To verify: cd ~/building-energy-load-forecast && PYTHONPATH=src ~/miniconda3/envs/ml_lab1/bin/python -m pytest tests/ -q
To verify: curl http://localhost:8000/health
To verify: docker compose ps
```
Rules: full paths only, never relative, never cite a number without a command to reproduce it.

### Issue naming convention
`DAN-{N}: [Verb] [object] — [qualifier]`

### Issue description template
```
## What
[1–2 sentences]

## Why
[1 sentence — what it unblocks]

## Acceptance criteria
- [ ] criterion 1

## References
[Doc names: DEPLOY_RUNBOOK.md · MODEL_CARD.md]

## To verify
[Runnable command or URL]
```

### Relationship types
- **Sub-issue** (`parentId`): implementation step
- **Related**: same sprint, separate concern — `issueRelationCreate(type: related)`
- **Blocks / blocked-by**: `issueRelationCreate(type: blocks)`

---

## Linear Auto-Sync Protocol

**Do NOT wait for Dan to say "update Linear."** Trigger rules:

| Trigger | Action |
|---------|--------|
| Decision made | Update/create issue |
| Technical procedure shared | Create issue with `To verify:` |
| Status change | Update issue description + state |
| New risk/blocker | Create issue with correct priority |
| Model metric published | Record with exact reproduce command |
| ADR-worthy decision | Create `docs/adr/` entry AND link from issue |

No action for: architecture explanations, ML science, anything with no decision and no next step.

---

## Session End Protocol

At end of every session (or "wrap up" / "we are done"):

**Step 1 — Append to CAREER_CONTEXT.md:**
```
### Session summary — [YYYY-MM-DD]
**Completed:** [bullet list]
**New artefacts:** [files created/updated with paths]
**Open items:** [unfinished / follow-up]
**Cross-project signals:** [career assets, GitHub status, or "none"]
```

**Step 2 — Update Energy row in MASTER_ROADMAP.md:**
`/Users/danalexandrubujoreanu/Personal Projects/0. Orchestrator Command Centre/MASTER_ROADMAP.md`
- Mark completed issues ✅
- Remove resolved blockers
- Add new blockers

Then tell Dan: "Session summary written to CAREER_CONTEXT.md and MASTER_ROADMAP updated. Run /project-relay in your Orchestrator session if you want a full cross-project sync."

---

## Career Loop — Cross-Project Intelligence

**Orchestrator → Energy (top-down):**
1. Orchestrator reads job spec → identifies matching capabilities → pushes task to `CAREER_CONTEXT.md`
2. Energy Claude picks it up at next session start

**Energy → Career (bottom-up):**
When a technical milestone is reached, write coach flag to:
`/Users/danalexandrubujoreanu/Personal Projects/Career/Cross_Project_Intelligence.md`

Format:
```
### Coach Flag — [Date] | Project: Energy | Milestone: [what] | Career relevance: [role] | Suggested action: [resume bullet / LinkedIn]
```

---

## Coding Principles (detail)

### Karpathy: Simplicity + Surgical Changes
- Minimum code. No speculative features, no abstractions for single-use code.
- Touch only what you must. Match existing style.
- Small commits: ~50 lines. >200 lines = break it into steps.

### Self-Instrumenting Diagnostics (RoboPhD)
```python
print(f"[build_features] Input: {df.shape}, buildings: {df.index.get_level_values(0).nunique()}")
print(f"[build_features] After lag features: {df_feat.shape}, NaN rows dropped: {nan_rows}")
print(f"[build_features] Final feature count: {len(feature_cols)}")
```
Use `print()` for iteration, `logging` for production.

### ADRs (Luca Rossi)
Create/update in `docs/adr/` for every significant technical decision:
- **Context**, **Options considered**, **Decision**, **Consequences**

### Test Coverage + CI Gates
New code → at least one happy-path test. CI gates: block on coverage drop >5% or any failure.

Code complexity (`radon`): target all A/B, flag C+:
```bash
radon cc src/ -s -a
radon mi src/ -s
```

### Deep Focus Protocol
1. Build in fresh context
2. Test against previous benchmark immediately
3. Only commit once new output beats/matches baseline
