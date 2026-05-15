# Intel Module Deployment — End to End
*How we built a local RAG system that answers plain-English questions about the Sparc Energy stack.*
*Last updated: 2026-05-09*

---

## What Was Built and Why

The Sparc system has 16+ explainer documents covering every subsystem. The problem: finding the right document and scanning it takes 5+ minutes. The goal: type a question, get an answer in 10 seconds.

**Example:**
```bash
# Instead of opening MYENERGI_POLLER_EXPLAINED.md and searching...
curl -X POST http://192.168.68.119:8000/intel/ask \
  -H "Content-Type: application/json" \
  -d '{"tier": "operational", "query": "How do I backfill myenergi data?", "top_k": 5}'

# Response in ~3 seconds:
{
  "answer": "To backfill myenergi data, run: python scripts/myenergi_backfill.py --start-date YYYY-MM-DD --force. The --force flag re-fetches even days already in the database. Expected runtime is ~90 minutes for 1200 days. The script uses the same MyEnergi jday API endpoint as the daily poller...",
  "sources": [{"file": "MYENERGI_POLLER_EXPLAINED.md", "score": 0.87}],
  "top_score": 0.87,
  "low_confidence": false,
  "llm_used": true,
  "model": "claude-haiku-4-5"
}
```

This is called a **RAG pipeline** — Retrieval-Augmented Generation. The documents are pre-processed into a searchable vector database, and when you ask a question, relevant chunks are retrieved and sent to Claude for synthesis.

---

## Architecture: Five Layers

```
Layer 1: DOCUMENTS
  intel/docs/operational/*.md
  (16 explainer files covering every subsystem)
         │
         ▼
Layer 2: INGEST PIPELINE  (intel/ingest.py)
  SimpleDirectoryReader → SentenceSplitter(512 tokens, 50 overlap)
  → HuggingFace all-MiniLM-L6-v2 → 384-dimensional vectors
  SHA-256 dedup: only re-embeds changed files
         │
         ▼
Layer 3: VECTOR STORE  (ChromaDB at /app/outputs/chromadb/)
  ~200 chunks, each a 384-dim vector
  Collection: intel_operational
         │
         ▼
Layer 4: RETRIEVAL  (intel/retrieval.py)
  Query → embed → cosine similarity → top-5 chunks
  Low confidence flag if top score < 0.60
         │
         ▼
Layer 5: LLM SYNTHESIS  (Anthropic API)
  Chunks + question → Claude haiku-4-5 → plain-English answer
  Fallback: returns raw chunks if no API key
```

---

## File Structure

```
building-energy-load-forecast/
├── intel/
│   ├── __init__.py
│   ├── ingest.py          # PDF/MD → chunk → embed → ChromaDB
│   ├── retrieval.py       # Query → cosine search → top-k chunks
│   ├── context_builder.py # Chunks + question → AdvisorContext
│   ├── routes.py          # FastAPI /intel/* endpoints
│   └── docs/
│       └── operational/   # 16 .md explainer files
│           ├── MYENERGI_POLLER_EXPLAINED.md
│           ├── SOLAR_ADVISORY_EXPLAINED.md
│           ├── OPERATIONS_MANUAL.md
│           └── ... (13 more)
```

---

## The Five Deployment Problems (and How We Fixed Them)

This is where "I've read about RAG" becomes "I've shipped RAG." These were real blockers.

### Problem 1: Python Can't Find the Module

**Symptom:** FastAPI started, but any request to `/intel/*` returned:
```
No module named 'intel'
```

**Root cause:** Docker Compose had:
```yaml
environment:
  PYTHONPATH: /app/src
```
But the intel module was at `/app/intel/` (copied there by rsync). Python searched `/app/src/` and couldn't find `intel/__init__.py`.

**Fix:**
```yaml
environment:
  PYTHONPATH: /app/src:/app   # Added :/app
```
Now Python searches both `/app/src/` (for the energy forecast package) AND `/app/` (where intel/ lives).

**Rule to remember:** When you add a new top-level module to a Docker container, check PYTHONPATH includes the directory it lives in.

---

### Problem 2: Dependencies Not in the Docker Image

**Symptom:** After fixing the import path:
```
No module named 'chromadb'
```
Then separately: `No module named 'llama_index'`, `No module named 'sentence_transformers'`

**Root cause:** The intel module had its own `requirements-intel.txt` on the Mac, but `deployment/requirements.txt` (which the Dockerfile uses) didn't include these packages.

