# Project Commands Reference

All slash commands live in `.claude/commands/`. They are invoked by typing the
command name in the Claude Code chat, or by saying "run /commandname" if the
slash command UI is unavailable.

---

## Core Commands

### `/sprint <topic>`
**When to use:** Starting a new piece of work. Always run this first.
**What it does:**
- Step 0 scope challenge (prevents over-engineering)
- 4-section review (architecture → code quality → tests → performance)
- Produces a 6-task sprint plan with concrete definition of done
- Identifies what already exists (no rebuilding from scratch)

**Examples:**
```
/sprint journal-paper
/sprint horizon-sensitivity
/sprint cer-irish-dataset
/sprint raspberry-pi-prototype
/sprint market-fit
```

---

### `/review`
**When to use:** Before any PR / before any commit that touches pipeline code.
**What it does:**
- 2-pass review of `git diff origin/main`
- Pass 1 CRITICAL: data leakage, model trust boundary
- Pass 2 INFORMATIONAL: config coupling, dead code, test gaps, API safety
- Cites `file:line`. Ends with READY / NEEDS WORK / BLOCKED.

**Note:** If on `main` branch, reports "Nothing to review."

---

### `/retro`
**When to use:** End of session, or when switching from one work type to another.
**What it does:**
- Detects session boundaries (45-min gap threshold)
- Saves JSON snapshot to `.context/retros/YYYY-MM-DD-N.json`
- Checks result quality (reads final_metrics.csv, oslo_final_metrics.csv)
- Checks paper progress (reads JOURNAL_PAPER_OUTLINE.md)
- Produces a tweetable summary line

---

## Pipeline Scripts

| Command | What it runs | Duration |
|---------|-------------|----------|
| `python scripts/run_pipeline.py` | Full pipeline (all setups) | ~6h |
| `python scripts/run_pipeline.py --setup A` | Setup A only (tree models) | ~15min |
| `python scripts/run_pipeline.py --save-predictions` | Full run + saves prediction arrays | ~6h + disk |
| `python scripts/run_dl_h24_only.py` | DL H+24 recovery | ~2h |
| `python scripts/run_raw_dl.py` | Setup C raw DL | ~2h |
| `python deployment/live_inference.py --dry-run` | Morning brief (safe, no writes) | <5s |

---

## Analysis Scripts

| Command | Purpose | Requires |
|---------|---------|----------|
| `python scripts/significance_test.py` | All significance tests | per_building_metrics.csv |
| `python scripts/significance_test.py --mode per_building` | Wilcoxon on 44 buildings | per_building_metrics.csv |
| `python scripts/significance_test.py --mode dm` | Diebold-Mariano DM test | prediction .npy files |
| `python scripts/quantile_evaluation.py` | Winkler score + coverage (Drammen) | splits parquets |
| `python scripts/quantile_evaluation.py --city oslo` | Winkler score + coverage (Oslo) | splits parquets |
| `python scripts/quantile_evaluation.py --city drammen oslo` | Both cities | splits parquets |

**Quantile results (paper-ready, runs in ~15s — no pipeline rerun needed):**
```
Drammen: P50 MAE=4.072 kWh | Winkler=19.457 | Coverage=78.3% | PI Width=12.737 kWh
Oslo:    P50 MAE=7.345 kWh | Winkler=35.021 | Coverage=80.0% | PI Width=23.603 kWh
```

**To generate DM prediction files:**
```bash
python scripts/run_pipeline.py --save-predictions  # saves {model_name}_h24_test_errors.npy
# then:
python scripts/significance_test.py --mode dm
```
DM comparisons: LightGBM vs CNN-LSTM, LightGBM vs Ridge, LightGBM vs XGBoost.

---

## Results Files

| File | Contains | Status |
|------|---------|--------|
| `outputs/results/final_metrics.csv` | Drammen master (22 rows) | ✓ Authoritative |
| `outputs/results/oslo_final_metrics.csv` | Oslo Phase 3A (10 rows) | ✓ Authoritative |
| `outputs/results/per_building_metrics.csv` | Drammen per-building (44 bldgs) | ✓ |
| `outputs/results/category_level_metrics.csv` | Drammen by category | ✓ |
| `outputs/results/h1_metrics.csv` | H+1 archive | ✓ |
| `outputs/results/significance_results.csv` | Per-building Wilcoxon results | ✓ |
| `outputs/results/dm_test_results.csv` | DM test results | Needs --save-predictions |
| `outputs/results/quantile_results.csv` | Winkler score + coverage (both cities) | ✓ |
| `outputs/results/drammen_quantile_per_building.csv` | Per-building quantile metrics | ✓ |
| `outputs/results/oslo_quantile_per_building.csv` | Per-building quantile metrics (Oslo) | ✓ |

---

## GitHub Actions

**Claude PR Review** (auto-runs on every PR):
- Workflow: `.github/workflows/claude-review.yml`
- Trigger: PR open/sync/reopen, or `@claude` in PR comment
- Uses: `anthropics/claude-code-action@v1` + `.claude/commands/review-checklist.md`
- **Required setup:**
  1. Add `ANTHROPIC_API_KEY` secret at: github.com/danbujoreanu/building-energy-load-forecast/settings/secrets/actions
  2. Install Claude GitHub App: github.com/apps/claude

---

## Paper Writing

**To start/continue the journal paper:**
Say: "Doc coauthoring — let's write Section N: [section name]"
Claude will invoke the `anthropic-skills:doc-coauthoring` skill.

**Paper target:** Applied Energy (primary) / Energy and Buildings (backup)
**Foundation:** AICS '25 12-page Springer paper
**Outline:** `docs/JOURNAL_PAPER_OUTLINE.md`

---

## Key Paths

```
/Users/danalexandrubujoreanu/building-energy-load-forecast/   ← pipeline root
/Users/danalexandrubujoreanu/NCI/0. MSCTOPUP/Thesis WIP 2026/ ← thesis docs
config/config.yaml                                             ← single source of truth
/miniconda3/envs/ml_lab1/bin/python                           ← correct Python
```

---

## Virtual Team Hats

Say "Dr. R hat", "Marcus hat", "Siobhán hat", "Oliver hat", or "Fiona hat"
to switch perspective. See `docs/TEAM.md` for full descriptions.
