# ADR-004: FastAPI for the Inference API

**Status:** Accepted
**Date:** 2026-Q1

---

## Context

The forecasting model needed a web API layer to expose `/predict` (raw H+24 inference) and `/control` (full demand-response pipeline) endpoints. This API serves as the product interface for Sparc Energy / LightEnergy.ie and as the demo surface for investor and conference presentations.

---

## Options Considered

| Framework | Auto schema | Async | Validation | Notes |
|-----------|------------|-------|-----------|-------|
| **FastAPI** | Yes (OpenAPI) | Yes | Pydantic | Candidate |
| Flask | No | No (by default) | Manual | Industry standard but verbose |
| Django REST | No (without DRF) | Partial | Serialisers | Too heavyweight for a single inference service |
| Plain Python HTTP | No | No | Manual | No value-add |

---

## Decision

**FastAPI**, with Pydantic v2 request/response models.

**Reasons:**
1. **Automatic Pydantic validation:** `PredictionRequest`, `PredictionResponse`, `ControlRequest`, `ControlResponse` are validated at the boundary. Malformed feature vectors, unknown cities, and empty inputs raise 422s automatically — no manual validation code needed.
2. **Auto-generated OpenAPI docs:** `/docs` (Swagger) and `/redoc` work out of the box. Critical for Sparc Energy client demos and Enterprise Ireland evidence of a working product.
3. **Async-ready for live connectors:** `OpenMeteoConnector` and `SEMOConnector` (planned) should be async HTTP clients. FastAPI's async support makes this a clean upgrade path without changing the framework.
4. **Lifespan context manager:** Model loading at startup (`@asynccontextmanager lifespan`) is a clean pattern — models load once, are reused across requests, and release on shutdown. Flask requires manual `before_first_request` patterns that are deprecated or fragile.
5. **Modern Python alignment:** Type annotations, dataclasses, Pydantic — consistent with the rest of the codebase style.

---

## Consequences

**Positive:**
- Input validation is automatic and documented in the OpenAPI schema
- Demo surface (Swagger UI) requires zero additional work
- Framework ready for async live connectors when API keys are configured
- Field validators (e.g., `features_must_be_non_empty`, `city_must_be_known`) are co-located with the schema, not scattered across endpoint logic

**Trade-offs:**
- Slightly more upfront ceremony than Flask for simple cases
- Full async benefit not yet realised (dry_run mode uses sync mock data; live connectors will unlock this)
- Requires understanding of Pydantic v2 field validators — subtle differences from v1 (`@field_validator` vs `@validator`)
