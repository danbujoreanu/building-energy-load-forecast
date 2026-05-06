# MyEnergi Poller — Complete Technical Walkthrough
*Part of the Explainers/ series. Local only — not tracked in git.*
*Covers: nightly poll design, cgi-jday field mapping, h1b+h1d vs hsk bug, backfill script*
*Last updated: 2026-05-06*

---

## What This Document Is

A technical walkthrough of `deployment/myenergi_poller.py` — the nightly job that fetches minute-level data from the MyEnergi Eddi hub, converts it to 30-min kWh slots, and persists it to TimescaleDB. Includes a detailed account of the `hsk` field bug discovered April 2026 and the `scripts/backfill_myenergi_eddi.py` correction.

---

## What the Poller Does

The poller runs at **23:30 Europe/Dublin** (APScheduler `CronTrigger`) to capture the full day's data before midnight. It does four things:

1. **Fetches minute-level Eddi data** via `cgi-jday-E{serial}-YYYY-MM-DD` → list of ~1440 minute entries
2. **Aggregates to 30-min kWh intervals** → upserts into `myenergi_readings`
3. **Logs actual GHI** from Open-Meteo archive API → upserts into `weather_log` (data_type='actual')
4. **Upserts daily totals** → `solar_actuals.eddi_kwh` + `solar_actuals.ghi_actual`

---

## The MyEnergi cgi-jday API

### Endpoint

```
GET https://director.myenergi.net/cgi-jday-E{HUB_SERIAL}-{YYYY}-{MM}-{DD}
Authorization: Digest (hub serial + API key)
```

The director endpoint first redirects to the actual hub server (e.g., `s18.myenergi.net`). The response is:

```json
{
  "U21509692": [
    {"hr": 0, "min": 0, "imp": 12345, "h1b": 0, "h1d": 0, ...},
    {"hr": 0, "min": 1, ...},
    ...
  ]
}
```

Entries only appear for minutes where there is *something* happening — the list is sparse. Minutes with no activity are absent entirely (not zero-filled). The parser handles this by building a `by_minute: dict[int, dict]` keyed on `hr * 60 + min`.

### Key fields

| Field | Meaning | Units |
|-------|---------|-------|
| `hr`, `min` | Hour and minute of the reading | Local time |
| `imp` | Grid import power | Instantaneous centi-Watts |
| `h1b` | Heater 1 boost power (grid-sourced) | Instantaneous centi-Watts |
| `h1d` | Heater 1 divert power (solar-sourced) | Instantaneous centi-Watts |
| `hsk` | Heat-sink status counter | **NOT energy — do not use** |
| `v1`, `frq` | Voltage and frequency | Volts, Hz |

**Important**: The first entry in the list (midnight) often has no `hr` or `min` key — both default to 0. The parser uses `.get("hr", 0)` and `.get("min", 0)` to handle this.

### cW → kWh conversion

All power fields are **instantaneous** centi-Watts sampled once per minute.

```
kWh for 30-min slot = avg_cW * 0.5h / 100 / 1000
                    = avg_cW * 0.5 / 100_000
```

The 0.5 is for the 30-minute slot duration in hours. The `/100` converts centi-Watts to Watts. The `/1000` converts Watt-hours to kWh.

---

## The `hsk` Bug (Root Cause Analysis)

### What was wrong

The original code used:

```python
avg_eddi_cw = sum(s.get("hsk", 0) for s in slot_samples) / len(slot_samples)
```

`hsk` is a **heat-sink status counter** — a slowly-incrementing integer that tracks thermal state (ranges roughly 373–503 over a day). It is **not** an energy field and should never be used in energy calculations.

### How the bug manifested

`hsk` ≈ 430 (typical midday value):

```
430 cW × 0.5h / 100 / 1000 = 0.00215 kWh per slot
× 48 slots/day = 0.103 kWh/day
```

The database showed `eddi_kwh ≈ 0.1 kWh/day` for all 846 historical days — exactly matching this calculation.

The true expected value from manual Eddi check-ins was ~1.7–2.5 kWh/day (two grid boosts × ~0.55 kWh each = 1.1 kWh minimum, plus solar diversion on sunny days).

### How it was discovered

