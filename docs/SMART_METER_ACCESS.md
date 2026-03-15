# Smart Meter Data Access — Regulatory, Privacy & Go-to-Market

**Last updated:** 2026-03-15
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

**Activation note**: Some older ESB smart meters require the customer to request P1 port
activation via their ESB Networks account. New meters have it active by default.
ESB Networks has confirmed the port is accessible to customers.

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

### Option C — CRU Third-Party Data Access Framework (future, 2026+)

The Commission for Regulation of Utilities (CRU) is developing a data access framework that
will allow consented third-party access to smart meter data via a standardised API. Timeline:
consultation ongoing, framework expected by end of 2026.

When live, this enables OAuth-style consent flows — customer logs in once, grants permission,
and our app pulls data automatically without hardware.

**Action**: Monitor CRU consultation process. Register as an interested party. This is the
eventual target architecture but not a dependency for MVP.

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
