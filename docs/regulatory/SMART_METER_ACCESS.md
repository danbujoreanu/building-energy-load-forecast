# Smart Meter Data Access — Regulatory, Privacy & Go-to-Market

**Last updated:** 2026-04-22
**Relevant to:** Product commercialisation, Phase 2 hardware, privacy policy, GDPR compliance

---

## The core question

A third party (us) accessing customer smart meter data requires:
1. Customer consent (always)
2. A technical access mechanism
3. Regulatory alignment

All three are achievable. The path is staged.

---

## Technical access mechanisms in Ireland

### Option A — P1 port (local hardware, Phase 2)

Every ESB Networks smart meter (post-2019 NSMP rollout, now ~1M+ homes) has a P1 optical
port on the meter enclosure. This port:

- Is on the **customer's side** of the meter
- Outputs DSMR P1 telegrams (standard optical protocol)
- Requires **no permission from ESB Networks** — the customer's meter, the customer's data
- Emits real-time 30-min interval consumption data
- Can be read by a small hardware adapter (Raspberry Pi Zero 2W-class device, <€30 BOM cost)

**Our device**: plugs into the P1 port. Reads data locally. Processes on-device or sends to
our cloud backend (with customer consent). No meter tampering, no network intrusion, no
utility involvement.

This is identical to the model used by:
- **Tibber Pulse** — Norway/Sweden, same P1 concept
- **HomeWizard Energy** — Netherlands (P1 is mature there, 10+ years)
- **DSMR P1 USB cables** — widely available, ESB-compatible

**Activation note (UPDATED 2026-03-16)**: P1 ports are physically present on ~half of
installed meters but are **currently disabled in software**. ESB Networks confirmed
activation will roll out in **late 2026** (esbnetworks.ie). This is a ~12-month delay
from the CRU202579 consultation estimate (June 2025 paper said "end of 2025").

**Interim real-time option**: LED Pulse Reader — clips to the front face of any ESB smart
meter, counts LED blinks (1000 pulses = 1 kWh), works on all 1.9M meters TODAY.
Lower data quality than P1 but usable for real-time monitoring. Available from third
parties (€20–50). This is the pre-P1 hardware path for early adopters.

**Important implication**: The SMDS API (Path C, CRU202517) may go live BEFORE P1 port
activation. If ESB Networks builds the SMDS by mid-2026 (PR6-funded), we get 30-min
interval data via OAuth API before the P1 hardware port is even enabled. Path C may
effectively leapfrog Path B for most users.

### Option B — ESB Networks My Account CSV export (MVP, works today)

Customers can download their half-hourly consumption history (up to 24 months) as a CSV
from the ESB Networks My Account portal. No hardware needed.

