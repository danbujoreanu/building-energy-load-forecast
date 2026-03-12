---
name: review
version: 2.0.0
description: |
  Pre-landing code review. Analyzes diff against main for data leakage,
  model trust boundaries, race conditions, and ML pipeline structural issues.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - AskUserQuestion
---

# Pre-Landing Review — Energy Forecast Pipeline

Analyze the current branch's diff against main for structural issues that tests don't catch.
Adapted from gstack /review for ML + FastAPI deployment context.

---

## Step 1: Check branch

1. Run `git branch --show-current`
2. If on `main`: output **"Nothing to review — you're on main."** and stop.
3. Run `git fetch origin main --quiet && git diff origin/main --stat`
   If no diff: output the same message and stop.

---

## Step 2: Read the checklist

Read `.claude/commands/review-checklist.md`.
**If unreadable, STOP.** Do not proceed without the checklist.

---

## Step 3: Get the diff

```bash
git fetch origin main --quiet
git diff origin/main
```

---

## Step 4: Two-pass review

**Pass 1 (CRITICAL):** Data Leakage & Feature Safety, Model Trust Boundary
**Pass 2 (INFORMATIONAL):** Conditional Side Effects, Config Coupling,
Dead Code, Test Gaps, Time Window Safety, API Boundary Safety

---

## Step 5: Output

```
Pre-Landing Review: N issues (X critical, Y informational)

**CRITICAL** (blocks deployment):
- [file:line] Problem description
  Fix: suggested fix

**Issues** (non-blocking):
- [file:line] Problem description
  Fix: suggested fix
```

If no issues: `Pre-Landing Review: No issues found.`

One-line verdict: **READY** / **NEEDS WORK** / **BLOCKED**
