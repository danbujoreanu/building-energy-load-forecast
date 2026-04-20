# Orchestrator Brief — 2026-04-20 (Energy Sparc Session 44)

**For:** Orchestrator session  
**From:** Energy Sparc session (Claude Code)  
**Priority:** Read before next career or gardening session

---

## Action Required: Career Session (DAN-95)

Run this command in a Career session or trigger it directly:

```bash
cd ~/building-energy-load-forecast
~/miniconda3/envs/ml_lab1/bin/python scripts/intel_ingest.py \
  --tier career --dir intel/docs/career/frameworks/

# Verify:
~/miniconda3/envs/ml_lab1/bin/python scripts/intel_ingest.py --status
```

**Four new files were added to `intel/docs/career/frameworks/`:**
1. `FRAMEWORK_SELECTION_GUIDE.md` — DASME / DMAIC / DMEDI situational guide + bridge statement
2. `AI_PM_Persona_DASME.md` — Full AI R&D Lead interview positioning (from Google Antigravity)
3. `aakash_ai_system_design_interview.md` — Mock AI system design interview transcript + DASME framework
4. `lenny_agent_levels_strategy.md` — L1/L2/L3 agent autonomy taxonomy for interview narratives

Once ingested, the career RAG will answer questions like:
- "Which framework should I use for this interview?"
- "How do I answer an AI system design question?"
- "What's the bridge statement between DASME and DMAIC?"

---

## Key Framework Decision to Propagate Across Projects

**Rule: Use frameworks situationally, name the switch.**

| Framework | Use when |
|-----------|----------|
| **DASME** | AI PM system design interview (new system, draw the diagram) |
| **DMAIC** | Process improvement with ops/utility audience |
| **DMEDI** | New product with structured evidence-gathering |
| **Porter + VRIN** | Competitive strategy discussions |
| **BMC** | Business model / funding applications |

**Bridge statement for all Career sessions:**
> *"I applied DASME to architect the ML pipeline — new system design problem. Switched to DMAIC for customer onboarding friction — that's process improvement. Different tools for different questions."*

Apply this framing to: job spec analysis, interview prep, LinkedIn posts, any career-facing output.

---

## Check: Does `lennyhub-rag` Exist?

Google Antigravity referenced a `lennyhub-rag` repository (a RAG over Lenny's Newsletter archive).

**Action:** Check if this repo exists at `~/lennyhub-rag` or anywhere in the user's filesystem. If it does:
- Report its status (what tier is it ingested into?)
- Link it to the career RAG if relevant

If it doesn't exist: note it as hallucinated (don't create it unless Dan requests it explicitly).

---

## Apply Issue Documentation Standard to GARDEN

The Sparc session created a documentation standard at:
`~/building-energy-load-forecast/docs/governance/ISSUE_DOCUMENTATION_STANDARD.md`

**Action for GARDEN team in Linear:**
- Any GARDEN issues you create must follow this standard
- Every Done issue needs a **"To verify"** runnable command
- Every Todo issue needs **exact commands** with full paths + `~/miniconda3/envs/ml_lab1/bin/python`

---

## Sparc Session State (for context)

| Item | Status | Where |
|------|--------|-------|
| AWS Activate application | 🔴 URGENT — deadline Apr 25 | `docs/funding/AWS_ACTIVATE_APPLICATION.md` |
| Docker stack first run | 🔴 Todo (DAN-92) | `docs/infra/DOCKER_BEGINNER_GUIDE.md` |
| Intel feeds first ingestion | 🟡 Todo (DAN-90) | `docs/features/intel-rag/README.md` |
| Azure dual-stack (DAN-80) | 🟠 This week | `Personal Projects/Azure Energy AI Portfolio/` |
| Career framework ingest | 🟡 Todo (DAN-95) | This brief |
| n8n local setup | 🟡 Backlog (DAN-94) | `docs/infra/services/N8N.md` |

---

## Nothing Required for Gardening Session

No actions from this session need to be cascaded to the Gardening/Greenhouse project.  
When the GARDEN project grows to a point where RAG or agent capability tiers are relevant, apply the same L1/L2/L3 framework from `docs/features/agent-autonomy/README.md`.
