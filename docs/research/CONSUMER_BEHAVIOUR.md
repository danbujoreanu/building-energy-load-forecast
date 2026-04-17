# Consumer Behaviour — Irish Energy Market
*Synthesis for building-energy-load-forecast product and research*
*Last updated: April 2026*
*Citation standard: all claims attributed to primary source, section, and page where confirmed from document*

---

## Citation Key

| Abbreviation | Full Reference |
|---|---|
| **SEAI BI** | SEAI, *Behavioural Insights on Energy Efficiency in the Residential Sector* (undated; based on Element Energy for SEAI 2016 and B&A 2016 survey data). Local copy: `Consumer insights and studies/Behavioural-insights-on-energy-efficiency-in-the-residential-sector.pdf` |
| **CRU202566** | CRU, *Consultation on a Review of the Accreditation Framework for Price Comparison Websites*, CRU/202566, published 09/05/2025. Local copy: `Consumer insights and studies/CRU Documents/CRU202566-...pdf` |
| **CRU202579** | CRU, *Smart Meter Upgrade: Access to Near Real Time Metering Data — Consultation Paper*, CRU/202579, published 04/06/2025. Local copy: `Consumer insights and studies/CRU Smart Meter Upgrade.../CRU202579-...pdf` |
| **CRU2024121** | CRU, *Decision on Dynamic Electricity Price Tariffs*, CRU/2024121, September 2024. Referenced in CRU202566, fn.15. |
| **CSO HEBEU** | CSO, *Household Energy Behaviours and Attitudes* (HEBEU), 2024. Online dataset: https://data.cso.ie/product/HEBEU. No local copy. Table-level citations require querying the PxStat platform directly. |
| **Kazempour BTM** | Kazempour group (DTU), arxiv:2501.18017, January 2025. |
| **SEAI 2030** | SEAI, *National Heat Study* and SEAI heat pump programme targets. Referenced in SEAI BI and SEAI website. |

---

## 1. The Core Problem: Massive Inertia

The Irish energy consumer market is characterised by **stubborn inertia**, not ignorance. The data paints a consistent picture across all sources:

| Metric | Figure | Source — specific location |
|--------|--------|---------------------------|
| Households who haven't switched tariff in a year | **61%** | CSO HEBEU 2024 *(table ref: query PxStat HEBEU dataset — specific table not verified in local files)* |
| Households unaware of their own tariff | **19%** | CSO HEBEU 2024 *(as above)* |
| Households who have shifted consumption to exploit TOU | **10%** | CSO HEBEU 2024 *(as above)* |
| Households on TOU tariffs (26%) vs not on TOU (74%) | **26% / 74%** | Referenced in CRU memory from CRU202358/CRU2023152 TOU incentivisation decisions *(exact page not confirmed in documents reviewed — requires verification against CRU2023152)* |
| Customers who have used a PCW for electricity | **45%** | CRU202566, Executive Summary, p.1 — *"According to a CRU consumer survey published in 2022, 45% of customers surveyed reported using a PCW for electricity"* |
| Smart meters installed | **>1.9 million** | CRU202579, Executive Summary, p.2 — *"The NSMP is well advanced with over 1.9 million smart meters installed in Irish homes and businesses"*; confirmed also at CRU202566, Section 1.1, p.11 |
| Households in potential energy poverty | **~28%** | SEAI BI, p.10, Figure 6 — *28% of households at the 10% income-to-energy-spend threshold (DCCAE 2016 data)* |

> **Note on CSO HEBEU figures:** The HEBEU dataset is a nationally representative survey published by the CSO via PxStat. The 61%, 19%, and 10% figures are widely cited from this source but have not been verified at table level in the current review. They should be confirmed against the PxStat dataset before use in academic writing.

**Product implication:** The market gap isn't about awareness — it's about **friction, trust, and effort**. Our product must remove all three.

---

## 2. SEAI Consumer Segmentation (3 Types)

*Source: SEAI BI, Section 1.1, p.7–8, Figures 3 and 4*

SEAI segmented Irish homeowners into groups by their **driver** for energy decisions. The segmentation is presented in Figure 3 (p.8) and described in Figure 4 (p.8–9).

