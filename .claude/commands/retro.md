---
name: retro
version: 2.0.0
description: |
  Research sprint retrospective. Analyzes commit history, result quality,
  paper progress, and work patterns. Persists history for trend tracking.
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
---

# /retro — Research Sprint Retrospective

Adapted from gstack /retro for an ML research pipeline (not a product codebase).

## Arguments
- `/retro` — last 7 days (default)
- `/retro 14d` — last 14 days
- `/retro 30d` — last 30 days
- `/retro compare` — current window vs prior same-length window

---

## Step 1: Gather raw data (run all in parallel)

```bash
git fetch origin main --quiet

# Commits in window
git log origin/main --since="<window>" --format="%H|%ai|%s" --shortstat

# Files changed most
git log origin/main --since="<window>" --format="" --name-only | grep -v '^$' | sort | uniq -c | sort -rn | head -20

# Commit timestamps for session detection (Europe/Dublin timezone)
TZ=Europe/Dublin git log origin/main --since="<window>" --format="%at|%ai|%s" | sort -n

# Conventional commit type breakdown
git log origin/main --since="<window>" --format="%s" | grep -oE '^(feat|fix|refactor|test|docs|chore|perf)' | sort | uniq -c | sort -rn
```

---

## Step 2: Compute metrics table

| Metric | Value |
|--------|-------|
| Commits to main | N |
| Total insertions | N |
| Total deletions | N |
| Net LOC | N |
| Active days | N |
| Detected sessions | N |
| Deep sessions (50+ min) | N |
| Avg session length | N min |
| Shipping streak | N consecutive days |

**Session detection:** 45-minute gap threshold between consecutive commits.

---

## Step 3: Result quality check

Read `outputs/results/final_metrics.csv` and `outputs/results/oslo_final_metrics.csv`.

Report:
- Best model and R² (Drammen H+24)
- Best model and R² (Oslo generalisation)
- Any row with R² < 0 or R² > 1 → flag as anomalous
- Any new result files added this sprint vs prior sprint

---

## Step 4: Paper progress check

Read `docs/JOURNAL_PAPER_OUTLINE.md` and `docs/SESSION_LOG.md` (last 2 sessions).

Report:
- Which paper sections have content vs are still placeholder
- Any section explicitly marked TODO or PENDING
- Date of last paper-related commit (any commit touching `docs/` or the paper outline)

---

## Step 5: Hotspot analysis

Top 10 most-changed files this sprint. Flag:
- Any file changed 5+ times (churn hotspot)
- Source files with no corresponding test file
- Config file changes (any `config.yaml` modification = note what changed)

---

## Step 6: Commit type breakdown

Show as percentage bar:
```
feat:      5  (35%)  ███████████████████
fix:       3  (21%)  ██████████
docs:      4  (29%)  ████████████████
refactor:  2  (14%)  ████████
```

If `fix` ratio > 50%: flag — signals debugging spiral, consider writing tests before next feature.

---

## Step 7: Work session patterns (Europe/Dublin time)

Hourly histogram of commits. Identify:
- Peak hours
- Whether pattern is morning-focused, evening-focused, or scattered
- Any sessions after midnight

---

## Step 8: Load history & compare

```bash
ls -t .context/retros/*.json 2>/dev/null | head -5
```

If prior retros exist: load the most recent, compute deltas:
```
                    Last        Now         Delta
R² (Drammen):       0.975  →   0.975       —
R² (Oslo):          0.963  →   0.963       —
Sessions:           8      →   12          ↑4
Net LOC:            +240   →   +180        ↓60
Paper sections:     3/8    →   5/8         ↑2
```

If no prior retros: skip comparison, note "First retro recorded."

---

## Step 9: Save snapshot

```bash
mkdir -p .context/retros
```

Save JSON to `.context/retros/YYYY-MM-DD-N.json`:
```json
{
  "date": "2026-03-12",
  "window": "7d",
  "metrics": {
    "commits": 12,
    "insertions": 340,
    "deletions": 80,
    "net_loc": 260,
    "active_days": 4,
    "sessions": 6,
    "deep_sessions": 3,
    "streak_days": 12,
    "feat_pct": 0.35,
    "fix_pct": 0.21,
    "docs_pct": 0.29
  },
  "results": {
    "drammen_best_r2": 0.9752,
    "oslo_best_r2": 0.9635,
    "paper_sections_complete": 5
  },
  "tweetable": "Sprint Mar 12: 12 commits, 260 LOC, Oslo R²=0.963, 5/8 paper sections"
}
```

---

## Step 10: Narrative output

**Tweetable summary (first line):**
```
Sprint Mar 12: 12 commits, 260 LOC net, Drammen R²=0.975, Oslo R²=0.963 | Streak: 12d
```

### Summary Table (Step 2)
### Result Quality (Step 3)
### Paper Progress (Step 4)
### Trends vs Last Retro (Step 8, if available)
### Work Patterns (Steps 6–7)
### Hotspots (Step 5)

### Top 3 Wins
Highest-impact things completed this sprint — anchor in actual commits.

### 3 Things to Improve
Specific, in actual code or workflow. "To get even better, you could..."

### Single Next Action
One concrete task. Not "work on the journal paper" but
"Write the Paradigm Parity definition paragraph in docs/JOURNAL_PAPER_OUTLINE.md §2.1"

---

## Tone
Encouraging but direct. Anchor every observation in actual commits.
Skip generic praise. Total output: ~1500 words max.
All timestamps in Europe/Dublin time.