**Fix 1 (immediate):** Manually pip install into the running container:
```bash
docker exec sparc-api pip install chromadb==0.6.3 \
  'llama-index-core==0.12.52.post1' \
  'llama-index-vector-stores-chroma==0.4.2' \
  'llama-index-embeddings-huggingface==0.5.5' \
  sentence-transformers==3.4.1 \
  'anthropic>=0.40.0'
```

**Fix 2 (permanent):** Added deps to `deployment/requirements.txt`:
```
llama-index-core==0.12.52.post1
llama-index-vector-stores-chroma==0.4.2
llama-index-embeddings-huggingface==0.5.5
chromadb==0.6.3
sentence-transformers==3.4.1
anthropic>=0.40.0
```
On next Docker image rebuild, deps will be baked in.

**Rule to remember:** Two requirements files is a liability. If a module needs packages, they belong in the same requirements file the Dockerfile references.

---

### Problem 3: pip Installs Don't Survive Container Recreation

**Symptom:** You install packages manually. Container works. Next time you run `docker compose up -d api` (even for an unrelated config change), all manual pip installs are gone.

**Root cause:** `docker compose up` recreates the container from the image. The image doesn't have the packages. The writable container layer (where pip install went) is thrown away.

**Fix — short term:** Use `docker restart sparc-api` instead of `docker compose up -d api` whenever possible. `docker restart` keeps the existing container (and its pip installs). `docker compose up` recreates it.

```bash
# This PRESERVES pip installs:
docker restart sparc-api

# This WIPES pip installs:
docker compose up -d api
```

**Fix — long term:** Rebuild the Docker image with the deps baked in. After adding packages to `deployment/requirements.txt`:
```bash
# On NUC:
cd ~/sparc
docker compose build api
docker compose up -d api
```
Then `docker compose up -d api` is safe because the image already has the packages.

**Rule to remember:** Container = image + writable layer. `compose up` replaces the whole thing. `restart` just bounces the existing container.

---

### Problem 4: ChromaDB Can't Write to the Default Path

**Symptom:** `/intel/status` returned HTTP 500. Container logs showed:
```
PermissionError: [Errno 13] Permission denied: '/app/data'
```

**Root cause:** `intel/ingest.py` defaulted ChromaDB to `./data/chromadb/` (relative to project root = `/app/data/chromadb/`). But `/app/data/` didn't exist as a volume mount in Docker — it was inside the container filesystem which isn't writable for that path.

**Fix:** Two changes:

1. Made `CHROMA_PATH` configurable via environment variable in `intel/ingest.py`:
```python
CHROMA_PATH = os.environ.get(
    "CHROMA_PATH",
    str(_PROJECT_ROOT / "data" / "chromadb"),  # fallback for local dev
)
```

2. Set the env var in `docker-compose.yml` to point to the existing writable volume:
```yaml
environment:
  CHROMA_PATH: /app/outputs/chromadb   # outputs/ already has a volume mount
```

**Rule to remember:** In Docker, only volume-mounted paths survive container recreation and are writable. Always check `volumes:` in docker-compose.yml to see what paths are safe to write to.

---

### Problem 5: Volume Mount Missing for the Intel Module

**Symptom:** `docker compose up -d api` recreates the container. The intel module is gone.

**Root cause:** The intel module was being copied into the container with `docker cp`. But `docker compose up` creates a fresh container from the image, which doesn't include the docker-cp'd files.

**Fix:** Added a volume mount in `docker-compose.yml`:
```yaml
volumes:
  - ./outputs:/app/outputs    # existing — for ChromaDB, logs
  - ./intel:/app/intel        # NEW: host ~/sparc/intel/ → container /app/intel/
```

Now `intel/` on the NUC host is live-mounted into the container. When you rsync from Mac:
```bash
rsync -av ~/building-energy-load-forecast/intel/ \
  dan@192.168.68.119:~/sparc/intel/
```
...the container immediately sees the changes. No docker cp, no container recreation needed.

**Rule to remember:** For code that changes frequently, a volume mount beats baking into the image. Changes are immediate; no rebuild cycle.

---

## How to Use the API

All endpoints are at `http://192.168.68.119:8000`.

### Ask a Question
```bash
curl -X POST http://192.168.68.119:8000/intel/ask \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "operational",
    "query": "How do I restart the API if it crashes?",
    "top_k": 5
  }'
```

**Response fields:**
- `answer` — Claude's plain-English synthesis (or raw context if no API key)
- `sources` — which documents were retrieved, with relevance scores
- `top_score` — best match score (0.0–1.0; >0.7 = good match)
- `low_confidence` — true if top_score < 0.60 (answer may be unreliable)
- `llm_used` — true if Claude synthesised the answer, false if raw context returned
- `model` — which Claude model was used

