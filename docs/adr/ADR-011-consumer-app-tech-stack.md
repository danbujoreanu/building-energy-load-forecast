# ADR-011: Consumer App Tech Stack — Next.js PWA + FastAPI + Supabase + Grafana

**Status:** Accepted
**Date:** 2026-04-16 (Session 42)
**Reference:** `docs/TECH_STACK.md` (full implementation guide)

---

## Context

The Sparc Energy product requires a consumer-facing application to deliver the morning brief, display H+24 forecasts, surface control recommendations, and manage household onboarding. The ML backend (FastAPI, LightGBM) already exists. The decision was to choose a full-stack architecture that:

1. Supports a single user on a Mac Mini M5 today (Phase 1)
2. Scales to a commercial beta with ≤ 100 households without rearchitecting (Phase 2)
3. Scales to 1,000+ households on AWS App Runner without code changes (Phase 3)
4. Minimises vendor lock-in and maximises open-source components
5. Respects GDPR (EU data residency, row-level security, no raw time-series to LLM API)

The app must work on mobile (Irish residential users check energy data on their phone, not a desktop) and must not require App Store distribution.

---

## Options Considered

### Frontend

| Option | Decision | Rationale |
|--------|----------|-----------|
| **Next.js 15 (App Router) PWA** | ✅ Chosen | Production-grade React framework. PWA = works on iOS/Android without App Store. TypeScript safety. Vercel/Cloudflare deployment path. shadcn/ui provides accessible component library. Tremor provides energy-native chart components (P10/P50/P90 bands, gauges). |
| Streamlit | ❌ Rejected | Too slow for consumer-facing UI. Not mobile-friendly. No PWA capability. Best reserved for internal analytics and paper figure iteration. |
| Gradio | ❌ Rejected | ML model demo tool, not a product interface. No routing, no auth, no offline. |
| React Native / Flutter | ❌ Rejected | Requires App Store submission. Adds native build overhead. PWA covers the mobile use case without stores. Revisit if native push notifications become a hard requirement. |
| Google AppSheet / Bubble | ❌ Rejected | No-code tools cannot support custom API calls to FastAPI, custom chart components, or the complex prediction/control data model. |

### Design Tooling

| Option | Decision | Rationale |
|--------|----------|-----------|
| **Google Stitch** (Gemini Labs) | ✅ Chosen for rapid prototyping | Generates interactive prototypes + Figma-exportable layouts from text prompts. 550 free generations/month included with Gemini Pro subscription. Use before hand-coding Next.js components. |
| Figma | ✅ Free tier | Receives Stitch exports for annotation and design reference. Not used for from-scratch design work at this stage. |
| Sketch / Adobe XD | ❌ Rejected | Paid tools with no advantage over Stitch + Figma free tier for a solo founder. |

### Backend

FastAPI already exists and is production-ready. No change — kept as the sole backend API layer.

### Database

| Option | Decision | Rationale |
|--------|----------|-----------|
| **PostgreSQL 16 + TimescaleDB** via Supabase | ✅ Chosen | Managed Postgres with row-level security, Auth, and real-time subscriptions. EU region (Frankfurt) for GDPR compliance. Free tier: 500MB, 50k rows (sufficient for Phase 1-2). TimescaleDB extension enables native time-series queries on `meter_readings` and `predictions` without a second database. Standard SQL — portable to AWS RDS with a connection string change. |
| InfluxDB | ❌ Rejected | Dedicated time-series DB adds operational complexity. PostgreSQL + TimescaleDB handles the same workload. Maintaining two databases (one relational, one time-series) is unnecessary at this scale. |
| Firebase Firestore | ❌ Rejected | NoSQL document model is a poor fit for structured energy data (households, tariffs, model versions). Row-level security is better enforced at the PostgreSQL level. Google Cloud lock-in. |
| SQLite | ⚠️ Phase 1 only | Acceptable for single-user local testing. Migrate to Supabase for Phase 2 (when multi-household is required). |

### Operator Dashboard

| Option | Decision | Rationale |
|--------|----------|-----------|
| **Grafana OSS** | ✅ Chosen | Pre-built time-series panels (no custom code), alerting, annotations, user management, native PostgreSQL connector. Free and self-hosted. Vega-Lite plugin available for custom energy chart specifications. Best for: model drift monitoring, rolling MAE, control audit log visualisation, system health. |
| Plotly Dash | ❌ Rejected | Requires writing every dashboard in Python. More maintenance overhead than Grafana for operational monitoring. Plotly charting library IS used inside Next.js via Tremor (different use case). |
| PowerBI / Tableau | ❌ Rejected | Paid licences, Microsoft/Salesforce ecosystem lock-in. No advantage over Grafana + Vega-Lite for this use case. |
| Streamlit | ✅ Internal analytics only | Fast to build, Python-native, excellent for ad-hoc data exploration and paper figure iteration. Not deployed — runs locally. |

### Caching

Redis (via Upstash serverless in production, local Docker in Phase 1). TTL 23h per household prediction. One prediction per household per day = negligible memory at any realistic scale.

