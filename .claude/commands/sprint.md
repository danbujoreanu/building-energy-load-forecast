---
name: sprint
version: 2.0.0
description: |
  Research sprint planning with scope challenge, architecture review,
  test gaps, and definition of done. One question per issue, interactive.
allowed-tools:
  - Read
  - Grep
  - Glob
  - AskUserQuestion
---

# /sprint — Research Sprint Planning

Adapted from gstack /plan-eng-review for ML research pipeline planning.
Takes an optional goal argument: `/sprint journal-paper`, `/sprint horizon-sensitivity`,
`/sprint irish-dataset`, `/sprint control-engine`.

If no argument given, read ROADMAP.md and recommend the next milestone.

---

## Step 0: Scope Challenge (run before anything else)

Answer these questions:
1. **What existing code/results already partially solve this sprint's goal?**
   (e.g., for journal-paper: AICS'25 paper exists, final_metrics.csv exists)
2. **What is the minimum work to achieve the stated goal?**
   Flag anything that could be deferred without blocking the core deliverable.
3. **Complexity check:** If the sprint touches more than 6 files or requires running
   more than 2 pipeline configurations, challenge whether scope can be tightened.

Then ask the user to choose:
- **A) FOCUSED:** Minimal version — what must be done for this specific deliverable
- **B) FULL:** Complete sprint as described in ROADMAP.md
- **C) REFRAME:** Different sprint goal entirely

**If user does not choose A, respect that fully.** Do not re-argue for smaller scope
after Step 0. Commit to the chosen scope and optimise within it.

---

## Review Sections (after scope agreed)

### 1. Architecture Review

For the chosen sprint, evaluate:
- What new files will be created vs modified?
- Does anything touch the data pipeline? (flag data leakage risk)
- Does anything touch model evaluation? (flag metric calculation risk)
- Does anything touch the FastAPI deployment? (flag API contract risk)
- ASCII diagram of any non-trivial data flow introduced by this sprint

**STOP after each issue. One AskUserQuestion per issue.**
Present 2–3 lettered options. Lead with recommendation. Explain WHY.
Only proceed to next section after all architecture issues resolved.

### 2. Code Quality Review

- DRY violations: does this sprint duplicate logic already in temporal.py, metrics.py, or ensemble.py?
- Config hygiene: any new parameter that should be in config.yaml?
- Error handling: what happens if the new code gets an empty DataFrame or NaN-heavy input?
- Existing ASCII diagrams in touched files — still accurate after this sprint?

**STOP after each issue. One AskUserQuestion per issue.**

### 3. Test Review

Diagram all new code paths, branches, and data flows introduced by this sprint.
For each new item:
- Is there a test in `tests/`?
- Does the test cover the H+24 horizon boundary (not just H+1)?
- Does the test cover Oslo generalisation (not just Drammen)?

If this sprint touches model evaluation: specify which result CSVs must be regenerated
and what the expected R² range is (flag if R² drops below 0.95 for LightGBM on Drammen).

**STOP after each issue. One AskUserQuestion per issue.**

### 4. Performance Review

- Any new loop over buildings that could be vectorised?
- Any new file I/O per request that should be loaded once at startup?
- If new pipeline run required: estimated runtime on M-series Mac (reference: full pipeline ~45 min)

**STOP after each issue. One AskUserQuestion per issue.**

---

## Required Outputs

### Sprint Plan

```
GOAL: [one sentence — what will be true at end of sprint]

DELIVERABLE: [one concrete file or result]

TASKS (ordered):
[ ] 1. Task description — file_path:section
[ ] 2. ...
[ ] 3. ...
(max 6 tasks)

RISKS:
- Risk 1
- Risk 2 (max 2)

DEFINITION OF DONE:
[e.g. "journal paper submitted to Applied Energy with all 8 sections complete"]
[e.g. "horizon_metrics.csv has 5 rows, LightGBM R²>0.90 for all horizons"]

ESTIMATED SESSIONS: N (at ~1.5 hours each)
```

### NOT In Scope
Work considered and explicitly deferred, with one-line rationale each.

### What Already Exists
Existing code or results that partially solve the sprint goal — confirm whether
the plan reuses or unnecessarily rebuilds them.

### Failure Modes
For each new code path: one realistic way it could fail silently in production.
Flag as **critical gap** if: no test + no error handling + failure would be silent.

### Completion Summary
```
Step 0 Scope Challenge: user chose ___
Architecture issues: N
Code quality issues: N
Test gaps: N
Performance issues: N
Critical gaps: N
Estimated sessions: N
```

---

## How to Ask Questions

Every AskUserQuestion MUST:
1. State recommended option FIRST: "We recommend B: one-line reason"
2. List all options as `A) ... B) ... C) ...`
3. Map recommendation to a concrete engineering preference
4. Be one issue only — never batch

Exception: if an issue has an obvious fix with no real alternatives,
state what you'll do and move on without a question.
