# Tech Stack — Sparc Energy
*Consumer App + Operator Dashboard + ML Backend*
*Last updated: 2026-04-16 | Owner: Dan (Product + Engineering)*

> **Scope:** This document covers every layer of the product stack — from the
> consumer-facing PWA to the operator dashboard to the ML inference backend.
> It is the single source of truth for tool choices and rationale.
> See `ROADMAP.md` D-23 through D-26 for delivery milestones.

---

## 1. Development Environment

### Development Tool Stack

Three complementary tools — each with a distinct role:

| Tool | Role | When to use |
|------|------|-------------|
| **Claude Code** | Deep codebase assistant — this session right now | Multi-file edits, architecture decisions, long-context reasoning, test writing, commit review |
| **Google Antigravity** | Agent-first IDE (VS Code fork, Gemini 3.1) | Parallel agent dispatch — run 5 agents simultaneously on different bugs/features. Best for: boilerplate generation, parallel refactors, UI scaffolding |
| **Cursor** | AI-powered VS Code (Claude + GPT models) | Day-to-day coding when Antigravity agents aren't needed. Inline multi-file edits, Python + TypeScript polyglot work |
| **Gemini Pro** | LLM subscription | Google Stitch (UI prototyping), Gemini Flash API (P-13 LLM Advisor in production), Gemini in Antigravity |

**Google Antigravity specifics (announced Nov 2025):**
- VS Code fork with "Manager View" — dispatch up to 5 parallel coding agents
- Each agent gets: Editor View (traditional IDE) + terminal + browser
- Generates "Artifacts" per task (plan, implementation, screenshots) for transparency
- Models: Gemini 3.1 Pro / Flash by default; also supports Claude Sonnet
- Pricing: Free tier, Pro ($20/mo), Ultra ($249.99/mo)
- Status (April 2026): Public preview, v1.22.2. Some stability issues on long tasks.

**Claude Code specifics:**
- Best for: tasks requiring full codebase context, architectural decisions, this project's CLAUDE.md protocol
- Run from repo root: `claude` (reads CLAUDE.md automatically)

**Workflow for this project:**
1. `claude` in terminal → architecture decisions, multi-file implementations, ROADMAP updates
2. Antigravity → parallel boilerplate tasks (e.g., "write 5 new tests" + "update 3 ADRs" simultaneously)
3. Cursor → iterative development, quick fixes, TypeScript frontend work

**Setup:** Open `~/building-energy-load-forecast/` as the workspace root in all three tools. The project ships with a `pyproject.toml` that configures `black`, `ruff`, and `mypy`.

---

## 2. Consumer App — Frontend

### Next.js 15 (App Router) + TypeScript
**Progressive Web App (PWA) — no App Store required.**

```
Framework:    Next.js 15 (App Router, React Server Components)
Language:     TypeScript (strict mode)
Styling:      Tailwind CSS v4
Components:   shadcn/ui (Radix primitives, fully accessible)
Charts:       Tremor (built on Recharts — energy-native chart components)
PWA:          next-pwa (offline support, "Add to Home Screen" on iOS/Android)
State:        Zustand (lightweight, no Redux overhead for this scale)
Forms:        React Hook Form + Zod
```

**Why Next.js over Streamlit / Gradio / Google AppSheet:**

| Tool | Verdict for Sparc Energy |
|------|--------------------------|
| **Streamlit** | ✅ **Use for internal operator dashboard only.** Too slow, too data-sciency for a consumer product. No offline, no PWA, no mobile-first layout. |
| **Gradio** | ❌ Gradio is for ML model demos (upload an image, run inference). Not a product interface. Never use for consumer-facing work. |
| **Google AppSheet** | ❌ No-code tool, good for internal CRUD apps. Can't build the UX quality or customisation Sparc needs. |
| **Bubble / Webflow** | ❌ Wrong abstraction level for an AI-powered product with custom API calls. |
| **Next.js** | ✅ Production-grade, React ecosystem, PWA capability, TypeScript safety, Vercel/Cloudflare deployment, builds trust with enterprise/RENEW partners. |

**Key pages (Phase 1 — single user on Mac Mini):**

```
/                     Morning brief — today's forecast + recommended actions
/history              30-day consumption history chart
/devices              Connected devices (Eddi status, EV future)
/settings             Tariff configuration, notification prefs
/admin/dashboard      Operator view (internal — gated by auth)
```

**Charts — Tremor:**
Tremor (tremor.so) ships React components designed for analytics: `AreaChart`, `BarChart`, `SparklineChart`. Energy-native look, dark mode support, responsive. Use for:
- 24-hour consumption forecast (area chart, P10/P50/P90 bands)
- Daily/weekly history (bar chart)
- Home Plan Score gauge

