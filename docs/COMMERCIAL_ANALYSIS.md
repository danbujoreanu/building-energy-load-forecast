# Commercial Analysis: Building Energy AI Forecasting
**Date:** 2026-03-13
**Author:** Dan Alexandru Bujoreanu
**Status:** Strategic assessment — pre-incorporation

---

## Executive Summary

**Is there a commercial product here, or just an academic paper?**
**Both. And the commercial timing is unusually precise.**

The CRU mandates that Ireland's five largest electricity suppliers offer dynamic 30-minute pricing by **June 2026**. Two million smart meters are already installed. No supplier-agnostic AI-powered demand-response device exists for the Irish market. Tibber — the closest global analog — is not in Ireland. Loop is UK-only. This is a confirmed gap at a confirmed point of market inflection.

The academic paper establishes the technical credibility (LightGBM R²=0.975, Oslo R²=0.963, well-calibrated P10/P90 intervals). The Phase 6 cyber-physical control layer is already built. The product concept is not a pivot from the research — it is the research, productised.

---

## 1. Market Trigger: Dynamic Pricing, June 2026

| Event | Date | Source |
|-------|------|--------|
| CRU deadline: top-5 suppliers must offer dynamic 30-min tariff | **June 1, 2026** | CRU Decision Paper |
| Ireland national smart meter rollout completion | End of 2025 | ESB Networks |
| Smart meters installed (as of Mar 2026) | ~2 million | ESB Networks |
| Suppliers affected | Electric Ireland, SSE Airtricity, Bord Gáis Energy, Energia, PrePay Power/Yuno | CRU |

**Why this matters:** Every Irish household with a smart meter (CTF score ≥4) will suddenly have a tariff where the price of electricity changes every 30 minutes. The average household will lose money without a device that optimises their loads against those prices. This creates a consumer pull that didn't exist before.

---

## 2. Competitive Landscape

### 2.1 Direct Competitors

| Company | Geography | Device | Forecasting | Control | Price | Gap vs Our Product |
|---------|-----------|--------|-------------|---------|-------|-------------------|
| **Tibber** | Norway, Sweden, DE, NL (NOT Ireland) | Tibber Pulse (P1 dongle) | Simple price-aware smart charging | EV + solar + HP via integrations | €0 app + Tibber contract required | Not in Ireland; locked to Tibber tariff; no building-level ML forecast |
| **Loop** | UK only (NOT Ireland) | None (uses smart meter API) | Basic carbon grid forecast; no load ML | None | Free | UK only; monitoring only; no control layer; no forecasting of your own load |
| **Hildebrand Glow** | UK only | £30 Zigbee CAD dongle | None | None (data only, MQTT/API) | £30 hardware, free app | UK only; data relay only; no ML, no control |
| **Sense** | US/Canada only | $299 panel clamp | ML appliance detection | None | $299 + subscription | US electrical panel architecture; no demand-response integration |
| **Emporia Vue 3** | US only | ~$150 panel clamp | None | EV charger integration only | $150 | US only; basic monitoring |
| **OhmConnect** | US only | None (virtual) | Grid peak prediction | Manual demand-response rewards | Free (revenue share) | US grid only; requires manual behaviour change |

**Confirmed gap:** No product exists combining (a) Irish market compatibility, (b) building-level ML load forecasting, (c) supplier-agnostic dynamic price optimisation, (d) automated device control for EV/hot water.

### 2.2 Irish Market — Supplier Apps (Indirect Competitors)

| Supplier | Smart Meter Feature | Forecasting | Demand Response | Assessment |
|----------|-------------------|-------------|-----------------|------------|
| Electric Ireland | Basic usage monitoring in app | None | None | Monitoring dashboard only |
| Energia | Smart meter plan + app | None | None | Monitoring dashboard only |
| SSE Airtricity | Usage tracking | None | None | Monitoring dashboard only |
| Bord Gáis | Smart meter readings | None | None | Monitoring dashboard only |
| ESB Networks | View consumption at esbnetworks.ie | None | None | No app; raw data portal |

