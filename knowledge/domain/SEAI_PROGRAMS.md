# SEAI Programmes — Irish Home Energy Grants
*Relevant to the diagnostic pathway in APP_PRODUCT_SPEC.md. Updated: 2026-03-15*
*Source: seai.ie + SEAI grant schedule 2024–2026*

---

## Available Grants (Homeowner-managed path)

| Upgrade | Max Grant | Notes |
|---------|-----------|-------|
| Solar PV ≤2kW | €2,100 | Grid-connected |
| Solar PV 2–4kW | €3,200 | Most Irish homes land here |
| Heat pump (air-to-water) | €6,500 | Most common; replaces gas/oil boiler |
| Heat pump (ground source) | €6,500 | Higher install cost, higher efficiency |
| Heating controls | €700 | Smart thermostat + TRVs |
| BER assessment | Up to €50 | Required for most grants |
| Cavity wall insulation | Up to €1,700 | |
| External/internal insulation | Up to €8,000 | |
| Attic insulation | Up to €1,500 | |

*Battery storage: NO current SEAI grant (standalone). Grant only when installed with new solar PV.*

## Programmes

### 1. Better Energy Homes
- Individual grants for specific upgrades
- Homeowner selects registered contractor from SEAI list
- Application before AND after work
- No minimum BER target required per upgrade

### 2. National Home Energy Upgrade Scheme (One Stop Shop)
- Target: whole house to minimum BER B2
- Single contractor manages all works end-to-end
- Typically: insulation + heat pump + solar in one project
- Higher grants than individual path for combined works
- **Implication for app**: If user's BER is D or below, this pathway is the better recommendation
  (can access higher blended grants and sequence is managed for them)

### 3. Warmer Homes Scheme
- Fully funded (100%) for recipients of certain welfare payments
- Homes built before 2006
- SEAI surveyor recommends upgrades
- **App eligibility check**: ask "are you on a means-tested payment?" → surface Warmer Homes

---

## Key Facts for Payback Calculations

- Solar PV (4kW system): €8,000 install – €3,200 grant = **€4,800 net cost**
  At 40c/kWh avoided export + 18.5c/kWh credit: typical Irish home saves ~€700–900/year
  Payback: ~5–7 years after grant
- Heat pump: €14,000 install – €6,500 grant = **€7,500 net cost**
  Gas replacement saving: €800–1,400/year (depends on insulation, thermostat behaviour)
  Payback: ~6–9 years — only viable in well-insulated home
- Insulation first: +30% improvement in heat pump efficiency → reduces payback by 2–3 years
- **Battery (standalone, no grant)**: ~€8,000 install, ~€400/year savings → 20-year payback
  Battery only justified when: solar > 3kW + TOU spread > 15c/kWh + high evening consumption

---

## The Sequencing Rule (from reimagine-energy.ai research)

Order: **Insulation → Heating Controls → Heat Pump → Solar → Battery**

- Efficiency measures *before* solar: solar self-consumption ratio is higher → better ROI
- Efficiency *after* solar: lower self-consumption (house was already wasting less), solar ROI drops ~28%
- Heat pump *after* insulation: undersized heat pump in uninsulated house = expensive and insufficient
- Battery *last*: only after solar profile and TOU tariff are established (need to know the arbitrage spread)

---

## App Integration Notes

- Layer 0–2 (behaviour + tariff): no SEAI involvement; fully automated from app
- Layer 3–5 (controls + insulation + solar): surface SEAI grants with personalised payback calculator
- Layer 6–7 (battery + heat pump): full SEAI grant lookup + recommended contractors from SEAI register
- **LLM advisor angle**: "Your solar panels generate ~2,800 kWh/year. Adding a 5kWh battery would cost ~€7,500 (no grant). Your current TOU spread is 17c/kWh. Estimated saving: €380/year. Payback: ~20 years. My recommendation: wait for battery grant or higher TOU spread before investing."

---

## Partnership / Referral Model

SEAI → registered One Stop Shop contractors → our app for pre-qualification
Our app → identifies upgrade opportunity → refers to SEAI grant page + contractor directory
Potential: SEAI co-branding or referral agreement (Climate Action alignment)
