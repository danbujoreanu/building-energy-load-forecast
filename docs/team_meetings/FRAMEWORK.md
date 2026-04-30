# Sparc Energy — Team Meeting Framework

*Based on how Meta, Google, and Intercom run product operations. Adapted for a pre-launch energy AI startup where one founder wears many hats. Each persona represents a decision lens applied to the same backlog.*

---

## The Personas

At Sparc's current stage, Dan applies each of these lenses when reviewing priorities. As the team grows, each becomes a separate hire. The PM persona owns the meeting framework.

| Persona | Primary concern | Typical questions |
|---|---|---|
| **Staff PM** | Product direction, user value, backlog | What do users need next? Is this the right problem? Is the sequence right? |
| **Staff PMM** | Messaging, positioning, GTM timing | How do we describe this? When do we launch? What's the competitor angle? |
| **VP Engineering** | Architecture, reliability, velocity | What's the tech debt risk? Is the infra scalable? What's blocking deploy? |
| **Director / Founder** | Commercial timing, funding, partnerships | What's the Jun 15 decision? Which grant do we apply for? Who do we need to meet? |
| **Staff Backend Engineer** | API design, DB schema, performance | Is the schema correct? Any N+1 queries? Is the endpoint contract stable? |
| **Staff Frontend Engineer** | User interface, onboarding flow | Can Sarah use this without a curl command? What does the upload screen look like? |
| **Data Scientist** | Model accuracy, feature drift, calibration | Is the MAE degrading? Is PANEL_FACTOR calibrated? Are predictions sane? |
| **UX Designer** | User journeys, information hierarchy | What does the first 5 minutes look like for a new user? What's confusing? |
| **Content Manager** | Documentation, blog, in-product copy | Is the advisory message clear? Is the onboarding copy accurate? |
| **Product Support** | User feedback, bug triage, edge cases | What breaks with a second household's CSV? What questions will users ask? |

---

## Meeting Types

### 1. Weekly Product Review (WPR)
- **Cadence**: Weekly, Thursdays 30 min (or async via shared doc)
- **Required personas**: PM, VP Engineering, Data Scientist
- **Optional**: Director (for commercial items), PMM (for GTM items)
- **Agenda**:
  1. Metrics pulse (2 min): active households, last 7d upload count, advisory delivery rate, recent MAE
  2. Sprint progress (5 min): what shipped, what slipped, blockers
  3. Linear triage (10 min): re-prioritise top 5 Todo items
  4. Decisions needed (5 min): anything requiring Director sign-off
  5. Actions (5 min): one owner per action, due date required
- **Output**: Updated Linear, decision log entry if decision was made

### 2. Strategy Review (Quarterly + ad hoc)
- **Cadence**: Quarterly, or triggered when: funding event, major market change, major product milestone
- **Required personas**: All (PM runs, Director decides)
- **Format**: 5-persona written check-in (see `template_strategy_review.md`) + live discussion
- **Output**: Updated priority order in Linear, updated MEMORY.md

### 3. Sprint Planning
- **Cadence**: Every 2 weeks (Monday)
- **Required personas**: PM, VP Engineering, Backend, Data Scientist
- **Agenda**:
  1. Review closed issues from last sprint
  2. Pull top-priority items from backlog into Todo
  3. Assign estimates (SP or T-shirt)
  4. Flag external dependencies (API, suppliers, regulators)
- **Output**: Linear sprint populated, ROADMAP.md updated

### 4. Design Review
- **Cadence**: Before any user-facing feature ships
- **Required personas**: UX Designer, Frontend Engineer, PM, PMM
- **Agenda**:
  1. Walk through user flow (Figma / wireframe / prototype)
  2. Edge cases: empty state, error state, loading state
  3. Copy review (Content Manager)
  4. Mobile-first check
- **Output**: Design approved or iteration requested

### 5. Incident Review (Post-mortem)
- **Trigger**: Any production issue affecting user data, advisory delivery, or model accuracy
- **Required personas**: VP Engineering, Backend, Data Scientist, PM
- **Format**: 5-whys, timeline, immediate fix, systemic fix
- **Output**: Post-mortem doc in `docs/ops/incidents/`, Linear issue for systemic fix

---

## Agenda Template (Strategy Review)

```
## Sparc Energy Strategy Review — [DATE]
**Facilitator**: [Name/Persona]
**Attendees**: [List personas present]

### Context since last review
- What shipped: [list]
- What's pending: [list]
- Key events (market, regulatory, commercial): [list]

### Persona Round-Table
(Each persona answers: what's the most important thing you'd change about the next 4 weeks?)

**Staff PM**: ...
**VP Engineering**: ...
**Data Scientist**: ...
**Director**: ...
**PMM**: ...
**UX Designer**: ...
**Content Manager**: ...
**Product Support**: ...

### Priority Reorder
| Rank | Issue | Owner | Why |
|---|---|---|---|

### Decisions Made
| Decision | Owner | Rationale | Date |
|---|---|---|---|

### Actions
| Action | Owner | Due | Linear issue |
|---|---|---|---|

### Stale Issue Flags
(Issues that have been in a state for >2 weeks without movement)

### Next Review Date
```

---

## Decision Log Format

Decisions are recorded in the meeting notes AND updated in the relevant Linear issue description. A decision is anything that: changes a build priority, affects commercial strategy, closes a technical option, or sets a direction that would be non-obvious to a future team member.

```
| Decision | Rationale | Owner | Date | Supersedes |
```

Example:
> | Use TimescaleDB over InfluxDB | Cross-table JOINs (meter × myenergi × tariff) are fundamental. InfluxDB's Flux cannot do multi-table joins. | VP Engineering | 2026-04-30 | — |

---

## The PM Checklist (before calling any meeting)

- [ ] What decision does this meeting need to produce?
- [ ] Can this be resolved async (Linear comment / shared doc) instead?
- [ ] Are the right personas in the room? (Not more — meeting drag is real)
- [ ] Is the agenda written and shared 24h in advance?
- [ ] Are the relevant metrics pulled and visible?
- [ ] Is there a clear action item format (owner + due date + Linear issue)?

---

## Working Principles

Borrowed from the best-run product orgs:

**Meta:** "Move fast with stable infrastructure." Ship features quickly but don't compromise the data pipeline. Every advisory that fails silently is a user trust loss.

**Google:** "Data beats opinion." Decisions about model accuracy, tariff rates, or feature priority should be backed by numbers, not intuition. If we don't have the data to decide, the next action is to collect it.

**Intercom:** "Jobs to be done over features." Sarah doesn't want a dashboard. She wants to stop overpaying for electricity without thinking about it. Every feature should trace to a job.

**Sparc-specific:** The model is not the product. The model is one ingredient. The product is: Sarah uploads a CSV, gets an advisory tomorrow morning, saves €178/year, and tells her neighbour. Every build decision should ask: does this get us closer to that sentence?

---

*Framework version: 1.0 | Created: 2026-04-30 | Owner: Staff PM*
*Review cadence: Update after each Strategy Review*
