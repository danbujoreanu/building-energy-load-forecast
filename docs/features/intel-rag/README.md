# Feature: Energy Intelligence RAG

**Status:** ✅ Production (Sprint 1+2 complete)
**Linear:** DAN-20 to DAN-27
**Owner:** Dan Bujoreanu

---

## What it does

Answers questions about CRU regulations, Irish energy market dynamics, competitor analysis, and academic research — by retrieving relevant chunks from a private corpus and optionally synthesising with Gemini Flash.

## Architecture

```
User query
  → HuggingFaceEmbedding (MiniLM-L6-v2, local, 384-dim)
  → ChromaDB cosine similarity search (top-k chunks)
  → [Optional] Gemini Flash synthesis
  → Answer + sources with scores
```

## Tiers

| Collection | Content |
|-----------|---------|
| `intel_operational` | CRU decisions, GDPR guidance, SMDS docs |
| `intel_strategic` | Funding, BMC, commercialisation |
| `intel_research` | Academic papers, literature review |
| `intel_market` | Competitor analysis, Irish PCW landscape |
| `intel_career` | Job specs, interviewer profiles, Dan's profile |

## API

```bash
POST /intel/query
  {"tier": "operational", "query": "When does the CRU mandate take effect?", "top_k": 5}

GET  /intel/status   # chunk counts per tier
GET  /intel/tiers    # valid tier names
```

## Key files

- `intel/ingest.py` — SHA-256 dedup, YAML frontmatter, SentenceSplitter(512, 50)
- `intel/retrieval.py` — query engine, Gemini fallback, LOW_CONFIDENCE_THRESHOLD=0.60
- `intel/routes.py` — FastAPI router
- `intel/gradio_app.py` — private chat UI (port 7861)
- `intel/career.py` — career-specific functions

## Config

```python
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
LOW_CONFIDENCE_THRESHOLD = 0.60  # prefixes answer with [Low confidence] if score < this
```

## Current corpus status

Run `python scripts/intel_status.py` for live counts.
Seed docs: SMART_METER_ACCESS.md (operational), FUNDING_AND_MONETISATION.md (strategic)
Target: 10+ docs across all 4 tiers (DAN-24)

## Known limitations

- sentence-transformers pinned to 2.7.0 (TF Metal plugin conflict in ml_lab1 env)
- Docker uses 3.4.1 (no TF installed — no conflict)
- LlamaIndex pinned to 0.12.x (companion packages have independent versioning)
