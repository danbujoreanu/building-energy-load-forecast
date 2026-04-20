# Energy Intel RAG — Feature Documentation

**Status:** ✅ Production | **Linear:** DAN-20 to DAN-27 | **Last updated:** 2026-04-20

---

## What It Does (30-second version)

The Intel RAG system lets you ask natural-language questions against a private knowledge base of energy market documents, regulatory notices, research papers, and strategy docs — and get synthesised, cited answers. Like ChatGPT, but running against YOUR documents, locally, with no data leaving your machine.

Example query:
> "What does the CRU's dynamic pricing mandate mean for Sparc Energy's go-to-market?"

The system retrieves the most relevant chunks from your ingested CRU documents and synthesises a grounded answer using Gemini Flash.

---

## How RAG Works — Technical Deep Dive

RAG = **Retrieval-Augmented Generation**. It combines:
- **Retrieval:** find the most relevant passages from a document store using semantic similarity
- **Generation:** use an LLM to synthesise a natural-language answer from those passages

Without RAG, an LLM answers only from training data (outdated, generic). With RAG, it answers from YOUR specific documents, grounded in real evidence.

### The Full Pipeline

```
INGESTION (one-time per document)
──────────────────────────────────────────────────
1. Document (.md or .pdf)
         │
         ▼
2. Text extraction
   .pdf  → pymupdf4llm.to_markdown()
            (preserves tables, headings, structure)
   .md   → read_text() + YAML frontmatter parsed
         │
         ▼
3. Chunking
   LlamaIndex SentenceSplitter
   chunk_size = 512 tokens (~400 words)
   chunk_overlap = 50 tokens
   Respects sentence boundaries (no mid-sentence cuts)
   A 10-page PDF → ~50–80 chunks
         │
         ▼
4. Embedding
   sentence-transformers/all-MiniLM-L6-v2
   LOCAL model, runs on-device (Apple Silicon MPS)
   384-dimensional dense vector per chunk
   Zero API cost, ~50ms/chunk on CPU
         │
         ▼
5. Storage
   ChromaDB persistent vector store
   Collection: intel_{tier}  (e.g. intel_strategic)
   Each chunk: {id, vector[384], text, metadata}
   SHA-256 hash dedup: same file twice → skipped

QUERY (every question)
──────────────────────────────────────────────────
6. User query string
   e.g. "CRU dynamic pricing mandate timeline"
         │
         ▼
7. Query embedding
   Same MiniLM-L6-v2 embeds the question into
   the same 384-dimensional vector space
         │
         ▼
8. Cosine similarity search (ChromaDB)
   Finds top-k chunks whose vectors are closest
   to the query vector
   Default: top_k = 5
         │
         ▼
9. Context assembly
   Top-k chunks assembled into an LLM prompt
   Each chunk annotated with source + metadata
         │
         ▼
10. LLM synthesis
    Gemini Flash generates a grounded answer
    from the retrieved context
    Falls back to raw retrieved text if no API key
         │
         ▼
11. Response
    {answer, sources, top_score, tier, llm_used}
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Intel RAG System                         │
├──────────────────────┬──────────────────────────────────────┤
│   INGESTION          │         QUERY                        │
│                      │                                      │
│  intel/ingest.py     │  intel/retrieval.py                  │
│  ├── ingest_file()   │  ├── query_tier(tier, q, top_k)      │
│  └── ingest_dir()    │  └── query_all(query)                │
│                      │                                      │
│  scripts/            │  FastAPI  /intel/query               │
│  intel_ingest.py     │  Gradio   port 7861                  │
│  intel_feeds.py      │  CLI      intel_ingest.py --query    │
└──────────────────────┴──────────────────────────────────────┘
                              │
              ┌───────────────▼───────────────┐
              │          ChromaDB             │
              │      data/chromadb/           │
              │                               │
              │  intel_operational  ←  arch docs, runbooks    │
              │  intel_strategic    ←  regulatory, GTM        │
              │  intel_research     ←  papers, thesis         │
              │  intel_market       ←  competitor intel       │
              │  intel_career       ←  job specs (gitignored) │
              │  intel_mba          ←  UCD MBA frameworks     │
              │  intel_garden       ←  gardening (future)     │
              └───────────────────────────────┘
                              │
              ┌───────────────▼───────────────┐
              │    all-MiniLM-L6-v2           │
              │    384-dim, LOCAL, FREE        │
              └───────────────────────────────┘
                              │
              ┌───────────────▼───────────────┐
              │    Gemini Flash API           │
              │    synthesis (optional)       │
              └───────────────────────────────┘
```

