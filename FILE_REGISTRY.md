# File Registry — Sparc Energy
# Read this before asking "what does X file do?"
# One line per file. Update when files are added/moved/deleted.

## Root
CLAUDE.md                        Claude operating instructions (trimmed session card — gitignored)
CHANGELOG.md                     Engineering changelog — one entry per DAN closed
README.md                        Public repo README — Sparc pitch + setup
ROADMAP.md                       Engineering roadmap — public GitHub version
docs/ROADMAP.md                  Product roadmap — public GitHub version
MASTER_ROADMAP.md                Full internal roadmap — NOT published (gitignored)
FILE_REGISTRY.md                 This file — one-line description of every non-code file

## docs/ — Engineering reference
docs/COMMANDS.md                 All CLI commands — make targets, curl, pytest, grafana push
docs/DEPLOY_RUNBOOK.md           End-to-end deployment — Docker stack, env vars, rollback
docs/TECH_STACK.md               Full tech stack + rationale
docs/HOW_TO_RUN.md               Quick-start (subset of COMMANDS.md)
docs/PUBLIC_REPO_POLICY.md       What can/cannot go to GitHub — check before git add
docs/SPRINT.md                   Active sprint — read this instead of list_issues (~200 tokens vs 28k)

## docs/ — Product / business (gitignored)
docs/APP_PRODUCT_SPEC.md         Consumer app specification (DAN-60, future)
docs/MARKET_POSITIONING.md       Irish market analysis + competitive landscape
docs/STRATEGY.md                 Product strategy brief
docs/FUNDING_AND_MONETISATION.md Funding strategy (gitignored)
docs/linkedin_posts.md           Sparc promotion posts (gitignored)

## docs/ — Dan's personal / home trial (gitignored)
docs/HOME_TRIAL.md               Dan's Maynooth electricity data — rates, consumption, Eddi schedule
docs/CAREER_PORTFOLIO_TECH.md    Interview portfolio (gitignored)
docs/JOURNAL_PAPER_DRAFT.md      Paper draft based on refactored code (gitignored)
docs/TEAM.md                     Claude persona definitions (Architect, PM, ML Engineer, etc.)

## docs/governance/
docs/governance/DATA_LINEAGE.md       Canonical data lineage — source to DB to model (8 stages)
docs/governance/DATA_PROVENANCE.md    Provenance chain for each data source (GDPR)
docs/governance/MODEL_CARD.md         EU AI Act model card (Art. 52, Limited Risk)
docs/governance/AIIA.md               AI Impact Assessment
docs/governance/SYSTEM_COMPONENT_MAP.md  Component diagram in markdown

## docs/engineering/
docs/engineering/BEST_PRACTICES.md    Python/FastAPI/async coding standards
docs/engineering/PR_WORKFLOW.md       PR + Linear linking workflow
docs/engineering/SOLAR_DATA_PIPELINE.md  Solar actuals pipeline walkthrough
docs/engineering/OPERATING_MODEL.md  Full Linear protocol, session rules, career loop, coding principle detail

## docs/ops/
docs/ops/HYPERCARE_PROTOCOL.md    Monitoring thresholds + rollback runbook (App Runner go-live)
docs/ops/RELEASE_PROTOCOL.md      Release checklist
docs/ops/CODE_AUDIT_2026-04-08.md Code audit findings — partially actioned
docs/ops/DECISIONS_MAP.md         Key technical decision log

## docs/regulatory/
docs/regulatory/SMART_METER_ACCESS.md  P1 port, SMDS, CRU202517, ESCO registration

## docs/explainers/ — Narrative walkthroughs (onboarding / paper appendix)
docs/explainers/METER_UPLOAD_PIPELINE_EXPLAINED.md
docs/explainers/MLOPS_OBSERVABILITY_EXPLAINED.md
docs/explainers/MYENERGI_POLLER_EXPLAINED.md
docs/explainers/SOLAR_ADVISORY_EXPLAINED.md
docs/explainers/TARIFF_ENGINE_EXPLAINED.md

## docs/adr/ — Architecture Decision Records (immutable once merged)
docs/adr/ADR-001 through ADR-012 — see docs/adr/README.md

## docs/api/
docs/api/MYENERGI_FIELD_REFERENCE.md   Field-by-field reference for MyEnergi API (h1b, h1d, imp, etc.)
docs/api/MyEnergi_API_Docs/            Full MyEnergi 3rd-party API docs (mirrored)

## knowledge/ — Domain reference (read-only, gitignored)
knowledge/domain/COMPETITORS.md        11 Irish suppliers + PCW analysis
knowledge/domain/TARIFF.md             Irish tariff structures
knowledge/domain/ESB_NETWORKS_INTEL.md ESB Networks data access + P1 port
knowledge/domain/HARDWARE_DECISIONS.md Zappi, Eddi, hub hardware decisions
knowledge/ERRORS.md                    Known errors + fixes (Critical Bugs active list)

## intel/ — RAG source material (gitignored — ingest via scripts/intel_ingest.py)
intel/docs/market/                      Supplier rate cards, PCW data
intel/docs/market/ANTIGRAVITY_TASKS.md  13 Antigravity scraping prompts — 6 missing suppliers

## scripts/ — Production scripts
scripts/intel_ingest.py       RAG ingest CLI
scripts/verify_tariffs.py     Verify tariff registry against live rates
scripts/myenergi_backfill.py  Backfill 846 days of MyEnergi data (idempotent)
scripts/run_pipeline.py       Full training pipeline CLI
scripts/export_predictions.py Export predictions from DB

## research/scripts/ — Thesis/research only (not production)
research/scripts/             See research/scripts/README.md — 7 MSc AI thesis scripts

## deployment/ — Production FastAPI app (after 2026-05-01 refactor)
deployment/app.py             FastAPI factory + lifespan (~146L)
deployment/scheduler.py       APScheduler jobs + create_scheduler()
deployment/schemas.py         All Pydantic request/response models
deployment/routers/health.py  /health, /metrics endpoints
deployment/routers/meters.py  /upload, /forecast/{household_id} endpoints
deployment/routers/control.py /predict, /control, /compare-plans endpoints
deployment/live_inference.py  Morning brief CLI (dry-run safe)
deployment/connectors.py      CSVConnector, OpenMeteoConnector, MyEnergiConnector, SEMOConnector
deployment/Dockerfile         Container build (non-root, health-checked)

## infra/
infra/db/init.sql               Full PostgreSQL schema (auto-runs on docker compose up)
infra/db/migrations/            SQL migrations — 001–004 applied; 005 = DAN-152 next
infra/grafana/                  Grafana dashboard + alert provisioning (auto-provisioned)
infra/n8n/                      n8n workflow exports
infra/Caddyfile                 Reverse proxy — api.sparc.localhost / grafana.sparc.localhost