---

## 3. Backend — FastAPI (existing)

**Keep it. It is production-ready.**

```
Framework:  FastAPI 0.115+ (existing — app.py)
Runtime:    Python 3.12 (existing miniconda env)
ASGI:       Uvicorn with Gunicorn workers (production)
Auth:       Supabase JWT → FastAPI dependency injection
Background: APScheduler 3.x (daily 16:00 prediction batch per household)
```

**Key endpoints (existing + planned):**

```
GET  /health             → Model status, drift report, last run
POST /predict            → On-demand H+24 forecast (single household)
POST /control            → ControlEngine decisions + audit log
GET  /brief/{city}       → Morning brief JSON (consumed by Next.js frontend)
POST /household          → Register new household (D-25 multi-tenant)
GET  /household/{id}     → Household profile + latest predictions
POST /outcome/{rec_id}   → Record whether user acted on recommendation
```

---

## 4. Database — PostgreSQL via Supabase

**Chosen over InfluxDB, Firebase, and plain SQLite.**

| Option | Verdict |
|--------|---------|
| **SQLite** | ✅ Fine for Phase 1 (single user, local). Migrate to Supabase for Phase 2. |
| **InfluxDB** | ❌ Specialised time-series DB. Adds a second DB to maintain. PostgreSQL + TimescaleDB extension handles our time-series load with no added complexity. |
| **Firebase Firestore** | ❌ NoSQL, poor fit for relational energy data (tariffs, household metadata, model versions). Row-level security is better in Postgres. |
| **Supabase (PostgreSQL)** | ✅ **Chosen.** Managed Postgres + Auth + Row-Level Security + real-time subscriptions + REST API auto-generated from schema. EU region (Frankfurt). Free tier: 500MB, 50k rows. |
| **Neon** | ✅ Strong alternative to Supabase if serverless branching matters. Same PostgreSQL semantics. |

**TimescaleDB extension:** Enable on Supabase for the `predictions` and `meter_readings` tables. Automatic time-series partitioning, faster range queries, built-in `time_bucket()` aggregate.

### Multi-Household Database Schema

```sql
-- ---------------------------------------------------------------
-- households — one row per registered property
-- ---------------------------------------------------------------
CREATE TABLE households (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    city            TEXT NOT NULL DEFAULT 'ireland',
    postcode        TEXT,
    tariff_name     TEXT,                           -- e.g. "BGE Free Saturday"
    tariff_start    DATE,
    tariff_end      DATE,
    day_rate_eur    NUMERIC(6,4),
    night_rate_eur  NUMERIC(6,4),
    peak_rate_eur   NUMERIC(6,4),
    has_solar       BOOLEAN DEFAULT FALSE,
    has_ev          BOOLEAN DEFAULT FALSE,
    has_heat_pump   BOOLEAN DEFAULT FALSE,
    hardware_id     TEXT,                           -- Eddi serial / hub serial
    btm_detected    JSONB,                          -- BTM asset inference output (E-25)
    onboarded_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Row-Level Security: users can only see their own household
ALTER TABLE households ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own household" ON households
    USING (user_id = auth.uid());

-- ---------------------------------------------------------------
-- meter_readings — 30-min interval HDF data (from CSV upload or P1 port)
-- ---------------------------------------------------------------
CREATE TABLE meter_readings (
    id              BIGSERIAL,
    household_id    UUID REFERENCES households(id) ON DELETE CASCADE,
    recorded_at     TIMESTAMPTZ NOT NULL,
    import_kwh      NUMERIC(8,4) NOT NULL,          -- grid import
    export_kwh      NUMERIC(8,4) DEFAULT 0,         -- solar export
    PRIMARY KEY (household_id, recorded_at)
);
SELECT create_hypertable('meter_readings', 'recorded_at');  -- TimescaleDB

-- ---------------------------------------------------------------
-- predictions — daily H+24 forecast output (one row per household per day)
-- ---------------------------------------------------------------
CREATE TABLE predictions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id    UUID REFERENCES households(id) ON DELETE CASCADE,
    issued_at       TIMESTAMPTZ NOT NULL,            -- when the model ran (~16:00)
    forecast_date   DATE NOT NULL,                   -- the day being forecast
    p10_kwh         NUMERIC[],                       -- 24-element arrays
    p50_kwh         NUMERIC[],
    p90_kwh         NUMERIC[],
    model_version   TEXT,                            -- ModelRegistry version_id
    UNIQUE (household_id, forecast_date)
);
SELECT create_hypertable('predictions', 'issued_at');

-- ---------------------------------------------------------------
-- recommendations — ControlEngine output per household per day
-- ---------------------------------------------------------------
CREATE TABLE recommendations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id    UUID REFERENCES households(id) ON DELETE CASCADE,
    prediction_id   UUID REFERENCES predictions(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    target_hour     INT NOT NULL,
    action          TEXT NOT NULL,                   -- ActionType enum value
    confidence      NUMERIC(4,3),
    reasoning       TEXT,
    user_message    TEXT,                            -- Rory-voice plain English
    p50_kwh         NUMERIC(8,4),
    price_eur_kwh   NUMERIC(6,4),
    solar_wh_m2     NUMERIC(8,2),
    dry_run         BOOLEAN DEFAULT FALSE
);

-- ---------------------------------------------------------------
-- recommendation_outcomes — did the user act on the advice?
-- ---------------------------------------------------------------
CREATE TABLE recommendation_outcomes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_id   UUID REFERENCES recommendations(id) ON DELETE CASCADE,
    household_id        UUID REFERENCES households(id),
    outcome             TEXT NOT NULL               -- 'accepted' | 'ignored' | 'partial'
                        CHECK (outcome IN ('accepted', 'ignored', 'partial')),
    recorded_at         TIMESTAMPTZ DEFAULT NOW(),
    savings_eur         NUMERIC(8,4),               -- calculated post-hoc from meter data
    UNIQUE (recommendation_id)                      -- one outcome per recommendation
);

-- ---------------------------------------------------------------
-- tariff_changes — investor North Star metric (P-17)
-- ---------------------------------------------------------------
CREATE TABLE tariff_changes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id    UUID REFERENCES households(id) ON DELETE CASCADE,
    changed_at      TIMESTAMPTZ DEFAULT NOW(),
    old_tariff      TEXT,
    new_tariff      TEXT,
    attributed_to   TEXT DEFAULT 'app'              -- 'app' | 'manual' | 'unknown'
);
```

