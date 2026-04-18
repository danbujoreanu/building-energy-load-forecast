# Sparc Energy — Documentation Hub

**Last updated:** 2026-04-18 | **Maintained by:** Dan Bujoreanu | **Linear:** linear.app (teams: DAN = Sparc Energy, GARDEN = Digital Twin Gardening)

> This README is the single entry point for all project documentation.
> Rule: if something important is decided, it goes here first, then in Linear.

---

## Quick Links

| Need to... | Go to |
|-----------|-------|
| Understand the system | [Architecture Overview](#architecture) |
| Understand the strategy | [STRATEGY.md](STRATEGY.md) |
| See the product roadmap | [ROADMAP.md](ROADMAP.md) |
| Sprint cadence + governance | [GOVERNANCE.md](GOVERNANCE.md) |
| Run the pipeline locally | [HOW_TO_RUN.md](HOW_TO_RUN.md) |
| Deploy to production | [INFRASTRUCTURE.md](INFRASTRUCTURE.md) |
| Check model results | [Results summary](#results) |
| Understand the product | [APP_PRODUCT_SPEC.md](APP_PRODUCT_SPEC.md) |
| Check competitors | [COMPETITORS.md](COMPETITORS.md) |
| Find an ADR | [adr/](adr/) |
| Query the intel corpus | `python scripts/intel_ingest.py --status` |
| Ingest RSS/Substack feeds | `python scripts/intel_feeds.py --ingest` |
| Analyse a job spec | `python scripts/career_ingest.py --match "role name"` |
| Understand the Personal OS | [PERSONAL_OS_ARCHITECTURE.md](PERSONAL_OS_ARCHITECTURE.md) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Sparc Energy Platform                        │
├─────────────┬──────────────┬─────────────────┬─────────────────┤
│  Data Layer │  ML Layer    │  API Layer      │  Interface Layer│
│             │              │                 │                 │
│ ESB HDF CSV │ LightGBM     │ FastAPI /predict│ Gradio Demo     │
│ P1 Port     │ H+1 / H+24   │ FastAPI /control│ (port 7860)    │
│ Eddi API    │ MAE 4.03 kWh │ Intel /query    │ Gradio Intel    │
│ OpenMeteo   │ R²=0.975     │ Scheduler 16:00 │ (port 7861)    │
│ SEMO Prices │ ControlEngine│                 │ Consumer App    │
│ ChromaDB    │ RAG Pipeline │                 │ (Phase 2)       │
└─────────────┴──────────────┴─────────────────┴─────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure                               │
│  Mac Mini M4 24GB (June 2026) + AWS managed services           │
│  Cloudflare Tunnel → energy.danbujoreanu.com                   │
│                    → intel.danbujoreanu.com                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Feature Documentation

Each major feature has its own doc in `docs/features/`:

| Feature | Status | Docs | Linear |
|---------|--------|------|--------|
| Load Forecast (LightGBM) | ✅ Production | [features/load-forecast/](features/load-forecast/) | DAN-5 to DAN-8 |
| Demand-Response Control | ✅ Production | [features/demand-response/](features/demand-response/) | DAN-32, DAN-33 |
| Energy Intel RAG | ✅ Production | [features/intel-rag/](features/intel-rag/) | DAN-20 to DAN-27 |
| Career Intel RAG | ✅ Production | [features/career-intel/](features/career-intel/) | DAN-79, DAN-80 |
| Consumer App | 🔵 Planning | [features/consumer-app/](features/consumer-app/) | DAN-60 |
| Morning Brief | 📋 Backlog | See DAN-22 | DAN-22 |
| LLM Advisor | 📋 Backlog | See DAN-40 | DAN-40 |

---

## Results

**Drammen test set (H+24):**

| Model | MAE (kWh) | R² |
|-------|-----------|-----|
| LightGBM | **4.03** | **0.975** |
| PatchTST (DL) | 6.96 | 0.910 |
| TFT (DL) | 8.77 | 0.865 |
| Stacking Ensemble | 4.03 | 0.975 |
| Mean Baseline | 22.67 | 0.442 |

DM test vs PatchTST: **−12.17 (p<0.001)** — statistically significant improvement.

Full results: `outputs/results/final_metrics.csv`

---

## Key Decisions

| Decision | Location | Date |
|----------|---------|------|
| Infrastructure: Mac Mini M4 + hybrid AWS | [INFRASTRUCTURE.md](INFRASTRUCTURE.md) | 2026-04-18 |
| Production model: LightGBM only (not ensemble, not DL) | [adr/ADR-010.md](adr/) | 2026-03-15 |
| RAG framework: LlamaIndex (not LangChain) | [TECH_STACK.md §15.6](TECH_STACK.md) | 2026-04-01 |
| Embedding: MiniLM-L6-v2 (not Ada-002) | [adr/ADR-012.md](adr/) | 2026-04-01 |
| Hosting: Cloudflare Tunnel (not static IP) | [INFRASTRUCTURE.md](INFRASTRUCTURE.md) | 2026-04-18 |

---

## Repository Structure

```
building-energy-load-forecast/
├── config/              ← config.yaml (single source of truth)
├── data/
│   ├── raw/             ← ESB HDF CSVs, Drammen, Oslo
│   ├── processed/       ← {city}/model_ready.parquet
│   └── chromadb/        ← vector store (all tiers incl. career)
├── deployment/          ← FastAPI app.py, connectors, mock data
├── docs/                ← THIS FOLDER
│   ├── README.md        ← you are here
│   ├── features/        ← per-feature documentation
│   ├── adr/             ← architecture decision records
│   ├── TECH_STACK.md    ← full tech stack + Azure equivalences
│   ├── COMPETITORS.md   ← competitive landscape
│   ├── INFRASTRUCTURE.md← hosting decision record
│   └── APP_PRODUCT_SPEC.md ← product specification
├── intel/               ← RAG module (operational/strategic/research/market/career)
│   ├── ingest.py        ← PDF/MD → ChromaDB
│   ├── retrieval.py     ← query engine
│   ├── routes.py        ← FastAPI /intel/* endpoints
│   ├── career.py        ← career-specific match/eval functions
│   └── docs/            ← source documents by tier
├── outputs/             ← models, results, logs (gitignored)
├── scripts/             ← CLI tools
│   ├── run_pipeline.py  ← full ML pipeline
│   ├── intel_ingest.py  ← intel corpus management
│   ├── career_ingest.py ← job spec management
│   └── career_watch.py  ← Obsidian watcher
├── src/energy_forecast/ ← core Python package
└── tests/               ← 12+ integration tests
```

---

## Workflow Principles

### Token Efficiency
- **Direct API over MCP**: use Python + GraphQL for Linear (10-50× fewer tokens than MCP tool schema loads)
- **Agents for open-ended search**: use `Agent` tool only for multi-step exploration, not known-path reads
- **Read before Edit**: always read files before editing to get correct line numbers
- **Batch Linear updates**: write all API mutations in one Python script, not one-by-one

### Documentation Ownership
- New feature? → Create `docs/features/{feature-name}/README.md` before coding
- New decision? → ADR in `docs/adr/` + summary in this README
- New issue in Linear? → Link to relevant doc in issue description
- Linear is the task manager; `docs/` is the knowledge base

### Cross-Project Links
- Mac Mini purchase → Linear LIFE team (when created) + DAN-53 (Sparc deployment)
- PhD application → CAREER team + DAN-8, DAN-10–14 (Sparc research)
- Career RAG → Career team + DAN-79 (Sparc intel)
