# Energy Intelligence Module — Build Brief
*Product + Engineering specification for the Sparc Energy Intelligence layer*
*Author: Orchestrator | Last updated: 2026-04-16*
*Status: READY TO BUILD — share this with the Energy Claude session to begin*

---

## 1. Strategic Context

The Energy app currently has:
- 153 tests, 10 ADRs, ModelRegistry, DriftDetector, DataValidator — strong engineering
- LightGBM H+24 R²=0.975, €178/yr home trial saving — real results
- Deep regulatory and market knowledge in docs — locked in PDFs and static markdown

**Three problems this brief solves:**

**P1 — Invisible work.** The portfolio is invisible. No live demo URL, no visual, no public evidence of what was built. The VIOTAS AI Solutions Lead loss was partly due to a zero-visual submission vs. a competitor with a polished portfolio. Fix: a live Gradio demo at `energy.danbujoreanu.com`.

**P2 — Locked knowledge.** ~40+ strategy and regulatory documents in `Energy (Sparc)/docs/` cannot be queried. Every time a regulatory question arises during development, someone re-reads a PDF. Fix: a queryable intelligence module at `intel.danbujoreanu.com`.

**P3 — Static roadmap.** The Sparc Roadmap is a manually maintained document. As new CRU consultations, EU directives, and research papers emerge, the Roadmap should update. Fix: a structured output pipeline that tags new regulatory signals to specific Roadmap items.

---

## 2. What We're Building

Two distinct layers. Both run on Mac Mini M5 via Docker Compose, exposed via Cloudflare Tunnel.

### Layer A — Portfolio Demo (`energy.danbujoreanu.com`)
A live, publicly accessible Gradio interface demonstrating the Energy forecast model.