**Assessment:** All five are monitoring tools, not optimisation tools. None is supplier-agnostic. None has a control layer. None does ML forecasting. This is the classic utility app gap — they can see your data but won't tell you what to do with it, because doing so might mean recommending a competitor's tariff.

### 2.3 Norwegian Market Reference (Where Tibber Succeeded)

Tibber launched in Norway in 2016 against exactly this competitive backdrop: smart meters rolled out nationally, dynamic spot pricing normalised (Nordpool hourly), but no consumer device to act on it automatically. Tibber's device (Pulse, ~€49) + contract model now has ~500k customers. The Irish market is smaller (~1.7M households) but structurally identical in June 2026.

Key lesson from Tibber: **the device is the moat, not the app.** The P1 port adapter creates a physical subscription relationship. Customers who own the dongle don't switch.

---

## 3. Our Product Concept: "EnergyOS" (working name)

### 3.1 What It Is

A supplier-agnostic home energy AI device for the Irish smart meter market:

- **Hardware:** Raspberry Pi Zero 2W-class device (~€25 BOM) + ESB Networks P1 port USB adapter
- **Software:** LightGBM H+24 load forecast + LightGBM Quantile P10/P90 + ControlEngine
- **Data inputs:** P1 smart meter (real-time consumption), OpenMeteo API (live weather + 48h solar forecast), SEMO/ENTSO-E day-ahead prices, supplier dynamic tariff (API or scrape)
- **Outputs:** Morning brief (what to charge, what to defer, peak/off-peak advisory), automated device control via myenergi Eddi/Zappi API (hot water diverter, EV charger)

### 3.2 Decision Logic (from Phase 6 ControlEngine)

```
H+24 forecast:   LightGBM → P50 demand + P10/P90 uncertainty bounds
Solar forecast:  OpenMeteo → irradiance next 48h
Price forecast:  SEMO day-ahead → €/kWh per 30-min slot

IF solar_forecast[h] > 200 W/m² AND P10[h] < 3 kWh:
    → Divert solar surplus to hot water tank (free heat)
IF dynamic_price[h] < off_peak_threshold AND EV.needs_charge:
    → Charge EV in this slot (cheapest window)
IF P90[h] > grid_demand_limit AND flexible_load.active:
    → Defer washing machine / dishwasher to off-peak
```

### 3.3 The H+5 Control Extension (Sprint 2)

The current pipeline has H+1 (real-time) and H+24 (day-ahead). A natural third horizon is **H+3 to H+8** — long enough to pre-heat hot water, short enough to act on current solar conditions. Training a direct H+5 LightGBM takes 13 seconds and requires only one parameter change (`target_shift=5` in run_pipeline.py). This gives a three-horizon control stack:

| Horizon | Decision | Model |
|---------|----------|-------|
| H+1 | Emergency load shed / real-time balancing | LightGBM H+1 |
| H+5 | Hot water pre-heat / near-term solar divert | LightGBM H+5 *(Sprint 2)* |
| H+24 | EV charge schedule / day-ahead market bid | LightGBM H+24 + Quantile |

---

## 4. Commercial Model

### 4.1 Revenue

| Stream | Price | Notes |
|--------|-------|-------|
| Hardware (device + P1 adapter) | €99–€149 | One-time; manufactured via Raspberry Pi supply chain |
| Software subscription | €3.99/month (€47/year) | Cloud model updates + SEMO price feed + priority support |
| **Consumer savings** | **€200–400/year** | Optimised EV charging + solar diversion + peak avoidance |
| **Payback period** | **3–6 months** | At €300 avg saving / €149 device + €48 subscription |

### 4.2 Funding Path

| Stage | Programme | Amount | Timing |
|-------|-----------|--------|--------|
| 1 | AWS Activate (already eligible via AWS conference demo) | $5–25k credits | Now |
| 2 | Enterprise Ireland HPSU Feasibility Grant | €35k | Q3 2026 |
| 3 | New Frontiers (EI Pre-Accelerator) | €15k stipend + 6 months | Q4 2026 |
| 4 | EI iHPSU (High Potential Start-Up) | Up to €1.2M equity + grant | 2027 |
| 5 | NCI SFI Commercialisation Fund | €300k–1.5M | Requires NCI academic partner |

