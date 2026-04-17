"""
intel/gradio_app.py
===================
Gradio chat interface for the Sparc Energy intelligence corpus.

URL    : intel.danbujoreanu.com  (via Cloudflare Tunnel)
Port   : 7861
Auth   : Cloudflare Access (Google OAuth) — gate set in Cloudflare dashboard
Audience: Private — Dan only (commercial strategy + regulatory docs)

Usage
-----
    python -m intel.gradio_app
    # OR
    python intel/gradio_app.py

Environment variables
---------------------
    GEMINI_API_KEY   — if set, enables Gemini Flash answer synthesis
    GRADIO_SERVER_PORT — override port (default: 7861)
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Generator

# Ensure project root on path when run as script
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import gradio as gr

from intel.ingest import VALID_TIERS, get_status
from intel.retrieval import query_tier, query_all_tiers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_PORT = int(os.environ.get("GRADIO_SERVER_PORT", 7861))
_TIER_CHOICES = ["all"] + sorted(VALID_TIERS)

# ── Chat handler ──────────────────────────────────────────────────────────────

def _format_sources(sources: list[dict]) -> str:
    if not sources:
        return "_No sources found._"
    lines = ["**Sources:**"]
    for i, s in enumerate(sources[:5], 1):
        title = s.get("title") or s["file"]
        score = s["score"]
        excerpt = s["excerpt"].strip().replace("\n", " ")[:200]
        lines.append(f"{i}. **{title}** (score: {score:.3f})\n   > {excerpt}...")
    return "\n".join(lines)


def chat(question: str, tier: str, history: list) -> tuple[list, str]:
    """Query the intel corpus and return (updated_history, sources_markdown)."""
    if not question.strip():
        return history, ""

    try:
        if tier == "all":
            result = query_all_tiers(question, top_k=5)
        else:
            result = query_tier(tier, question, top_k=5)
    except Exception as exc:
        logger.error("Query failed: %s", exc)
        error_msg = f"⚠️ Error: {exc}"
        history = history + [[question, error_msg]]
        return history, ""

    answer = result["answer"]
    top_score = result["top_score"]
    tier_used = result["tier"]
    llm_flag = " _(Gemini synthesis)_" if result["llm_used"] else " _(retrieval-only)_"

    # Build response message
    response = f"{answer}\n\n---\n_Tier: **{tier_used}** | Top score: **{top_score:.3f}**{llm_flag}_"
    history = history + [[question, response]]
    sources_md = _format_sources(result["sources"])
    return history, sources_md


# ── Status panel ──────────────────────────────────────────────────────────────

def get_corpus_status() -> str:
    status = get_status()
    lines = ["| Tier | Docs | Chunks |", "|------|------|--------|"]
    total_d = total_c = 0
    for tier in sorted(status):
        d, c = status[tier]["docs"], status[tier]["chunks"]
        lines.append(f"| {tier} | {d} | {c} |")
        total_d += d
        total_c += c
    lines.append(f"| **TOTAL** | **{total_d}** | **{total_c}** |")
    return "\n".join(lines)


# ── Example queries ───────────────────────────────────────────────────────────

_EXAMPLES = [
    ["When does the CRU dynamic pricing mandate take effect?", "operational"],
    ["What is the SMDS and when will third-party access open?", "operational"],
    ["What GDPR lawful basis do we use for processing smart meter data?", "operational"],
    ["Who are our main Irish competitors?", "market"],
    ["What is the academic evidence for tree models outperforming DL on tabular data?", "research"],
]


# ── Build Gradio UI ───────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    with gr.Blocks(
        title="Sparc Energy — Intelligence",
        theme=gr.themes.Soft(primary_hue="blue"),
        css="""
        .source-panel { font-size: 0.85em; background: #f8f9fa; padding: 12px; border-radius: 6px; }
        footer { display: none !important; }
        """,
    ) as demo:
        gr.Markdown(
            """
# ⚡ Sparc Energy — Intelligence
**Regulatory, strategy and research corpus** — powered by LlamaIndex + ChromaDB

_Ask questions about CRU regulations, Irish market dynamics, competitor analysis, or research literature._
            """
        )

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Intel Chat",
                    height=480,
                    bubble_full_width=False,
                )
                with gr.Row():
                    question_box = gr.Textbox(
                        placeholder="e.g. When does the CRU mandate take effect?",
                        show_label=False,
                        scale=4,
                    )
                    tier_dropdown = gr.Dropdown(
                        choices=_TIER_CHOICES,
                        value="all",
                        label="Tier",
                        scale=1,
                    )
                with gr.Row():
                    submit_btn = gr.Button("Ask", variant="primary")
                    clear_btn = gr.Button("Clear")

            with gr.Column(scale=1):
                gr.Markdown("### Sources")
                sources_box = gr.Markdown(
                    value="_Sources will appear here after a query._",
                    elem_classes=["source-panel"],
                )
                gr.Markdown("### Corpus status")
                status_box = gr.Markdown(value=get_corpus_status())
                refresh_btn = gr.Button("↻ Refresh status", size="sm")

        with gr.Accordion("Example queries", open=False):
            gr.Examples(
                examples=_EXAMPLES,
                inputs=[question_box, tier_dropdown],
                label="",
            )

        # ── Event wiring ──────────────────────────────────────────────────────
        submit_btn.click(
            fn=chat,
            inputs=[question_box, tier_dropdown, chatbot],
            outputs=[chatbot, sources_box],
        ).then(fn=lambda: "", outputs=question_box)

        question_box.submit(
            fn=chat,
            inputs=[question_box, tier_dropdown, chatbot],
            outputs=[chatbot, sources_box],
        ).then(fn=lambda: "", outputs=question_box)

        clear_btn.click(fn=lambda: ([], ""), outputs=[chatbot, sources_box])

        refresh_btn.click(fn=get_corpus_status, outputs=status_box)

    return demo


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ui = build_ui()
    logger.info("Starting Sparc Energy Intel chat on port %d", _PORT)
    ui.launch(
        server_name="0.0.0.0",
        server_port=_PORT,
        share=False,
        show_error=True,
    )
