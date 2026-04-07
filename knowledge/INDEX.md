# Knowledge Index — Building Energy Load Forecast
*This file is the entry point. Read it top-down, then follow links only as needed.*
*Last updated: 2026-03-31 (Session 38)*

---

## Quick State
- **Pipeline**: Complete. LightGBM H+24 R²=0.975, Oslo R²=0.963. 90 tests passing.
- **Governance**: 4 artefacts done — `docs/governance/` (MODEL_CARD, DATA_PROVENANCE, AIIA, DATA_LINEAGE)
- **Paper**: `docs/research/JOURNAL_PAPER_DRAFT.md` — 8 sections, submission-ready
- **Phase 7 (Docker/AWS)**: Config built. Mac Mini alternative under consideration.
- **Phase 8 (Home Trial)**: Eddi API live; billing score computed; `log_eddi.py` ready
- **Docs**: Reorganised into 7 subfolders. Session index in `docs/ops/SESSION_INDEX.md`.
- **Next action**: Journal submission → BGE contract renewal (June 15) → Mac Mini deploy

---

## Domain Knowledge (what things are)
→ [`domain/RESULTS.md`](domain/RESULTS.md) — all key metrics, model performance numbers
→ [`domain/APIS.md`](domain/APIS.md) — myenergi, ESB, Open-Meteo endpoint specs
→ [`domain/TARIFF.md`](domain/TARIFF.md) — BGE rates, tariff logic, scoring model
→ [`domain/DECISIONS.md`](domain/DECISIONS.md) — locked production decisions (do not re-debate)
→ [`domain/HOME_SETUP.md`](domain/HOME_SETUP.md) — Dan's home devices, schedules, setup
→ [`domain/SEAI_PROGRAMS.md`](domain/SEAI_PROGRAMS.md) — SEAI grants, sequencing, payback calculations

## Procedural Knowledge (how to do things)
→ [`procedural/RUN_COMMANDS.md`](procedural/RUN_COMMANDS.md) — all pipeline/script commands
→ [`procedural/DEPLOY.md`](procedural/DEPLOY.md) — Docker/ECR/AppRunner steps
→ [`procedural/EDDI_API.md`](procedural/EDDI_API.md) — myenergi API usage, confirmed endpoints

## Error Log
→ [`ERRORS.md`](ERRORS.md) — known bugs, status, and conclusions

## Full History
→ `docs/ops/SESSION_INDEX.md` — **one-row-per-session table** (start here: "what happened in session X?")
→ `docs/ops/DECISIONS_MAP.md` — **every locked decision** mapped to session + rationale ("why did we do X?")
→ `docs/ops/SESSION_LOG.md` — full narrative (Sessions 1–38 — search by session number, don't read end-to-end)
