# Strategy Review — Session 51 (2026-04-30)

**Facilitator**: Staff PM (Dan)
**Personas present**: PM, VP Engineering, Director, Data Scientist, PMM, UX Designer, Product Support
**Session type**: Scheduled — requested after completing major data infrastructure work (myenergi backfill, dashboard upgrade)
**Linear issue**: DAN-122

---

## Context since last review (2026-04-24)

**What shipped since session 45:**
- `POST /upload` endpoint — ESB CSV → TimescaleDB (DAN-96 ✅)
- `GET /forecast/{household_id}` endpoint (DAN-97 ✅)
- APScheduler: 16:00 inference, 23:30 myenergi poll, 20:00 solar advisory (DAN-100 ✅)
- myenergi backfill completed: 850 days (2024-01-01 → 2026-04-29), 0 failures
- BTM panel redesigned: stacked barchart (Eddi | House load | Solar export) replaces state-timeline green bar
- household_intelligence.json v11: tariff cost breakdown (panel 20), export revenue tracker (panel 21), free Saturday utilisation (panel 22)
- solar_pipeline.json v2: ESB vs MyEnergi reconciliation panels (DAN-147 ✅)
- DAN-129, 132, 133, 147 → Done
- 21 new Linear issues created (DAN-129 → DAN-150) from ideas brainstorm
- saveon.ie references removed from all git-tracked files (replaced with "PCW partner")
- Public repo policy (`docs/PUBLIC_REPO_POLICY.md`) in place
- ESB Networks intel: Renewable Energy Forecast tool documented (`knowledge/domain/ESB_NETWORKS_INTEL.md`)

**Key market events:**
- CRU dynamic pricing mandate: June 30, 2026 (confirmed)
- BGE contract renewal: June 15, 2026 (6.5 weeks away — action needed)
- SEAI RD&D call: May–July 2026 window

---

## Persona Round-Table

**Staff PM:**
The pipeline is complete as backend infrastructure. The gap is now product surface: no second user, no public URL, no user-facing interface. The highest-priority build is the plan comparison engine (DAN-131) — it directly answers the BGE contract decision in 6.5 weeks AND it's the strongest product demo story ("I used Sparc to decide my own contract").

**VP Engineering:**
DAN-115 (metrics endpoint) and DAN-116 (correlation IDs + prediction sanity checks) have been sitting overdue since April 26. A model silently serving NaN values or stale predictions produces bad advisories with no alert. These must ship before any second household is onboarded. APScheduler running inside a single FastAPI process is fine for demo and App Runner; monitoring gaps matter more at this stage.

**Data Scientist:**
Panel factor calibration (DAN-142) is now unblocked — backfill provides 850 days of Eddi data. Need to check how many `solar_actuals` rows have both `eddi_kwh` and `export_kwh` populated (the latter requires ESB upload for the same date). The morning advisory's PANEL_FACTOR constant is currently manually set at 1.6; auto-calibration will improve solar diversion estimates.

Day-ahead cost forecast (DAN-143) closes the "what will tomorrow cost me?" loop. This is a one-day build: LightGBM P50 forecast (already running) × tariff rates per slot → predicted €/day.

**Director:**
DAN-66 (ESCO registration — CRU202517 Appendix A) has been Urgent for multiple sessions and is a form, not a build. File it this week. DAN-70 (SEAI RD&D, €50-200k) is due July 1 — 9 weeks. Needs 2-3 page technical proposal with NCI supervisor co-authorship.

BGE contract renewal June 15: the decision requires the plan comparison engine (DAN-131). Without it, the renewal decision is guesswork on 2 years of data we already have.

**Staff PMM:**
The June 30 CRU TOU mandate is a zero-cost acquisition channel. When 5 suppliers announce their new TOU products (likely May), publish: "Here's how to model whether the new TOU tariff benefits your household." Prepare a one-pager in the next 2 weeks. The €178.65/year free Saturday story is the best two-sentence close: concise, personal, real data.

**UX Designer:**
The critical path to a second user is: public URL + upload page + post-upload "here's your dashboard" link. No authentication is needed for a 10-household beta (household_id from the upload response is the implicit session token). The biggest friction point is that a non-technical user receives a JSON response after upload with no next step.

