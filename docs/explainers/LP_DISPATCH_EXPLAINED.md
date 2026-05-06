# LP Thermal Dispatch — Explainer
*DAN-164 Stream 3 | `src/energy_forecast/control/lp_dispatcher.py`*

---

## What It Does

The LP dispatcher answers one question daily: **when should the Eddi immersion heater run from the grid (instead of waiting for solar)?**

It uses **linear programming** (scipy HiGHS solver) to minimise the electricity cost of heating the hot-water cylinder over a 24-hour horizon, subject to physical temperature constraints.

---

## What It Does NOT Control

- **Home heating (gas boiler)** — completely separate system, not modelled here.
- **EV charging** — separate logic (DAN future).
- **Solar diversion** — Eddi always diverts solar when available, regardless of this schedule. The LP only governs **grid boosting** (pulling from the grid deliberately).

---

## Pricing Model

Ireland is **not** on dynamic/day-ahead electricity pricing (as of 2026). Residential customers pay fixed tariff slots.

The LP uses **retail BGE tariff rates** (`src/energy_forecast/tariff.py`):

| Slot | Hours | Rate (incl. 20% Affinity) |
|------|-------|--------------------------|
| Night | 23:00–07:59 | €0.2372/kWh ← cheapest |
| Day | 08:00–22:59 | €0.3227/kWh |
| Peak | Mon–Fri 17:00–18:59 | €0.3942/kWh ← avoid |
| Free | Saturday 09:00–16:59 | €0.00/kWh ← use first |

**SEMO wholesale prices** (fetched at 14:00 daily by `_fetch_semo_prices`) are stored in the `semo_prices` table for monitoring and future dynamic-tariff customers. They are **not** used by the LP dispatcher.

---

## Tank Temperature Model

The LP models the hot-water cylinder as a thermal store with:

- `tank_volume_liters = 200 L` (typical Irish hot-water cylinder)
- `max_heater_kw = 3.0 kW` (standard Eddi immersion)
- `min_temp_c = 45°C` — Legionella safety floor
- `max_temp_c = 65°C` — immersion thermostat cutoff

**How temperature is calculated:**
```
temp[h] = initial_temp
          + Σ_{i≤h} (grid_boost[i] + solar[i]) × η / capacity_kwh_per_C
          - Σ_{i≤h} draw_energy[i] / capacity_kwh_per_C
```

Where:
- `capacity_kwh_per_C = 200 L × 0.001163 kWh/L/°C = 0.2326 kWh/°C`
- `η = 1.0` (resistive immersion is ~100% efficient)
- `draw_energy[h]` = estimated daily draw spread across waking hours (06:00–22:00)

**Initial temperature:** Hardcoded to 55°C (no sensor). A future improvement (DAN-166) would infer it from the previous day's Eddi run log.

---

## Decision Variable

`grid_boost_kw[h]` for h in 0..23 — how much to pull from the grid each hour. Bounded `[0, max_heater_kw]`.

**Objective:** minimise `Σ_h  price[h] × grid_boost_kw[h]`

---

## Example Output

**Wednesday** (typical day):
```
Heat grid: 06:00–07:59, 15:00–15:59 | avg 0.266 €/kWh | est. €1.50/day
```
Interpretation: heat at last 2 night-rate hours (right as morning draw starts), pre-load at 15:00 to avoid the 17:00–18:00 peak window. No heating during peak.

**Saturday** (BGE Free Saturday):
```
Heat grid: 06:00–07:59, 09:00–16:59 | avg 0.047 €/kWh | est. €0.27/day
```
Interpretation: LP picks all 8 free hours (€0.00) + 2 night-rate hours. Cost drops from €1.50 to €0.27 vs a normal day.

---

## Fallback

If the HiGHS solver fails (infeasible constraints, missing scipy), the dispatcher falls back to a **greedy cheapest-N-hours** rule:
- Calculates energy needed to go from `min_temp` to `max_temp`
- Excludes hours with meaningful solar surplus (≥ 0.5 kW)
- Picks the cheapest remaining hours

Result is marked `fallback_used=True` in the `DispatchResult`.

---

## Scheduler Integration

```
14:00  _fetch_semo_prices     → stores SEMO wholesale prices (monitoring only)
14:30  _run_lp_dispatch       → builds BGE tariff curve for tomorrow
                                → LPThermalDispatcher.optimize()
                                → INSERT 24 rows into recommendations
                                → Pushover: "Heat grid: 06:00–07:59…"
```

---

## Database

Results stored in `recommendations` table (migration 005) — 24 rows per day per household:

| Column | Value |
|--------|-------|
| `household_id` | UUID |
| `target_hour` | 0–23 |
| `action` | `HEAT_NOW` or `DEFER_HEATING` |
| `confidence` | 0.70–0.90 |
| `reasoning` | `LP: boost 3.00 kW at 0.2372 €/kWh → 0.712 € estimated cost` |
| `price_eur_kwh` | retail tariff rate for that hour |

Re-running at 14:30 deletes and replaces today's LP rows (idempotent).

---

## Origin Note

The LP formulation concept came from a handoff (`claude_handoff/lp_thermal_dispatch.py`) referencing an open-source Home Assistant integration. Our implementation is a complete independent rewrite with different structure, BGE retail pricing (not Nordic/SMP), graceful fallback, type annotations, and 19 tests. No code was copied.

---

## Tests

`tests/test_lp_dispatcher.py` — 19 tests covering:
- LP solve returns 24 elements within heater bounds
- Cheap night → LP concentrates heating in cheap window
- Solar surplus → reduces total grid boost
- Fallback: greedy correctly picks cheapest hours
- `DispatchResult.to_control_actions()` → 24 ControlAction objects
- `_compress_hours` utility

---

## Known Limitations / Future Work

| Limitation | Fix |
|-----------|-----|
| Initial tank temp hardcoded at 55°C | Infer from yesterday's Eddi kWh log (DAN-166) |
| Daily draw distribution is uniform estimate | Use historical shower/draw patterns once data accumulates |
| Single-household MVP | Scheduler loops over all households already |
| Solar surplus input is zero | Wire to SolarBaselineModel.predict() output once 60d of data exists |
| BGE tariff hardcoded | Read `day_rate_eur`/`night_rate_eur` from households table per customer (DAN-152 done) |
