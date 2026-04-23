# PR Workflow — How to Merge
*Created: 2026-04-22 | Last modified: 2026-04-23*

> **One-line rule:** If all 4 Required checks are green, use Squash and merge. If any Required check is red, stop and fix it first.

---

## The full flow

```
A feature branch is created and changes pushed
           ↓
A PR is opened — GitHub link available in the PR list
           ↓
CI runs automatically (~60 seconds)
           ↓
Open the PR → scroll to bottom → check status
           ↓
       Decision point — see table below
```

---

## Decision table — what to do at the merge button

| What you see | What it means | What to do |
|---|---|---|
| 4 green ✅ Required + "Able to merge" | All gates passed | **Squash and merge** ✅ |
| 4 green ✅ Required + AI review ❌ (not Required) | CI passed; automated reviewer had an infra issue | **Squash and merge** ✅ — AI review is informational |
| 4 green ✅ Required + AI review left a comment saying **BLOCKED** | Automated review found real data leakage or feature count error | **Do NOT merge** — fix the issue first |
| Any red ❌ marked **Required** | A real test, quality, or Docker failure | **Do NOT merge** — investigate the failing check |
| "Merge pull request" button is fully greyed / missing | Merge conflict, or Required check still running | Wait 2 min then refresh; if still grey, check for merge conflict |

---

## How to merge — step by step

1. Open the PR link
2. Scroll to the bottom of the PR page
3. Click the **dropdown arrow** next to "Merge pull request"
4. Select **"Squash and merge"** ← always use this
5. GitHub shows a text box with the commit message — edit or leave as-is
6. Click **"Confirm squash and merge"**
7. Branch auto-deletes (enabled 2026-04-22 — no manual cleanup needed)

---

## Check colours explained

```
✅ Green check + "Required" label  →  gate passed, counts toward merge
❌ Red check  + "Required" label   →  gate failed, blocks merge — STOP
✅ Green check (no Required label) →  informational, does not block merge
❌ Red check  (no Required label)  →  informational, does not block merge
⏳ Yellow circle                   →  still running, wait ~60s then refresh
```

---

## The 4 Required checks and what they catch

| Check | Time | What a failure means |
|---|---|---|
| **CI / Tests (Python 3.10)** | ~60s | A test broke — likely a code logic error |
| **CI / Tests (Python 3.11)** | ~55s | Same as above on a different Python version |
| **CI / Code quality** | ~30s | black formatting, ruff lint, or mypy type error |
| **CI / Docker image builds** | ~50s | Dockerfile broken, or `outputs/models/` missing |

---

## AI PR Review — how it works

- Runs on every PR automatically
- **Not** a Required check — never blocks merge on its own
- Checks for: data leakage, 35-feature contract, city allowlist, model trust boundary
- Leaves a comment on the PR with findings, ending in one of:
  - `READY` — no issues found
  - `NEEDS WORK` — informational issues noted, your call
  - `BLOCKED` — critical issue (data leakage, feature count wrong) — treat as a Required failure
- If it fails with an infrastructure error and leaves **no comment** — ignore, merge anyway

---

## Branch naming conventions

| Type | Pattern | Example |
|---|---|---|
| Feature / new capability | `feature/short-description` | `feature/upload-endpoint` |
| Bug fix | `fix/short-description` | `fix/drift-detector-threshold` |
| Documentation | `docs/short-description` | `docs/cicd-workflow` |
| Engineering / refactor | `eng/short-description` | `eng/pytest-audit` |

Branches auto-delete after merge — no manual cleanup needed.

---

## Responsibility summary

| Step | Owner |
|---|---|
| Create branch, make changes, open PR | Developer |
| Wait for CI to run | Automatic |
| Check the decision table and merge | Developer |
| Branch cleanup | Automatic |
| Investigate and fix a failing Required check | Developer |

---

## Quick reference card

```
All 4 Required green?        →  Squash and merge
Any Required red?            →  Investigate the failing check, fix before merging
AI review BLOCKED?           →  Real issue found — fix it
AI review infra failure ❌   →  Ignore, merge
Merge button greyed out?     →  Check for merge conflict or still-running check
```