During panel factor calibration work:
1. `solar_actuals.panel_factor_obs` was computing to ~0.37 (expected ~1.6)
2. Cross-referencing ESB export data with myenergi data revealed Eddi diversion appeared near-zero
3. Live API inspection of April 28 data showed:
   - `h1b ≈ 174,000 cW` at 06:00 UTC (= 07:00 Dublin grid boost)
   - `h1b ≈ 178,000 cW` at 18:45 UTC (= 19:45 Dublin grid boost)
   - `hsk` ranging 373–503 slowly throughout the day (a counter, not power)
4. The `hsk` misidentification was confirmed by verifying `h1b + h1d` produced the correct daily total

### The fix

```python
# Before (wrong):
avg_eddi_cw = sum(s.get("hsk", 0) for s in slot_samples) / len(slot_samples)

# After (correct):
# h1b = grid boost (centi-Watts), h1d = solar diversion (centi-Watts).
# hsk is a heat-sink status counter, NOT energy — do not use it here.
avg_eddi_cw = sum(s.get("h1b", 0) + s.get("h1d", 0) for s in slot_samples) / len(slot_samples)
```

Verification: dry-run on April 28 produced `eddi_kwh=2.248 kWh` — two boosts visible.

---

## Backfill Script

All 846 historical days (2024-01-01 → 2026-04-29) had wrong `eddi_kwh` values. The backfill script corrects them:

```bash
export $(cat .env | grep -v '#' | xargs)
python scripts/backfill_myenergi_eddi.py [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--dry-run]
```

What the backfill does for each date:

1. Calls `_fetch_day_minutes(d)` — live API fetch (the same function the poller uses)
2. Runs `_aggregate_to_30min(minutes_raw, d)` — now using corrected `h1b + h1d`
3. Upserts all 48 slots into `myenergi_readings` via `ON CONFLICT DO UPDATE`
4. Queries `weather_log` for that date's actual GHI
5. Upserts into `solar_actuals` with corrected `eddi_kwh` + `ghi_actual`

The 0.4 s sleep between API calls avoids hammering the residential hub. Total runtime: ~6 min for 846 days.

---

## `solar_actuals` Population Chain

Three separate jobs each contribute a column to `solar_actuals`:

```
ESB CSV upload         → meter_readings.export_kwh
  ↓
_sync_solar_actuals()  → solar_actuals.export_kwh   (APScheduler 23:45)
(deployment/app.py)

myenergi_poller        → solar_actuals.eddi_kwh      (APScheduler 23:30)
(deployment/myenergi_poller.py)

myenergi_poller        → solar_actuals.ghi_actual    (APScheduler 23:30)
(deployment/myenergi_poller.py, via Open-Meteo archive)
```

`panel_factor_obs` is computed inline by the `_UPSERT_SOLAR_ACTUALS` SQL:

```sql
panel_factor_obs = ROUND(
    ((solar_actuals.export_kwh + COALESCE(EXCLUDED.eddi_kwh, 0)) / EXCLUDED.ghi_actual)::NUMERIC,
    4
)
```

This only fires when `ghi_actual > 0` AND `export_kwh IS NOT NULL`. Both conditions failed historically because:
- `export_kwh` was NULL (no `_sync_solar_actuals()` job existed before DAN-149)
- `eddi_kwh` was wrong (~0.1 kWh/day from `hsk`)

Both are now fixed. After the backfill completes, run `calibrate_panel_factor.py` to recompute a valid PANEL_FACTOR constant.

---

## Eddi Schedule (Home Setup Reference)

| Boost | Local time | UTC | Rate | Notes |
|-------|-----------|-----|------|-------|
| Grid boost 1 | 07:00 +30 min | 06:00 UTC (winter) / 05:00 (summer) | Night | End of night rate; ~0.55 kWh |
| Grid boost 2 | 19:45 +30 min | 18:45 UTC (winter) / 17:45 (summer) | Day | Post-peak; tank for morning shower |
| Solar divert | All day | — | Free (solar) | Variable; `h1d` field |
| Free Sat boost 1 | 09:15 +3h | — | Free Sat | Within 09:00–17:00 window |
| Free Sat boost 2 | 14:00 +3h (ends 17:00) | — | Free Sat | Ends exactly at free window close |

The `h1b` peaks in the DB at boost start times; `h1d` peaks during midday solar hours.

---

## Decision Log

