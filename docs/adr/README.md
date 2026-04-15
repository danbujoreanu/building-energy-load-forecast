# Architecture Decision Records (ADRs)
*Retroactively documented from design decisions made during MSc AI thesis and Sparc Energy build.*
*Format adapted from Luca Rossi / Refactoring.fm ADR pattern.*

---

## Index

| ADR | Decision | Status | Date |
|-----|----------|--------|------|
| [ADR-001](ADR-001-lightgbm-primary-model.md) | LightGBM as primary H+24 forecasting model | Accepted | 2025-Q4 |
| [ADR-002](ADR-002-stacking-ensemble-oof.md) | Stacking Ensemble with OOF meta-features | Accepted | 2025-Q4 |
| [ADR-003](ADR-003-oracle-safe-features.md) | Oracle-safe feature engineering (lag ≥ horizon enforcement) | Accepted | 2025-Q4 |
| [ADR-004](ADR-004-fastapi-deployment.md) | FastAPI for the inference API | Accepted | 2026-Q1 |
| [ADR-005](ADR-005-mock-first-design.md) | Mock-first deployment with dry_run=True default | Accepted | 2026-Q1 |
| [ADR-006](ADR-006-eu-ai-act-classification.md) | EU AI Act Limited Risk (Art. 52) classification | Accepted | 2026-03-28 |
| [ADR-007](ADR-007-quantile-regression-p10-p90.md) | Quantile regression for P10/P50/P90 confidence intervals | Accepted | 2026-04-13 |
| [ADR-008](ADR-008-model-monitoring-drift.md) | Model monitoring and drift detection (file-based registry + weekly script) | Accepted | 2026-04-13 |
| [ADR-009](ADR-009-city-specific-processed-paths.md) | City-specific processed data paths to prevent cross-city overwrites | Accepted | 2026-03-15 |
| [ADR-010](ADR-010-lightgbm-only-production.md) | LightGBM-only production model — stacking ensemble non-complementarity | Accepted | 2026-03-15 |

---

## How to Add a New ADR

Copy this template into `ADR-NNN-short-title.md`:

```markdown
# ADR-NNN: Title

**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-NNN
**Date:** YYYY-MM-DD
**Context:** What problem or situation prompted this decision?
**Options considered:** What alternatives were evaluated?
**Decision:** What was decided and why?
**Consequences:** What are the trade-offs and implications?
```
