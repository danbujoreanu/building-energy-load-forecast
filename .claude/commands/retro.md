# /retro — Sprint Retrospective

Analyse recent git history and project state to produce a structured retrospective.
Run this at the start of each new research sprint to orient before doing new work.

## Steps

1. Run `git log --oneline -20` to see the last 20 commits
2. Run `git diff HEAD~10 HEAD --stat` to see what files changed most
3. Read the last session entry in docs/SESSION_LOG.md
4. Read outputs/results/final_metrics.csv and oslo_final_metrics.csv for current result state

## Retrospective Report Structure

### What Was Completed (last sprint)
List commits grouped by theme: data, features, models, deployment, docs

### Current Result State
Reproduce the key metrics table from final_metrics.csv and oslo_final_metrics.csv.
Flag any result that looks anomalous (R² < 0 or > 1, MAE > 50).

### Open Threads
Scan SESSION_LOG.md for any item marked TODO, PENDING, stub, or NotImplementedError.
List them with the file and line reference.

### Velocity Assessment
How many commits in the last 7 days vs the 7 days before?
Are we accelerating or slowing down?

### Next Sprint Recommendation
Based on ROADMAP.md and the current open threads, recommend ONE concrete next action.
Be specific: not "work on journal paper" but "expand Methods section of journal paper —
start with the Paradigm Parity definition paragraph in JOURNAL_PAPER_OUTLINE.md".

## Output
Keep the report under 40 lines. Be direct, no padding.
