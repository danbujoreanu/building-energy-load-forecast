# Competitive Landscape Analysis

**Last updated:** 2026-03-15
**Purpose:** Investor pitch preparation, Business Model Canvas inputs, differentiation narrative

---

## Institutional / Research Projects (Ireland)

These are not direct commercial competitors but occupy overlapping space. Institutionally backed, slow-moving, validated the market exists.

### RENEW
**Status:** Irish research project, supported by researchers, recognised by SEAI/SFI/similar bodies.
**Model:** Research-led. Not a consumer product. Likely focused on grid-level or academic energy data analysis.
**Assessment:** Validates that the Irish energy AI space is taken seriously at institutional level. Their slow pace is Dan's window — consumer UX and speed to market are the differentiator. Potential future partner (academic credibility + commercial product = complementary).
**Action:** Monitor. If RENEW researchers publish or present, engage — potential co-author or advisory relationship.

### elec-tariffs.ie
**Status:** Live Irish site. Tariff comparison / information resource.
**Model:** Informational — tariff data and comparison. No AI forecasting, no load prediction, no household optimisation.
**Assessment:** Validates consumer interest in Irish electricity tariffs. Closest to the "energy plan recommendation" feature (Section 4 of APP_PRODUCT_SPEC). Not a threat to the AI forecasting core — they provide information, we provide intelligence and action.
**Differentiator:** elec-tariffs.ie tells you what tariffs exist. Our product tells you which tariff fits your actual consumption pattern and schedules your appliances accordingly.
**Potential:** Could be a distribution partner (recommend our device to users who want to go beyond comparison to optimisation).

---

## Direct Competitors

### Loop (loop.homes)
**Status:** UK only. Recently acquired by Procode (UK energy tech).

| Dimension | Loop | Our Product |
|-----------|------|-------------|
| Market | UK | Ireland (first mover) |
| Hardware | App only | P1 port adapter + app |
| Pricing | Free | €99-149 device + €3.99/month |
| Forecast | 24h carbon intensity window | H+24 load + price + solar forecast |
| Heat pump | No | Yes (core use case) |
| LLM advisor | No | Phase 2 (Claude API) |
| Energy plan rec | No | Yes (tariff compatibility match) |
| ML model | Unknown | LightGBM 4.0 kWh MAE (R²=0.975) |
| Academic backing | None | AICS '25 paper + journal paper |

**Key Loop features (for awareness):**
- Real-time grid carbon intensity + 24h renewable forecast (EcoMeter)
- Phantom load / standby detection
- "Turn Down and Save" demand response rewards
- Loop Optimise AI (home battery optimisation)
- 15% average energy reduction claim (~£250/year)
- Press: BBC, ITV, Guardian, Times — strong PR machine

**Their gap is our wedge:** Loop is carbon-focused, app-only, UK-centric, no hardware, no Irish market, no heat pump optimisation, no household load forecast. Their model relies on UK Smart Energy GB data infrastructure (SMETS2 meters, IHD). This doesn't translate to Ireland without significant rework.

---

### Climote (climote.com)
**Status:** Ireland + UK. Hardware thermostat controller.

| Dimension | Climote | Our Product |
|-----------|---------|-------------|
| Hardware | Smart thermostat (~€100) | P1 port adapter |
| AI/ML | None | LightGBM load forecast |
| Forecast | No | H+24 load + price + solar |
| Energy plan | No | Yes |
| Heat pump | Basic scheduling only | Optimised scheduling with forecasting |
| Price | ~€100 one-off | €99-149 + €3.99/month |

**Note:** Climote's heating control is useful but dumb — it doesn't know when electricity is cheap or when solar will be generating. Our product adds the intelligence layer.

---

### Tibber (tibber.com)
**Status:** Norway, Sweden, Germany, Netherlands, Austria, Spain. NOT in Ireland.
**Hardware:** Tibber Pulse — P1/HAN port adapter, same concept as our device.
**Model:** App + dynamic tariff (Tibber is the supplier). They are the energy supplier AND the analytics layer.
**Differentiator vs Tibber:** We are supplier-agnostic. We work with any Irish tariff. Tibber requires customers to switch supplier (not yet possible in Ireland). Our device is a pure analytics layer — no supplier relationship risk.
**Risk:** If Tibber enters Ireland (possible post-CRU dynamic pricing mandate, 2026+), they are a well-funded competitor. Watch them closely. Our moat: first-mover, local regulatory knowledge, academic validation, SEAI partnership potential.

