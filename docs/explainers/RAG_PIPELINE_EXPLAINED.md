# RAG Pipeline — How Sparc Retrieves and Synthesises Operational Knowledge
*Pedagogical explainer. Last updated: 2026-05-15 — Corpus maintenance patterns added (excerpt fix, PDF audit, single-topic reference).*

---

## What This Does

When you ask `/intel/ask "How do I restart the API if it crashes?"`, the system:

1. Embeds your question into a 384-dimension vector using `all-MiniLM-L6-v2` (runs locally, ~10ms)
2. Cosine-searches ChromaDB across ~330 stored chunk vectors to find the 5 most semantically similar passages
3. Packages those passages into a structured prompt (`AdvisorContext`)
4. Calls Gemini 3.1 Flash Lite (free tier API) to synthesise a plain-English answer
5. Returns the answer with source attribution, top similarity score, and a `low_confidence` flag if the best match scored below 0.60

**Live endpoints:**

| Endpoint | What it does |
|----------|-------------|
| `POST /intel/ask` | Retrieve → context → LLM synthesis → answer |
| `POST /intel/query` | Retrieve only — returns raw chunks + scores, no LLM |
| `GET /intel/status` | Document and chunk counts per tier |
| `GET /intel/tiers` | List valid tier names |

**UIs:**
- `http://localhost:8502` — from your Mac (via SSH tunnel)
- `http://192.168.68.119:8502` — direct LAN on NUC

---

## The Concept Underneath

**Retrieval-Augmented Generation (RAG)** solves the problem of LLMs not knowing about your private data. Instead of fine-tuning (expensive, stale), you retrieve relevant context at query time and give it to the LLM as part of the prompt.

The core insight is **semantic search via cosine similarity**:

```
Given two vectors A and B:
similarity = (A · B) / (|A| × |B|)

Range: -1 (opposite meaning) to +1 (identical meaning)
Practical threshold: > 0.60 = probably relevant
```

This works because a **neural embedding model** maps semantically similar text to geometrically nearby points in high-dimensional space. "How do I restart the API?" and "reboot the FastAPI service" will produce vectors with cosine similarity ~0.75, even though they share no keywords. That's the key difference from keyword search (Elasticsearch, CTRL+F) — it understands *meaning*, not exact words.

**The pipeline in five functions:**

```
1. INGEST  (intel/ingest.py)
   .md files → SimpleDirectoryReader → Document objects
   → SentenceSplitter(512 tokens, 50 overlap) → chunks
   → HuggingFaceEmbedding(all-MiniLM-L6-v2) → 384d vectors
   → ChromaDB collection.add() — with SHA-256 dedup

2. VECTOR STORE  (outputs/chromadb/)
   ChromaDB PersistentClient — persists to disk on NUC
   Collection: intel_operational (~32 docs, ~330 chunks)

3. RETRIEVAL  (intel/retrieval.py)
   Query → embed → cosine search → top-k chunks
   low_confidence = True if top_score < 0.60

4. CONTEXT BUILDER  (intel/context_builder.py)
   Chunks + question → AdvisorContext(system_prompt, user_message, sources)

5. LLM SYNTHESIS — two paths exist:
   Path A (FastAPI + Streamlit): call_llm() → Gemini 3.1 Flash Lite → answer
   Path B (CLI scripts/rag_query.py): _get_llm() → Ollama (not on NUC → raw fallback)
```

**Why 512 tokens with 50 overlap?** A chunk must be long enough to capture one complete concept, but short enough that a single chunk doesn't dilute the embedding with unrelated content. 50-token overlap prevents a sentence that straddles a chunk boundary from losing its context entirely.

**Why SHA-256 dedup?** Without it, re-ingesting after adding one document would double all 330 chunks. The hash check `collection.get(where={"doc_hash": sha256})` skips any file whose content hasn't changed. Cost of ingesting a fresh file: ~£0.00 API cost, ~2s local compute per file. Cost of re-ingesting the whole corpus: identical (only changed files re-embed).

---

## Why This Approach — and What Was Rejected

