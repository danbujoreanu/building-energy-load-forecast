# Pallonetto / RENEW — Contact Log and Next Steps
*Prof. Fabiano Pallonetto, IRESI / Maynooth University*
*fabiano.pallonetto@mu.ie*
*Updated: April 2026*

---

## Status: WAITING — No response since April 8 call

Initial call with Prof. Pallonetto completed April 8. PhD/collaboration angle explored.
*(Source: Orchestrator ACTION_ITEMS.md, completed section)*

**No response received since the call (as of April 15, 2026).** User decided to wait rather than chase.

### PhD Context — Updated Priority
**Decarb-AI (UCD-led) is now the active PhD track:**
- Programme: *Decarbonising Ireland: AI-Powered Pathways to Climate Resilience*
- Stipend: €31k/year tax-free + fees paid (4 years)
- Start: Autumn 2026; 10 positions; Round 2 application submitted via Google Form
- Interview: **Tue Apr 21, 15:00 with Andrew Parnell (UCD)** — see prep brief at `Career/Applications/Active/PhD - Decarb-AI Energy/prep_brief_2026-04-10.md`
- Topic alignment: AI-optimised renewable energy systems, transparent AI decision-support, energy-efficient AI infrastructure

**RENEW / Pallonetto = research-only contingency.** If Decarb-AI is successful, the Pallonetto angle becomes a research collaboration without the PhD ask. If Decarb-AI is unsuccessful, revisit as PhD Route 2.

---

## Post-Call Follow-Up Email

*Use this if/when you decide to follow up. Personalise based on what was agreed on the April 8 call.*

**To:** fabiano.pallonetto@mu.ie
**Subject:** Follow-up — RENEW / Load Forecasting Collaboration

---

Dear Fabiano,

Thank you for the time on April 8 — it was a genuinely useful conversation. I wanted to follow up briefly to confirm next steps as we discussed.

[Personalise: summarise the 1–2 things that were agreed or that he expressed interest in — e.g. seeing the pipeline demo, a specific dataset question, the PhD funding structure, etc.]

To recap what I can contribute on the technical side:
- Household-level H+24 load forecast: LightGBM, MAE 0.171 kWh/hr on Irish residential HDF data
- Live myenergi Eddi API integration — hot water scheduling against tariff signals
- Full deployment stack: FastAPI, Docker, AWS App Runner (eu-west-1)
- Published: AICS 2025 (Springer CCIS); journal paper targeting Applied Energy in progress

The specific value for RENEW's HEMS is the forecasting layer — answering "what will this household consume in each 30-minute slot tomorrow, at what cost?" upstream of the control decisions.

[Add specific next step agreed on call — e.g. "I'll send you the GitHub repo link" / "Happy to do a 20-min demo when convenient" / "I'll look into the GOIPG structure and come back to you"]

Thanks again,

**Dan Bujoreanu**
MSc AI (NCI) | BSc Mathematics | Maynooth, Co. Kildare
[email] | [LinkedIn] | github.com/danbujoreanu/building-energy-load-forecast

---

## PhD / Funding Structure — Reference

- **Decarb-AI (ACTIVE TRACK):** €31k/year tax-free + fees, 4 years, UCD-led, Autumn 2026. Interview Apr 21.
- **Irish Research Council GOIPG stipend:** ~€22k/year + fees — fallback if Decarb-AI unsuccessful
- **RENEW NCF prize (€2M):** May have PhD capacity — secondary option only
- **NexSys SFI partnership:** Could support a co-funded studentship
- **Reframe:** Decarb-AI is the primary PhD path. RENEW/Pallonetto = research collaboration regardless of PhD outcome. If Okta or senior role comes through, PhD becomes a 2027 conversation.

## What to Bring to Any Follow-Up Meeting

- One-page technical brief (architecture diagram: Data → Intelligence → Control layers)
- Home Plan Score demo: 62/100 score, €178.65/yr identified saving, live Eddi schedule
- `docs/PROJECT_OVERVIEW.md` — shareable end-to-end brief if he asks for something to circulate internally
