# Issue Documentation Standard

**Owner:** Dan Bujoreanu | **Applies to:** All Linear teams (DAN, GARDEN) | **Created:** 2026-04-20

---

## Why This Exists

When an issue says "97 docs / 4,306 chunks", that number is meaningless without:
- **Where** the data lives (file path, collection name)
- **How to verify** it (runnable command)
- **How to reproduce** it (exact commands with paths)
- **What to do next** (next step, related issues)

Every completed or in-progress issue must be a self-contained runbook — not a summary.

---

## Required Sections by Status

### Todo / In Progress issues

```markdown
## What to do
[1–3 sentence description of the task]

## Commands to run
```bash
# Step 1: [description]
cd ~/building-energy-load-forecast
~/miniconda3/envs/ml_lab1/bin/python scripts/example.py --flag value

# Step 2: verify
~/miniconda3/envs/ml_lab1/bin/python scripts/example.py --status
```

## Prerequisites
- [ ] Prerequisite 1 (what must be true before this runs)
- [ ] Prerequisite 2

## Where results go
- Path/collection/table: `data/chromadb/` or `outputs/` etc.

## Source docs / related files
- Implementation: `src/file.py`
- Feature docs: `docs/features/feature-name/README.md`
- Config: `config/config.yaml` → `section`
```

---

### Done issues

```markdown
**Status: ✅ DONE — completed YYYY-MM-DD by [who/which session]**

## Results
[Specific numbers: X documents, Y chunks, Z MAE, etc.]

**To verify (run this to confirm):**
```bash
[one-liner to reproduce or check the result]
```

## What was done
[Brief description with specifics — modules, files, parameters]

## Data location
- ChromaDB collection: `collection_name` at `data/chromadb/`
- Output files: `outputs/experiment_name/`
- Model artefacts: `models/lightgbm_h24/`

## To reproduce from scratch
```bash
[exact commands to reproduce, with full paths]
```

## Source docs
- Implementation: `src/file.py`
- Feature docs: `docs/features/X/README.md` → "Section Name"
```

---

## Traceability Rules

| Rule | Why |
|------|-----|
| Always use absolute paths or `~/` paths in commands | Another session / Orchestrator has no `cd` context |
| Include the Python interpreter path: `~/miniconda3/envs/ml_lab1/bin/python` | Avoids wrong env |
| Link to the feature README, not just the script | Feature README has the full context |
| State which session produced results (if known) | Helps debug discrepancies |
| Include a `--status` or verify command for every Done issue | Numbers need to be checkable |
| Never cite a number (chunks, docs, MAE) without a verification command | Numbers drift; commands don't lie |

---

## Naming Conventions

### Sub-issue titles
Format: `{PARENT-ID}.N: [Action] [Object]`

Examples:
- `DAN-69.1: Draft AWS Activate application`
- `DAN-24.1: Run intel_feeds first ingestion`
- `DAN-80.1: Provision Azure AI Search resource`

This makes parent-child relationships explicit in the issue title, visible without opening the issue.

---

## Python Environment Reference

| Context | Python path |
|---------|------------|
| ML pipeline, RAG, intel scripts | `~/miniconda3/envs/ml_lab1/bin/python` |
| System Python (avoid) | `/usr/bin/python3` |
| Activate env for interactive use | `conda activate ml_lab1` |

---

## Applying This Standard

### To existing issues
When you touch an issue (change state, add comment), update the description to meet this standard.
Do not retroactively update all issues — only issues in the current sprint.

### To new issues
Every new issue created by Claude Code sessions MUST include:
1. Commands section (even if empty: "TBD — commands will be added when scoped")
2. Prerequisites
3. Source docs link (or "N/A — new feature")

### Orchestrator scope
This standard applies to ALL Linear teams:
- **DAN** (Sparc Energy) — enforced from this session
- **GARDEN** (Digital Twin Gardening) — enforce from first GARDEN session
- Any future teams

Orchestrator: when creating issues across projects, use the templates above. When closing an issue, always include a "To verify" command.

---

## Template — Quick Copy

### Done issue description (paste and fill):
```
**Status: ✅ DONE — completed YYYY-MM-DD**

## Results
[X docs / Y chunks / Z MAE / etc.]

**To verify:**
```bash
cd ~/PROJECT_PATH
~/miniconda3/envs/ml_lab1/bin/python SCRIPT --status
```

## Data location
[path]

## Source docs
- [link]
```

### Todo issue description (paste and fill):
```
## What to do
[description]

## Commands
```bash
cd ~/PROJECT_PATH
~/miniconda3/envs/ml_lab1/bin/python SCRIPT --flag
```

## Prerequisites
- [ ] item

## Source docs
- [link]
```
