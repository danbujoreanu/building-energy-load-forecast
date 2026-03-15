# Competitive Landscape Analysis

**Last updated:** 2026-03-15
**Purpose:** Investor pitch preparation, Business Model Canvas inputs, differentiation narrative

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
