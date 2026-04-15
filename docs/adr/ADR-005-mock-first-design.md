# ADR-005: Mock-First Deployment Design (dry_run=True Default)

**Status:** Accepted
**Date:** 2026-Q1

---

## Context

The system requires three external data sources at inference time:
1. **Historical load data** — building electricity consumption (CSVConnector)
2. **Solar + weather forecast** — OpenMeteo API (OpenMeteoConnector)
3. **Electricity prices** — SEMO day-ahead market (SEMOConnector, not yet implemented)

All three may be unavailable in demo, development, or CI contexts. The system needed to run end-to-end — producing a full morning brief and control decisions — without any live API calls. Simultaneously, it needed to be trivially upgradeable to live data without structural changes.

---

## Options Considered

1. **Hard-fail if connectors unavailable** — simplest, but blocks demos and CI
2. **Optional connectors with silent fallback** — hard to distinguish "working with real data" from "silently using stale data"
3. **Mock-first with explicit dry_run flag (chosen)** — clear separation, fail-fast for live mode, zero-config for demo mode

---

## Decision

**All endpoints and scripts default to `dry_run=True`.**

- `deployment/app.py`: `ControlRequest.dry_run: bool = True`. Live mode raises `HTTPException(501)` until real connectors are configured — this is intentional: it prevents silent production failures.
- `deployment/live_inference.py`: `--dry-run` flag is the default; `--live` must be explicitly passed.
- `deployment/mock_data.py`: Canonical mock solar profile (`MOCK_SOLAR_24H`), `MockPriceConnector`, `MockDeviceConnector` — all deterministic, seeded, and representative of real Irish residential data.

**Live mode upgrade path:** Remove the `HTTPException(501)` guard in `app.py` and configure `OpenMeteoConnector` + `SEMOConnector` API keys. No structural changes needed.

---

## Consequences

**Positive:**
- Conference and investor demos work immediately, zero setup (`python deployment/live_inference.py --dry-run`)
- CI pipelines can exercise the full control pipeline without API keys
- Live mode failure is explicit (501) not silent — prevents mistaking mock output for live output
- `MockDeviceConnector.command_log` records all commands sent — inspectable in tests

**Trade-offs:**
- `app.py /control` endpoint currently returns a heuristic P50 (sinusoidal) rather than a real model prediction in live mode — a known gap (`# TODO: wire CSVConnector for historical data`) documented in the code
- The mock solar profile is representative but not location-specific — fine for demos, not for production accuracy assessment