**Purpose:** Show (don't tell) what the app does. Link this URL from `www.danbujoreanu.com` Projects page (Adobe Portfolio). Portfolio reviewers, PhD interviewers, and potential investors click this URL and see the model working in 60 seconds.

**What it shows:**
```
Input:  Upload ESB-format CSV  OR  use the built-in demo dataset
        City selector (Dublin / Cork / Galway)
        Tariff type (Standard / Night Saver / Smart / TOU)

Output: Area chart — P10/P50/P90 H+24 forecast (24 hourly bars + uncertainty bands)
        Recommendation card — "Cheapest window: 02:00–06:00. Est. saving: €X.XX"
        ModelRegistry version badge (e.g. v1.2.0-ACTIVE)
        Home Plan Score — if tariff is suboptimal, show annual saving estimate
```

**Above the input (always visible):**
> "70% of Irish households are on the wrong energy plan. Behind-the-meter assets — heat pumps, EVs, solar — are creating an intelligence blind spot in the Irish grid that current tariffs cannot see. By June 2026, CRU mandates all top-5 suppliers to offer time-of-use tariffs. This tool forecasts your household's electricity demand 24 hours ahead — enabling the right tariff decision, automatically."

**This is NOT the consumer product.** The production consumer app is Next.js PWA (see `docs/TECH_STACK.md`). Gradio is appropriate here because: ML demo interface, instant public URL, zero frontend build pipeline, hiring managers can use it without instructions.

### Layer B — Intelligence Module (`intel.danbujoreanu.com`)
A queryable knowledge base over Sparc Energy's regulatory, strategic, research, and market intelligence corpus.

**Purpose (three distinct consumers — see Section 5 Output Pipeline for full spec):**
1. **Dan** — conversational research window. Ask "What does CRU mandate for June 2026?" and get an answer with source citations.
2. **Energy Claude session** — structured context injection. A `regulatory_digest.md` that gets regenerated and read at every session start.
3. **Roadmap** — structured tags from regulatory signals to specific Roadmap items (E-X codes).

---

## 3. Publishing Model — How Demos Connect to `www.danbujoreanu.com`

`www.danbujoreanu.com` is hosted on Adobe Portfolio — a static site builder. You cannot run a process there.

`energy.danbujoreanu.com` and `intel.danbujoreanu.com` are **subdomains** with separate DNS records. They point to the Mac Mini M5 via Cloudflare Tunnel. Both live under the same domain (`danbujoreanu.com`) registered at Squarespace.

**DNS setup in Squarespace:**
```
Type:  CNAME
Name:  energy
Value: <your-tunnel-id>.cfargotunnel.com

Type:  CNAME
Name:  intel
Value: <your-tunnel-id>.cfargotunnel.com
```
Cloudflare Tunnel then routes by hostname to the correct local port.

**Connection to Adobe Portfolio:**
The Projects page on `www.danbujoreanu.com` has two portfolio cards. Each card has a "Live Demo →" button linking to the subdomain. No embedding needed — just links.

**Auth:**
- `energy.danbujoreanu.com` — **public** (portfolio showcase, no auth)
- `intel.danbujoreanu.com` — **Cloudflare Access** (Google OAuth, free tier). The intel corpus contains commercially sensitive strategy and competitive intel (`COMPETITORS.md`, `COMMERCIAL_ANALYSIS.md`). Gate it with your Google account.

**Mac Mini resilience (set before leaving Maynooth):**
- System Preferences → Energy → "Prevent Mac from automatically sleeping" — ON
- System Preferences → Energy → "Wake for network access" — ON
- Docker Desktop set to start on login
- Docker Compose `restart: unless-stopped` on all services
- Test: SSH from laptop to Mac Mini IP, confirm all services up

---

## 4. Input Pipeline — Full Specification

### 4.1 Supported Formats
```
.md    — Primary format. All existing docs are .md. No conversion needed.
.pdf   — Secondary format. Requires conversion step (see §4.2).
.txt   — Supported natively by LlamaIndex SimpleDirectoryReader.
.docx  — Convert to .md first using pandoc (not auto-handled).
```

**PDF → .md conversion (required for CRU and EU docs published as PDFs):**
```bash
# Install once
pip install pymupdf4llm

# Convert a CRU PDF to markdown
python -c "
import pymupdf4llm, pathlib
md = pymupdf4llm.to_markdown('CRU202600XX_document.pdf')
pathlib.Path('CRU202600XX_document.md').write_text(md)
"
```
After conversion, move original PDF to `docs/regulatory/pdfs/` (archive). Ingest the `.md` file.

### 4.2 Document Metadata Schema
Every document in the intel corpus should have a YAML frontmatter block. The ingest script reads this metadata and stores it with each chunk in ChromaDB — enabling structured queries like "show me all documents effective after June 2026."

```yaml
---
title: "CRU Dynamic Pricing Consultation — Appendix A Draft"
source_org: "CRU"                         # CRU | EirGrid | EU | SEAI | Research | Market
source_url: "https://www.cru.ie/..."      # original URL if available
publication_date: "2025-03-01"
effective_date: "2026-06-01"              # when the regulation takes effect (if applicable)
document_type: "consultation_draft"       # consultation_draft | final_decision | strategy | paper | market_intel
tier: "operational"                       # operational | strategic | research | market
roadmap_tags: ["E-15", "E-25"]           # which Roadmap items this doc is relevant to
status: "active"                          # active | superseded | archived
---
```

Add this block to existing docs before ingesting. For new docs, add it at creation time.

### 4.3 Document Tier Taxonomy
```
intel/docs/operational/    CRU active mandates, EirGrid policies, pricing consultations
                           → Everything that has a compliance deadline for Sparc Energy
                           Examples: CRU202517 dynamic pricing mandate, smart meter access rules

intel/docs/strategic/      EU Green Deal, Irish Climate Action Plan, SEAI Strategy to 2030
                           National Development Plan, heating electrification targets
                           → Macro tailwinds that shape market timing and investor narrative

intel/docs/research/       arXiv papers, PhD programs, ICHEC, Decarb-AI, conference proceedings
                           → BTM detection (Kazempour arXiv:2501.18017), demand response papers
                           → Competitive research intel (who is working on what)

intel/docs/market/         Competitor profiles, PCW comparisons, Tibber/Octopus playbooks
                           Pricing surveys, consumer adoption data
                           → Direct inputs to COMMERCIAL_ANALYSIS and MARKET_POSITIONING
```

### 4.4 Ingest Workflow

**Option A — CLI (manual trigger per document):**
```bash
# Ingest a single document
python scripts/intel_ingest.py --file intel/docs/operational/CRU202517_APPENDIX_A_DRAFT.md

# Ingest all documents in a tier
python scripts/intel_ingest.py --tier operational

# Ingest everything
python scripts/intel_ingest.py --all

# Check corpus status
python scripts/intel_status.py
# Output: {operational: 12 docs / 847 chunks, strategic: 3 docs / ...}
```

**Option B — Watch folder (auto-trigger on file drop):**
Add a Docker Compose service `intel-watcher` using Python `watchdog` library. When a `.md` or `.pdf` file is dropped into `intel/docs/{tier}/`, it auto-triggers ingest. Good for when the system matures. **Build Option A first.**

### 4.5 Deduplication
The ingest script must check before inserting:
```python
# Check by document hash, not filename (filenames can change)
import hashlib
doc_hash = hashlib.sha256(content.encode()).hexdigest()
if chroma_collection.get(where={"doc_hash": doc_hash})["ids"]:
    print(f"Skipping — already ingested: {file_path}")
    return
```
Store `doc_hash` in ChromaDB metadata for every chunk from a document.

### 4.6 Update Handling
When CRU publishes v2 of a document (e.g., final decision replacing consultation draft):
```bash
# Step 1: Mark old version as superseded (update metadata, don't delete)
python scripts/intel_update.py --supersede CRU202517_APPENDIX_A_DRAFT.md --reason "Final decision published"

# Step 2: Ingest new version
python scripts/intel_ingest.py --file intel/docs/operational/CRU202517_FINAL_DECISION.md
```
Superseded documents are retained in ChromaDB (useful for "how did this regulation evolve?") but tagged `status: superseded` so they rank lower in retrieval.

### 4.7 Seed Corpus — Available NOW (no conversion needed)
These files are at `~/Personal Projects/Energy (Sparc)/docs/` and ready to ingest immediately.

**Operational (start here):**
- `regulatory/CRU202517_APPENDIX_A_DRAFT.md` — CRU smart meter data access framework
- `regulatory/SMART_METER_ACCESS.md` — Smart meter access, P1 port, GDPR pathway

**Market intelligence:**
- `COMPETITORS.md` — Tibber, Loop, elec-tariffs.ie, Climote, Octopus
- `COMMERCIAL_ANALYSIS.md` — Market sizing, pricing model, revenue projections
- `MARKET_POSITIONING.md` — Differentiation, segments, messaging

**Research:**
- `research/CONSUMER_BEHAVIOUR.md` — Consumer demand response patterns
- `research/METHODOLOGY_ARCHITECTURE.md` — Model architecture decisions
- `research/JOURNAL_PAPER_DRAFT.md` — Applied Energy submission draft

**Governance (cross-tier context):**
- `governance/AIIA.md` — AI Impact Assessment
- `governance/MODEL_CARD.md` — Model transparency
- `governance/DATA_LINEAGE.md` — Data flows

**Strategic — to be added (require PDF → .md conversion):**
- Irish Climate Action Plan 2024 (gov.ie — free PDF)
- SEAI Strategy to 2030 (seai.ie — free PDF)
- EU Green Deal — Net Zero Industry Act summary

---

## 5. Output Pipeline — Full Specification

Four distinct outputs. Build in this order.

### Output 1 — Dan (Conversational Research, Day 2)
**Interface:** Gradio chat at `intel.danbujoreanu.com`
**Authentication:** Cloudflare Access (Google OAuth)
**Behaviour:**
- Text input → query all tiers OR specific tier → LlamaIndex retrieval → answer + source citations
- Source citations must show filename + relevant excerpt (not just filename)
- Confidence signal: if top retrieved chunk similarity < 0.6, prepend "Low confidence — no strong match found in corpus."
- Query examples the system must handle correctly:
  - "When does the CRU dynamic pricing mandate take effect?" → operational tier, date extraction
  - "Who are our main Irish competitors?" → market tier, list format
  - "What does Kazempour's BTM research say about heat pump detection?" → research tier

### Output 2 — Energy Claude Session (Context Injection, Day 3)
**File:** `docs/regulatory_digest.md` (auto-generated, not manually edited)
**Trigger:** `python scripts/intel_digest.py` — regenerates the digest from current corpus
**Content format:**
```markdown
# Regulatory & Intel Digest
*Auto-generated from intel corpus — last updated: {timestamp}*
*Do not edit manually. Run `python scripts/intel_digest.py` to refresh.*

## Active Regulatory Deadlines
| Date | Regulator | Requirement | Roadmap Impact |
|------|-----------|-------------|---------------|
| Jun 2026 | CRU | Top-5 suppliers must offer TOU tariffs | E-15 (tariff engine) |
| ... | ... | ... | ... |

## Key Market Intel (last 90 days)
- {bullet summary of market tier docs}

## Research Signals
- {bullet summary of research tier docs with Roadmap tags}

## Superseded Documents (last 30 days)
- {any docs marked superseded recently}
```

**Integration into Energy sessions:** Add this line to `building-energy-load-forecast/CLAUDE.md`:
```
Read `~/Personal Projects/Energy (Sparc)/docs/regulatory_digest.md` at session start
for current regulatory and market context.
```

### Output 3 — ROADMAP Integration (Structured Tags, Day 4)
The intel module tags documents to Roadmap items via the `roadmap_tags` metadata field. A separate script generates a Roadmap context view:
```bash
python scripts/intel_roadmap.py --item E-25
# Output: All documents tagged to E-25 (BTM Asset Detection), with relevant excerpts
```

This does NOT auto-edit ROADMAP.md. It generates a context report Dan reviews before manually updating the Roadmap. Full automation is Phase 2.

### Output 4 — Portfolio Reviewers (Live Demo, Day 1)
**Interface:** Gradio demo at `energy.danbujoreanu.com`
**Authentication:** None (fully public)
**Connected from:** `www.danbujoreanu.com` Projects page — "Live Demo →" button

The demo must be robust enough to handle a recruiter or PhD interviewer clicking it cold:
- Must work with the built-in demo dataset (don't force CSV upload as the only path)
- Must complete in < 5 seconds
- Must not crash on bad input (validate and show friendly error)
- Screenshot the working demo — use this as the portfolio card visual

---

## 6. Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  INPUT LAYER                                                    │
│  Drop .md / .pdf into intel/docs/{tier}/                       │
│  python scripts/intel_ingest.py --tier {tier}                  │
│  → chunk (512 tokens, 50 overlap) → embed (MiniLM-L6-v2)       │
│  → ChromaDB (persistent volume, collection per tier)           │
├─────────────────────────────────────────────────────────────────┤
│  RETRIEVAL LAYER                                                │
│  LlamaIndex VectorStoreIndex over ChromaDB                     │
│  FastAPI endpoints:                                             │
│    POST /intel/query   {tier, query, top_k} → {answer, sources}│
│    GET  /intel/status  → {tier: doc_count, chunk_count}        │
│    GET  /intel/digest  → regenerate regulatory_digest.md       │
│    GET  /intel/roadmap/{item_id} → docs tagged to roadmap item │
├─────────────────────────────────────────────────────────────────┤
│  INTERFACE LAYER                                                │
│  Gradio Chat (intel) — port 7861 → intel.danbujoreanu.com     │
│  Gradio Demo (energy) — port 7860 → energy.danbujoreanu.com   │
├─────────────────────────────────────────────────────────────────┤
│  STORAGE                                                        │
│  ChromaDB — persistent Docker volume (./data/chromadb)         │
│  Collections: intel_operational, intel_strategic,              │
│               intel_research, intel_market                     │
├─────────────────────────────────────────────────────────────────┤
│  EMBEDDINGS                                                     │
│  sentence-transformers/all-MiniLM-L6-v2 (90MB, local)         │
│  Pre-download in Dockerfile build step (not at runtime)        │
│  Zero API cost — runs entirely on Mac Mini M5                  │
└─────────────────────────────────────────────────────────────────┘
```

### Module structure (inside `building-energy-load-forecast/`)
```
intel/
  __init__.py
  ingest.py          # PDF/MD → chunk → embed → ChromaDB
  retrieval.py       # LlamaIndex query wrapper, confidence scoring
  digest.py          # generates regulatory_digest.md from corpus
  routes.py          # FastAPI /intel/* endpoints (include in app.py)
  gradio_app.py      # Gradio chat interface (intel.danbujoreanu.com)
  gradio_demo.py     # Gradio forecast demo (energy.danbujoreanu.com)

scripts/
  intel_ingest.py    # CLI wrapper for intel/ingest.py
  intel_status.py    # corpus stats
  intel_digest.py    # regenerate regulatory_digest.md
  intel_roadmap.py   # roadmap context view
```

### Dependencies (pin versions)
```txt
# requirements-intel.txt
llama-index-core==0.12.x
llama-index-vector-stores-chroma==0.12.x
llama-index-embeddings-huggingface==0.12.x
chromadb==0.6.x
sentence-transformers==3.4.x
pymupdf4llm==0.0.x        # PDF → markdown conversion
gradio==4.44.x
watchdog==4.0.x           # for auto-watch option (Phase 2)
```
**Important:** LlamaIndex has had breaking API changes across major versions. Pin to `0.12.x` (current stable at Apr 2026). Do not upgrade without reading the migration guide.

### Dockerfile.intel (new file)
```dockerfile
FROM python/3.12-slim

WORKDIR /app
COPY requirements-intel.txt .
RUN pip install --no-cache-dir -r requirements-intel.txt

# Pre-download embedding model during build (not at runtime)
RUN python -c "from sentence_transformers import SentenceTransformer; \
               SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY intel/ ./intel/
COPY scripts/ ./scripts/

CMD ["python", "-m", "intel.gradio_app"]
```

### Docker Compose additions
```yaml
gradio-demo:
  build:
    context: .
    dockerfile: Dockerfile.gradio
  ports:
    - "7860:7860"
  volumes:
    - ./models:/app/models:ro
    - ./data:/app/data:ro
  depends_on:
    - api
  restart: unless-stopped

intel:
  build:
    context: .
    dockerfile: Dockerfile.intel
  ports:
    - "7861:7861"
  volumes:
    - ./intel/docs:/app/intel/docs:ro
    - chromadb_data:/app/data/chromadb     # NAMED VOLUME — persists across rebuilds
  restart: unless-stopped

volumes:
  chromadb_data:    # Named volume — survives container restart, survives image rebuild
                    # DOES NOT survive `docker-compose down -v` — never run with -v flag
```

**ChromaDB backup strategy:**
```bash
# Weekly backup cron on Mac Mini (add to crontab -e)
0 9 * * 1 tar -czf ~/backups/chromadb_$(date +%Y%m%d).tar.gz ~/building-energy-load-forecast/data/chromadb
```

### Cloudflare Tunnel config
```yaml
# ~/.cloudflared/config.yml
tunnel: <your-tunnel-id>
credentials-file: /path/to/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: energy.danbujoreanu.com
    service: http://localhost:7860
  - hostname: intel.danbujoreanu.com
    service: http://localhost:7861
  - hostname: greenhouse.danbujoreanu.com
    service: http://localhost:3000    # Grafana
  - service: http_status:404
```

---

## 7. Key Code Patterns

### ingest.py
```python
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SentenceSplitter
import chromadb, hashlib
from pathlib import Path

EMBED_MODEL = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
CHROMA_PATH = "./data/chromadb"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50

def ingest_file(file_path: str, tier: str):
    """Ingest a single .md file into ChromaDB, with deduplication."""
    content = Path(file_path).read_text()
    doc_hash = hashlib.sha256(content.encode()).hexdigest()

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(f"intel_{tier}")

    # Deduplication check
    existing = collection.get(where={"doc_hash": doc_hash})
    if existing["ids"]:
        print(f"Skipping — already ingested: {file_path}")
        return

    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
    # Attach doc_hash to all chunks from this document
    for doc in documents:
        doc.metadata["doc_hash"] = doc_hash
        doc.metadata["tier"] = tier
        doc.metadata["source_file"] = Path(file_path).name

    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=EMBED_MODEL,
        transformations=[splitter],
        show_progress=True
    )
    print(f"Ingested {Path(file_path).name} → tier '{tier}'")
```

### retrieval.py
```python
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import chromadb

EMBED_MODEL = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
CHROMA_PATH = "./data/chromadb"
LOW_CONFIDENCE_THRESHOLD = 0.60

def query_tier(tier: str, question: str, top_k: int = 5) -> dict:
    """Query a tier, return answer + source citations + confidence flag."""
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(f"intel_{tier}")
    vector_store = ChromaVectorStore(chroma_collection=collection)
    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=EMBED_MODEL)
    query_engine = index.as_query_engine(similarity_top_k=top_k)
    response = query_engine.query(question)

    sources = [
        {"file": n.metadata.get("source_file", "unknown"),
         "score": round(n.score or 0.0, 3),
         "excerpt": n.text[:200]}
        for n in response.source_nodes
    ]
    top_score = sources[0]["score"] if sources else 0.0
    answer = str(response)
    if top_score < LOW_CONFIDENCE_THRESHOLD:
        answer = f"[Low confidence — no strong match found in corpus]\n\n{answer}"

    return {"answer": answer, "sources": sources, "tier": tier, "top_score": top_score}