> **What the document actually shows:** Figure 3 (p.8) presents a 2×2 matrix of owner-occupier motivation. The four quadrants are labelled A (Aspirational), B (Comfort and Value), C (an overlap group), and D (Cost-Driven). Approximate proportions given for owner-occupiers: A = ~8%, B = ~11%, C = ~10%, D = ~71%.
> *(SEAI BI, p.8, Figure 3 — exact labels and percentages are from the figure; verify segment naming convention against current SEAI publications before citing in academic work)*

### Segment A — Aspirational (~8% owner-occupiers)
*(SEAI BI, p.8, Figure 3 and Figure 4)*
- Motivated by sustainability and environment
- Concerned about the future; evidence-driven
- Willing to adopt new technology
- **Our early adopter.** Target with environmental framing + innovation angle.

### Segment B — Comfort and Value Seekers (~11% owner-occupiers)
*(SEAI BI, p.8, Figure 3 and Figure 4)*
- "Home is heart" — long-term, investment-driven, practical
- Want comfort improvement AND cost reduction
- Will invest if the case is clear and the process is easy
- **Our primary market.** Target with comfort + savings framing, especially heat pump owners.

### Segment D — Cost-Driven (~71% owner-occupiers)
*(SEAI BI, p.8, Figure 3 and Figure 4)*
- Short-term considerations; reactive to triggers
- Need immediate, visible savings; want a "quick fix"
- Will act at trigger points (high bill, new appliance, contract renewal)
- **The stubbornly inactive majority.** Need strong default nudges + automation.

> **Key insight for product design:** *"only 10% of homeowners actually intend carrying out retrofit works in the coming few years"* *(SEAI BI, p.12, citing B&A 2016 Retrofit Research Survey — a separate primary source used within the SEAI document)*. The majority (Cost-Driven) will NOT proactively engage. The product must work *automatically* in the background. **Automation > engagement for this segment.**

---

## 3. Decision-Making Trigger Points

*Source: SEAI BI, Section 2 (trigger points discussion, approximate pp.10–13)*

Consumers make energy decisions at **specific life events**, not continuously. These are the moments to acquire customers:

| Trigger Point | Communication Channel |
|--------------|----------------------|
| Anticipated home improvement | Architects, contractors, obligated energy suppliers |
| Buying a new house | Mortgage broker, BER assessor, estate agent |
| Retirement | Pension provider, employer |
| Illness / extending family | Hospitals, community-based services |
| **Contract renewal** | Direct supplier contact, PCW |
| **High bill shock** | Supplier app notification, PCW referral |
| **Heat pump / EV installation** | Installer, SEAI grant application process |

> **Our acquisition strategy:** Target at SEAI grant applications (HPSS, BEC), heat pump installers, contract renewal windows (June 2026 = BGE contract deadline). The trigger-point framework is grounded in SEAI BI; however, verify specific trigger point labels against the most recent SEAI publications as the 2016 underlying survey data may have been updated.

---

## 4. Barriers to Action (Investment Behaviour)

*Source: SEAI BI, Sections 3–4, pp.14–20*

Consumers' investment decisions are NOT purely cost-based. Key barriers:

1. **Finance availability** — most important barrier.
   > *"over 70% identified 'not having sufficient funds' as the most relevant barrier to home improvements"* *(SEAI BI, p.15, citing Element Energy for SEAI 2016 survey)*
   Low-interest loans + grants = most attractive combination.

2. **Payback period sensitivity**
   > *"around 10% of owner occupiers are willing to invest...for a payback time of 4 years, falling to 0% for a payback time of 6 years for some segments"* *(SEAI BI, p.18–19, Figure 12, citing Element Energy for SEAI 2016)*

3. **Comfort framing > cost framing**
   > Figure 14 (SEAI BI, p.19): **90% of respondents** rate "comfort improvement" as "very important" or "important" — the single highest-rated factor in the investment decision, above financial savings.
   > Grant emotional impact: *"grants have more than 30% additional emotional impact: i.e. 1 Euro grant corresponds to 1.3 Euro in consumers' minds"* *(SEAI BI, p.18–19, citing Element Energy for SEAI 2016)*

