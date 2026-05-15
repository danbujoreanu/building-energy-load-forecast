# Eddi Solar Diversion Bug — Investigation Log
*Property: 107 Carton | Date: 2026-05-07 | Eddi serial: 21509692*
*Linked issue: DAN-168*

---

## The Problem

The Eddi is splitting solar surplus exactly 50/50 between the hot water tank and the grid. On a sunny day (~1,300 W peak solar), the Eddi diverts ~650 W to the tank while simultaneously exporting ~650 W to the grid. This means roughly 3–4 kWh per sunny day goes to the grid instead of heating water for free.

---

## What the Data Shows

Minute-by-minute analysis of the MyEnergi API data for 2026-05-06 (sunny day, GHI 3.6 kWh/m²):

- Every single minute from 09:00–13:00: `h1d` (solar → Eddi) = `exp` (grid export) to within ±10 W
- This holds at every power level: 450 W, 500 W, 550 W, 600 W, 650 W, 700 W — the ratio never changes
- The split is exactly 50.0% — not approximately, not seasonally variable — it is mathematically exact at all generation levels
- When the tank thermostat trips (element turns off at temperature): export jumps to 1,300–1,400 W confirming total solar generation is ~1,300–1,400 W
- In winter / low-solar months: Eddi appears to capture 90%+ of surplus. This is because the "missing" 50% is small enough to be absorbed by household base load (lighting, appliances) and doesn't visibly export

---

## What Was Ruled Out

| Hypothesis | Why ruled out |
|------------|---------------|
| Element fault | Boost mode draws full 3 kW with no problem — element, wiring, MCB healthy |
| Tank thermostat cycling | Split happens simultaneously in real-time at fixed ratio; not sequentially |
| 3-phase CT boundary | All 7 panels face south on a single array; not split across phases |
| Seasonal / panel orientation | Split correlates with generation LEVEL (W), not time of year |
| CT wiring mismatch | CT CONFIG display shows CT INT=Internal Load, CT1=None, CT2=None — Eddi uses wireless Harvi data, not physical CT wires at the device |
| App / settings issue | Ciarán (Staff Engineer): "The dead-even 50/50 split is the tell. This is not a settings issue." |

---

## Root Cause

The Eddi uses ONE Harvi wireless sensor (serial **13541598**, currently showing `~` = active on the device screen).

The original installer stated at installation that a second Harvi would give a "clear picture" — it was never purchased or installed. Invoice dated at install confirms: **1× Harvi @ €57.33**. No second unit.

With only ONE Harvi, the Eddi receives incomplete measurement data. It can only "see" half of the net power flow between the solar panels and the grid. The eco-divert control loop balances the half it can see to zero — the other half exports uncontrolled.

The device screen also shows `harvi 13541116 ?` (offline — likely a neighbour's device picked up by the hub). Only serial 13541598 is ours.

---

## The Fix

Install a second MyEnergi Harvi wireless sensor.

- Hardware cost: ~€57–70 (same model as existing)
- Labour: ~€150–200 (electrician, ~1 hour)
- Payback: approximately one summer season

---

## Instructions for the Electrician

> "The Eddi has been diverting solar surplus exactly 50/50 between the hot water tank and grid export. We confirmed this from minute-by-minute API data — the split is exactly 50% at all power levels from 450 W to 700 W, indicating the Eddi only has visibility of half the solar power flow.
>
> We have one Harvi installed (serial **13541598**, currently showing `~` on the Eddi device screen). The original installer mentioned a second Harvi would give a clearer picture. It was never installed.
>
> Please:
> 1. Locate the existing Harvi — check which cable its CT clamp is installed on (solar generation cable, or main incomer?)
> 2. Install a second Harvi at the complementary measurement point:
>    - If existing Harvi is on the solar generation output → second Harvi goes on the main incomer
>    - If existing Harvi is on the main incomer → verify CT clamp orientation and install second on solar output
> 3. After installation, confirm both Harvis show as active (`~`) on the Eddi device screen
> 4. Check the MyEnergi app hub leaf — it should now show generation (currently shows 0% because the hub has no generation visibility)
>
> **Expected result after fix:** eco-divert should capture the full solar surplus (~1,300 W peak) instead of half. The app should show 0 W export during Eddi diversion sessions."

---

## Verification Query (run after fix)

```sql
SELECT
    solar_date,
    ROUND(ghi_actual::numeric, 2)                          AS ghi_actual_kwh,
    ROUND(eddi_kwh::numeric, 2)                            AS eddi_kwh,
    ROUND(export_kwh::numeric, 2)                          AS export_kwh,
    ROUND((eddi_kwh / NULLIF(ghi_actual, 0))::numeric, 3) AS diversion_efficiency
FROM solar_actuals
WHERE ghi_actual BETWEEN 3.0 AND 5.0
ORDER BY solar_date DESC;
```

**Before fix:** `diversion_efficiency` ≈ 0.35–0.45 on GHI 3–5 days, `export_kwh` ≈ `eddi_kwh`

**After fix:** `diversion_efficiency` should rise to 0.75–0.85+; `export_kwh` should drop to near zero during diversion hours

---

## Financial Impact

| Metric | Value |
|--------|-------|
| Wasted on 2026-05-06 (sunny day, GHI 3.6 kWh/m²) | ~4.2 kWh exported instead of heating water |
| Estimated annual waste (June–August, ~50 sunny days) | ~135–180 kWh |
| Lost at SEG export rate 18c/kWh | ~€24–32 |
| Same energy avoiding grid electricity at night rate 23.72c/kWh | ~€32–43 saved per summer |
| Second Harvi hardware + install | ~€220–270 one-off |
| Payback | ~2–3 summers (net gain = 23.72c − 18c = 5.72c/kWh diverted) |

---

## System Impact (beyond water heating efficiency)

Without the second Harvi, the following system components are also affected:

- **`est_solar_kwh` in the advisory** — currently ~2× the actual Eddi diversion → every SKIP recommendation is optimistic
- **`panel_factor_obs` auto-calibration** — calibrates from observed `eddi_kwh`; with 50% diversion it will converge on the wrong value, making the advisory progressively worse over time
- **Forecast accuracy baseline** — the ~15% cross-validation overcount vs ESB (identified in BST investigation) may partially be a phase netting issue

**Harvi install is P0 for the self-calibration loop to function correctly.**

---

*Related: DAN-168 — BUG: Eddi CT reads exactly 50% of solar surplus — equal split to tank and grid*
*Related: `docs/explainers/FORECAST_ACCURACY_EXPLAINED.md` — how advisory accuracy is evaluated*
