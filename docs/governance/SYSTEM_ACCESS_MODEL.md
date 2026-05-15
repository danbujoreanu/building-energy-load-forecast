# System Access Model — Sparc Energy
*Created: 2026-03-28 | Last modified: 2026-03-28*
*Format: Operational credential register — who calls what, what auth is required, what breaks if a credential is revoked*
*Governance reference: companion to System Component Map and Deployment Runbook*

---

## Purpose

An ops team inheriting a system needs to know: "What credentials does this system require, who owns each one, where is each one stored, and what is the impact if it is revoked or rotated?" This document is that register.

---

## Credential Register

| Credential | Service | Auth type | Stored where | Owner | Revocation impact | Rotation policy |
|-----------|---------|-----------|-------------|-------|-------------------|-----------------|
| `MYENERGI_API_KEY` | myenergi Eddi API (hot water control) | HTTP Digest password | `.env` (gitignored) | Dan Bujoreanu (personal myenergi account) | **HIGH** — no Eddi control commands; device reverts to fixed schedule | On account compromise; via myenergi app → Settings → Advanced → Regenerate |
| `MYENERGI_SERIAL` | myenergi hub (Eddi gateway) | HTTP Digest username | `.env` (gitignored) | Dan Bujoreanu | **HIGH** — paired with API key; both required | Fixed — hub serial does not change |
| `DB_PASSWORD` | TimescaleDB / PostgreSQL | Password auth | `.env` + `docker-compose.yml` secrets | Dan Bujoreanu | **HIGH** — FastAPI cannot write predictions; API returns 503 | Rotate via `docker compose down && update .env && docker compose up -d` |
| `GRAFANA_PASSWORD` | Grafana admin dashboard | HTTP Basic (admin user) | `.env` | Dan Bujoreanu | **LOW** — dashboard inaccessible; no data loss; API unaffected | Via Grafana UI → Profile → Change Password |
| `ANTHROPIC_API_KEY` (GitHub CI) | AI PR reviewer (GitHub Actions) | Bearer token | GitHub Secrets (`ANTHROPIC_API_KEY`) | Dan Bujoreanu (Anthropic account) | **LOW** — AI PR review fails; 4 Required CI checks unaffected | Via Anthropic console → API Keys → Regenerate; update GitHub Secret |
| `ANTHROPIC_API_KEY` (NUC — `Intel_NUC` key) | `/intel/ask` LLM synthesis fallback (Claude haiku-4-5) | Bearer token | `~/sparc/.env` on NUC (gitignored) | Dan Bujoreanu (Anthropic account) | **LOW** — `/intel/ask` falls back to Gemini or raw context; retrieval still works | Via console.anthropic.com → API Keys → Create key; add to `~/sparc/.env`. **Requires paid credits.** Secondary to Gemini. |
| `GEMINI_API_KEY` (`...als8` — Free tier) | `/intel/ask` LLM synthesis — **primary, preferred** (Gemini 2.0 Flash) | Bearer token | `~/sparc/.env` on NUC (gitignored) | Dan Bujoreanu (Google account — AI Studio free tier) | **LOW** — `/intel/ask` falls back to Anthropic or raw context; retrieval always works | Via aistudio.google.com → API Keys → Create key. **Free tier: 15 RPM, 1M tokens/day. No credit card required.** Rotation: delete old key, create new, update `.env`, run `docker compose up -d api` + reinstall intel deps. |
| `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` | AWS ECR (Docker push) + App Runner (deploy) | AWS IAM | `~/.aws/credentials` or env vars (Makefile) | Dan Bujoreanu (AWS account) | **MEDIUM** — cannot push new Docker images or deploy; existing App Runner instance continues serving | Via AWS IAM console → rotate key; update local `~/.aws/credentials` |
| `LINEAR_API_KEY` | Linear project management API | Bearer token | `.env` (gitignored) | Dan Bujoreanu (Linear workspace) | **LOW** — roadmap sync scripts fail; no system impact | Via Linear → Settings → API → Personal API Keys → Regenerate |
| Open-Meteo API | Live weather data (Open-Meteo) | None (public API) | N/A | N/A (public) | N/A — no auth required | N/A |
| ESB Networks SMDS API *(planned)* | Smart meter data access (when SMDS live, mid-2026) | OAuth2 / ESCO registration | TBD — pending CRU202517 Appendix A | Dan Bujoreanu / Sparc Energy Ltd (ESCO) | **HIGH** — no automatic meter data; fall back to manual CSV upload | Per CRU202517 data access code requirements |

