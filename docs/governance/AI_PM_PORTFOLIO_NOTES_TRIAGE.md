# AI PM Portfolio Notes — Triage Decision Log

**Source:** `/Users/danalexandrubujoreanu/NCI/0. MSCTOPUP/Thesis WIP 2026/AI_PM_Portfolio_Notes/`
**Reviewed:** 2026-04-20 | **Reviewed by:** Claude Code (Energy Sparc session)

---

## Source Accuracy Assessment

Google Antigravity (the tool that produced these notes) had read access to Sparc repo files.
Accuracy was higher than initially expected:

| Claim | Status | Reality |
|-------|--------|---------|
| 153 tests | ⚠️ Close | **178 tests** (12 integration, 20 registry, 23 drift, 19 validation, 54 connector) |
| TimescaleDB in stack | ✅ Accurate | In `docker-compose.yml` + `infra/db/init.sql` — full schema, not yet in production |
| Redis in stack | ✅ Accurate | In `docker-compose.yml`, wired to FastAPI — not yet in production |
| Grafana in stack | ✅ Accurate | In `docker-compose.yml` + `infra/grafana/provisioning/` — not yet in production |
| DriftDetector (KS+PSI) | ✅ Accurate | `src/energy_forecast/monitoring/drift_detector.py`, 23 tests |
| ModelRegistry | ✅ Accurate | `src/energy_forecast/registry/model_registry.py`, 20 tests |
| APScheduler | ❌ Not in repo | Concept in docs; not coded |
| n8n in docker-compose | ❌ Not there | Mentioned in TECH_STACK.md as planned |
| Dual-stack (OSS + Azure) | ✅ Accurate | Already executing (DAN-80) |

**Key lesson:** CLAUDE.md + docker-compose are the ground truth. Memory.md was incomplete.
The Haiku agents (and my own initial read) overstated the hallucination problem.

---

## Triage by File

### IMPLEMENTED in Sparc (this session)

| File | What was taken | Where it went |
|------|---------------|--------------|
| `Lenny_Newsletter_RAG_Strategy.md` | Agent Level taxonomy (L1/L2/L3) mapped to roadmap | `docs/features/agent-autonomy/README.md` |
| `Energy_Sparc_Architecture_Diagram.md` | Mermaid architecture diagram (corrected for accuracy) | `docs/features/agent-autonomy/TARGET_ARCHITECTURE.md` |
| `n8n_ClaudeCode_Integration.md` | Custom PR hook concept (without n8n overhead) | `.claude/commands/sparc-pr.md` |
| `AI_PM_Persona_DASME.md` | DASME applied to Energy Planner L2 | `docs/features/agent-autonomy/README.md` → DASME table |
| `aakash_ai_system_design.md` | Agent-friendly CLI recommendation | Added to roadmap backlog (--json flag) |

### ROUTED TO CAREER SESSION

Forward these files (or ingest into `intel/docs/career/`) for Career RAG:

| File | Career value |
|------|-------------|
| `AI_PM_Persona_DASME.md` | Full interview positioning framework — AI R&D Lead persona |
| `aakash_ai_system_design.md` | DASME framework for AI system design interviews; mock interview transcript (churn agent) |
| `Lenny_Newsletter_RAG_Strategy.md` | Agent level taxonomy as interview narrative: "We restricted MVP to L2 deliberately" |

**Orchestrator instruction for Career session:**
> Ingest these three files into `intel/docs/career/frameworks/` and add them to the career ChromaDB tier.
> When Dan prepares for AI PM interviews, the morning brief query should surface:
> - DASME framework (Define → Architect → Specify → Map → Edge Cases)
> - Agent level taxonomy (L1 observer → L2 co-pilot → L3 autonomous)
> - Key interview principle: 30-40% product framing, 60-70% system architecture

### ROUTED TO ORCHESTRATOR

| Item | Instruction |
|------|------------|
| `lennyhub-rag` repository | Verify if this repo exists at `~/lennyhub-rag`. If yes, report its status and whether it's connected to any active RAG tier. If no, this is a hallucinated reference. |
| DASME framework for GARDEN | When GARDEN project grows to interview-relevant state, apply the same L1/L2/L3 agent capability tiers to the Digital Twin Gardening roadmap |
| Agent-friendly CLI pattern | Apply `--json` output flag standard across all CLI scripts (Sparc + future projects) when implementing |

### SKIPPED (not applicable)

| File | Reason |
|------|--------|
| `n8n_ClaudeCode_Integration.md` — full n8n stack | Over-engineering; git hooks achieve same quality gate; n8n is in TECH_STACK.md as future consideration, not Sprint 1 |
| `implementation_plan.md` + `task.md` | These are Antigravity's own task notes for transcribing a Linear intro video — not Sparc content |
| `video_transcript.md` | Linear intro video transcript — no actionable content |
| Auto-fix flaky tests | 178 tests are stable; autonomous patching risks masking real bugs |

---

## What to Claim in Interviews (Verified Facts Only)

| Claim | Verified | Source |
|-------|----------|--------|
| 178 tests, 0 failures | ✅ | `pytest tests/ -q` — 2026-04-20 |
| LightGBM MAE 4.03 kWh, R²=0.975 | ✅ | `outputs/results/final_metrics.csv` |
| DM significance: LightGBM vs PatchTST −12.17*** | ✅ | `scripts/significance_test.py` |
| DriftDetector with KS+PSI | ✅ | `src/energy_forecast/monitoring/drift_detector.py` |
| ModelRegistry with rollback | ✅ | `src/energy_forecast/registry/model_registry.py` |
| JSONL audit log (EU AI Act Art. 52) | ✅ | `outputs/logs/control_decisions.jsonl` |
| TimescaleDB in stack | ✅ (with caveat) | In compose; say "infrastructure defined, activating with first multi-user deployment" |
| Grafana dashboard | ✅ (with caveat) | In compose; say "provisioned, activating post Phase 7 App Runner deploy" |
| Redis caching layer | ✅ (with caveat) | In compose; say "wired, activating under load" |
| 7-tier ChromaDB RAG | ✅ | `intel/` — operational |
| €178/year saving identified | ✅ | `scripts/score_home_plan.py` on ESB HDF file |

**Do NOT claim:**
- APScheduler (not in code)
- n8n (in TECH_STACK.md as planned, not deployed)
- Autonomous test-repair (not built)
