# Strategy Review — Session 45 (2026-04-24)

**Facilitator**: Staff PM (Dan)
**Personas present**: PM, VP Engineering, Director, Data Scientist
**Session type**: Ad hoc — triggered by industry feedback gap

---

## Context since last review

**What shipped:**
- LLM advisory layer (Phase 13) — natural language explanations from LightGBM predictions
- README governance section — Model Card, AIIA, Data Lineage all visible on first page
- PR #10 merged to main
- HOW_WE_WORK.md + MEMORY.md updated with token efficiency protocol

**Key event that triggered this review:**
Industry feedback highlighted that end-to-end Gen AI application visibility was a gap — the pipeline's AI/ML sophistication wasn't legible from the outside. This triggered a priority reorder.

**Correction logged:**
RAG stack is LlamaIndex + ChromaDB (NOT LangChain + FAISS). LangChain appears only in the Azure dual-stack portfolio project (DAN-80). This distinction is critical for interview prep.

---

## Persona Round-Table

**Staff PM:**
The POST /upload endpoint (DAN-96) is the highest-priority gap. Without it, there is no data ingest path and the app is a demo with hardcoded data. Every other product feature is blocked until real ESB data can flow in.

**VP Engineering:**
Phase 7 (Docker → ECR → AWS App Runner) is the production deployment path. apprunner.yaml exists, Dockerfile exists. The path is clear — execution is what's needed. CI is already green (lint, type check, pytest, Docker smoke test on Python 3.10/3.11). Need to add the CD layer.

**Data Scientist:**
The Regulatory RAG tier (DAN-119) is the most defensible differentiator in this domain. CRU documents, ESB Networks compliance requirements, EU AI Act compliance Q&A — these change slowly, are publicly available, and are critical for any energy ESCO. LlamaIndex + ChromaDB + MiniLM is the right stack.

**Director:**
AWS Activate deadline was April 25 (imminent). Application at `docs/funding/AWS_ACTIVATE_APPLICATION.md`. Submit today. No engineering blocked, this is just a form submission.

---

## Priority Reorder

| Rank | Issue | Rationale |
|---|---|---|
| 1 | DAN-89 — AWS Activate | Hard deadline April 25 |
| 2 | DAN-96 — POST /upload | MVP critical path; data ingest |
| 3 | DAN-119 — Regulatory RAG | Highest strategic differentiator |
| 4 | DAN-49 — App Runner | Public URL needed for demos |
| 5 | DAN-120 — Streamlit dashboard | Demo artefact alongside App Runner |
| 6 | DAN-5 — Journal paper | Parallel track, due May 31 |
| 7 | DAN-121 — How-to-build guides | Valuable but not critical path |
| 8 | DAN-112 — Engineering RAG | Build last |

---

## Decisions Made

| Decision | Rationale | Owner | Date |
|---|---|---|---|
| Visibility gap was the issue, not depth | LLM advisory + README governance closes the gap. No architectural changes needed. | PM | 2026-04-24 |
| Regulatory RAG is highest-value RAG tier | No Irish energy company currently does regulatory document Q&A | VP Engineering | 2026-04-24 |
| LlamaIndex, not LangChain | Sparc uses LlamaIndex + ChromaDB + MiniLM. LangChain = Azure portfolio only. Critical for interviews. | Data Scientist | 2026-04-24 |

---

## Actions

| Action | Owner | Due | Linear |
|---|---|---|---|
| Submit AWS Activate application | Director | 2026-04-25 | DAN-89 |
| Build POST /upload endpoint | Backend | 2026-05-01 | DAN-96 |
| Start Regulatory RAG tier | Data Scientist | 2026-05-10 | DAN-119 |
| Begin App Runner deploy | VP Engineering | 2026-05-15 | DAN-49 |

---

## Next Review
After DAN-96 (POST /upload) ships.