**MVP approach**: Customer downloads and uploads their CSV to our app. We process it and
show insights. No real-time data, but sufficient for:
- Tariff recommendation
- Historical pattern analysis
- Feasibility calculations (solar payback, heat pump optimisation windows)
- Model training (cold start with household's own data)

**Limitation**: Manual, not real-time. Good for Phase 1 validation; not for day-ahead scheduling.

### Option C — CRU Smart Meter Data Access Code (CRU202517, PUBLISHED 19/02/2025)

**Status: Framework is LIVE. Technical infrastructure (SMDS) still being built by ESB Networks.**

The CRU published the Smart Meter Data Access Code (reference: CRU202517) on **19 February
2025**. This is the Irish equivalent of the UK's Smart Energy Code — the regulatory instrument
that will enable N3rgy-style third-party access in Ireland. It is already law.

**What CRU202517 establishes:**

| Element | Detail |
|---------|--------|
| **Data System Provider (DSP)** | ESB Networks (DSO) — builds and operates the Smart Meter Data System (SMDS) |
| **Data available** | 30-min interval import kW, 30-min export kW, 24h kWh registers, Day/Peak/Night registers, 24 months historical |
| **Eligible Parties** | Energy Service Companies (ESCOs), Aggregators, Electricity Suppliers, TSO, SEMO, Citizen/Renewable Energy Communities, Balancing Service Providers, and **"other third parties offering energy related services to Final Customers"** |
| **We qualify as** | **Energy Service Company (ESCO)** — explicitly listed: "a party offering energy-related services to the Final Customer, but not directly active in the energy value chain or the physical infrastructure itself" |
| **Access charges** | **FREE for Eligible Parties** (DSP recovers costs via price review process, not from third parties) |
| **Other Users** | Any party not in the above list may apply as "Other User" — DSP may charge "reasonable costs" |
| **Consent flow** | Customer grants "Active Permission" via DSP permission portal (online, free, revocable at any time) |
| **Permission log** | Customer can view all active permissions and data access log online, free — analogous to N3rgy consumer portal |
| **Application process** | Submit Appendix A application form to DSP; specify data items + use case + lawful basis |
| **Testing** | DSP must provide testing facilities free of charge before production access is granted |

**The N3rgy equivalent for Ireland:**
```
ESB smart meter → ESB Networks SMDS (Smart Meter Data System)
                      ↓ Permission API (Active Permission required)
                  Our IREGridConnector (apply as ESCO via Appendix A form)
                      ↓ REST API
                  Our app
```

**Consumer onboarding (future — once SMDS is live):**
1. Customer creates account on our app
2. Customer authorises via ESB Networks permission portal (grants "Active Permission")
3. Our app pulls 30-min interval data automatically — zero friction
→ Identical 3-click flow to Loop/N3rgy in the UK

**What the Code does NOT yet specify:**
- The "Code Access Procedure document" — detailed API specs — is still "to be developed by the DSP" (ESB Networks)
- Actual SMDS technical infrastructure is still being built
- Timeline for SMDS go-live: not stated in the Code; expected 2026, but CRU has not published a date

**Our action items:**
1. **Register as interested party** with CRU/ESB Networks for SMDS beta testing
2. **Prepare Appendix A application form** (template in CRU202517 Schedule 2) — we qualify as ESCO
3. **Monitor CRU Code Panel** meetings for SMDS launch timeline announcements
4. **Architect `IREGridConnector`** now (CSVConnector swap-out already planned in codebase)

**Key strategic insight:** The Code is published and our category (ESCO) is explicitly included.
When SMDS goes live, the onboarding friction drops from "5-minute CSV download" to "3-click consent
flow" — same as what Loop does in the UK via N3rgy. This is no longer a speculative 2026+ scenario;
it's a published regulatory instrument waiting for ESB Networks to build the infrastructure.

---

### Reference: How Loop does it in the UK (confirmed 2026-03-16)

Loop's "no device needed" story rests entirely on UK-specific infrastructure that Ireland does
not yet have. Understanding this is important for investor questions and competitive analysis.

**UK mechanism (DCC → N3rgy → Loop):**
```
SMETS2 meter → DCC (Data Communications Company — UK government data relay)
                    ↓ SEC Party API (accredited access)
              N3rgy Data Ltd (https://data.n3rgy.com)
              SEC = Smart Energy Code — UK regulatory framework
                    ↓ REST API
              Loop app
```

**Consumer onboarding (3 steps, ~2 minutes):**
1. Create Loop account
2. Accept N3rgy consent (GDPR-compliant; consumer portal at data.n3rgy.com/consumer)
3. Enter last 4 digits of IHD (In-Home Display) GUID/MAC/EUI → N3rgy verifies ownership
→ 30-minute interval data (import, export, tariff) available within 24 hours

**Why this doesn't work in Ireland:**
- **No DCC** — Ireland has no central smart meter data relay; ESB Networks holds data directly
- **No SEC** — the Smart Energy Code is a Great Britain-only regulatory instrument
- **No accredited intermediaries** — no N3rgy equivalent licensed to pull Irish meter data
- **CRU framework** — will eventually enable this model in Ireland, expected 2026+

**Conclusion:** Loop's zero-hardware onboarding is a UK regulatory advantage, not a technical
advantage. Our CSV path is the Irish equivalent (correct for now). When CRU framework arrives,
we build an `IREGridConnector` to replicate the same 3-click flow. Our app architecture
(CSVConnector as a swappable class) is already designed for this transition.

---

## Regulatory framework

### GDPR (directly applicable in Ireland)

| Requirement | How we comply |
|------------|--------------|
| Lawful basis | Contractual necessity — customer explicitly signs up and consents |
| Data minimisation | Process consumption data + weather only. No additional personal data required for forecasting. |
| Purpose limitation | Energy insights and scheduling only. State this explicitly in privacy policy. |
| Data retention | Define and communicate (suggested: 36 months rolling, configurable by user) |
| Right to erasure | Self-service deletion in app settings; automated pipeline to purge from all stores |
| Right to access | Download CSV of all stored data (trivial to implement from time-series store) |
| Data residency | All processing on AWS eu-west-1 (Dublin). No data leaves the EU. |
| Data breach notification | 72h notification to DPC if breach occurs; notify affected users without undue delay |

### DPC registration

Processing energy consumption data does not constitute a "special category" under GDPR
(Article 9), so no additional requirements. However, since we may infer sensitive patterns
(occupancy, appliance usage), a **Data Protection Impact Assessment (DPIA)** is strongly
recommended before launch. Cost: ~€2-5k with a GDPR consultant, or DIY with DPC templates.

### CRU licensing

We are a **data processor** acting on behalf of the customer (data subject). We are NOT
accessing ESB Networks' systems. No CRU licence required for the P1 port model or CSV upload
model.

If we ever aggregate demand-side data and sell flexibility to the grid (Viotas model), that
would require registration as a demand aggregator with CRU. That is a separate business model.

### Consumer protection

Tariff recommendation is **information service**, not regulated financial advice. Precedent:
MoneySavingExpert, uSwitch, and similar comparison sites in the UK operate under this framing.
Do not use language like "best deal" or "advice" — use "based on your usage pattern, this
tariff is most compatible." Legal review recommended before launch.

---

## Privacy considerations

### What smart meter data reveals

30-minute interval consumption data, when disaggregated or correlated with weather, reveals:

- **Occupancy patterns** — when the home is occupied, sleep/wake times
- **Appliance inference** — EV charging windows, immersion heater patterns, dishwasher timing
- **Security risk** — an attacker knowing a home is consistently empty 9am-6pm could target it
- **Sensitive inferences** — night shifts, irregular hours, potential health issues (unusual night-time consumption)

### Mitigations

| Risk | Mitigation |
|------|-----------|
| Raw data breach | On-device inference preferred long-term (data never leaves home) |
| Cloud inference | Send only pre-computed features/statistics, not raw intervals, to LLM or external APIs |
| LLM advisor | Send: "average kWh last 30d, peak hour, tariff name, forecasted kWh tomorrow" — not raw intervals |
| Third-party sharing | Never. State explicitly in privacy policy. |
| Encryption | TLS in transit, AES-256 at rest in S3/RDS |
| Access logging | Log all API access to customer data; accessible to customer on request |

### On-device inference (long-term architecture)

The ideal architecture processes LightGBM inference **on the edge device** (Raspberry Pi or
equivalent). Only the forecast output and scheduling decisions are sent to the cloud/app.
Raw consumption data stays on-device.

This is feasible: LightGBM model for H+24 is ~2MB. Inference takes 2ms. Raspberry Pi Zero 2W
(512MB RAM, ~€15) handles this trivially. The model is updated monthly via OTA update.

---

## Go-to-market sequence

### Phase 1 — Web MVP (no hardware, validate demand)
- Landing page with CSV upload
- Show: tariff compatibility analysis, usage insights, basic savings estimate
- Collect: email addresses, feedback on what matters most
- Cost: €0 incremental. Build time: 2-3 sessions.
- **Goal**: 100 signups before building any hardware

### Phase 2 — Hardware beta (P1 port adapter, 20-50 beta users)
- Source P1 adapter hardware (€15-25 BOM, €40-60 retail)
- Ship to beta users with app onboarding
- Real-time data, actual scheduling recommendations
- **Goal**: measure demand response compliance rate, NPS, MAE on real residential loads

### Phase 3 — Scale (post-validation)
- CRU data access framework integration (if live)
- Supplier tariff API integrations
- Heat pump and EV hardware partnerships (myENERGI, SolarEdge)
- SEAI partnership for bundled hardware grant

---

## Comparable products and their access model

| Product | Country | Access method | Notes |
|---------|---------|--------------|-------|
| Tibber Pulse | Norway/Sweden/NL | P1 port adapter | Direct precedent; same model |
| HomeWizard Energy | Netherlands | P1 port | Mature product, 5+ years |
| Octopus Energy (Agile) | UK | Smart meter DCC API | Utility-partner model (different) |
| Hive+ | UK | In-app utility link | Requires specific utility partner |
| Climote | Ireland | Thermostat only | No consumption data; no AI |
| Loop Energy | UK/IE | Manual upload | Closest to our Phase 1 MVP |

**Loop Energy** (loopenergyapp.com) is the closest current analogue for Phase 1:
CSV upload → consumption insights. They have traction in Ireland.
Differentiation: we add forecasting, price-aware scheduling, heat pump/EV optimisation.

---

## Key questions still open

1. **ESB Networks P1 port activation process**: Does it require a written request or is it
   self-service through My Account? Needs verification before Phase 2 hardware design.

2. **DSMR protocol version**: Irish smart meters use a variant of DSMR P1. Confirm exact
   telegram format with ESB Networks technical documentation or existing community implementations
   (github.com/nrocchi/irish-smart-meter is a starting point).

3. **Supplier tariff data**: Some suppliers (Electric Ireland, Energia) publish tariffs on their
   websites but have no API. Options: web scraping (fragile), manual update monthly, or reach
   out for data partnership.

4. **Heat pump remote control API**: myENERGI eddi (immersion diverter) has an API. Grant
   permission requires myENERGI account + device pairing. Integrate in Phase 2 control layer.

5. **SEAI partnership path**: Contact SEAI's Innovation & Policy unit. They fund pilots through
   the SEAI Research, Development & Demonstration programme. A pilot showing demand shifting
   from heat pump load would align directly with their targets.

---

## Demand Response / Flex Events

*Added 2026-04-22 — confirmed live in the Irish market.*

### What they are

ESB Networks runs a **Turn Down** demand response programme where opted-in customers receive alerts asking them to reduce electricity usage during defined windows. These are grid-balancing events triggered by EirGrid when demand is high, generation is constrained, or there is a transmission bottleneck.

**First observed in production:** 2026-04-22 at 14:14. SMS received: *"There will be a flex event today between 5-7pm. Please minimise your electricity usage where possible during this timeframe."* Opt-out link: https://esbn.ie/unsub (confirms opt-in programme exists).

**Timing:** The 2026-04-22 event ran 17:00–19:00 — exactly the BGE peak rate window (Mon–Fri, 49.28c/kWh). This alignment is not coincidental — peak grid stress and peak pricing are the same phenomenon.

### Why this is important for Sparc Energy

The demand response market is **live and operational**, not a 2030 roadmap item. The infrastructure exists: ESB Networks already has opt-in lists and notification capability. What is missing is **automated, intelligent device response** at the household level. That is exactly what Sparc Energy provides.

Current state of the market (as of 2026-04-22):
- ESB sends a text message asking customers to manually reduce usage
- No automated device response
- No per-appliance intelligence
- No price-aware substitution (e.g., pre-heating before the event window)

Sparc Energy closes this gap: receive the signal, calculate the optimal device response, present a one-tap confirmation to the user, execute.

### Integration path

| Phase | Mechanism | Status |
|-------|-----------|--------|
| Phase 1 MVP | None — user manually reads ESB SMS and acts | Current |
| Phase 2 | Push notification to app + one-tap Accept/Decline | Planned (DAN-114) |
| Phase 3 | Aggregator webhook (Endeco, Electric Ireland Flex) or SMDS flex channel | TBD — depends on SMDS go-live |

The `deployment/connectors.py` stub for SEMO/flexibility signals is the placeholder for Phase 3 integration.

### Consent model (mandatory design constraint)

Sparc Energy **must not automatically execute device actions in response to flex events without explicit user confirmation** for any action that affects comfort or resource availability (hot water, heating). See `docs/governance/AIIA.md § Flex Event Consent Model` for full rationale, tiered autonomy table, and EU AI Act / GDPR alignment.

Summary: recommend → user confirms → system acts. Never auto-act on comfort-affecting decisions.