---

## Key Design Decisions

| Decision | Chosen | Why | Azure equivalent |
|----------|--------|-----|-----------------|
| RAG framework | **LlamaIndex** | Document-centric, clean PDF pipeline, minimal boilerplate | LangChain (used in DAN-80 Azure portfolio) |
| Vector store | **ChromaDB** | Local, persistent, zero cost, Python-native | Azure AI Search |
| Embedding | **MiniLM-L6-v2** | Free, local, 384-dim (fast), strong English performance | text-embedding-3-small (Azure OpenAI) |
| Chunk size | **512 tok / 50 overlap** | ~400 words per chunk; respects sentence boundaries | Same — configurable |
| LLM synthesis | **Gemini Flash** | Generous free tier, fast, good quality | Azure OpenAI GPT-4o |
| Dedup | **SHA-256 content hash** | Deterministic; handles renames; re-ingest = skip | Custom metadata field |
| PDF extraction | **pymupdf4llm** | Preserves tables, headings as markdown | Azure Document Intelligence |

---

## Tiers — What Goes Where

| Tier | Add documents here | Typical content |
|------|-------------------|----------------|
| `strategic` | `intel/docs/strategic/` | CRU notices, SEAI reports, market research, regulatory PDFs |
| `operational` | `intel/docs/operational/` | Architecture docs, API runbooks, deployment guides |
| `research` | `intel/docs/research/` | ML papers, thesis chapters, academic references |
| `market` | `intel/docs/market/` | Competitor profiles, Irish PCW landscape, pricing data |
| `career` | auto-ingested from Obsidian | Job specs — gitignored, never in git |
| `mba` | `intel/docs/mba/` | Grant textbook, lecture PDFs, strategy frameworks |
| `garden` | `intel/docs/garden/` | Plant guides, grow calendars (future) |

> **Shortcut:** `Personal Projects/Energy (Sparc)/intel/docs/{tier}/` is the same folder as `building-energy-load-forecast/intel/docs/{tier}/` — it's a symlink.

---

## How to Add a Document (step by step)

### 1. Drop a file into the right tier folder

```
Personal Projects/Energy (Sparc)/intel/docs/strategic/   ← regulatory & market
Personal Projects/Energy (Sparc)/intel/docs/research/    ← papers
Personal Projects/Energy (Sparc)/intel/docs/operational/ ← architecture notes
Personal Projects/Energy (Sparc)/intel/docs/mba/         ← MBA materials
```

### 2. For `.md` files — add YAML frontmatter (recommended)

```yaml
---
title: "CRU202517 — Smart Meter Data Access Code"
document_type: regulatory
tier: strategic
date_added: "2026-04-20"
tags: [CRU, SMDS, smart-meter, regulatory]
---
```

Frontmatter fields become searchable metadata. If you skip it, the file still ingests — you just lose filtering.

### 3. Run the ingest command

```bash
# Single file:
cd "Personal Projects/Energy (Sparc)"
python scripts/intel_ingest.py --tier strategic \
  --file intel/docs/strategic/CRU202517.pdf

# Whole folder:
python scripts/intel_ingest.py --tier strategic \
  --dir intel/docs/strategic/

# Check what's in the store:
python scripts/intel_ingest.py --status
```

### 4. Query immediately

```bash
python scripts/intel_ingest.py --tier strategic \
  --query "CRU smart meter data access timeline for ESCOs"
```

---

## How to Run intel_feeds (RSS/Substack)

```bash
cd "Personal Projects/Energy (Sparc)"

# Run all configured feeds (SEAI, CRU, EirGrid, arXiv, etc.):
python scripts/intel_feeds.py --ingest

# Check item counts:
python scripts/intel_feeds.py --status

# Run only one tier:
python scripts/intel_feeds.py --ingest --tier strategic

# Add a new Substack newsletter:
# 1. Open config/config.yaml
# 2. Under intel_feeds.market (or strategic), add:
#    - url: "https://newsletter.substack.com/feed"
#      name: "Newsletter Name"
# 3. Run: python scripts/intel_feeds.py --ingest
```

**First run will pull:** SEAI updates, CRU notices, Energy Monitor articles, EirGrid news, arXiv ML papers (cs.LG), signal processing papers (eess.SP), AI industry analysis.

Already-seen articles are skipped — safe to run daily.

---

## How to Use MBA RAG (intel_mba)

