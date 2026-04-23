# Public Repository Policy — Sparc Energy
*Created: 2026-04-23 | Owner: Dan Alexandru Bujoreanu*
*Purpose: Define the permanent public/private boundary for this repository.*

---

## Principle

This repository is a **public academic and engineering showcase**. It contains
the ML pipeline, governance artefacts, infrastructure code, and engineering
standards for the Sparc Energy building energy forecasting system.

It does **not** contain commercial strategy, personal files, unpublished research,
internal tooling, or any document that could compromise the author's competitive
or personal interests if read by a recruiter, competitor, or journal reviewer.

> If in doubt, keep it private. The `.gitignore` is the enforcement mechanism.
> This document is the policy that governs it.

---

## What Is Public (intentionally committed)

| Category | Examples | Why public |
|----------|---------|-----------|
| **ML source code** | `src/energy_forecast/` | Engineering credibility |
| **Deployment code** | `deployment/app.py`, `deployment/connectors.py` | Shows production-ready work |
| **Tests** | `tests/` | Quality signal |
| **Architecture Decision Records** | `docs/adr/ADR-001` to `ADR-011` | Engineering rigour |
| **Governance artefacts** | `docs/governance/AIIA.md`, `MODEL_CARD.md`, `DATA_LINEAGE.md`, `DATA_PROVENANCE.md`, `SYSTEM_COMPONENT_MAP.md`, `SYSTEM_ACCESS_MODEL.md` | Regulatory + EU AI Act alignment |
| **Deployment runbook** | `docs/DEPLOY_RUNBOOK.md` | MLOps evidence |
| **Engineering standards** | `docs/engineering/BEST_PRACTICES.md`, `docs/engineering/PR_WORKFLOW.md` | Team-readiness signal |
| **Infrastructure docs** | `docs/infra/` | DevOps credibility |
| **Feature docs (public-safe)** | `docs/features/load-forecast/`, `docs/features/demand-response/` | Product transparency |
| **Regulatory research** | `docs/regulatory/SMART_METER_ACCESS.md` | Shows regulatory depth |
| **Project overview + stack** | `docs/PROJECT_OVERVIEW.md`, `docs/TECH_STACK.md`, `docs/ROADMAP.md` | Public narrative |
| **Figures** | `docs/figures/` | Paper + presentation assets |

---

## What Is Private (gitignored — never commit)

| Category | Examples | Reason |
|----------|---------|--------|
| **Commercial strategy** | `docs/COMMERCIAL_ANALYSIS.md`, `docs/COMPETITORS.md`, `docs/MARKET_POSITIONING.md`, `docs/STRATEGY.md` | Competitive intelligence |
| **Personal files** | `docs/PERSONAL_OS_ARCHITECTURE.md`, `docs/PALLONETTO_EMAIL.md`, `CAREER_CONTEXT.md` | Personal / private |
| **Funding applications** | `docs/funding/`, `docs/FUNDING_AND_MONETISATION.md` | Commercial sensitivity |
| **Unpublished research** | `docs/research/JOURNAL_PAPER_DRAFT.md`, `docs/REVIEWER_RESPONSE_MATRIX.md`, `docs/journal/` | Pre-submission confidentiality |
| **Session logs** | `docs/SESSION_LOG.md`, `docs/SESSION_OVERVIEW.md` | Internal workflow, personal details |
| **Internal briefs** | `docs/ENERGY_INTELLIGENCE_MODULE_BRIEF.md`, `docs/governance/ORCHESTRATOR_BRIEF_*.md` | Internal strategic planning |
| **Product spec** | `docs/APP_PRODUCT_SPEC.md` | Reveals unannounced product roadmap |
| **Intel RAG tooling** | `intel/`, `scripts/intel_*.py`, `docs/features/intel-rag/` | Internal research tooling |
| **Agent autonomy notes** | `docs/features/agent-autonomy/` | Contains interview prep, personal strategy |
| **Meeting notes** | `docs/governance/MEETING_NOTES_*.md` | Internal governance discussions |
| **Smart meter personal data** | `data/ESB*/`, `HDF_calckWh*.csv` | GDPR — personal consumption data |
| **Model artefacts** | `outputs/models/*.pkl` | Large binaries + proprietary weights |
| **Secrets** | `.env`, `*.env` | Credentials |
| **Internal roadmap** | `ROADMAP_INTERNAL.md` | Personas, funding strategy, personal details |

---

## Decision Rules

Apply these in order when deciding whether a new file belongs in the public repo:

1. **Does it contain credentials, personal data, or home infrastructure details?** → Private.
2. **Does it contain unpublished research or pre-submission academic content?** → Private until published.
3. **Does it reveal commercial strategy, pricing, or go-to-market plans?** → Private.
4. **Does it reference or depend on the `intel/` RAG module (internal tooling)?** → Private.
5. **Does it contain interview prep, personal career notes, or job application details?** → Private.
6. **Is it engineering code, governance documentation, or published research evidence?** → Public.

---

## Enforcement

The `.gitignore` at the repository root covers all private categories above.

Before any `git add .` or bulk staging operation, run:
```bash
git status --short | grep -v "^?"   # shows only tracked changes
git diff --name-only --cached       # shows exactly what will be committed
```

If a file has been committed accidentally, remove it from the index:
```bash
git rm --cached path/to/file
# Then add it to .gitignore and commit the removal
```

For files that were committed historically and must be purged from all git history,
use `git filter-repo` (see Git History Rewrite section below).

---

## Git History Rewrite (Scheduled)

Several files were committed in earlier sessions before this policy existed and were
later removed from the working tree. They remain in git history. A `git filter-repo`
rewrite is planned to purge them completely before:

- Journal submission to Applied Energy (unpublished paper draft must not be discoverable)
- Any public sharing of the GitHub URL beyond current private visibility

**Procedure (do not run until all open PRs are merged into main):**

```bash
# Install
pip install git-filter-repo

# Create a paths file listing everything to purge
cat > /tmp/paths-to-purge.txt << 'EOF'
docs/PALLONETTO_EMAIL.md
docs/PERSONAL_OS_ARCHITECTURE.md
docs/research/JOURNAL_PAPER_DRAFT.md
docs/SESSION_LOG.md
docs/SESSION_OVERVIEW.md
docs/COMMERCIAL_ANALYSIS.md
docs/COMPETITORS.md
docs/MARKET_POSITIONING.md
docs/STRATEGY.md
docs/TEAM.md
docs/GOVERNANCE.md
docs/APP_PRODUCT_SPEC.md
docs/funding
docs/marketing
docs/product
docs/research
docs/governance/ORCHESTRATOR_BRIEF_2026-04-20.md
docs/ENERGY_INTELLIGENCE_MODULE_BRIEF.md
docs/REVIEWER_RESPONSE_MATRIX.md
docs/journal
docs/features/intel-rag
docs/features/agent-autonomy
docs/features/career-intel
scripts/intel_feeds.py
scripts/intel_ingest.py
intel
EOF

# Rewrite history (IRREVERSIBLE — backup first)
git filter-repo --invert-paths --paths-from-file /tmp/paths-to-purge.txt

# Force push (sole contributor — safe)
git push origin main --force
git push origin --force --tags
```

> ⚠️ This is irreversible. Ensure all open PRs are merged and all local work is committed
> before running. GitHub will show rewritten history immediately after force push.

---

*This policy was established 2026-04-23 after a structured audit of all tracked files.*
*Review whenever a new document category is added to the repository.*
