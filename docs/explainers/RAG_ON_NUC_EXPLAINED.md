# RAG on Production Hardware — How We Deployed the Intel Module to the NUC
*What happened in this session, why it matters, and how to explain it in a BSS interview.*
*Last updated: 2026-05-13*

---

## What Was Built

A RAG (Retrieval-Augmented Generation) system running on a local Intel NUC (home server), served as live API endpoints, queryable by any HTTP client. It indexes 15 operational explainer documents and answers plain-English questions about the Sparc Energy system.

**Live endpoints (as of 2026-05-09, updated 2026-05-13):**
```
POST /intel/ask      → Ask a question, get a Gemini-synthesised answer
POST /intel/query    → Retrieve raw matching chunks (no LLM)
GET  /intel/status   → Document and chunk counts per tier
GET  /intel/tiers    → Available knowledge tiers
```

**Chat UI (Streamlit):**
- `http://localhost:8502` — from your Mac (via permanent SSH tunnel in launchd)
- `http://192.168.68.119:8502` — direct LAN access
- Service: `sparc-intel-ui` in `docker-compose.yml` (auto-starts with the stack)

**Example query:**
```bash
curl -X POST http://192.168.68.119:8000/intel/ask \
  -H "Content-Type: application/json" \
  -d '{"tier": "operational", "query": "How do I backfill myenergi data?", "top_k": 5}'
```

---

## The Architecture — End to End

```
1. DOCUMENTS (.md files in intel/docs/operational/)
   15 explainers covering every subsystem:
   - MYENERGI_POLLER_EXPLAINED.md
   - SOLAR_ADVISORY_EXPLAINED.md
   - OPERATIONS_MANUAL.md
   - GRAFANA_DASHBOARDS_EXPLAINED.md
   - ... (12 more)

2. INGEST PIPELINE (intel/ingest.py)
   SimpleDirectoryReader → SentenceSplitter (512 tokens, 50 overlap)
   → HuggingFaceEmbedding (all-MiniLM-L6-v2, 384d vectors)
   → ChromaDB PersistentClient (collection: intel_operational)
   SHA-256 dedup: skips unchanged files on re-ingest

3. VECTOR STORE (data/chromadb/)
   ChromaDB persisted to disk on NUC
   ~15 documents → ~200 chunks → ~200 × 384d vectors

4. RETRIEVAL (intel/retrieval.py)
   Embed query → cosine similarity search → top-k chunks
   Confidence flag if top_score < 0.60

5. CONTEXT BUILDER (intel/context_builder.py)  [E-25]
   Chunks + question → AdvisorContext (system_prompt + user_message)

6. LLM SYNTHESIS — two paths exist in the codebase:

   Path A: intel/context_builder.py → call_llm()        [used by FastAPI /intel/ask + Streamlit]
     Gemini 3.1 Flash Lite (free API) → raw chunks

   Path B: intel/retrieval.py → _get_llm()              [used by scripts/rag_query.py CLI only]
     Ollama gemma3:4b (local) → raw chunks
     (Ollama not installed on NUC → always falls back to raw chunks today)

   Note: Claude Haiku fallback removed 2026-05-13 — was burning paid API tokens.
```

## LLM Synthesis Chain — Current vs Target

| | Path A (FastAPI/UI) | Path B (CLI) | Target (Mac Mini M5) |
|---|---|---|---|
| Primary | Gemini 3.1 Flash Lite | Ollama gemma3:4b (→ raw, not on NUC) | Ollama gemma3:4b |
| Fallback | Raw chunks | Raw chunks | Gemini 3.1 Flash Lite |
| Final fallback | — | — | Raw chunks |

**The two paths should be unified.** Path B was written assuming Ollama runs locally — it doesn't on the NUC. Path A (Gemini) is what actually synthesises answers today.

**When Mac Mini M5 arrives:** point `OLLAMA_HOST=http://<mac-mini-ip>:11434` in the NUC `.env`. Both paths pick it up. Priority order becomes: Ollama → Gemini → raw — same as Gardening project. This is the target for both projects.

**Privacy:** Only the synthesis step sends data outside the home network (query + doc excerpts to Google). Embeddings and retrieval are 100% local on the NUC. Ollama as primary eliminates any external data transfer entirely.

---

## The Deployment Problem — What Made This Interesting

Getting the RAG module to run inside the Docker container involved solving three real infrastructure problems. This is the kind of thing that separates "I've read about RAG" from "I've shipped RAG."

### Problem 1: Python module not found

The FastAPI app tried `from intel.routes import router` and got `No module named 'intel'`.

**Root cause:** Docker Compose set `PYTHONPATH: /app/src`, but the intel module was copied to `/app/intel/`. Python only searched `/app/src/` and couldn't see it.

**Fix:** Changed `PYTHONPATH: /app/src` → `PYTHONPATH: /app/src:/app` in docker-compose.yml. `/app` is now in the search path, so `import intel` finds `/app/intel/__init__.py`.

**Pattern to remember:** When you add a new module to a containerised app, check PYTHONPATH matches where the module actually lives.