4. **Trust in source** — consumers engage far more when information comes from a trusted advisor (BER assessor, credit union, local community group). Generic campaigns don't shift behaviour. *(SEAI BI, Section 3, pp.14–16)*

5. **Process complexity** — ease of application is critical. One-stop-shop model dramatically increases uptake. *(SEAI BI, Section 3)*

> **Product implication:** Frame the product around **comfort and control**, not savings alone. Make onboarding a one-stop-shop (HDF upload → instant analysis). Partner with trusted intermediaries (BER assessors, SEAI, saveon.ie).

---

## 5. PCW Landscape and Switching Behaviour

*Primary source: CRU202566 — Consultation on a Review of the Accreditation Framework for Price Comparison Websites, published 09/05/2025*

### Current accredited PCWs: Bonkers, Switcher, Power to Switch
*(CRU202566, Executive Summary, p.1 — "To date, there have been three PCWs granted CRU accreditation: Bonkers, Switcher and Power to Switch.")*

### Key findings with citations:

**45% PCW usage:**
> *"According to a CRU consumer survey published in 2022, 45% of customers surveyed reported using a PCW for electricity, and 53% claimed the same for gas in 2022. This has been increasing year on year."* *(CRU202566, Executive Summary, p.1, citing CRU2022986 Consumer and Business Survey)*

**4 new requirements for accreditation:**
> CRU202566, Executive Summary, p.2 — proposed new requirements:
> 1. Smart meter HDF data integration for personalised comparisons
> 2. Dynamic tariff comparisons
> 3. Export tariff comparisons
> 4. Customers with <100,000 kWh/year consumption

**Dynamic tariffs — zero currently offered:**
> *"At present, there are no dynamic tariffs offered in the Irish energy retail markets. The deadline for the five obligated suppliers to introduce dynamic tariffs is currently June 2026, however suppliers may introduce dynamic tariffs before this deadline if they wish."* *(CRU202566, Section 4.2, p.23–24)*
> Dynamic Unit Rate: *"A cost associated with each unit of electricity imported. This element of dynamic tariffs will change every half hour of the day in accordance with the prices set by the day ahead market (DAM)."* *(CRU202566, Section 4.2, p.24)*
> The June 2026 deadline derives from CRU2024121 (Decision on Dynamic Electricity Price Tariffs, September 2024), cited in CRU202566 at Section 4.2, p.23, footnote 15.

### What this means for us:
- CRU is actively creating the infrastructure for our use case (smart meter data + dynamic tariffs)
- PCWs will be required to support HDF upload — same pipeline we use
- **We are NOT a PCW** (backward-looking comparison) — we are the **next layer** (forward-looking forecasting + active optimisation)
- Our product answers "what will I spend?" and "how do I spend less?" — PCWs only answer "who's cheapest right now?"

---

## 6. Near Real-Time Metering Data — The Hardware Layer

*Primary source: CRU202579 — Smart Meter Upgrade: Access to Near Real Time Metering Data, published 04/06/2025*

### Status of Irish smart meter rollout:
> *"The National Smart Metering Programme...involves the nation-wide instalment of more than two million smart meters over a six-year period. There are now over 1.9 million smart meters installed in Irish homes and businesses."* *(CRU202579, Section 1.1, p.6)*
> Phase 2 (Smart Pay-As-You-Go) completed Q2 2025. Phase 3: near real-time data access. *(CRU202579, Section 1.1, p.6)*

### Two hardware access paths:
*(CRU202579, Section 1.2, p.9 — confirmed from document)*
> 1. **LED Pulse Reader** — *"All of the smart meters installed to date have an LED pulse on the front of the meter that pulses when energy is used. A device, known as an LED Pulse Reader, can be attached to the front of the meter."*
> 2. **P1 port** — *"Approximately half of the meters installed to date have a P1 port...Those ports are currently not operational, and it will be end of 2025 before ESB Networks roll-out the necessary updates to make the ports accessible."* *(CRU202579, Section 1.2, p.9)*

