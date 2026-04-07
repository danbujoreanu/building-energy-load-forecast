# LinkedIn Post Drafts — Irish Home Energy AI

Three posts, each standalone. Designed to build credibility without disclosing the full system.
Post order: 1 → 2 → 3 (space them 3–5 days apart for best reach).

---

## Post 1 — Technical Credibility
*Angle: The research result. Anchors your ML credibility. References AICS '25.*

---

I spent the last year building a machine learning system to forecast electricity consumption in public buildings — and the results genuinely surprised me.

**LightGBM: MAE = 4.0 kWh, R² = 0.975 at H+24 across 42 buildings.**

But the more interesting finding wasn't the headline number. It was what happened when I tested it on an entirely unseen city — Oslo — with no retraining. The model transferred: R² = 0.963.

That generalisation result matters more than the Drammen score. It suggests the learned patterns (occupancy rhythms, thermal inertia, holiday effects) are structural, not overfitted to one dataset.

A few things that drove this:
- **Feature engineering over architecture**: lag features, rolling windows, and cyclical time encodings outperformed a PatchTST transformer trained on raw sequences (+72% MAE gap, confirmed by Diebold-Mariano test at p < 0.001)
- **Gradient-boosted trees on tabular data still win** — consistent with Grinsztajn et al. (NeurIPS 2022) and Moosbrugger et al. (arXiv 2501.05000)
- **Scale matters**: 42 buildings × 2+ years of 30-minute interval data. The model sees enough structural variation to generalise

This work was presented at AICS '25 (Springer CCIS). Now it's the inference engine behind something I'm building for the Irish residential market — more on that soon.

Happy to share the paper if you're working on similar problems.

#MachineLearning #EnergyForecasting #LightGBM #BuildingEnergy #DataScience #Ireland

---

## Post 2 — Dynamic Pricing Market Opportunity
*Angle: The regulatory trigger. Positions you as someone who understands the Irish energy market.*

---

On 30 June 2026, Irish electricity prices will change every 30 minutes.

That's not speculation — it's CRU regulation (CRU202517). Five major suppliers (Electric Ireland, SSE Airtricity, Bord Gáis Energy, Energia, Yuno) are mandated to offer Standard Dynamic Price Contracts by that date. Each contract: prices published the evening before, 30-minute intervals, capped at €0.50/kWh. Currently, not one of the five is offering it.

Right now: **74% of Irish households who would benefit from time-of-use tariffs aren't on one.** The CRU's own estimate is that 95% of customers would gain financially from switching. That gap is enormous — and it has a name: risk.

Dynamic tariffs expose households to real bill volatility. If you don't know when your heat pump, EV charger, or hot water cylinder will run, you can't manage it. Most people will look at a tariff that changes every half hour and immediately switch back to flat rate.

This is the product gap.

The households that will benefit most — heat pump owners (80,000 today, 400,000 targeted by 2030), EV drivers, solar households — need something between the raw price signal and their devices. A layer that reads tomorrow's prices, forecasts their consumption, and automatically schedules controllable loads into the cheap windows.

That's the problem I'm building a solution for: an Irish home energy AI that makes dynamic tariffs safe. H+24 load forecast + device control + a €200–400/year saving — without the user having to think about it.

June 2026 is 3 months away.

#EnergyTransition #SmartEnergy #DynamicPricing #IrishEnergy #CleanTech #CRU #HeatPumps

---

## Post 3 — System Architecture
*Angle: The engineering depth. Goes with the architecture diagram. Shows production maturity.*

---

When people ask what an "AI energy system" actually looks like under the hood, I show them this diagram.

[📎 attach: docs/linkedin_architecture.png]

Four layers — each one live or in active development:

**1. Data Ingestion**
Smart meter data via ESB Networks' new Smart Meter Data System (SMDS, active under CRU202517). Real-time weather and solar irradiance from Open-Meteo. P1 port hardware adapter for 30-second live reads — the same standard used in the Netherlands, Belgium, and Luxembourg.

**2. AI Forecast Engine**
LightGBM model trained on 2+ years of 30-minute interval data. Produces P10/P50/P90 probabilistic forecasts at H+1 and H+24. Deployed as a FastAPI service in Docker on AWS App Runner (eu-west-1). Retrained monthly on a rolling 24-month window, with a drift trigger if 7-day MAE exceeds 1.5× the training baseline.

**3. Optimisation & Control**
A rule-based control engine takes the forecast bundle and a real-time electricity price signal, then outputs demand-response setpoints. Currently integrated with the myenergi Eddi API for hot water diversion — the device that shifts load into cheap or solar windows automatically.

**4. User Interface**
React Native app (in design). Weekly savings digest. In-app LLM advisor (Claude API) that answers questions like "why did my bill spike?" without exposing raw consumption data to the model.

The insight that shaped the architecture: the forecast only matters if it closes the loop to the device. Dashboards don't change behaviour. Control actions do.

90-test suite. Integration tests covering temporal leakage, horizon consistency, and end-to-end inference. R² = 0.975 on held-out data.

If you're working on demand-side management, smart home energy, or Irish cleantech — I'd love to connect.

#SystemArchitecture #MLOps #EnergyAI #AWS #FastAPI #SmartHome #IrishTech #CleanTech #DemandResponse

---

## Notes on Posting Strategy

- **Post 1** (technical): best on a Tuesday or Wednesday morning (08:00–09:30 IST). Target: ML engineers, researchers, NCI/UCD alumni.
- **Post 2** (market): best on a Monday. Tag: @CRU_Ireland if comfortable. Target: energy sector, policy, investors.
- **Post 3** (architecture): best on a Thursday. Attach the PNG. Target: engineers, CTOs, AWS Ireland community.

**What NOT to disclose yet:**
- Specific tariff scoring algorithm details
- The exact feature set (lag windows, rolling features)
- Revenue model numbers
- Company name / domain (until registered)

**What to mention in comments if asked:**
- "Pre-incorporation stage, building toward a June 2026 launch aligned with the dynamic pricing mandate"
- "AICS '25 paper available on request"
- "Happy to connect if you're in the Irish energy / cleantech space"