---

### Viotas (viotas.com)
**Status:** Ireland. B2B only.
**Model:** Demand flexibility aggregator — pays businesses (LEAP participants) to reduce demand during grid stress events.
**Not a direct competitor:** Different customer (enterprise, not residential), different model (grid flexibility payments, not household savings). Potential partner: Viotas aggregates demand response from large consumers; we could serve the residential side of the same demand-response stack.

---

### Hive (hivehome.com)
**Status:** UK + Ireland. Owned by British Gas / Centrica.
**Products:** Smart thermostat, EV charger, solar/battery management, Hive+ subscription.
**Hive+ plan:** AI-driven energy optimisation, demand shifting, solar + battery arbitrage.
**Threat level:** Medium. Hive has brand recognition and existing Irish customer base. But they are tethered to their own hardware ecosystem and require British Gas relationship. Our product is hardware-agnostic and supplier-neutral.

---

### Shelly / Tapo / Meross (smart plug ecosystems)
**Status:** Global.
**Not competitors but integration targets:** These platforms provide the actuator layer (smart plugs controlling appliances). Our product provides the intelligence layer. The right relationship is integration/partnership, not competition.

---

## Porter's Five Forces

### 1. Threat of New Entrants — MEDIUM-HIGH
- Low software barriers: any good ML team could replicate the forecast model
- High credibility barriers: academic backing (AICS paper, journal), regulatory relationships (SEAI, CRU) take time to build
- Hardware creates switching costs once installed
- CRU dynamic pricing trigger (June 2026) will attract UK/EU incumbents to Ireland — move fast

### 2. Bargaining Power of Buyers — MEDIUM
- Individual consumers have low switching costs (uninstall app, unplug device)
- But: personalised model trained on their data creates stickiness (30-day learning phase → household-specific model)
- €3.99/month is a low-friction subscription — equivalent to one coffee

### 3. Bargaining Power of Suppliers
- Hardware: Raspberry Pi / ESP32 commodity components — low power
- Cloud: AWS, GCP, Azure all viable — no lock-in
- Data: OpenMeteo (free), SEMO (public), ESB P1 port (no supplier relationship) — low dependency
- LLM API: Claude / OpenAI — substitutable — low power

### 4. Threat of Substitutes — MEDIUM
- Manual tariff comparison (bonkers.ie, switcher.ie) — addresses plan selection but not optimisation
- Smart home platforms (Google Home, Apple Home) — scheduling without load forecasting
- Energy supplier apps (Electric Ireland, Bord Gáis) — consumption history but no AI optimisation
- None of these combine forecast + schedule + LLM in an Ireland-specific package

### 5. Industry Rivalry — LOW (now) → HIGH (post-2026)
- Currently: no direct Irish competitor with AI load forecasting
- Post-CRU mandate (June 2026): Tibber, Loop, Hive likely to consider Irish expansion
- Window of opportunity: ~18 months to establish brand, SEAI partnerships, and customer base before funded incumbents arrive

---

## Business Model Canvas Inputs

