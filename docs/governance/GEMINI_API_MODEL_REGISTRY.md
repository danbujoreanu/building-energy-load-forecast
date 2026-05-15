# Gemini API — Available Models Registry
*Last audited: 2026-05-09 | Updated: 2026-05-13 | Key: `...als8` (Free tier, AI Studio project)*
*How to re-audit: see command at bottom of this file.*

---

## Target Architecture — Both Projects

Both Energy (Sparc) and Gardening use the same RAG stack (ChromaDB + LlamaIndex + HuggingFace embeddings). The LLM synthesis chain should be identical across both:

```
Priority 1: Ollama local (gemma3:4b)        — private, zero API cost, zero network
Priority 2: gemini-flash-lite-latest         — free tier fallback, ~3k tokens/query, auto-upgrades
Priority 3: Raw chunks                        — no LLM, retrieval-only
```

**Current state (2026-05-13):**

| Project | Synthesis chain | Why |
|---------|----------------|-----|
| Gardening | Ollama → gemini-flash-lite-latest → raw | Mac has Apple Silicon, Ollama runs fast |
| Energy | gemini-flash-lite-latest → raw | NUC (Pentium N3700) can't run Ollama usefully |

**When Mac Mini M5 arrives:** Energy adopts the same 3-layer chain as Gardening — set `OLLAMA_HOST=http://<mac-mini-ip>:11434` in NUC `.env`. Both projects then unified on Ollama → gemini-flash-lite-latest → raw.

**Privacy note:** Only the synthesis step (query + retrieved doc excerpts) leaves the local network. Embeddings and retrieval are 100% local. Ollama as primary eliminates this entirely.

## How the API vs Local distinction works (NUC hardware context)

```
Google API (current Energy primary)    Local inference (NUC — not viable)
───────────────────────────────────    ──────────────────────────────────
Query + chunks sent to Google    →     Download model weights to NUC
Google runs model on A100 GPUs   →     Pentium N3700 runs inference
Answer returns in ~1–2s          →     7B model: 60–120s. 27B: out of RAM.
Cost: €0 on free tier            →     Cost: €0 but unusable

Mac Mini M5 (future):
Metal GPU, 24–32GB RAM           →     gemma3:4b runs at ~20–30 tok/s
Ollama becomes primary for both  →     No data leaves home network
```

---

## Current Model Used

| Setting | Value |
|---------|-------|
| Model | `models/gemini-flash-lite-latest` (floating alias) |
| Config file | `intel/context_builder.py` → `call_llm()` |
| Response label | `"gemini-flash-lite-latest"` — returned by `/intel/ask` `model` field |
| Env var | `GEMINI_API_KEY` in `~/sparc/.env` on NUC |
| Claude Haiku fallback | **Removed** (2026-05-13) — saves Claude Code tokens |
| career.py | Updated to `gemini-flash-lite-latest` (was `gemini-1.5-flash`, 2026-05-13) |

---

## Token Costs (measured 2026-05-13)

Token usage is logged at INFO level: `Gemini tokens — prompt: X, candidates: Y, total: Z`

| Query type | Prompt tokens | Output tokens | Total |
|------------|--------------|---------------|-------|
| Simple factual (no RAG chunks) | ~11 | ~7 | ~18 |
| Typical RAG query (5×512-token chunks) | ~2,600–3,000 | ~200–400 | ~3,000–3,400 |
| Full advisory synthesis | ~3,000–4,000 | ~300–500 | ~3,500–4,500 |

Free tier limits: **1M tokens/day, 15 RPM** — effectively unlimited for this use case.
Every RAG query answered by Gemini saves an equivalent number of Claude Code tokens.

---

## Why `gemini-flash-lite-latest` (floating alias strategy)

### The `-latest` alias approach

Google maintains floating aliases that always resolve to the current stable version of that model family:

| Alias | Resolves to | Use when |
|-------|------------|----------|
| `gemini-flash-lite-latest` ✅ **current** | Latest stable Flash Lite | Personal RAG synthesis — auto-upgrades, zero maintenance |
| `gemini-flash-latest` | Latest stable Flash | When you need higher reasoning capability |
| `gemini-pro-latest` | Latest stable Pro | Long docs, complex reasoning |