### CRU position — market-led approach:
> *"The CRU is of the view that access to near real time metering data services, such as the IHD, should be market led. The CRU sees an opportunity for competition in the electricity market which can bring benefits to customers by driving value and innovation."* *(CRU202579, Executive Summary, p.2)*
>
> *"The CRU views the provision of near real time metering data services as a potential market opportunity for suppliers and other energy service providers."* *(CRU202579, Section 3.1, p.14–15)*
>
> *"The CRU encourages suppliers and other potential market participants to consider the market opportunities in providing customers with a near real time data service such as an IHD, or through an application."* *(CRU202579, Executive Summary, p.2; repeated in substance at Section 3.1, p.14–15)*

> **This is the direct regulatory invitation for products like ours to exist.** The CRU is explicitly removing the ESB Networks monopoly on IHDs and inviting market participants to build near real-time data products.

### IHD effectiveness evidence:
> *"Research shows that use of an IHD can reduce electricity consumption generally between 2%–4%."* *(CRU202579, Section 3.1, p.14, footnote 16 — citing OFGEM 2011, Energy Demand Research Report, Final Analysis)*
> However: *"other studies have shown that IHDs become less engaging over time"* *(CRU202579, Section 3.1, p.14, footnote 17 — citing Energies 2021)*

### Smartphone penetration:
> *"Research suggests that approximately 80% of Irish adults own and use a smartphone."* *(CRU202579, Section 3.1, p.14, footnote 19 — citing S. Gibney and T. McCarthy, Profile of Smartphone Ownership and Use in Ireland, Department of Health, May 2020)*

### Vulnerable customer provision:
> CRU is considering ESB Networks making near real-time data available to registered vulnerable customers, funded through DUoS network charges. *(CRU202579, Executive Summary, p.3; Section 3.2, p.16–19)*
> **Potential product angle:** SEAI/CRU partnership for subsidised IHD/device rollout to vulnerable customers.

---

## 7. EV and Heat Pump Owners — The Early Adopter Signal

*Source: CSO HEBEU 2024 (EV and age data — table-level references require PxStat query); SEAI HPSS programme targets*

- **EV owners**: 50%+ already on flexible tariffs vs ~30% non-EV — strongest indicator of tech-forward energy behaviour *(CSO HEBEU 2024 — verify table ref in PxStat)*
- **Heat pump owners**: SEAI targets 400,000 heat pumps installed by 2030 *(SEAI National Heat Study; SEAI Heat Pump Support Scheme documentation)*. Heat pumps make households extremely sensitive to electricity tariffs (heating cost shifts from gas to electricity entirely)
- **Age 40–49**: primary demand shifters (16%) — primary buyer demographic *(CSO HEBEU 2024 — verify table ref)*

> **Early adopter profile**: EV owner OR heat pump owner, age 35–55, homeowner, high energy spend. Already financially motivated and technically willing. Our hardware device + app is a natural fit.

> **Important caveat:** SEAI's 400k heat pump target has faced headwinds. Verify current HPSS uptake statistics from seai.ie before citing in product materials or investor decks.

---

## 8. Behavioural Economics Angles

*Sources: SEAI BI (interventions); academic literature on energy demand response*

Directly applicable to product design and research:

### Proven interventions (SEAI BI, Section 5, pp.21–25 approx.):
- **Social comparison / neighbour benchmarking** — "Your neighbour uses 20% less electricity" — one of the highest-impact nudges in energy research *(referenced in SEAI BI; robust evidence base in broader academic literature — e.g. Allcott 2011, NBER)*
- **Default opt-in** — consumers accept defaults; make smart scheduling the default, not an opt-in *(SEAI BI, Section 5 / general behavioural economics literature)*
- **Loss framing** — "You're leaving €178/year on the table" outperforms "You could save €178/year" *(Kahneman & Tversky prospect theory; applied in energy context via SEAI BI)*
- **Progress indicators** — real-time feedback increases engagement; IHD effect *(CRU202579, Section 3.1, p.14: "use of an IHD can reduce electricity consumption generally between 2%–4%", citing OFGEM 2011)*
- **Trusted advisor referral** — BER assessor, credit union, community group as acquisition channel *(SEAI BI, Section 3, p.14–16)*