### 4.3 NCI / Academic Partnership

The MSc at NCI is the seed IP for an SFI Commercialisation Fund application. NCI academic partner = required for SFI funding. This is not a conflict — the academic paper (journal) and the commercial product are complementary. The paper provides peer-reviewed validation; the product provides commercialisation evidence for SFI.

---

## 5. Differentiation Summary

| Feature | Loop | Tibber | Hildebrand | Our Product |
|---------|------|--------|------------|-------------|
| Works in Ireland | No (UK) | No (not yet) | No (UK) | **Yes** |
| Supplier-agnostic | Partial | No (locked to Tibber) | Yes | **Yes** |
| ML load forecasting | No | Basic | No | **Yes (LightGBM R²=0.975)** |
| P10/P90 uncertainty | No | No | No | **Yes** |
| Hardware device | No | Yes (P1 dongle) | Yes (Zigbee CAD) | **Yes (P1 adapter)** |
| Automated control | No | EV only | No | **Yes (EV + hot water + deferral)** |
| Day-ahead H+24 | No | Basic price-only | No | **Yes (building-level ML)** |
| Open API / Home Assistant | No | Yes | Yes | **Yes (FastAPI + planned HA integration)** |
| Academic validation | No | No | No | **Yes (journal paper + Oslo generalisation)** |

---

## 6. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Tibber launches in Ireland before us | High | Tibber is supplier-locked; our product works with any tariff; focus on supplier-agnostic positioning |
| CRU dynamic tariff deadline slips again (already slipped once) | Medium | June 2026 is the hard deadline; product can still demonstrate value on smart tariffs already available (night rate, EV tariffs) |
| ESB Networks P1 port access policy changes | Medium | ESB Networks P1 protocol is HAN (Home Area Network) — consumer data right, analogous to SMETS2 CAD access in UK. CRU consumer data right covers this. |
| Hardware unit economics | Low-Medium | Raspberry Pi Zero 2W = €20 BOM; P1 USB adapter = €8. €28 BOM → €99 retail = healthy margin. As volume scales, switch to custom SoC. |
| ML model generalisation to residential | Medium | Current models trained on municipal buildings. CER household dataset (6,435 households) is the next validation step. Key features (weather × time interactions) transfer to residential. |

---

## 7. Immediate Next Steps (Commercial Path)

1. **AWS conference demo** (March 2026) — `python deployment/live_inference.py --dry-run` demonstrates the full control layer live
2. **H+5 model training** — one parameter change, 13 seconds, completes the three-horizon control stack
3. **CER household dataset** — validate residential generalisation; strongest commercial evidence
4. **Patent filing** — provisional patent on the three-horizon demand-response architecture + building-specific quantile calibration method (before journal publication)
5. **NCI partnership meeting** — registry inquiry on alumni researcher status + NCI academic sponsor for SFI Commercialisation Fund

---

## 8. The Two-Track Strategy

The academic paper and the commercial product are not in tension — they are sequenced:

```
ACADEMIC PAPER (Applied Energy / Energy and Buildings)
  └── Establishes: LightGBM R²=0.975, Oslo R²=0.963, P10/P90 calibration
  └── Establishes: Paradigm parity (trees > DL) with statistical significance
  └── Provides: Peer-reviewed validation for SFI / EI applications

COMMERCIAL PRODUCT (EnergyOS)
  └── Extends to: residential loads (CER dataset), H+5 control horizon
  └── Extends to: live SEMO price integration, ESB Networks P1 port
  └── Provides: Real-world deployment evidence for second journal paper
  └── Provides: Commercial traction for iHPSU funding round
```

The journal paper is the scientific foundation. The product is what transforms it from a research contribution into a sustainable business. Both are needed; neither substitutes for the other.

---

*Generated: 2026-03-13. Sources: CRU Decision Paper on Dynamic Electricity Price Tariffs, ESB Networks Smart Meter rollout data, Tibber business model analysis, Loop product analysis, Hildebrand Glow API documentation.*