**Why floating over pinned (`gemini-3.1-flash-lite`)?**
- Personal RAG synthesis on operational docs has no regulatory reproducibility requirement
- Google handles model quality regressions — if an alias degrades, they roll back
- Pinned versions can be deprecated without warning; the alias survives version bumps
- Zero maintenance: no CLAUDE.md annotation needed when a new version releases

**When to use pinned instead:** Research pipelines, regulated outputs (EU AI Act Article 52 systems), or anywhere you need bit-for-bit reproducibility between runs. This system is not in that category.

### Previous models and why they were superseded

| Model | Status | Why superseded |
|-------|--------|----------------|
| `gemini-flash-lite-latest` ✅ | **Current** | — |
| `gemini-3.1-flash-lite` | Previous pinned | Superseded by alias strategy (same model, manual maintenance) |
| `gemini-2.5-flash` | Previous default | Older generation, superseded by 3.x series |
| `gemini-1.5-flash` | Stale (career.py) | Updated 2026-05-13 |
| `gemini-3-flash-preview` | Skipped | Preview — can be deprecated any time |
| `gemma-4-31b-it` | Not used | Slower, looser instruction-following for RAG |
| `gemini-2.5-pro` | Not used | Slower, overkill for 512-token chunk synthesis |

---

## Full Model List (audited 2026-05-09)

Models confirmed available for `generateContent` on this key:

```
models/deep-research-max-preview-04-2026
models/deep-research-preview-04-2026
models/deep-research-pro-preview-12-2025
models/gemini-2.0-flash
models/gemini-2.0-flash-001
models/gemini-2.0-flash-lite
models/gemini-2.0-flash-lite-001
models/gemini-2.5-computer-use-preview-10-2025
models/gemini-2.5-flash
models/gemini-2.5-flash-image
models/gemini-2.5-flash-lite
models/gemini-2.5-flash-preview-tts
models/gemini-2.5-pro
models/gemini-2.5-pro-preview-tts
models/gemini-3-flash-preview
models/gemini-3-pro-image-preview
models/gemini-3-pro-preview
models/gemini-3.1-flash-image-preview
models/gemini-3.1-flash-lite
models/gemini-3.1-flash-lite-preview
models/gemini-3.1-flash-tts-preview
models/gemini-3.1-pro-preview
models/gemini-3.1-pro-preview-customtools
models/gemini-flash-latest
models/gemini-flash-lite-latest             ← CURRENT (floating alias)
models/gemini-pro-latest
models/gemini-robotics-er-1.5-preview
models/gemini-robotics-er-1.6-preview
models/gemma-4-26b-a4b-it                   ← Gemma 4 (via API, not local)
models/gemma-4-31b-it                       ← Gemma 4 31B (via API, not local)
models/lyria-3-clip-preview
models/lyria-3-pro-preview
models/nano-banana-pro-preview
```

---

## How to re-audit available models

Run this on the NUC when you want to check for new releases:

```bash
ssh dan@192.168.68.119
docker exec sparc-api python3 -c "
from google import genai
client = genai.Client()
models = [m.name for m in client.models.list() if 'generateContent' in (m.supported_actions or [])]
for m in sorted(models):
    print(m)
"
```

Then update the list above and note the audit date.

---

## Switching the active model

Edit one line in `intel/context_builder.py` on the Mac:

```python
# Line ~144 in call_llm():
model="models/gemini-flash-lite-latest",   # floating alias → change only if pinning for reproducibility
```

Then sync and restart:
```bash
rsync -av ~/building-energy-load-forecast/intel/context_builder.py \
  dan@192.168.68.119:~/sparc/intel/
docker restart sparc-api   # volume-mounted — no compose up needed
```

No pip install required — the `google-genai` SDK handles all model names.

---

*Source: `intel/context_builder.py`, `intel/routes.py`, `intel/career.py`, `~/sparc/.env` (NUC)*
*See also: SYSTEM_ACCESS_MODEL.md (credential register), INTEL_MODULE_DEPLOYMENT_EXPLAINED.md*
