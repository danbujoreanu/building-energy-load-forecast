# ADR-013: Irish Training Data Strategy for Load Forecasting

**Date:** 2026-05-08
**Status:** Accepted
**Linked issue:** DAN-169

---

## Context

The LightGBM H+24 load forecast model is currently trained on Norwegian Drammen building data. To validate the thesis claim that the model transfers to Irish residential households, we need a suitable Irish dataset.

Three options were considered:

| Option | Dataset | Pros | Cons |
|--------|---------|------|------|
| **A — Dan's ESB data** | 3 years of Dan's household smart meter data | Available immediately, Irish, real | Gas boiler household → flat electrical load, no weather-electricity correlation; cannot represent heat pump persona (Sparc's primary buyer) |
| **B — CER Smart Metering Trial** | ~5,000 anonymised Irish households, half-hourly, 2009–2010, ISSDA | Large, Irish, half-hourly | **2009–2010 data: no heat pumps in Ireland at that time. Zero weather-correlated electrical load for heating. Cannot answer the thesis question for electrically-heated homes.** |
| **C — Synthetic** | Irish weather + heat pump COP curves | Fast | Less authentic; harder to defend in thesis |
| **D — Norwegian model + Irish calendar** | Norwegian Drammen (already trained) + Irish calendar features (school terms, bank holidays, DST) | Immediately available; Drammen has electric heating + strong weather correlation | Cross-domain transfer claim needs explicit framing and validation |

---

## Decision

**Use Option D as the immediate validation path.** The Norwegian model is validated on Drammen buildings which have electric heating — this is a better proxy for Irish heat pump households than either Dan's gas-heated household or the 2009–2010 CER data.

Option B (CER data) is ruled out: heat pump penetration in Ireland in 2009 was negligible. The CER dataset would show the same flat electrical load as Dan's household — weather correlation was dominated by gas/oil heating, not electricity.

**Thesis framing:** This becomes the cross-domain transfer section:
- Claim: "A model trained on electrically-heated Norwegian buildings transfers to electrically-heated Irish homes"
- Evidence: Norwegian model performance on Irish calendar features; comparison to same-hour-last-week naive baseline

---

## Consequences

1. **Unblocks DAN-167** (forecast accuracy evaluation pipeline) — no new training data needed; existing model generates predictions once Irish calendar features are added
2. **Research question refinement** — thesis should explicitly scope to "households with weather-correlated electrical load" (heat pump / storage heater owners), not all Irish households
3. **Future work** — when a more current Irish heat pump household dataset becomes available (SEAI home survey, grid operator programs), retraining is straightforward
4. **Option A remains useful** — Dan's household data is correct for validating *advisory accuracy* (Track 1: GHI forecast vs actual, SKIP/KEEP correctness), just not for load forecasting validation

---

## Notes

- CER data ISSDA application not pursued (ruled out by this ADR)
- If a collaborator with heat pump household smart meter data becomes available, revisit
- The `panel_factor_obs` calibration loop in `solar_actuals` is unaffected — it uses Eddi/export data, not load forecasting