### Check Index Status
```bash
curl http://192.168.68.119:8000/intel/status
# Returns: { "operational": { "docs": 16, "chunks": 203 } }
```

### Retrieve Raw Chunks (No LLM)
```bash
curl -X POST http://192.168.68.119:8000/intel/query \
  -H "Content-Type: application/json" \
  -d '{"tier": "operational", "query": "panel factor", "top_k": 3}'
```
Useful for debugging: see exactly what chunks would be sent to the LLM.

### Trigger Re-Ingest
```bash
curl -X POST http://192.168.68.119:8000/intel/ingest \
  -H "Content-Type: application/json" \
  -d '{"tier": "operational"}'
```
Run this after adding or changing any .md file in `intel/docs/operational/`. SHA-256 deduplication ensures unchanged files are skipped.

---

## Adding New Documents

When you write a new explainer:

```bash
# 1. Write the explainer on Mac
# (put it in ~/building-energy-load-forecast/intel/docs/operational/)

# 2. Sync to NUC
rsync -av ~/building-energy-load-forecast/intel/docs/ \
  dan@192.168.68.119:~/sparc/intel/docs/

# 3. Trigger re-ingest
curl -X POST http://192.168.68.119:8000/intel/ingest \
  -H "Content-Type: application/json" \
  -d '{"tier": "operational"}'

# 4. Verify
curl http://192.168.68.119:8000/intel/status
```

The `SHA-256 dedup` means even if you run ingest 10 times, unchanged files are skipped instantly. Only new or changed files get re-embedded.

---

## If the RAG Stops Working

**Symptom: `/intel/ask` returns 500**
```bash
# Check container logs
ssh dan@192.168.68.119 "docker logs sparc-api --tail 50 | grep -i intel"

# Most likely cause: pip installs were lost after docker compose up
# Fix: reinstall deps
docker exec sparc-api pip install chromadb==0.6.3 \
  'llama-index-core==0.12.52.post1' 'llama-index-vector-stores-chroma==0.4.2' \
  'llama-index-embeddings-huggingface==0.5.5' sentence-transformers==3.4.1 \
  'anthropic>=0.40.0'
docker restart sparc-api
```

**Symptom: `answer` is returned but `llm_used: false`**
- ANTHROPIC_API_KEY is not set or expired in `.env`
- The raw retrieved context is still returned — functionally useful
- Fix: check `~/sparc/.env` on NUC, add/update `ANTHROPIC_API_KEY=sk-ant-...`
- Then `docker restart sparc-api`

**Symptom: `low_confidence: true` on every query**
- Documents may not be ingested — check `/intel/status` first
- Query may be too vague — try more specific wording
- Score threshold is 0.60; most good matches score 0.75+

**Symptom: `/intel/status` shows 0 docs**
- ChromaDB database is empty — trigger ingest:
```bash
curl -X POST http://192.168.68.119:8000/intel/ingest \
  -d '{"tier": "operational"}' -H "Content-Type: application/json"
```

---

## Tiers and Expansion

The intel module supports multiple knowledge tiers. Currently only `operational` is populated, but the code supports:
- `operational` — how to run and operate the Sparc system
- `strategic` — business strategy, market analysis
- `research` — academic papers, energy research
- `market` — tariff analysis, market data
- `career`, `mba`, `garden`, `regulatory`, `engineering`

To add a new tier:
1. Create `intel/docs/{tier}/` directory
2. Add .md files
3. Sync to NUC
4. POST to `/intel/ingest` with `{"tier": "{tier}"}`

---

## The Bigger Picture

Most RAG tutorials stop at a Jupyter notebook demo. This system is different:

| Challenge | Solution |
|-----------|----------|
| Index survives container restarts | ChromaDB on volume-mounted path |
| New documents don't require full re-embedding | SHA-256 hash deduplication |
| No API key? Still functional | Returns raw context as fallback |
| Variable cloud documents | Multiple tiers, each with their own ChromaDB collection |
| Code changes propagate without docker cp | Volume mount for intel/ directory |
| Module not found in Docker | PYTHONPATH includes /app |

This is the infrastructure plumbing that separates "I built a RAG demo" from "I deployed a RAG system."

---

*Source: intel/ingest.py, intel/retrieval.py, intel/context_builder.py, intel/routes.py*
*docker-compose.yml (NUC at ~/sparc/docker-compose.yml)*
*deployment/requirements.txt*
*See also: RAG_ON_NUC_EXPLAINED.md (BSS interview version), OPERATIONS_MANUAL.md*
