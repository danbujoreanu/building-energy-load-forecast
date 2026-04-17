"""
intel/routes.py
===============
FastAPI router for /intel/* endpoints.

Include this router in deployment/app.py:
    from intel.routes import router as intel_router
    app.include_router(intel_router)

Endpoints
---------
POST /intel/query
    Body: {"tier": "operational", "query": "...", "top_k": 5}
    Returns: {"answer": "...", "sources": [...], "tier": "...", "top_score": 0.30, "llm_used": false}

    Set tier to "all" to query all tiers and merge results by score.

GET  /intel/status
    Returns: {"operational": {"docs": 2, "chunks": 27}, ...}

GET  /intel/tiers
    Returns the list of valid tiers.
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intel", tags=["Intelligence"])

# Lazy imports so the embedding model is NOT loaded at module import time.
# It's loaded on first request to avoid slowing down the main API startup.
_retrieval = None


def _get_retrieval():
    global _retrieval
    if _retrieval is None:
        import intel.retrieval as r
        _retrieval = r
    return _retrieval


# ── Request / Response schemas ────────────────────────────────────────────────

class IntelQueryRequest(BaseModel):
    tier: str = Field(
        default="operational",
        description=(
            "Tier to query: operational | strategic | research | market | all. "
            "Use 'all' to search every tier and merge results by score."
        ),
    )
    query: str = Field(..., min_length=3, max_length=1000, description="Natural language question.")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve per tier.")


class SourceCitation(BaseModel):
    file: str
    score: float
    excerpt: str
    tier: str
    title: Optional[str] = None


class IntelQueryResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    tier: str
    top_score: float
    llm_used: bool


class TierStatus(BaseModel):
    docs: int
    chunks: int


class IntelStatusResponse(BaseModel):
    status: dict[str, TierStatus]
    total_docs: int
    total_chunks: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/query", response_model=IntelQueryResponse, summary="Query the intelligence corpus")
def intel_query(request: IntelQueryRequest) -> IntelQueryResponse:
    """Retrieve relevant context from the intel corpus and return an answer.

    - If ``tier`` is ``"all"``, all tiers are queried and results merged by score.
    - If ``GEMINI_API_KEY`` env var is set, answer is synthesised by Gemini Flash.
    - Otherwise, the top retrieved chunks are concatenated as the answer.
    - Answers prefixed with ``[Low confidence ...]`` when top chunk score < 0.60.
    """
    r = _get_retrieval()

    VALID_TIERS = r.VALID_TIERS
    tier = request.tier.lower().strip()

    if tier != "all" and tier not in VALID_TIERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown tier '{tier}'. Valid values: {sorted(VALID_TIERS)} or 'all'.",
        )

    try:
        if tier == "all":
            result = r.query_all_tiers(request.query, top_k=request.top_k)
        else:
            result = r.query_tier(tier, request.query, top_k=request.top_k)
    except Exception as exc:
        logger.error("Intel query failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retrieval error: {exc}") from exc

    sources = [
        SourceCitation(
            file=s["file"],
            score=s["score"],
            excerpt=s["excerpt"],
            tier=s.get("tier", request.tier),
            title=s.get("title"),
        )
        for s in result["sources"]
    ]

    return IntelQueryResponse(
        answer=result["answer"],
        sources=sources,
        tier=result["tier"],
        top_score=result["top_score"],
        llm_used=result["llm_used"],
    )


@router.get("/status", response_model=IntelStatusResponse, summary="Intel corpus document counts")
def intel_status() -> IntelStatusResponse:
    """Return document and chunk counts for each tier."""
    from intel.ingest import get_status

    raw = get_status()
    status = {tier: TierStatus(docs=v["docs"], chunks=v["chunks"]) for tier, v in raw.items()}
    total_docs = sum(v.docs for v in status.values())
    total_chunks = sum(v.chunks for v in status.values())

    return IntelStatusResponse(
        status=status,
        total_docs=total_docs,
        total_chunks=total_chunks,
    )


@router.get("/tiers", summary="List valid intel tiers")
def intel_tiers() -> dict:
    """Return the list of valid tier names and their descriptions."""
    return {
        "tiers": [
            {"name": "operational", "description": "Regulatory docs, CRU decisions, compliance deadlines"},
            {"name": "strategic",   "description": "Business strategy, funding, commercialisation"},
            {"name": "research",    "description": "Academic papers, literature review, PhD context"},
            {"name": "market",      "description": "Competitor analysis, market research, Irish PCW landscape"},
        ]
    }