| Block | Content |
|-------|---------|
| **Value Proposition** | "Your home learns when electricity is cheap and acts on it. Save €200-400/year on electricity — more if you have a heat pump." |
| **Customer Segments** | (1) Heat pump owners on TOU tariffs; (2) Solar PV homeowners; (3) EV owners; (4) Energy-aware 30-55 homeowners on smart tariff |
| **Channels** | Direct (web + App Store); SEAI partnership (Home Energy Kits programme); Solar installer partnerships; Comparison sites (bonkers.ie) |
| **Customer Relationships** | Self-serve onboarding (P1 plug + app); weekly digest (low friction); LLM advisor (Phase 2); community/forum |
| **Revenue Streams** | Device: €99-149 one-off; Subscription: €3.99/month; B2B: fleet dashboard for councils/housing bodies; Affiliate: tariff referrals |
| **Key Resources** | ML pipeline (LightGBM, 0.975 R²); AICS academic credibility; P1 port hardware design; SEMO/ESB API integrations |
| **Key Activities** | Model retraining (monthly); SEMO/weather data pipeline (daily); Customer support; Regulatory monitoring (CRU) |
| **Key Partnerships** | SEAI (grant programme alignment); MyEnergi (eddi/Zappi API for heat pump control); Solar installers (upsell channel); EirGrid (carbon intensity data) |
| **Cost Structure** | AWS hosting (~€50/month/1000 users at scale); Hardware COGS (~€30/unit at volume); Claude API (~€0.04/user/month Phase 2); Support |

---

## Product Naming (Working Options)

Working names to evaluate — no decision made yet:

| Name | Tone | Risk |
|------|------|------|
| GridSense | Technical, credible | Generic |
| Watt | Clean, minimal | Too similar to existing brands |
| Edify Energy | Educational | Not punchy |
| Volta | Irish-ish (Volta cinema), clean | Unrelated brand exists |
| Lumio | Bright, easy | Not energy-specific |
| Ember | Warm, energy | Ember (US thermostat startup) exists |
| **TBD** | — | Need user testing |

**Naming criteria:** Memorable; works as app name, company name, and device name; .ie domain available; no trademark conflicts in Ireland.

---

## Solar Partnership Note

User's partner operates a solar panel installation company. This is a strong distribution channel but requires arm's-length handling:
- The product recommendation engine must be provably independent (no referral kickback in the algorithm)
- Commercial arrangement (referral fee) documented and disclosed in T&Cs
- Consider: separate legal entities with a disclosed commercial agreement
- Opportunity: solar company installs panels → recommends our device to customers → device shows them their solar self-sufficiency in real time → virtuous loop
- This is the same model as Tibber Pulse being recommended by energy efficiency consultants in Norway

---

## Monitoring List

Track these for Ireland entry signals:
- Tibber: watch their EU expansion announcements and Irish App Store listing
- Loop: post-Procode acquisition strategy; any CRU engagement
- Hive+: Hive Ireland presence and Hive+ plan rollout outside UK
- ESB Networks API: CRU data access consultation papers (watch CRU website)
- SEAI Home Energy Kits 2026 call for applications

---

## Updated Analysis — April 2026

### Ento.ai (ento.ai)
**Founded:** 2019, Aarhus, Denmark | **Funding:** $3.6M seed (byFounders, Voyager, AURA Ventures)
**Platform:** 55,000+ buildings on platform

| Dimension | Ento.ai | Sparc Energy |
|-----------|---------|-------------|
| Target market | B2B: large commercial portfolios (50+ buildings) | B2C residential + Irish SME |
| Forecasting | No load prediction — anomaly detection only | H+24 load forecast, MAE 4.03 kWh |
| Device control | No actuation — insights and reporting only | Direct Eddi/device control |
| M&V | Automated IPMVP-standard (ESG/green bond reporting) | Not implemented |
| Data input | Utility meter feeds (no hardware) | P1/HDF CSV, Eddi API |
| Revenue | Annual SaaS, quote-only (by portfolio size) | €99 device + €3.99/month |
| Geography | Denmark, Italy, UK, Nordics | Ireland (first mover) |
| Threat level | **Low** — different segment | N/A |

**Assessment:** Ento is the right benchmark for Phase 3 if/when Sparc targets Irish commercial portfolios (local authorities, SEAI-funded buildings). Their strength is IPMVP-compliant M&V and portfolio analytics — neither of which Sparc needs for Phase 1. They solve reporting; we solve control.

**Competitive moat vs Ento if we enter commercial:**
- Sparc has active device dispatch (Ento is advisory only)
- Sparc's LightGBM forecast is more accurate than anomaly detection for demand-response scheduling
- Ento requires dedicated energy managers — Sparc is self-serve

---

### mySigen / Sigenergy (sigenergy.com)
**Status:** Global hardware manufacturer. Developer API public at developer.sigencloud.com.
**Hardware:** Residential/commercial solar + battery storage systems (€4,000–12,000 installed)

