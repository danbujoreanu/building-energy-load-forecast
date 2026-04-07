# Tariff Knowledge — BGE Free Time Saturday + Scoring Model

---

## BGE Free Time Saturday Rates (with 20% Affinity Discount — valid to 15 June 2026)

| Slot | Rate (after discount) | When |
|------|-----------------------|------|
| Day | 32.27 c/kWh | Mon–Sun outside other slots |
| Night | 23.72 c/kWh | 23:00–08:00 |
| Peak | 39.42 c/kWh | **Mon–Fri 17:00–19:00 ONLY** — NOT Saturday |
| Free Time | 0 c/kWh | Saturday 09:00–17:00 |
| Export | 18.5 c/kWh | Net export credit |
| Standing charge | 61.52 c/day | Always |

**Critical**: Peak is weekday ONLY (`weekday() < 5`). Saturday 17-19 is day rate, not peak.
**Cap**: BGE claims "up to 100 kWh/month" free. In practice, no hard cap observed in ESB data.
**Discount expires**: 15 June 2026. Check renewal 90/30/7 days before (=16 Mar / 15 May / 8 Jun 2026).

---

## Plan Optimisation Score — Formula

Score = free_score × 0.50 + peak_score × 0.30 + night_score × 0.20

```
free_score   = min(100, (monthly_free_avg / 100) × 100)
peak_score   = max(0, 100 − (peak_pct × 15))
night_score  = min(100, night_pct × 3.0)
```

Where:
- `monthly_free_avg` = average kWh consumed in Saturday 09:00–17:00 per month
- `peak_pct` = peak kWh as % of total import
- `night_pct` = night kWh as % of total import

**Dan's scores** (Oct 2023 – Oct 2025):
- `free_score` = 54 (53.9 kWh/month average, 54% of 100 kWh cap)
- `peak_score` = 55 (3% peak exposure — acceptable for working household)
- `night_score` = 94 (31% night usage — excellent, Eddi 07:00 boost drives this)
- **Overall: 62/100**

---

## Scoring Nuances (known limitations)

**Summer free-window undercount**: May–Sep Saturday free kWh drops to 20–45 kWh because
solar diversion (Eddi) is covering demand. The free window score understates performance —
actual energy cost is zero on those Saturdays regardless.
→ TODO: Add `solar_diverted_on_saturdays` to free window calculation when Eddi history is available.

**Peak score**: 3% peak exposure is reasonable for a working household. Some loads (cooking,
returning home, shower) cannot be shifted away from 17–19. Score should contextually distinguish:
- "Avoidable" peak: Eddi boost during peak, EV charging during peak → recommend shift
- "Unavoidable" peak: kettle, shower on arriving home → note but don't penalise

**Season adjustment**: TODO — weight free_score by expected solar potential.
In summer, even 20 kWh free Saturday score is "good" if solar covered the rest.

---

## Plan Comparison Framework (future feature)

Priority of plan optimisation: **optimise current plan FIRST, then assess battery ROI**.
A battery assessed on a suboptimal plan will show inflated ROI — misleading the user.

Steps:
1. Score current plan (done)
2. Identify shifting opportunities (free window, night window)
3. Calculate optimised plan cost
4. THEN calculate battery ROI on the OPTIMISED baseline (not current)
5. Then recommend plan switch if battery + plan optimised together justify it

Battery considerations for Ireland:
- Battery typical cost: €6,000–10,000 for 5 kWh (BYD, Growatt, Tesla Powerwall)
- SEAI grant: not currently available for standalone battery (only with new solar install)
- Payback driver: same-day solar arbitrage (store midday → use evening)
- NOT seasonal storage — never. 1–2 day storage only.
- At current Irish prices (40c/kWh day, 18.5c/kWh export), battery saves ~€0.215/kWh cycled
- A 5 kWh battery cycling once daily = ~€0.215 × 5 × 365 = ~€393/year savings
- Payback: €8,000 / €393 ≈ 20 years — marginal unless solar + TOU tariff makes it stronger
- Recommendation: only advise battery AFTER confirming solar capacity + optimised plan

---

## ESB Data
- File: `/Users/danalexandrubujoreanu/Downloads/HDF_calckWh_10306822417_22-10-2025.csv`
- MPRN: 10306822417 | Meter serial: 33140689
- Format: 30-min intervals, "Active Import/Export Interval (kWh)"
- Date range: 2023-10-22 → 2025-10-20 (730 days)
- Score script: `python scripts/score_home_plan.py --csv <path>`