**Customer tier view (P-16) — materialised on demand:**
```sql
CREATE VIEW customer_tiers AS
WITH stats AS (
    SELECT
        h.id                                                    AS household_id,
        h.user_id,
        COUNT(ro.id) FILTER (WHERE ro.outcome = 'accepted')::FLOAT
            / NULLIF(COUNT(ro.id), 0)                          AS acceptance_rate,
        MAX(ro.recorded_at)                                     AS last_active,
        COUNT(tc.id)                                            AS tariff_changes
    FROM households h
    LEFT JOIN recommendations rec ON rec.household_id = h.id
    LEFT JOIN recommendation_outcomes ro ON ro.recommendation_id = rec.id
    LEFT JOIN tariff_changes tc ON tc.household_id = h.id
    GROUP BY h.id, h.user_id
)
SELECT
    household_id,
    user_id,
    acceptance_rate,
    last_active,
    tariff_changes,
    CASE
        WHEN acceptance_rate >= 0.70 AND last_active >= NOW() - INTERVAL '14 days'
            THEN 'tier_1_optimiser'
        WHEN tariff_changes > 0
            THEN 'tier_3_switcher'
        WHEN last_active >= NOW() - INTERVAL '30 days'
            THEN 'tier_2_tracker'
        ELSE 'tier_4_dormant'
    END AS tier
FROM stats;
```

---

## 5. Auth — Supabase Auth

**Free, included with Supabase PostgreSQL.**

- Magic link (email) — no password to forget, high conversion for energy app users
- Google OAuth — single sign-on for low-friction onboarding
- Row-Level Security (RLS) policies enforce data isolation at the DB layer — not just the API layer
- JWT tokens validated by FastAPI's `Depends(get_current_user)` dependency

---

## 6. Caching — Redis (via Upstash)

**Purpose:** Cache the daily H+24 prediction so the FastAPI `/predict` endpoint is fast for UI loads.

```
TTL:        23 hours (prediction re-runs at 16:00 daily)
Key:        predict:{household_id}:{forecast_date}
Backend:    Upstash Redis (serverless, free tier: 10k commands/day)
            OR local Redis via Docker Compose for Mac Mini phase
```

- At 100 households: 100 predictions × 24 floats × 3 bands = tiny (< 1MB total)
- At 10,000 households: still < 100MB — cache TTL strategy unchanged
- Prevents re-running LightGBM inference per page load (inference = 2ms but avoids disk reads)

---

## 7. Scheduling — APScheduler

**Daily batch prediction run at 16:00 (post-SEMO day-ahead prices).**