### When to use hardware/automation instead of behaviour change:
*(SEAI BI product design implication; Segment D = Cost-Driven majority)*

If a consumer segment won't change behaviour, the answer is **automation**:
- **Hot water scheduling** (Eddi/Myenergi) — we already do this
- **Battery storage** — charges at low-price periods automatically; no behaviour change required
- **EV smart charging** — schedules charge during Free Saturday or night rate; user does nothing
- **Smart plugs / appliance control** — dishwasher, washing machine scheduled automatically

> **Battery storage angle:** If dynamic pricing creates large price differentials (€0.05–€0.50/kWh range under CRU2024121 mandate), a home battery amortises in 3–5 years. We can recommend batteries as a product upgrade path — using our forecast to decide optimal charge/discharge cycles.

---

## 9. Behind-the-Meter (BTM) Inference — Kazempour Approach

*Source: Kazempour group (DTU), arxiv:2501.18017, January 2025 — "Behind-the-Meter Asset Detection from Smart Meter Data"*

Rather than asking consumers what devices they have (survey fatigue, inaccuracy), we can **infer BTM assets from smart meter data**:

### What we can detect from 30-min HDF data:
*(Kazempour et al., arxiv:2501.18017 — detection signals summarised from paper; verify exact methodology against Section 3 of the paper)*

| Asset | Detection Signal |
|-------|-----------------|
| Solar PV | Net export patterns, generation signature |
| EV charger | Overnight demand spike, 7–11 kWh pulse |
| Heat pump | Winter heating signature, weather-correlated load |
| Eddi/hot water diverter | Morning/evening load spike pattern |
| Battery storage | Charge/discharge oscillation pattern |

### Application for our product:
1. **Onboarding survey replacement** — infer household asset profile from 4 weeks of HDF data, confirm with user ("We think you have solar panels — is that right?")
2. **Personalised recommendations** — if we detect no EV but high night rate usage, recommend switching to night rate; if solar detected, recommend export tariff comparison
3. **Anomaly detection** — sudden change in consumption pattern = new appliance, leak, or fault
4. **Savings quantification** — "Based on your profile, you have an Eddi-like device. Here's how to optimise its schedule."

This is methodologically complementary to our load forecasting work — same data, different analytical lens.

> **Citation note:** The Kazempour paper is a preprint. Cite as arxiv:2501.18017 until a peer-reviewed version is confirmed.

---

## 10. Pre-Adoption Survey Design

A lightweight survey at app signup (3–5 questions max) to personalise recommendations immediately:

### Proposed questions:
1. **What's your primary goal?** (Save money / Reduce carbon / Understand my usage / All of the above)
2. **Which of these do you have?** (Heat pump / EV / Solar panels / Hot water diverter / None)
3. **How do you currently heat your home?** (Gas boiler / Heat pump / Oil / Solid fuel)
4. **Who is your current supplier?** (BGE / Electric Ireland / Energia / SSE / Other)
5. **Are you open to switching supplier?** (Yes, if savings are clear / No, happy with current / Already switched recently)

### Research value:
- Validated against BTM inference (does survey match what the data shows?) — *a direct test of Kazempour et al. methodology in the Irish context*
- Segment users into SEAI archetypes at signup *(SEAI BI, Figures 3–4, p.8)*
- Informs personalised first-week experience

---

## 11. Research Gaps — What We Still Need

