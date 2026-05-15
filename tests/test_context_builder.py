"""Tests for intel/context_builder.py — E-25 (IBM Skill 3: Tool & Contract Design)."""

from intel.context_builder import (
    AdvisorContext,
    LOW_CONFIDENCE_THRESHOLD,
    SPARC_SYSTEM_PROMPT,
    build_context,
    call_llm,
)


SAMPLE_CHUNKS = [
    {
        "file": "tariff_guide.md",
        "title": "BGE Night Rate Guide",
        "score": 0.82,
        "excerpt": "The BGE night rate applies 23:00–08:00 at €0.237/kWh.",
        "tier": "operational",
    },
    {
        "file": "eddi_setup.md",
        "title": "Eddi Setup Guide",
        "score": 0.71,
        "excerpt": "The Eddi diverts surplus solar to the hot water tank.",
        "tier": "operational",
    },
]


class TestBuildContext:
    def test_returns_advisor_context(self):
        ctx = build_context("What is the night rate?", SAMPLE_CHUNKS, top_score=0.82)
        assert isinstance(ctx, AdvisorContext)

    def test_system_prompt_default(self):
        ctx = build_context("test", SAMPLE_CHUNKS, top_score=0.8)
        assert ctx.system_prompt == SPARC_SYSTEM_PROMPT

    def test_user_message_contains_question(self):
        ctx = build_context("What is the night rate?", SAMPLE_CHUNKS, top_score=0.8)
        assert "What is the night rate?" in ctx.user_message

    def test_user_message_contains_chunk_excerpts(self):
        ctx = build_context("test", SAMPLE_CHUNKS, top_score=0.8)
        assert "BGE Night Rate Guide" in ctx.user_message
        assert "€0.237/kWh" in ctx.user_message

    def test_low_confidence_false_above_threshold(self):
        ctx = build_context("test", SAMPLE_CHUNKS, top_score=LOW_CONFIDENCE_THRESHOLD + 0.01)
        assert ctx.low_confidence is False

    def test_low_confidence_true_below_threshold(self):
        ctx = build_context("test", SAMPLE_CHUNKS, top_score=LOW_CONFIDENCE_THRESHOLD - 0.01)
        assert ctx.low_confidence is True

    def test_empty_chunks_handled(self):
        ctx = build_context("test", [], top_score=0.0)
        assert "(no context retrieved)" in ctx.user_message
        assert ctx.low_confidence is True

    def test_sources_pass_through(self):
        ctx = build_context("test", SAMPLE_CHUNKS, top_score=0.8)
        assert ctx.sources == SAMPLE_CHUNKS

    def test_custom_system_prompt(self):
        custom = "You are a recruitment advisor."
        ctx = build_context("test", SAMPLE_CHUNKS, top_score=0.8, system_prompt=custom)
        assert ctx.system_prompt == custom


class TestCallLlm:
    def test_no_api_key_returns_context(self, monkeypatch):
        """Without ANTHROPIC_API_KEY, call_llm returns raw context, never raises."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = build_context("What is the night rate?", SAMPLE_CHUNKS, top_score=0.8)
        result = call_llm(ctx)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_api_key_low_confidence_prefixed(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = build_context("test", [], top_score=0.0)
        result = call_llm(ctx)
        assert "[Low confidence" in result