```python
# deployment/scheduler.py (to be created — D-23)
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(
    run_daily_predictions,      # calls run_pipeline logic per household
    trigger="cron",
    hour=16, minute=0,
    timezone="Europe/Dublin",
    id="daily_prediction_batch",
)
scheduler.start()
```

**At scale (Phase 3 — 1000+ households):** Replace APScheduler with AWS EventBridge → Lambda → SQS fan-out. APScheduler is correct for Mac Mini + App Runner phases.

---

## 8. Notifications — WhatsApp Business API + Email

**Morning brief delivery (P-14 / Phase A):**

| Channel | Tool | Cost | Status |
|---------|------|------|--------|
| WhatsApp | Meta WhatsApp Business API via Twilio | ~€0.03/message | Phase A planned |
| Email | Resend (modern SendGrid replacement) | Free: 3k/month | Implement now — no cost |
| Push (web) | Web Push API (built into Next.js PWA) | Free | Phase 2 |
| SMS | Twilio SMS | ~€0.04/SMS | Fallback only |

**Implementation:** The morning brief content is already generated by `deployment/live_inference.py`. Notification channels are delivery adapters — they consume the same structured JSON output.

---

## 9. Operator Dashboard — Grafana + Streamlit

**Two separate internal tools, each for a different purpose.**

### Grafana — Infrastructure & ML Monitoring
```
Hosted:     localhost:3000 (Docker Compose, Mac Mini)
Data source: PostgreSQL (direct connection to Supabase or local PG)
Dashboards:
  - Model Drift (rolling 7-day MAE vs training MAE, PSI per feature)
  - Per-Household Consumption (time series from meter_readings)
  - Control Actions (JSONL audit log → PostgreSQL via Fluent Bit)
  - System Health (/health endpoint scrape → Prometheus → Grafana)
```

**Why Grafana over InfluxDB + Grafana:**
InfluxDB as a *database* adds complexity. Grafana connects directly to PostgreSQL — no extra service. TimescaleDB turns Postgres into a capable time-series store. One DB, one connection.

**Why Grafana over Plotly Dash:**
Grafana is pre-built for monitoring (alerting, annotations, user management built in). Dash requires you to write every dashboard in Python. Use Grafana for operations; use Plotly charts *inside* the Next.js app for consumer-facing visualisation.

### Streamlit — Internal Analytics & Research
```
Purpose:    Ad-hoc data exploration, paper figure generation, model debugging
Not for:    Consumer-facing product (too slow, not mobile-friendly)
Run:        streamlit run scripts/explore.py (local, not deployed)
```

Use Streamlit for:
- Building the Home Plan Score visualisation quickly during development
- Exploring drift reports, SHAP values, feature importance
- Research / paper figure iteration

---

## 10. Local Hosting — Mac Mini M5 (Phase 1)

**The Mac Mini M5 is a genuine production host for a beta with ≤ 50 users.**

```
Hardware:   Mac Mini M5, 16GB RAM, 512GB SSD
OS:         macOS Sequoia
HTTPS:      Caddy (auto-HTTPS via Let's Encrypt, dead-simple config)
            OR Cloudflare Tunnel (free, no port-forwarding needed)
Containers: Docker Desktop for Mac (Docker Compose)
Services (Docker Compose):
  - api          FastAPI + Uvicorn (port 8000)
  - frontend     Next.js (port 3000)
  - db           PostgreSQL 16 + TimescaleDB (port 5432)
  - redis        Redis 7 (port 6379)
  - grafana      Grafana OSS (port 3001)
  - caddy        Reverse proxy (ports 80/443)
```

**Cloudflare Tunnel (free):**
```bash
# Install cloudflared once
brew install cloudflare/cloudflare/cloudflared

# Authenticate and create tunnel
cloudflared tunnel login
cloudflared tunnel create sparc-energy

# Route: sparc.yourdomain.com → localhost:3000 (Next.js)
#        api.sparc.yourdomain.com → localhost:8000 (FastAPI)
cloudflared tunnel run sparc-energy
```
No open ports on your router. Cloudflare handles TLS. Works with any domain.

**Resource envelope (Mac Mini M5 idle load):**
```
PostgreSQL:     ~200MB RAM
Redis:          ~50MB RAM
FastAPI:        ~150MB RAM (+ model in memory ~80MB)
Next.js:        ~120MB RAM
Grafana:        ~200MB RAM
Total:          ~800MB / 16GB = 5% RAM — vast headroom
```

**Scale limit before migrating to AWS:** ~500 households. At that point the bottleneck is the daily batch (500 predictions × 2ms = 1s) and PostgreSQL write throughput — not RAM or CPU.

---