```bash
# Ingest Grant's textbook (do this once — ~45 min first run):
python scripts/intel_ingest.py --tier mba \
  --file "/Users/danalexandrubujoreanu/UCD/1. Competitive Strategy/Contemporary Strategy Analysis - Robert M. Grant.pdf"

# Ingest Entrepreneurship module lectures:
python scripts/intel_ingest.py --tier mba \
  --dir "/Users/danalexandrubujoreanu/UCD/2. Entrepreneurship/Lectures pdf/"

# Query the frameworks:
python scripts/intel_ingest.py --tier mba \
  --query "VRIN framework for sustainable competitive advantage"

python scripts/intel_ingest.py --tier mba \
  --query "Business Model Canvas key partnerships energy startup"

python scripts/intel_ingest.py --tier mba \
  --query "Porter Five Forces Irish energy retail market"
```

Once ingested, every Claude Code session can query your MBA knowledge without re-reading PDFs.

---

## Interview Stories

### Story 1 — "I built a production RAG system from scratch"

> "I designed and deployed a RAG system that powers the knowledge layer of Sparc Energy. Every document — CRU regulatory notices, SEAI reports, ML papers, MBA strategy frameworks — is chunked at 512 tokens using LlamaIndex's sentence-aware splitter, embedded with MiniLM-L6-v2 into a 384-dimensional vector space, and stored in ChromaDB. Queries embed the question into the same space, cosine similarity retrieves the top-5 most relevant passages, and Gemini Flash synthesises a grounded answer. The entire ingestion pipeline is local — zero data sent externally. I understand every layer: from PDF extraction (pymupdf4llm preserving table structure) to vector similarity mathematics to LLM prompt construction."

### Story 2 — "LlamaIndex vs LangChain design decision"

> "I chose LlamaIndex for this project because the corpus is document-centric: regulatory PDFs, research papers, markdown knowledge files. LlamaIndex's SimpleDirectoryReader and SentenceSplitter handle this natively with minimal boilerplate. LangChain is better for agentic tool chains. That said, I'm building the Azure equivalent with LangChain specifically to demonstrate both frameworks — using LangChain's AzureSearchRetriever with Azure AI Search instead of ChromaDB, and Azure OpenAI embeddings instead of MiniLM-L6-v2."

### Story 3 — "Multi-tier knowledge architecture"

> "The system has seven ChromaDB collections serving different knowledge domains: operational, strategic, research, market, career (gitignored — private), MBA frameworks, and a future gardening digital twin. Same embedding model and retrieval interface across all tiers. This means I can query 'What does Porter say about sustainable advantage for platform businesses?' against MBA content, and 'What's the CRU's latest position on SMDS?' against regulatory content — same API call, just different tier parameter."

### Story 4 — "The Azure equivalent" (for Microsoft-stack interviews)

> "The Azure equivalent architecture uses Azure AI Search as the managed vector store, text-embedding-3-small via Azure OpenAI for embeddings, LangChain as the retrieval framework, and Azure OpenAI GPT-4o for synthesis. I've built this in my Azure portfolio project to demonstrate dual-stack capability. The key architectural difference is that Azure AI Search manages the embedding + indexing as a hosted service, whereas with ChromaDB you manage the vector store yourself — which gives more control but requires more operational overhead."

---

## Performance

| Metric | Value |
|--------|-------|
| Embedding model | MiniLM-L6-v2, 384-dim |
| Ingestion speed | ~2–5 chunks/second (CPU), ~10/s (MPS) |
| Query latency — retrieval only | ~50ms |
| Query latency — with Gemini synthesis | ~1–3s |
| Chunk size | 512 tokens ≈ 400 words |
| Typical document → chunk count | 1 page ≈ 6–8 chunks |
| Deduplication | SHA-256 content hash |

---

## Files Reference

| File | What it does |
|------|-------------|
| `intel/ingest.py` | Core pipeline: chunk → embed → store with dedup |
| `intel/retrieval.py` | Query engine: embed → cosine search → synthesise |
| `intel/routes.py` | FastAPI `/intel/query`, `/intel/status` endpoints |
| `intel/career.py` | Career RAG: job spec matching, tech stack eval |
| `scripts/intel_ingest.py` | CLI: `--tier`, `--file`, `--dir`, `--query`, `--status` |
| `scripts/intel_feeds.py` | RSS/Substack ingester: `--ingest`, `--status`, `--tier` |
| `intel/docs/{tier}/` | Source documents (add files here) |
| `data/chromadb/` | Persisted vector store (gitignored — ~100MB+) |
| `config/config.yaml` | `intel_feeds` section for RSS feeds |
