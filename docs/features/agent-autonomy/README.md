# Sparc Energy — Agent Capability Tiers

**Status:** Product reference | **Last updated:** 2026-04-20 | **Linear:** DAN-40, DAN-22, DAN-38

---

## Why This Matters

Sparc Energy's product roadmap is structured around **progressive agent autonomy**. Each level represents a deliberate design decision, not a technical limitation. The constraint is trust and regulatory readiness, not engineering capability.

> Interview narrative: *"We intentionally shipped Level 1 first. Our MVP is a Level 1 assistant — it observes, forecasts, and advises. We have Human-in-the-Loop at Level 2 specifically because the EU AI Act, GDPR, and our own AI Impact Assessment require user consent before any autonomous control action executes against a physical device in someone's home. The architecture already supports Level 3 — we've chosen not to enable it yet."*

---

## The Three Levels

| Level | Name | Sparc Feature | User role | Current status |
|-------|------|--------------|-----------|---------------|
| **L1** | Assistant | Morning Brief | Reads report, acts manually | ✅ **LIVE** (Phase 6) |
| **L2** | Co-Pilot | Energy Planner | Reviews schedule, clicks Approve | 🗓 Sprint 3–4 (DAN-22, DAN-38) |
| **L3** | Autonomous Agent | Smart Control Engine | Monitors log, intervenes if needed | 🔮 Q3 2026+ (DAN-40) |

---

## Level 1 — Morning Brief (Assistant)

**Current implementation.** The system observes, forecasts, and advises. The human decides.

```
[LightGBM H+24 Forecast] → [Morning Brief CLI] → [WhatsApp/email report]
       ↑                                                       ↓
  [Open-Meteo]                                        [User reads, acts manually]
  [ESB Smart Meter]
```

**What it does:**
- Predicts next 24h household energy consumption (MAE 4.03 kWh, R²=0.975)
- Identifies cheapest load window given BGE tariff + tomorrow's weather
- Shows Eddi diversion opportunity (solar + hot water)
- No automated action — human runs schedule manually

**Technical reality:** `deployment/live_inference.py` → `scripts/morning_brief.py`

**Design decision:** L1 first because the free-tier validation (€178/year identified) doesn't require automation. Trust must be built before control is granted.

---

## Level 2 — Energy Planner (Co-Pilot)

**Target: Sprint 3–4 (May–June 2026).** The system proposes a schedule; the user approves before any device action executes.

```
[LightGBM Forecast] → [Schedule Optimiser] → [Proposed Schedule UI]
[Dynamic Pricing API]                                    ↓
[Eddi API]                               [User: Approve / Modify / Reject]
                                                         ↓
                                         [Eddi executes schedule]
                                                         ↓
                                         [Audit log: JSONL, EU AI Act Art.52]
```

**What it adds over L1:**
- Pulls day-ahead dynamic price signal (BGE/EI/Energia — post June 2026 CRU mandate)
- Proposes optimal Eddi schedule (e.g. "Heat at 02:00–04:00, avoid 17:00–19:00")
- Requires explicit user approval before any Eddi command is sent
- Full audit trail: every proposed+executed action logged to JSONL

**Why HITL (Human-in-the-Loop):**
- **Regulatory:** EU AI Act Article 52 transparency requirements for automated energy control
- **Safety:** A wrong schedule in winter (miscalculated tank capacity, unexpected guests) has real household impact
- **Trust building:** Users must develop confidence in 30+ correct decisions before considering Level 3

**Key metric:** % of proposed schedules approved without modification (target: >80% = model is well-calibrated to user preferences)

---

## Level 3 — Smart Control Engine (Autonomous Agent)

**Target: Q3/Q4 2026+.** The system acts autonomously. The human monitors and can override.

```
[LightGBM Forecast] → [Decision Engine] ──→ [Eddi: HEAT_NOW / DEFER_HEATING]
[Real-time Price Feed]                   ├──→ [Audit log + EU AI Act report]
[Occupancy signals]                      └──→ [Push notification: "Acted at 02:15"]
                                                          ↓
                                              [User: Override if needed]
```

**What changes from L2:**
- No approval step — system executes within pre-set guardrails
- User configures bounds: "Never heat during 17:00–19:00", "Always maintain 55°C floor"
- Post-hoc notification: "I shifted your hot water to 02:00 — saved €0.31"
- Monthly report: total savings, actions taken, override count

**Why not yet:**
1. CRU dynamic pricing mandate only live June 2026 — no real price signals before then
2. Need 90+ days of L2 approval data to validate model confidence
3. GDPR legitimate interest basis needs clear consent flow for automated IoT control
4. P1 port real-time data stream needed for closed-loop feedback (target: late 2026)

**Guardrails that ALWAYS apply at L3:**
- Tank temperature floor: never drop below 50°C
- Peak rate lockout: never execute non-critical loads Mon–Fri 17:00–19:00
- Daily cost cap: never schedule actions that increase daily bill by >€0.50
- Emergency override: one tap in app cancels all autonomous actions

---

## Design Principles

### 1. Deterministic core, LLM at the edges
- **LightGBM** handles all forecasting — cheap, fast, interpretable, no hallucination risk
- **LLM (Claude haiku-4-5)** used only for natural language output (morning brief narrative, user-facing explanations)
- This distinction is important: an LLM making direct scheduling decisions would be inappropriate at L2/L3