## 11. Production Hosting — AWS App Runner (Phase 3)

*Existing Dockerfile + apprunner.yaml (commit a15d297) already targets this path.*

```
Backend:    AWS App Runner (FastAPI container, auto-scale 1–10 instances)
Database:   AWS RDS PostgreSQL 16 + TimescaleDB (eu-west-1, Multi-AZ)
Cache:      Upstash Redis (serverless, no VPC needed)
Frontend:   Vercel OR Cloudflare Pages (Next.js, global CDN)
CI/CD:      GitHub Actions → ECR → App Runner auto-deploy
Secrets:    AWS Secrets Manager
```

**Migration path from Mac Mini:** Identical Dockerfile. Update `DATABASE_URL` and `REDIS_URL` env vars. Zero code changes needed.

---

## 12. Microsoft vs Google vs AWS

**Short answer: AWS + Supabase + Vercel. Avoid vendor lock-in to Microsoft or Google stacks.**

| Stack | Verdict |
|-------|---------|
| **Microsoft Azure + Copilot Studio** | ❌ Azure AI is excellent but locked to Microsoft's ecosystem. Copilot Studio is for enterprise chatbots, not energy apps. Over-engineered for this stage. |
| **Google Cloud + Firebase + Vertex AI** | ⚠️ Firebase is a real option but NoSQL Firestore is wrong for structured energy data. Vertex AI adds cost without benefit (we run LightGBM locally). |
| **AWS** | ✅ Chosen. App Runner + ECR is the smoothest path from Mac Mini to cloud. eu-west-1 is Ireland (GDPR-native). Existing Dockerfile already configured. |
| **Supabase** | ✅ Managed PostgreSQL with zero vendor lock-in (standard SQL — portable to RDS with a connection string change). |
| **Vercel** | ✅ Best Next.js deployment. EU region available (Frankfurt). Free hobby tier covers beta. |

**"Google Stitch":** Not a Google product. If you saw this referenced somewhere, it may be:
- **MongoDB Atlas (formerly MongoDB Stitch)** — NoSQL, not our choice
- **Databricks / Stitch Data** — ETL pipeline tool (overkill for this scale)
- **Google Firebase** — addressed above

---

## 13. Full Stack Summary

```
┌─────────────────────────────────────────────────────────────────┐
│  CONSUMER LAYER                                                 │
│  Next.js 15 PWA + TypeScript + Tailwind + shadcn/ui + Tremor   │
│  ↓ HTTPS via Caddy / Cloudflare Tunnel                         │
├─────────────────────────────────────────────────────────────────┤
│  API LAYER                                                      │
│  FastAPI + Uvicorn + APScheduler                                │
│  Auth: Supabase JWT → FastAPI dependency                        │
│  Cache: Redis (TTL 23h per household prediction)               │
├─────────────────────────────────────────────────────────────────┤
│  ML LAYER                                                       │
│  LightGBM H+24 (ModelRegistry — CANDIDATE/ACTIVE/RETIRED)      │
│  DriftDetector (KS + PSI) → auto-check post-training (E-22)    │
│  ControlEngine (Rule-based) → JSONL audit log (E-20)           │
├─────────────────────────────────────────────────────────────────┤
│  DATA LAYER                                                     │
│  PostgreSQL 16 + TimescaleDB (Supabase managed)                │
│  Tables: households, meter_readings, predictions,               │
│          recommendations, outcomes, tariff_changes             │
├─────────────────────────────────────────────────────────────────┤
│  OPERATOR LAYER (internal)                                      │
│  Grafana → PostgreSQL (drift, consumption, model health)        │
│  Streamlit → ad-hoc analytics + paper figures                  │
├─────────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE (Phase 1: Mac Mini M5)                         │
│  Docker Compose · Caddy · Cloudflare Tunnel · GitHub Actions   │
│  (Phase 3: AWS App Runner + RDS + Vercel)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 14. Phase Delivery

| Phase | Milestone | Stack additions |
|-------|-----------|----------------|
| **Phase 1** | Single user on Mac Mini M5 | FastAPI (existing) + SQLite + CLI morning brief + Streamlit internal dash |
| **Phase 2** | Consumer beta (≤ 50 households) | + Next.js PWA + Supabase PostgreSQL + Redis + Grafana + Cloudflare Tunnel |
| **Phase 3** | Scale (1000+ households) | + AWS App Runner + RDS + Vercel + Upstash + EventBridge scheduler |

---

*See `ROADMAP.md` items D-23 through D-26 for delivery tickets. See `docs/adr/` for architectural decision records (ADR-011 forthcoming for this tech stack decision).*