| Decision | What we chose | Why | Alternatives rejected |
|----------|--------------|-----|----------------------|
| `h1b + h1d` for Eddi energy | Sum both fields | `h1b` = grid-sourced boost; `h1d` = solar diversion; both are physical power fields in centi-Watts | `hsk` (status counter, not energy) — was the original bug |
| Sparse minute list → `by_minute` dict | Build indexed dict, then query by minute range | API returns only active minutes (no zeros for idle minutes). Dict lookup is O(1) vs scanning the list. | Fill all 1440 slots with 0 — requires knowing which minutes are missing, adds memory |
| 0.4 s sleep between backfill API calls | Rate limit to ~2.5 req/s | Residential hub (not a cloud API); no documented rate limit but aggressive polling could lock out the hub or trigger auth resets | No sleep — risk hub refusal; 1 s sleep — doubles backfill time for no extra safety benefit |
| Dry-run mode in backfill script | `--dry-run` flag skips DB writes | Allows verifying corrected values before committing all 846 days | No dry-run — any formula bug would corrupt all historical data with no easy recovery |
| `ON CONFLICT DO UPDATE SET eddi_kwh` | Full update on conflict | Idempotent: backfill can re-run safely; later poller re-runs also safe | `DO NOTHING` — would leave wrong values in place if a date already exists |
| `_sync_solar_actuals()` as separate 23:45 job | Separate from poller | ESB export data arrives via manual upload; myenergi arrives nightly. Decoupling means either can fail independently without losing the other's data | Single combined job — export data not available at poller time; combined job would silently ignore missing export |

---

## Changes Since Initial Write (2026-05-06)

### Migration 007 — `panel_factor_seasonal` now exists
`households` table now has `panel_factor_seasonal` JSONB and `panel_factor_obs` NUMERIC.
The `_recompute_panel_factor_seasonal` job (APScheduler 23:45) was silently failing on NUC
because this column was missing from the live DB (the NUC volume was created before the column
was added to `init.sql`). Migration 007 applied 2026-05-06, now fixed.

### Backfill scripts — two different scripts, different purposes

| Script | Purpose | When to use |
|--------|---------|-------------|
| `scripts/backfill_myenergi_eddi.py` | Corrects `eddi_kwh` using `h1b+h1d` after the `hsk` bug. Fetches 846 days (2024-01-01 to 2026-04-29). | **One-time historical correction** — already run |
| `scripts/myenergi_backfill.py` | General date-range backfill. Same as the nightly poller but accepts `--start-date`/`--end-date` args. | **Fill gaps** — run after NUC deploy or to backfill from Eddi installation date |

**Running on NUC** (scripts dir isn't in the Docker image, use `docker cp`):
```bash
# On NUC host:
docker cp ~/sparc/scripts/myenergi_backfill.py sparc-api:/app/scripts/myenergi_backfill.py
docker exec sparc-api python /app/scripts/myenergi_backfill.py --start-date 2025-XX-XX
# DATABASE_URL is automatically picked up from the container env (db:5432)
```

### Grafana Free Saturday panels now query `myenergi_readings`
Panels 22 and 25 in `household_intelligence.json` were switched from `meter_readings`
(ESB CSV) to `myenergi_readings` (live hub data). Query joins via `households.hardware_id = myenergi_readings.hub_serial`. ESB CSV remains in `meter_readings` for delta validation only.

### LP Thermal Dispatcher uses myEnergi context
`lp_dispatcher.py` receives `solar_surplus_kw` input (future: from `solar_actuals.eddi_kwh`
and `SolarBaselineModel`). Currently zero until enough data accumulates. The LP also
schedules grid boosts to complement the Eddi's automatic solar diversion — it only controls
grid-sourced heating, never overrides the hub's solar diversion logic.

---

## References

- `deployment/myenergi_poller.py` — poller implementation
- `deployment/scheduler.py` — APScheduler job registrations (poller at 23:30, solar_actuals at 23:45)
- `scripts/backfill_myenergi_eddi.py` — historical correction script (hsk bug, one-time use)
- `scripts/myenergi_backfill.py` — general gap-fill backfill script
- `scripts/calibrate_panel_factor.py` — PANEL_FACTOR recalibration (run after backfill)
- `docs/explainers/SOLAR_ADVISORY_EXPLAINED.md` — how PANEL_FACTOR is used in the advisory
- `docs/explainers/LP_DISPATCH_EXPLAINED.md` — LP thermal dispatcher design and pricing model