### ChromaDB, not Pinecone/Qdrant/pgvector

ChromaDB's `PersistentClient` persists to a directory on disk — one line of setup, zero managed infrastructure, no API keys. For a single-machine NUC with <10k chunks, it is the right choice.

**What to use at scale:**
- `pgvector` (PostgreSQL extension) — collapses infrastructure: one DB for both relational data and vectors. Best choice if you're already on Postgres (TimescaleDB or Supabase both support it).
- `Qdrant` — self-hosted, HNSW index, handles concurrent writes. Right for >1M chunks or multi-user query load.
- ChromaDB itself does not support concurrent writes (single-process). Known limitation.

### `all-MiniLM-L6-v2`, not `text-embedding-ada-002` or larger models

384-dimension vectors, 80MB model weights, <10ms per chunk on Pentium N3700 CPU, zero API cost. For English technical documents at this corpus size, the semantic precision is sufficient.

**Trade-off accepted:** `all-mpnet-base-v2` (768d) and OpenAI `text-embedding-3-small` (1536d) give better precision on ambiguous queries and domain-specific jargon. At >100k chunks or with dense technical terminology, the precision gain is worth the cost increase. At 330 chunks, MiniLM is fine.

### Gemini 3.1 Flash Lite (free API), not Claude Haiku

Gemini 3.1 Flash Lite is on Google's free tier: 1M tokens/day, 15 RPM. A typical RAG query (5 × 512-token chunks) costs ~3,000–3,400 tokens. At the free tier limit, that's ~300 queries/day — effectively unlimited for this use case, and it saves equivalent Claude Code tokens on every query.

Claude Haiku fallback was **removed 2026-05-13** — it consumed paid Claude Code API tokens for a task where Gemini is free and equal quality.

**Target architecture when Mac Mini M5 arrives:** Ollama gemma3:4b (local, zero data leaves home network) → Gemini 3.1 Flash Lite (free API fallback) → raw chunks. Both Energy and Gardening will use this identical chain.

### LlamaIndex as framework, not raw Python

LlamaIndex saves ~150 lines of boilerplate: PDF parsing, chunking, embedding batch calls, index format handling. The architectural decisions (embedding model, chunk strategy, dedup, metadata design, confidence scoring, tier routing, context format, LLM chain) are not made by LlamaIndex — they're all explicit in `intel/`.

**What LlamaIndex provides vs what's manual:**

| LlamaIndex component | Manual equivalent |
|---|---|
| `SimpleDirectoryReader` | `pathlib.Path.read_text()` + PyMuPDF for PDF |
| `SentenceSplitter(512, 50)` | `tiktoken.encode()` + sliding window loop |
| `HuggingFaceEmbedding` | `sentence_transformers.SentenceTransformer.encode()` |
| `VectorStoreIndex` | `collection.add(ids, embeddings, documents, metadatas)` |
| `RetrieverQueryEngine` | `collection.query(query_embeddings, n_results)` → build prompt |

---

## Corpus Maintenance — Three Recurring Patterns

These patterns emerged from running the Energy RAG pipeline in production. Apply them on any corpus audit session.

### 1. Excerpt Slice — Must Be ≥ 500 Characters

`intel/retrieval.py` builds the `sources` list with `"excerpt": node.text[:N]`. If `N` is too small, Gemini's context window receives truncated chunks — facts in the second half of a 512-token chunk are **silently dropped**.

**What happened:** The NUC's `retrieval.py` had `[:200]`. A 512-token chunk is ~400 characters. At `[:200]`, every chunk's second half was invisible to Gemini. Regulatory decisions, tariff numbers, and competitor facts stored mid-chunk were never synthesised.

**Fixed to `[:500]`** — covers the full body of all but the longest chunks. Canonical in `intel/retrieval.py` (line ~197). After any rsync, verify: `grep "excerpt" ~/sparc/intel/retrieval.py`.

---

### 2. PDF Eviction Audit — Counter() Pattern

Run before any major corpus sync to find PDF debt (a PDF that contributes 300+ chunks whose facts are already summarised in a curated `.md`):