---

## Storage Locations

| Location | What's stored there | Access control | Committed to git? |
|----------|--------------------|--------------|--------------------|
| `.env` (project root) | MYENERGI_API_KEY, MYENERGI_SERIAL, DB_PASSWORD, GRAFANA_PASSWORD, LINEAR_API_KEY | Local file, owner read-only | ❌ No — `.gitignore` line 1 |
| `~/.aws/credentials` | AWS IAM access key + secret | Local file, macOS permissions | ❌ No — outside repo |
| GitHub Secrets | ANTHROPIC_API_KEY | GitHub Actions runtime only; not visible after set | ❌ No — GitHub-managed |
| `docker-compose.yml` | DB_PASSWORD reference via `${DB_PASSWORD}` | Reads from `.env` at runtime | ✅ Yes — but value is a variable, not the secret itself |
| `outputs/models/` | Trained LightGBM model artefacts | Local filesystem | ❌ No — `.gitignore` |
| `outputs/logs/control_decisions.jsonl` | Audit log (no credentials) | Local filesystem | ❌ No — `.gitignore` |

---

## Service-to-Service Access Map

```
FastAPI ──────────────────→ TimescaleDB     (DB_PASSWORD via env)
FastAPI ──────────────────→ Redis           (no auth — internal Docker network)
FastAPI ──────────────────→ Open-Meteo      (no auth — public HTTPS)
FastAPI ──────────────────→ myenergi API    (MYENERGI_SERIAL + MYENERGI_API_KEY)
GitHub Actions ───────────→ Anthropic API   (ANTHROPIC_API_KEY via GitHub Secret)
GitHub Actions ───────────→ AWS ECR         (AWS IAM credentials)
AWS App Runner ───────────→ FastAPI image   (pulls from ECR at deploy time)
Grafana ──────────────────→ TimescaleDB     (DB_PASSWORD — Grafana datasource config)
n8n ──────────────────────→ FastAPI         (localhost:8000 — no auth — internal only)
```

**External-facing surface (API endpoints accessible outside Docker network):**
- `POST /predict` — no auth (Phase 7: add API key gate before public launch)
- `POST /control` — no auth (Phase 7: add API key gate before public launch)
- `GET /health` — no auth (intentional — monitoring requirement)
- `POST /upload` — no auth (Phase 7: add household auth before multi-tenant)
- `GET /intel/query` — no auth (Phase 7: add API key gate)

> **Phase 7 security action:** Add API key authentication to all non-health endpoints before the App Runner URL is shared publicly. Recommended: HTTP header `X-API-Key` checked against an env var `SPARC_API_KEY`.

---

## What an Ops Team Needs on Day One

If this system is handed to an operations team (or if Dan needs to rebuild after a credential loss), the minimum credential set is:

| Priority | Credential | Where to get it | Time to restore |
|----------|-----------|----------------|----------------|
| P0 | `DB_PASSWORD` | Set a new one in `.env` — no external dependency | 2 minutes |
| P0 | `MYENERGI_API_KEY` | myenergi app → Settings → Advanced → API Key | 5 minutes |
| P1 | `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys | 5 minutes + GitHub Secret update |
| P1 | AWS IAM key | AWS console → IAM → Users → Security credentials | 10 minutes |
| P2 | `LINEAR_API_KEY` | linear.app → Settings → API → Personal API Keys | 2 minutes |
| P3 | `GRAFANA_PASSWORD` | Any string — set in `.env` before `docker compose up` | 1 minute |

Rebuild procedure: populate `.env` from the table above → `docker compose up -d` → run `scripts/run_pipeline.py --city ireland` to restore model artefacts → verify with `/health`.

---

## Compliance Notes

| Requirement | How it's met |
|-------------|-------------|
| No secrets in version control | `.gitignore` covers `.env`, `~/.aws/`, `outputs/` |
| EU AI Act Article 52 — audit trail | `control_decisions.jsonl` is append-only; every automated decision logged with timestamp, action, confidence, reasoning |
| GDPR — data minimisation | No raw meter data in repo; only processed features; ESB CSV never committed |
| Audit trail integrity | Audit log is append-only; model registry tracks all model versions; runbook documents change control |

---

*Owner: Dan Alexandru Bujoreanu | Review cycle: on each Phase boundary or credential rotation*