**Content Manager:**
The morning advisory messages are technically correct but could be more human. "SKIP_BOOST" as a recommendation string will confuse a non-technical user if it ever surfaces in a UI. The advisory copy needs a plain-English rewrite pass before any user-facing surface exists.

**Product Support:**
No multi-household ESB upload test has been run. The parser handles kW/kWh auto-detection and column mapping, but CRLF line endings (Windows Excel export), encoding variants, and edge-case column naming have not been tested with a second household's file. The first support ticket will be about this.

---

## Priority Reorder

| Rank | Issue | Effort | Why now |
|---|---|---|---|
| **1** | DAN-66 — ESCO registration | ~2h | Urgent since session 40. Just a form. File this week. |
| **2** | DAN-131 — Plan comparison engine | 1 day | BGE June 15 decision; best product demo story |
| **3** | DAN-49 — App Runner deploy | 0.5 day | Scaffolding exists; blocks every second user |
| **4** | DAN-143 — Day-ahead cost forecast | 0.5 day | Extends advisory with €/day figure; high user value |
| **5** | DAN-141 — Eddi schedule optimiser | 0.5 day | Adds explicit kWh diversion estimate to advisory |
| **6** | DAN-115/116 — Metrics + observability | 1 day | Overdue; needed before 10-household beta |
| **7** | DAN-5 — Journal paper | Ongoing | Due May 31 |
| **8** | DAN-70 — SEAI RD&D application | 1 week writing | Due July 1 |

**Deprioritised:**
- DAN-80 (Azure dual-stack): unless tied to a specific interview deadline, deferred
- DAN-34 (HP BTM detection): blocked on DAN-150 data
- DAN-44 (Customer intelligence dashboard): relevant at 10+ users, not now

---

## Decisions Made

| Decision | Rationale | Owner | Date |
|---|---|---|---|
| No user auth required for 10-household beta | household_id returned on upload is implicit session token; avoids 2-week auth build | PM + VP Engineering | 2026-04-30 |
| DAN-131 before DAN-49 | Plan comparison needed for BGE June 15; demo story more important than public URL right now | Director + PM | 2026-04-30 |
| DAN-66 is a form not a build — file this week | Has been Urgent for 3+ sessions with no movement; unblocks ESCO eligibility | Director | 2026-04-30 |
| Morning advisory copy needs plain-English rewrite | "SKIP_BOOST" must never reach a user UI unchecked | Content Manager | 2026-04-30 |

---

## Actions

| Action | Owner | Due | Linear |
|---|---|---|---|
| File CRU202517 Appendix A (ESCO registration) | Dan (Director) | 2026-05-07 | DAN-66 |
| Build plan comparison engine + `/compare-plans` endpoint | Backend + Data Scientist | 2026-05-05 | DAN-131 |
| Implement `/metrics` endpoint + prediction sanity checks | Backend + VP Eng | 2026-05-05 | DAN-115, DAN-116 |
| Day-ahead cost forecast in advisory | Data Scientist | 2026-05-05 | DAN-143 |
| Eddi schedule optimiser (kWh estimate in advisory) | Data Scientist | 2026-05-05 | DAN-141 |
| Panel factor auto-calibration script | Data Scientist | 2026-05-07 | DAN-142 |
| Submit SEAI RD&D application | Dan (Director) | 2026-07-01 | DAN-70 |
| Prepare CRU TOU mandate one-pager | PMM | 2026-05-14 | — |

---

## Stale Issue Flags

| Issue | Status | Days stale | Recommended action |
|---|---|---|---|
| DAN-8 (Decarb-AI PhD interview Apr 21) | In Progress | 9 days past due date | Mark Done or Cancelled — interview happened |
| DAN-115 (/metrics endpoint) | Backlog | 4 days past due date (Apr 26) | Move to Todo, start this week |
| DAN-116 (Correlation IDs) | Backlog | 4 days past due date (Apr 26) | Move to Todo, start this week |
| DAN-81 (RSS/Substack intel feed) | In Progress | Due May 4 (4 days) | Start today or push date |

---

## Next Review
After DAN-49 (App Runner) ships — public URL live.