### Problem 2: Dependencies not in the Docker image

After fixing the import path: `No module named 'chromadb'`.

**Root cause:** `chromadb`, `sentence-transformers`, and `llama-index-*` weren't in `deployment/requirements.txt` — only in `requirements-intel.txt` (which the Dockerfile didn't reference).

**Fix:** Added the intel dependencies to `deployment/requirements.txt`. For the running container (no image rebuild), used `pip install` directly into the container. On next image rebuild, the deps will be baked in.

**Pattern:** Two requirements files is a liability. Keep a single source of truth, or clearly document which file drives each environment.

### Problem 3: Volume mount for persistence

The intel Python module was docker-cp'd into the container, but `docker compose up` recreates containers from the image — wiping any docker-cp'd files.

**Fix:** Added a volume mount to docker-compose.yml:
```yaml
volumes:
  - ./outputs:/app/outputs
  - ./intel:/app/intel    # ← new: host ~/sparc/intel/ → container /app/intel/
```

Now `intel/` on the NUC host is live-mounted into the container. `rsync` from Mac keeps it in sync. Container restarts preserve the module — no docker-cp needed.

**Pattern:** For code that changes frequently (like a RAG document corpus), a volume mount beats baking into the image. Faster iterations, no rebuild cycle.

---

## Why This Matters for BSS — The Interview Angle

### "Have you deployed a RAG pipeline to production?"

Yes. Not to AWS — to a home NUC server, which is actually harder: no managed services, no auto-scaling, no ECR. Every infrastructure decision was explicit.

The deployment stack:
- **FastAPI** serves the `/intel/ask` endpoint
- **ChromaDB** persists the vector index to disk (`/app/data/chromadb/`)
- **all-MiniLM-L6-v2** runs locally (no API cost, ~10ms per query)
- **Claude haiku-4-5** synthesises the answer (ANTHROPIC_API_KEY in `.env`)
- **Docker Compose** orchestrates everything (9 containers total)
- **rsync** syncs document updates from Mac to NUC

### "How would you build this for BSS?"

The architecture maps directly:
- Replace `intel/docs/operational/*.md` with Tracker RMS candidate profiles + job briefs
- Replace `intel_operational` ChromaDB collection with `ats_candidates` + `job_briefs`
- Replace the Sparc system prompt with a recruitment-domain prompt
- Hook Tracker webhooks into n8n → ingest pipeline (exactly as described in RAG_PIPELINE_EXPLAINED.md)

The Sparc system taught me the failure modes before building BSS's version. That's worth more than a theoretical design.

### The three real problems above — use them

When BSS asks "what went wrong during your builds?" — these three problems are the honest, specific answer. They're real. They're infrastructure. They show you debug systematically rather than guess.

---

## How to Add More Documents

```bash
# 1. Write a new .md explainer on Mac
echo "# My New Doc\n..." > ~/building-energy-load-forecast/intel/docs/operational/NEW_THING.md

# 2. Sync to NUC
rsync -av ~/building-energy-load-forecast/intel/docs/ \
  dan@192.168.68.119:~/sparc/intel/docs/

# 3. Trigger re-ingest (once intel routes are live)
curl -X POST http://192.168.68.119:8000/intel/ingest

# That's it. SHA-256 dedup means only new/changed files are re-embedded.
```

---

## Testing the System

```bash
# Is the index working?
curl http://192.168.68.119:8000/intel/status

# Ask a question
curl -X POST http://192.168.68.119:8000/intel/ask \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "operational",
    "query": "How do I restart the API if it crashes?",
    "top_k": 5
  }'

# Expected response shape:
{
  "answer": "To restart the API...",
  "sources": [{"file": "OPERATIONS_MANUAL.md", "score": 0.84, "excerpt": "..."}],
  "top_score": 0.84,
  "low_confidence": false,
  "llm_used": true,
  "model": "claude-haiku-4-5"
}
```

If `llm_used: false` → ANTHROPIC_API_KEY is not set in `.env`. The answer will still be the raw retrieved context, just not synthesised.

---

## The Bigger Picture — What "Putting RAG in Production" Actually Means

Most RAG tutorials stop at `langchain.run("What is X?")` in a Jupyter notebook. Production RAG involves:

1. **Persistence** — the vector index survives container restarts (ChromaDB on disk + volume mount)
2. **Incremental updates** — new documents don't require re-embedding the entire corpus (SHA-256 dedup)
3. **Confidence signalling** — low-score queries return `low_confidence: true` so the caller can decide whether to trust the answer
4. **Graceful degradation** — no API key? Returns raw context instead of a 500 error
5. **Infrastructure plumbing** — PYTHONPATH, volume mounts, dependency management — the boring part that stops most demos from shipping

All five are live on the NUC. Not in theory.

---

*Source: intel/ingest.py, intel/retrieval.py, intel/context_builder.py, intel/routes.py*
*Deployment: docker-compose.yml (NUC), migration 011, OPERATIONS_MANUAL.md*