### 2. Explain before you act
Every Level 2+ action must be explainable in plain English:
> *"Scheduling Eddi to heat at 02:00–04:00 because tonight's rate drops to 29.65c (Night rate) vs tomorrow's daytime 40.34c. Expected saving: €0.31."*

### 3. Fail safe, not fail open
If the forecast confidence is low, the dynamic price feed is unavailable, or the Eddi API is unreachable — **do nothing**. Never guess. Alert the user.

### 4. Audit everything
Every automated action at L2/L3 creates a JSONL audit entry:
```json
{
  "timestamp": "2026-06-15T02:00:00Z",
  "action": "HEAT_NOW",
  "trigger": "price_signal",
  "price_signal": 0.2965,
  "forecast_kwh": 0.55,
  "estimated_saving_eur": 0.31,
  "user_approved": false,
  "level": 3
}
```
This satisfies EU AI Act Article 52 transparency obligations for automated energy management systems.

---

## Interview Stories

### "Why LightGBM and not an LLM for control?"

> *"LLMs hallucinate. An LLM that hallucinates a price signal or misunderstands a boiler's thermal inertia could run a heat pump at peak tariff — costing the user money instead of saving it. LightGBM gives us deterministic, interpretable, auditable predictions at 50ms per inference with no API cost. We use the LLM only where it belongs — natural language output for the morning brief. The decision engine is always ML, never generative AI."*

### "How did you decide your MVP autonomy level?"

> *"We shipped Level 1 deliberately. The morning brief proves the forecast is accurate — we've validated €178/year in identified savings on my own household. Users need 30–90 days of accurate advice before they'll trust an automated action on a device in their home. Level 2 requires HITL specifically because the EU AI Act and our own AI impact assessment require it for automated IoT control in residential settings. Level 3 won't ship until we have 90 days of L2 approval data showing >80% accept rate — that's our confidence threshold."*

### "What happens if your model is wrong?"

> *"At Level 1: nothing — the user decides. At Level 2: the user sees the proposed schedule and rejects it. At Level 3: we apply four guardrails — temperature floor, peak rate lockout, daily cost cap, and one-tap emergency override. The system fails safe: if the price feed is unavailable, we don't schedule anything. If the forecast uncertainty exceeds our threshold, we drop to L1 and alert the user."*

---

## Mapping to PM Interview Frameworks

### Which framework, when?

Use frameworks **situationally** — and name the switch in interviews. That signals MBA-level fluency.

| Context | Framework | Why |
|---------|-----------|-----|
| AI PM interview (system design round) | **DASME** | Built specifically for AI architecture interviews; "Architect" forces the diagram |
| Irish energy company / SEAI / ops conversation | **DMAIC** | Six Sigma lingua franca for process improvement |
| New product design with structured evidence | **DMEDI** | Design for Six Sigma — better than DMAIC for greenfield |
| Strategy/competitive discussion | **Porter + VRIN** | MBA canonical; see `docs/STRATEGY.md` |

Interview bridge: *"I used DASME to architect the ML pipeline — that's a new system design problem. But when I looked at customer onboarding friction, I switched to DMAIC — that's a process improvement problem. Different tools for different questions."*

---

### DASME Applied to Energy Planner (L2)

| DASME Stage | Energy Planner Answer |
|-------------|----------------------|
| **Define** | Problem: households can't manually optimise against 30-min dynamic pricing. Solution: co-pilot that proposes + executes on approval. |
| **Architect** | LightGBM → Optimiser → Approval UI → Eddi API → JSONL audit |
| **Specify** | LightGBM for scheduling (deterministic, cheap); Claude haiku-4-5 for explanation text (semantic). Response time <2s. |
| **Map** | Success: % schedules approved unchanged (>80%). Model drift: 7d MAE >1.5× threshold. Business: €/household/month saved. |
| **Edge Cases** | Price feed down → alert, no action. Forecast uncertainty high → alert. Eddi API timeout → retry ×3, then alert. Tank temp <50°C → override to HEAT_NOW. |

### DMAIC Applied to Smart Meter Onboarding (improving existing process)

> Use this framing when talking to a utility, SEAI, or operations-oriented interviewer.

| DMAIC Stage | Onboarding Answer |
|-------------|------------------|
| **Define** | Problem: 74% of Irish households not on TOU tariffs despite 95% benefiting (CRU202566). Define: reduce time-to-first-saving for new users. |
| **Measure** | Current: manual CSV upload, 10-minute setup, one tariff comparison. Baseline: €178/year identified but not acted on. |
| **Analyse** | Root cause: no automated data access (SMDS not live), no schedule recommendation, no approval workflow. Gap: L2 Co-Pilot not built yet. |
| **Improve** | SMDS integration → automated HDF pull; Energy Planner → one-tap schedule approval. |
| **Control** | % schedules approved, MAE drift monitoring, monthly savings report to user. |

---

## References
- `deployment/live_inference.py` — Level 1 implementation
- `src/energy_forecast/control/` — control engine (L2/L3 foundation)
- `docs/APP_PRODUCT_SPEC.md` — full product specification
- `docs/STRATEGY.md` — BMC, Porter 5 Forces, OKRs
- CRU202517 — Smart Meter Data Access Code (regulatory context for L3 data access)
- EU AI Act Article 52 — transparency for automated systems