| Gap | Why It Matters | Potential Source | Citation Status |
|----|---------------|-----------------|-----------------|
| Willingness to pay for energy app subscription | Pricing strategy for €3.99/month | Primary survey or conjoint study | No existing Irish data found |
| Willingness to pay for hardware (€99–149) | Hardware pricing | Primary survey | No existing Irish data found |
| Heat pump owner behaviour with dynamic tariffs | Core use case validation | Pallonetto/RENEW, SEAI pilot data | RENEW project ongoing — contact PI |
| Consumer response to automated device control | Trust + control perception | Behavioural experiment | No existing Irish data found |
| TOU tariff adoption rate (26%/74% figure) | Market sizing; cited in memory but not confirmed in docs reviewed | CRU2023152 (TOU Incentivisation Decision) — **needs verification** | **Unconfirmed — check CRU2023152** |
| BTM asset penetration rates by household segment | Market sizing for control layer | CSO HEBEU detailed tables, SEAI | HEBEU table ref not verified |
| Fuel poverty + smart technology access | Equity and inclusivity | SEAI, St Vincent de Paul | SEAI BI p.10, Figure 6 (28% at 10% threshold) |
| Tenant vs owner-occupier split | Landlord-tenant split incentive | CSO HEBEU, RTB data | HEBEU table ref not verified |

---

## 12. Strategic Implications for Product and Research

### If consumer behaviour is stubborn → automate everything
*(SEAI BI: 71% Cost-Driven segment; SEAI BI p.12: only 10% intend retrofit)*
- Device control (Eddi, EV, battery) replaces manual behaviour change
- Battery storage = ultimate "set and forget" for Cost-Driven segment
- Morning brief (our Phase 6 CLI) should push to WhatsApp/SMS, not require app open

### If we want to influence behaviour → apply behavioural economics
*(SEAI BI, Section 5; OFGEM / academic literature)*
- Social comparison: "Homes like yours in Maynooth save 23% more"
- Loss framing on bills: quantify what's being left on the table
- Progress indicators: weekly savings meter

### Regulatory white space is NOW open
*(CRU202579, Exec Summary p.2 + Section 3.1 p.14-15; CRU202566 Section 4.2 p.23)*
- CRU has explicitly invited market participants to build near real-time data products
- June 2026 dynamic pricing mandate = product-market fit trigger
- P1 port software activation (end of 2025/2026) = hardware MVP trigger

### Research opportunity → build the evidence base
- Run a 3-month pilot with 20–50 households (SEAI pilot partnership)
- Pre/post: usage patterns, bill savings, survey satisfaction
- BTM inference validation study (Kazempour et al. approach in Irish context)
- This becomes a journal paper AND commercial validation
- RENEW project (Pallonetto/IRESI, Maynooth) = natural collaboration partner

---

## Source Documents

| Document | Local Path / URL | Key sections with page refs |
|---------|------|-------------|
| **SEAI BI** | `Consumer insights and studies/Behavioural-insights-on-energy-efficiency-in-the-residential-sector.pdf` | Consumer segments (p.8, Figs 3–4); energy poverty (p.10, Fig 6); retrofit intent (p.12); finance barriers (p.15); payback/grant impact (pp.18–19); comfort framing (p.19, Fig 14) |
| **CRU202566** | `Consumer insights and studies/CRU Documents/CRU202566-...pdf` | 45% PCW usage (Exec Summary p.1); 4 new requirements (Exec Summary p.2); 1.9M meters (Section 1.1 p.11); dynamic tariffs / June 2026 deadline (Section 4.2 pp.23–24) |
| **CRU202579** | `Consumer insights and studies/CRU Smart Meter Upgrade.../CRU202579-...pdf` | 1.9M meters (Exec Summary p.2); LED pulse + P1 port (Section 1.2 p.9); market-led invitation (Exec Summary p.2 + Section 3.1 p.14–15); IHD 2–4% reduction (Section 3.1 p.14, fn.16); 80% smartphones (Section 3.1 p.14, fn.19) |
| **CRU2024121** | Referenced in CRU202566 Section 4.2 fn.15 — not held locally | Dynamic tariff decision (September 2024): 5 obligated suppliers, June 2026 deadline |
| **CSO HEBEU 2024** | https://data.cso.ie/product/HEBEU | Tariff awareness, switching rates, TOU adoption — **table-level refs require PxStat query** |
| **Kazempour BTM** | arxiv:2501.18017 | BTM asset inference from smart meter data — detection methodology |
| **RENEW Project (IRESI)** | https://www.iresi.eu/renew/ | AI-enabled HEMS, demand flexibility, community energy — €2M NCF prize Dec 2025 |