### Scheduling

APScheduler (Phase 1–2) → AWS EventBridge + Lambda fan-out (Phase 3). APScheduler embedded in FastAPI is correct for Mac Mini and App Runner phases.

### Notifications

Resend (email, free 3k/month) for Phase 1. WhatsApp Business API via Twilio for Phase 2 (P-02). Web Push API (Next.js PWA) for Phase 2. n8n as a visual workflow orchestrator to replace custom notification code in Phase 2.

### Workflow Automation (Phase 2)

n8n (self-hosted, open-source, runs in Docker). Handles: CSV upload → process → notify, daily brief delivery, webhook triggers from P1 port data. Replaces custom notification code with a visual workflow. Avoids "costly SaaS subscriptions" (Zapier, Make) for a solo founder.

### Local Hosting (Phase 1 — Mac Mini M5)

Docker Compose + Caddy (automatic TLS) + Cloudflare Tunnel (free, no router config). Mac Mini M5 with 16GB RAM can host the full stack at < 5% memory utilisation. Scales to ~500 households before AWS migration is needed.

### Production (Phase 3)

AWS App Runner (existing Dockerfile) + AWS RDS PostgreSQL + Upstash Redis + Vercel (Next.js). Zero code changes needed from Mac Mini → AWS (connection string change only). eu-west-1 (Ireland) for GDPR.

### AI/LLM Advisor (P-13)

**Gemini Flash via Gemini API** (not Claude API). The user has a Gemini Pro subscription. Gemini Flash is cost-effective (~$0.075/1M input tokens) and already covered by the subscription. Claude remains the development assistant (Cursor + Claude Code). Gemini Flash is the user-facing energy advisor model.

### IDE

| Option | Decision | Rationale |
|--------|----------|-----------|
| **Claude Code** | ✅ Chosen (deep codebase) | Deep multi-file context, subagent dispatch, PreToolUse safety hook. Primary tool for architecture work, multi-file refactors, test generation, and governance docs. |
| **Google Antigravity** | ✅ Chosen (parallel agents) | Agent-first VS Code fork (Google Labs, Nov 2025). Gemini 3.1 Pro. "Manager View" runs 5 parallel agents simultaneously. Use for: running horizon sweeps, parallel model experiments, scaffolding multiple files at once. Free tier + Pro $20/month. User has Gemini Pro subscription. |
| **Cursor** | ✅ Chosen (iterative coding) | AI-powered VS Code fork, best-in-class autocomplete for Python + TypeScript polyglot. Use for: day-to-day feature coding, frontend iteration, CSS/Tailwind work. |
| GitHub Copilot | ❌ Rejected | Weaker multi-file reasoning than Cursor. No agent dispatch. Offers no advantage when Claude Code + Cursor are already in the stack. |

Three tools serve different roles — they are complementary, not competing. See `docs/TECH_STACK.md` Section 1 for workflow guidance on when to use each.

---

## Decision

**Production tech stack:**

```
Consumer App:   Next.js 15 PWA + TypeScript + Tailwind CSS + shadcn/ui + Tremor
Backend:        FastAPI (existing) + APScheduler
Database:       PostgreSQL 16 + TimescaleDB (Supabase managed)
Auth:           Supabase Auth (magic link + Google OAuth)
Cache:          Redis (Upstash serverless, TTL 23h)
Op. Dashboard:  Grafana OSS (PostgreSQL datasource, Vega-Lite panels)
Dev Analytics:  Streamlit (internal, not deployed)
Notifications:  Resend (email) → Twilio WhatsApp (Phase 2)
Automation:     APScheduler → n8n (Phase 2)
Design:         Google Stitch → Figma (free tier) → Next.js hand-coded
LLM Advisor:    Gemini Flash (Gemini API, user has Pro subscription)
Local hosting:  Docker Compose + Caddy + Cloudflare Tunnel (Mac Mini M5)
Production:     AWS App Runner + RDS + Vercel (Phase 3)
IDE:            Claude Code (deep codebase) + Google Antigravity (parallel agents) + Cursor (iterative coding)
```

---

## Consequences

**Positive:**
- No App Store dependency (PWA covers iOS/Android)
- Single database (PostgreSQL) handles both relational and time-series workloads
- Mac Mini M5 is sufficient for Phase 1–2 (< 500 households) — zero cloud costs
- Supabase row-level security enforces data isolation at the DB layer, not the API layer
- Grafana auto-provisioned via Docker Compose — zero manual setup required
- Full stack portable to AWS with environment variable changes only

**Trade-offs acknowledged:**
- Next.js frontend not yet built (D-23 outstanding)
- Supabase free tier (500MB) requires upgrade before Phase 2 scale (known, €25/month Pro)
- n8n migration from APScheduler adds Phase 2 effort (deferred intentionally to Phase 1)
- Gemini Flash for LLM Advisor requires Gemini API key setup (separate from Pro subscription — see `.env.example`)