```python
import chromadb
from collections import Counter

client = chromadb.PersistentClient(path="data/chromadb")
for tier in ["regulatory", "market", "mba", "strategic"]:
    try:
        col = client.get_collection(f"intel_{tier}")
    except Exception:
        continue
    results = col.get(include=["metadatas"])
    counter = Counter(m.get("source_file", "?") for m in results["metadatas"])
    print(f"\n=== intel_{tier} ({col.count()} chunks) ===")
    for fname, count in counter.most_common():
        flag = " *** AUDIT" if count > 300 else (" >50" if count > 50 else "")
        print(f"  {count:5d}  {fname}{flag}")
```

**Eviction candidate:** any PDF with >300 chunks whose facts are already covered by a `.md` summary. Delete the PDF from `intel/docs/`, delete its chunks via `delete_file()`, re-flush.

**Energy audit result (2026-05-15):**
- `intel_regulatory`: 39 chunks — all `.md`. No PDF debt.
- `intel_market`: 46 chunks — all `.md`. No PDF debt.

Energy is clean by design: all curated content written as `.md` first; PDFs never ingested into regulatory/market tiers.

---

### 3. Single-Topic Reference File Pattern

**Pattern:** one file, one topic, golden numbers only, written so that each H2 section is < 512 tokens = exactly one RAG chunk = retrieval score typically 0.85+.

**Trigger:** `top_score < 0.60` on a factual query you know the answer to. The fact exists in the corpus but is buried in a large document behind noisy prose.

**Energy examples live:**
- `ENERGY_QUICK_REFERENCE.md` — 10 H2 sections each < 512 tokens. BGE tariff rates, CRU decisions, competitor landscape, SEAI grants, ESB demand response, RAG pipeline numbers.
- `TARIFF_SLOTS_REFERENCE.md` — tariff slots and windows, dense reference.

**File template:**

```markdown
---
title: <Topic> Reference — Sparc Energy
tier: <tier>
tags: [<keyword1>, <keyword2>]
---
# <Topic> Reference

*Dense reference. Last verified: YYYY-MM-DD.*

## <Subtopic 1>
< 400 words of dense facts. No prose padding. >

## <Subtopic 2>
...
```

**Rule:** Write it → ingest it immediately. Do not leave an unindexed `_REFERENCE.md` on disk.

---

## What Dan Needs to Rebuild This

If the NUC were wiped and this had to be rebuilt from scratch:

**1. Python packages** (in `deployment/requirements.txt`):
```
chromadb>=0.5
llama-index-core
llama-index-embeddings-huggingface
llama-index-vector-stores-chroma
sentence-transformers
google-genai
```

**2. The five source files:**
- `intel/ingest.py` — reads docs, chunks, embeds, stores with SHA-256 dedup
- `intel/retrieval.py` — embeds query, cosine searches, returns `RetrievalResult`
- `intel/context_builder.py` — formats `AdvisorContext`, calls Gemini via `call_llm()`
- `intel/routes.py` — FastAPI router mounting `/intel/ask`, `/intel/query`, `/intel/status`, `/intel/tiers`
- `intel/streamlit_app.py` — chat UI with live status sidebar

**3. Environment variables** (in `~/sparc/.env` on NUC):
```
GEMINI_API_KEY=...          # Google AI Studio free tier key
CHROMA_PATH=/app/outputs/chromadb   # must point to a writable volume
```

**4. Docker Compose additions:**
```yaml
volumes:
  - ./intel:/app/intel          # live mount — no rebuild cycle for doc updates
  - ./outputs:/app/outputs      # ChromaDB persists here

intel-ui:                       # Streamlit chat UI
  image: python:3.11-slim
  ports: ["8502:8501"]
  ...
```

**5. SSH tunnel** (on Mac, managed by launchd):
```
/Library/LaunchAgents/com.sparc.nuc-tunnel.plist
→ forwards localhost:8502 → NUC:8502
```

