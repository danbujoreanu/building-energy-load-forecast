# /sprint — Sprint Planning

Design the next research sprint with a concrete work plan.
Takes an optional argument: the sprint goal (e.g. `/sprint journal-paper` or `/sprint horizon-sensitivity`).
If no argument is given, recommend the sprint goal from ROADMAP.md.

## Steps

1. Read ROADMAP.md to identify the next incomplete milestone
2. Read docs/JOURNAL_PAPER_OUTLINE.md if sprint goal is journal-paper
3. Read config/config.yaml if sprint goal involves running experiments
4. Check outputs/results/ for which result files exist and are non-empty

## Sprint Plan Structure

### Goal
One sentence. What will be demonstrably true at the end of this sprint that is not true now?

### Deliverable
One concrete file or output: a submitted paper, a new results CSV, a new feature,
a new section in the paper. Not "make progress" — a specific artefact.

### Tasks (ordered, with file references)
Maximum 6 tasks. Each task must reference the specific file to create or modify.
Format: `[ ] Task description — file_path:approximate_line`

### Risks
What could block this sprint? Name at most 2.

### Definition of Done
How will we know the sprint is complete? (e.g. "journal paper submitted to Applied Energy",
"horizon_metrics.csv has 5 rows covering H+3/6/12/24/48 with R²>0.90 for LightGBM")

### Estimated Sessions
How many Claude Code sessions (roughly 1-2 hours each) to complete?