| Dimension | mySigen | Sparc Energy |
|-----------|---------|-------------|
| Hardware requirement | Sigenergy battery only | Any Irish household (no battery required) |
| Forecasting | Basic TOU scheduling (time-programmed) | H+24 ML forecast |
| AI features | "Sigen AI Insight" (plain language dispatch explanation) | Full ControlEngine + LLM advisor |
| API access | Public REST API, VPP/third-party integration supported | Own API |
| EV integration | Yes (OCPP for third-party chargers) | Phase 2 |
| Irish presence | No specific Irish push | First mover |
| Threat level | **Low** — hardware-locked, no Irish focus | N/A |

**Key insight from user:** A customer with 10 solar panels + 10kWh battery is largely self-sufficient in summer and can weather most tariff bands — the optimization value for Sparc is lower for this segment. **Customer segmentation implication:**

| Segment | Sparc Value | Priority |
|---------|------------|---------|
| Heat pump (no solar/battery) | HIGHEST — large electricity bill, can't self-generate | Tier 1 |
| EV + heat pump | HIGH — two large loads to schedule, dynamic tariff arbitrage | Tier 1 |
| Solar + no battery | HIGH — export timing optimization + consumption shift | Tier 2 |
| Solar + large battery (>10kWh) | MEDIUM — battery absorbs most arbitrage; value in cloudy season | Tier 3 |
| Standard household (no assets) | MEDIUM — demand shift value, smaller bills | Tier 2 |
| Commercial building (SME) | HIGH B2B — large bills, predictable patterns, budget for solutions | Tier 1 (Phase 2) |

**Sigenergy integration opportunity:** Their public API supports VPP-style control — Sparc could read Sigenergy battery SoC and solar generation via the developer API, making mySigen hardware owners a distinct user segment rather than an excluded one. See DAN-38 (battery scheduler).

---

### Tibber — Enhanced Analysis

**Updated threat model (April 2026)**
- Tibber's fastest Irish entry lever — Pulse P1 hardware — is blocked until ESB Networks activates P1 software (late 2026 at earliest)
- Irish retail supply licence: multi-year CRU process; no application reported
- Their product strength: spot-price pass-through (€5/month subscription, no kWh markup) + Home Assistant integration + EV smart charging ecosystem
- **Critical structural difference vs Sparc:** Tibber IS the electricity supplier. Sparc is supplier-agnostic. If Tibber enters Ireland, customers must switch supplier (a decision with inertia). Sparc works alongside existing BGE/EI/Energia contracts.
- **If Tibber enters Ireland post-2027:** They become a Medium-High threat for tech-forward EV owners. Our moat: (1) Irish regulatory relationships (CRU/SEAI), (2) heat pump optimisation (Tibber's control is EV-focused), (3) load forecasting (Tibber optimises on *price*, not on *predicted demand*), (4) SMDS ESCO registration gives us automatic data access they'd also need to apply for.

---

## Commercial Building Segment — Competitive Landscape

For Phase 2+ commercial expansion (Irish offices, schools, SME), the competitive field is different:

| Company | Focus | Notes |
|---------|-------|-------|
| **Ento.ai** | Portfolio anomaly detection, IPMVP M&V | No control, B2B only |
| **Schneider Electric EcoStruxure** | Enterprise BMS, large commercial | €50k+ contracts, not SME |
| **Siemens Desigo CC** | Enterprise BMS | Same tier as Schneider |
| **EpiSensor (episensor.com)** | Irish B2B IoT, P1 + demand response | 970 customers, 25k devices — potential partner |
| **Viotas** | Demand flexibility aggregation (LEAP) | Pays businesses, not residential |
| **Enertiv / Willow** | US-focused commercial building analytics | No Irish presence |

**Sparc's commercial entry wedge:** SME segment (50–5,000 sqm: GP surgeries, small offices, schools) — too small for Schneider/Siemens, too tech-light for Ento's portfolio focus. EpiSensor is the closest Irish B2B IoT player — evaluate as a channel partner, not a competitor.