**6. To add documents** — write an `.md` explainer to `intel/docs/operational/`, rsync to NUC, then `POST /intel/ingest`. SHA-256 dedup means only the new file is re-embedded.

---

## Test Yourself

**Conceptual (interview level):**
> "I've indexed 30 documents into ChromaDB. I ask 'What is the BGE night rate?' and get `top_score: 0.43, low_confidence: true`. Why might this happen, and what are two different ways to fix it?"

<details>
<summary>Answer</summary>

Score 0.43 means the best matching chunk is only weakly similar — the query's vector is far from all stored vectors. Two causes:

1. **The document doesn't exist yet** — `TARIFF_SLOTS_REFERENCE.md` was never ingested. Fix: write and ingest the document.
2. **Semantic mismatch** — the document says "night-time tariff" and "23:00–08:00 pricing" but never uses "night rate". The embedding model sees these as related but not the same. Fix: add a short glossary section to the document that uses both phrasings, so the chunk that gets embedded contains both terms.

The 0.60 threshold is tunable in `intel/retrieval.py`. You'd lower it (more permissive) if you're getting too many `low_confidence` flags on valid queries, or raise it if you're getting overconfident answers from weak matches.
</details>

**Architectural:**
> "Why does `intel/retrieval.py:_get_llm()` exist alongside `intel/context_builder.py:call_llm()`? What bug does having two LLM paths create?"

<details>
<summary>Answer</summary>

`_get_llm()` was written assuming Ollama runs locally (used by `scripts/rag_query.py` CLI). `call_llm()` was written for the FastAPI/Streamlit path and uses Gemini.

The bug: the CLI always returns raw chunks (Ollama isn't on the NUC), while the API returns Gemini-synthesised answers. A developer running CLI queries sees different output quality than the live endpoint, which makes it hard to test. The fix is to unify both paths behind a single synthesis function: try Ollama → try Gemini → return raw. This is the target architecture, pending Mac Mini M5 for local Ollama.
</details>

**PhD-level:**
> "You have 10,000 candidate profiles in ChromaDB. A recruiter types 'experienced site manager, M50 infrastructure, available now'. Cosine similarity returns profiles that match semantically but the top result is a candidate who left construction in 2019. How would you fix this without rebuilding the embedding model?"

<details>
<summary>Answer</summary>

Cosine similarity is purely semantic — it has no notion of recency or domain-specific constraints. Three fixes without touching the embedding model:

1. **Metadata filtering at query time:** `collection.query(query_embeddings=[q], where={"last_active": {"$gte": "2024-01-01"}})`. ChromaDB supports pre-filtering on stored metadata fields. Store `last_active` as a metadata field at ingest time.

2. **Re-ranking:** After cosine retrieval, apply a second scoring pass. `cross-encoder/ms-marco-MiniLM-L-6-v2` is a cross-encoder that jointly encodes the query+document pair and scores relevance more precisely than bi-encoder cosine similarity. Top-50 cosine → cross-encoder re-rank → return top-5. Higher compute cost, better precision.

3. **Hybrid search:** Combine vector similarity (semantic) with BM25 keyword score (exact term matching for "M50", "site manager"). A weighted sum `0.7 × cosine + 0.3 × BM25` handles both. ChromaDB doesn't support BM25 natively — use Qdrant (supports hybrid search) or implement a parallel keyword index.
</details>

---

## Related Documents

- `LEARNING_PLAN.md` — study path if any concept above is unclear
- `RAG_ON_NUC_EXPLAINED.md` — deployment history (3 real infrastructure problems solved)
- `GEMINI_API_MODEL_REGISTRY.md` — token costs, model selection rationale, target LLM architecture
- `OPERATIONS_MANUAL.md` — how to restart services, re-ingest documents, check ChromaDB status

---

*Source: `intel/ingest.py`, `intel/retrieval.py`, `intel/context_builder.py`, `intel/routes.py`, `intel/streamlit_app.py`*
*Architecture: ChromaDB PersistentClient + LlamaIndex + all-MiniLM-L6-v2 + Gemini 3.1 Flash Lite*
