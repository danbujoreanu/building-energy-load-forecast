# Production Decisions — Locked
*Do not re-debate these. They were decided with full context. Reference the session if you need to understand why.*

---

## Inference
- **Model**: LightGBM only. Not ensemble (marginal gain, added complexity). Not DL.
- **Cadence**: H+24 at 16:00 daily (post-SEMO prices). H+1 hourly for real-time.
- **Retraining**: Monthly, rolling 24-month window. Drift trigger: 7d MAE > 1.5× training MAE.
- **Cold start**: 30 days population-average → household-specific.
- **Feedback signal**: Observed consumption ONLY. NOT user action compliance (selection bias + gamification risk).

## Product
- **Residential first, then SME**. Not commercial/industrial until residential validated.
- **Irish market primary**. Norway is research, not product.
- **Pricing**: €99–149 device + €3.99/month subscription.
- **Heat pump angle**: Strongest commercial frame. Ireland 400k target by 2030.
- **No seasonal battery storage advice**: Batteries store 1–2 days ONLY. Never suggest storing summer solar for winter.
- **Loop Optimise validates direction**: Loop (UK) has launched AI battery HEMS (48 adjustments/day, £360/yr savings). Confirms market is moving from monitoring → active control. Our Phase 2 battery arbitrage + Eddi control roadmap is correct.
- **Phantom load detection**: Do NOT build manual "walk round the house" UX like Loop Snoop. Build ML-based or Eddi-aware detection — that is the differentiator.
- **Demand response**: "Turn Down and Save" (Loop UK) = earn from grid operators for demand reduction. Irish equivalent: EirGrid/SEMO flexibility products. Future opportunity post-MVP, not MVP priority.

## Data Access (Ireland)
- **MVP**: Manual ESB CSV upload (no hardware, no permission needed). Works now.
- **Phase 2**: P1 port hardware adapter (Slimmelezer+ equivalent, ~€25). Customer self-install.
- **CRU Smart Meter Data Access Code (CRU202517)**: PUBLISHED 19/02/2025 — framework is law. ESB Networks (DSP) builds the Smart Meter Data System (SMDS). We qualify as an ESCO (Eligible Party). Free access once SMDS live. 30-min interval data, 24 months history, 3-click consent flow. File ESCO application when SMDS opens for testing. Full analysis: `docs/regulatory/SMART_METER_ACCESS.md`.
- **No CT clamp required**: Eddi API (`che` field) gives daily diversion. Total solar = export + `che`.

## Eddi Control
- **Monitor-only by default**. No setpoint changes without explicit user opt-in.
- **19:45 Eddi boost**: Do NOT move to 23:00. Water needed at 09:30. If tank full from solar, boost self-suppresses.
- **Saturday boosts** (09:15+14:00): Do NOT touch. These are the primary free-window drivers.

## Technology
- **Python/FastAPI** for backend. Not Node, not Go.
- **LightGBM inference** in-process (<10ms). No separate model server needed at MVP scale.
- **AWS eu-west-1 (Ireland)**: GDPR Art. 44 adequacy. No raw data to LLM APIs.
- **Phase 7 deployment**: Docker → ECR → AWS App Runner.

## Journal
- **Target**: Applied Energy or Energy and Buildings (both Q1).
- **Do NOT backport H+24 results** to AICS 2025 Springer CCIS paper — different venues.
- **AICS foundation** is locked. Journal paper builds on it with Oslo + DM tests + quantile + responsible AI.

## PhD
- Full-time preferred; open to self-funded.
- Best fit supervisors: Aoife Foley (DCU/Queen's Belfast), Brian Ó Gallachóir (UCC), Kazempour group (DTU).
- Strategy: journal paper → 2 more papers → PhD proposal.
- Paul Cuffe (UCD EE): re-contact viable for full-time supervision.