```

---

## 8. Build Sequence

```
Sprint 1 — Foundation (Days 1–2)
  ✦ pip install / requirements-intel.txt
  ✦ Create intel/ module structure
  ✦ Build ingest.py with deduplication
  ✦ Add YAML frontmatter to seed corpus docs (metadata schema §4.2)
  ✦ Ingest 2 operational docs (CRU202517, SMART_METER_ACCESS)
  ✦ Test: python -c "from intel.retrieval import query_tier; print(query_tier('operational', 'When does the CRU mandate take effect?'))"
  → Gate: retrieval returns answer + source citation

Sprint 2 — API + Interfaces (Days 3–4)
  ✦ Build retrieval.py with confidence scoring
  ✦ Add /intel/* endpoints to FastAPI (routes.py → include in app.py)
  ✦ Build gradio_app.py (intel chat interface — port 7861)
  ✦ Build gradio_demo.py (energy forecast demo — port 7860)
  ✦ Test both Gradio apps at localhost
  → Gate: both interfaces work end-to-end

Sprint 3 — Docker + Tunnel (Day 5)
  ✦ Dockerfile.intel + Dockerfile.gradio
  ✦ Add services to docker-compose.yml (named volume for ChromaDB)
  ✦ Cloudflare Tunnel config — add energy.* and intel.* routes
  ✦ Squarespace DNS — add CNAME records for subdomains
  ✦ Cloudflare Access — configure Google OAuth gate on intel.danbujoreanu.com
  ✦ Verify energy.danbujoreanu.com and intel.danbujoreanu.com load externally
  → Gate: both live URLs accessible from mobile browser

Sprint 4 — Corpus Expansion + Outputs (Days 6–8)
  ✦ Add YAML frontmatter to remaining seed corpus docs
  ✦ Ingest full seed corpus (10+ documents across all tiers)
  ✦ Build intel_digest.py → generates regulatory_digest.md
  ✦ Build intel_roadmap.py → roadmap context view
  ✦ Add `Read docs/regulatory_digest.md at session start` to Energy CLAUDE.md
  ✦ Run 10 test queries — verify answers + source citations
  ✦ Weekly ChromaDB backup cron
  → Gate: regulatory_digest.md generated and useful

Sprint 5 — Tests + ADR (Day 9)
  ✦ Unit tests for ingest.py (dedup, metadata extraction, chunk count)
  ✦ Unit tests for retrieval.py (known-answer queries on seeded corpus)
  ✦ Integration test: ingest → query → verify answer contains expected fact
  ✦ ADR-012-regulatory-intelligence-rag.md (why LlamaIndex > LangChain, why ChromaDB > Pinecone)
  ✦ Update docs/TECH_STACK.md Section 15 — Regulatory Intelligence Module
  → Gate: tests pass in CI
```

---

## 9. Constraints — What NOT to Do

| Constraint | Reason |
|-----------|--------|
| No n8n | Has associated costs. Manual-first ingest is the right architecture at this stage. |
| No Pinecone or external vector DB | ChromaDB local on Mac Mini M5. No ongoing API costs. |
| No OpenAI embeddings | sentence-transformers/all-MiniLM-L6-v2 runs locally. Zero cost. |
| No separate FastAPI instance for intel | Add /intel/* routes to the existing deployment/app.py. One service, one port (8000). |
| No Streamlit for the Gradio demo | Streamlit is internal analytics only (docs/TECH_STACK.md). |
| No auto-edit of ROADMAP.md | The intel module outputs context reports. Dan reviews and manually updates the Roadmap. Full automation is Phase 2. |
| `docker-compose down -v` is forbidden | The `-v` flag destroys named volumes, including ChromaDB data. Use `docker-compose down` only. |
| Do not confuse the demo with the consumer product | `energy.danbujoreanu.com` is a portfolio showcase. The consumer product is Next.js PWA. See docs/TECH_STACK.md. |

---

## 10. Tests Required

Every module in `intel/` must have a corresponding test file. The test suite must pass before considering the module complete.

**Minimum test coverage:**
```
tests/intel/
  test_ingest.py
    - test_ingest_single_file_creates_chunks()
    - test_deduplication_prevents_double_ingest()
    - test_metadata_stored_with_chunks()
    - test_pdf_to_md_conversion()

  test_retrieval.py
    - test_known_answer_query()         # query known fact from seeded doc, verify answer
    - test_low_confidence_flag()        # query on empty collection, verify flag returned
    - test_source_citations_included()  # verify sources list not empty
    - test_tier_isolation()             # query operational tier, verify no market chunks returned

  test_routes.py
    - test_intel_query_endpoint_returns_200()
    - test_intel_status_endpoint_returns_counts()
```

**ADR required:**
`docs/adr/ADR-012-regulatory-intelligence-rag.md`
Cover: why LlamaIndex over LangChain, why ChromaDB over Pinecone, why local embeddings over OpenAI, why manual-first over n8n automation.

---

## 11. Definition of Done

**Layer A — Portfolio Demo:**
- [ ] `energy.danbujoreanu.com` loads without auth
- [ ] Built-in demo dataset works without CSV upload
- [ ] P10/P50/P90 chart renders
- [ ] Recommendation card shows cheapest window + estimated saving
- [ ] ModelRegistry version badge visible
- [ ] Page loads in < 5 seconds
- [ ] Screenshot taken for portfolio card

**Layer B — Intelligence Module:**
- [ ] `intel.danbujoreanu.com` loads behind Cloudflare Access (Google OAuth)
- [ ] "When does the CRU dynamic pricing mandate take effect?" returns correct answer with source citation
- [ ] At least 8 documents ingested across at least 3 tiers (verified via /intel/status)
- [ ] /intel/query endpoint returns structured JSON: {answer, sources, tier, top_score}
- [ ] ChromaDB persists across Docker restart (verify: restart container, re-query)
- [ ] `regulatory_digest.md` generated and useful
- [ ] `Read docs/regulatory_digest.md at session start` added to CLAUDE.md
- [ ] Weekly backup cron active
- [ ] Tests pass (Sprint 5)
- [ ] ADR-012 written

---

## 12. Portfolio Card Outputs
*For Website session — use these verbatim for `www.danbujoreanu.com` Projects page*

### Energy Forecasting
**OBJECTIVE:** AI forecasts a household's electricity demand 24 hours ahead, matching it to the optimal Irish tariff. Demonstrated €178/yr saving in live home trial.
**TECH STACK:** LightGBM · FastAPI · Gradio · Docker · Cloudflare Tunnel · PostgreSQL · LlamaIndex
**LIVE DEMO:** energy.danbujoreanu.com
**VISUAL:** Screenshot of Gradio demo — P10/P50/P90 forecast chart + recommendation card

### Regulatory Intelligence
**OBJECTIVE:** Queryable knowledge base over Irish energy regulatory, market, and research documents — surfaces CRU mandates, compliance deadlines, and market signals that shape the Sparc Roadmap.
**TECH STACK:** LlamaIndex · ChromaDB · sentence-transformers · FastAPI · Gradio · Docker
**LIVE DEMO:** intel.danbujoreanu.com (gated)
**VISUAL:** Screenshot of Gradio chat answering a regulatory query with source citations

---

## 13. Infrastructure Checklist
*Complete before any remote working session*

- [ ] Docker Desktop: start on login — confirmed
- [ ] All Docker Compose services: `docker-compose up -d` → all healthy
- [ ] SSH access from laptop to Mac Mini IP — tested
- [ ] Cloudflare Tunnel: running + configured as launchd daemon (auto-restarts)
- [ ] DNS CNAMEs for energy.* and intel.* — added in Squarespace
- [ ] Mac Mini: never sleep + wake for network access — confirmed
- [ ] Weekly ChromaDB backup cron — active

---

*This brief is self-contained. The Energy Claude session at `~/building-energy-load-forecast/` can execute this without Orchestrator context. When the module is built, use `/project-relay` in the Orchestrator session to update WIKI_INDEX, ACTION_ITEMS, and Career/Cross_Project_Intelligence.md with the live demo URLs.*
