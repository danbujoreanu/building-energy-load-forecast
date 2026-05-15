# MyEnergi Poller — Complete Technical Walkthrough
*Part of the Explainers/ series. Local only — not tracked in git.*
*Covers: nightly poll design, cgi-jday field mapping, h1b+h1d vs hsk bug, backfill script*
*Last updated: 2026-05-07*

---

## What This Document Is

A technical walkthrough of `deployment/myenergi_poller.py` — the nightly job that fetches minute-level data from the MyEnergi Eddi hub, converts it to 30-min kWh slots, and persists it to TimescaleDB. Includes a detailed account of the `hsk` field bug discovered April 2026 and the `scripts/backfill_myenergi_eddi.py` correction.

---

## What The Poller Does

The poller runs at **00:15 Europe/Dublin** (APScheduler `CronTrigger`) to capture the full previous day's data. It does four things:

1. **Fetches minute-level Eddi data** via `cgi-jday-E{serial}-YYYY-MM-DD` → list of ~1440 minute entries
2. **Aggregates to 30-min kWh intervals** → upserts into `myenergi_readings`
3. **Logs actual GHI** from Open-Meteo archive API → upserts into `weather_log` (data_type='actual')
4. **Upserts daily totals** → `solar_actuals.eddi_kwh` + `solar_actuals.ghi_actual`

> [!IMPORTANT]
> **Why 00:15? (Edit by Antigravity)**
> Previously, the schedule was set to `23:30` to fetch data just before midnight. However, the Open-Meteo archive endpoint (used for actual GHI) returns a `400 Bad Request` if you query the current date. The archive only builds data for dates in the past. Moving the cron job to 00:15 requests data for "yesterday", allowing both the MyEnergi daily data and Open-Meteo archive data to succeed cleanly.


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
| `hr`, `min` | Hour and minute of the reading | **UTC** (not Dublin local) |
| `imp` | Total household grid import energy in this minute | **Joules** |
| `exp` | Grid export energy in this minute (solar surplus to grid) | **Joules** — persisted to `myenergi_readings.export_kwh` and aggregated into `solar_actuals.export_kwh` nightly (2026-05-13) |
| `h1b` | Heater 1 boost energy in this minute (grid-sourced) | **Joules** |
| `h1d` | Heater 1 divert energy in this minute (solar-sourced) | **Joules** |
| `hsk` | Heat-sink status counter | **NOT energy — do not use** |
| `v1`, `frq` | Voltage and frequency | Volts, Hz |

**Units confirmed 2026-05-07**: `h1b=181,680` at boost minute → 181,680 J ÷ 60 s = **3,028 W** (3 kW immersion heater ✓). Previously documented as centi-Watts, which was wrong — that interpretation gave 1,817 W (no such heater).

**`hr`/`min` are UTC**: Boost scheduled at 07:00 Dublin BST appears at `hr=6` in the API (06:00 UTC = 07:00 BST). See the UTC vs Dublin Timezone section below for full details on how the poller handles this and a known slot-alignment bug that was fixed 2026-05-07.

**`imp` scope**: Measures household grid draw via the hub's internal CT. Covers most circuits but has a small ~8% undercount vs ESB smart meter (confirmed 2026-05-07 by comparing API Joules totals with live MyEnergi app). Root cause: the hub CT does not yet see every circuit. **Will be fully corrected once Harvi CT clamp is installed on the main supply** — no code changes needed, `imp` will then equal total household grid import. `eddi_kwh` (h1b+h1d) is accurate regardless of Harvi.

**Important**: The first entry in the list (midnight) often has no `hr` or `min` key — both default to 0. The parser uses `.get("hr", 0)` and `.get("min", 0)` to handle this.

### J → kWh conversion

Energy fields (`imp`, `exp`, `h1b`, `h1d`) are **Joules per 1-minute interval** — total energy measured in that minute, not instantaneous power.

```
kWh for any slot = sum_of_J_in_slot / 3,600,000
```

Where 3,600,000 = 3,600 seconds/hour × 1,000 Wh/kWh.

**Previous (wrong) formula** — do not use:
```
# WRONG: treated values as cW, multiplied by 0.5h slot duration
# Underestimates by factor 1.667×
kWh = avg_cW * 0.5 / 100 / 1000
```

**Why the old formula underestimated**: `avg_J * 0.5 / 100 / 1000 = avg_J / 200,000`. Correct is `sum_J / 3,600,000`. For a 30-sample slot: `avg_J × 30 / 3,600,000 = avg_J / 120,000`. Ratio: 200,000 / 120,000 = **1.667×** undercount — matches the observed discrepancy vs MyEnergi app.

---

## UTC vs Dublin Timezone — Critical Details

### API uses UTC date boundaries; `hr`/`min` are UTC

The `cgi-jday-E{serial}-YYYY-MM-DD` endpoint returns data bounded by **UTC midnight**, not Dublin local midnight.

Verified empirically 2026-05-07:
- Requesting `2026-05-06` returns entries from `hr=0, min=0` (UTC 00:00 May 6) through `hr=23, min=59` (UTC 23:59 May 6) — plus one carry-over entry at the end (see below).
- The `dom` field in each entry reflects the UTC date.

In **winter (GMT, UTC+0)**: Dublin midnight = UTC midnight. No mismatch.

In **summer (BST, UTC+1)**: Dublin midnight = **UTC 23:00 of the previous day**. So:
- Dublin May 7 covers UTC 23:00 May 6 → UTC 22:59 May 7
- API for `2026-05-07` covers UTC 00:00 May 7 → UTC 23:59 May 7

The first hour of every Dublin summer day (00:00–01:00 Dublin = UTC 23:00–00:00 prev day) is not in that day's API response — it's in the **previous day's** API response.

### The slot-alignment bug (fixed 2026-05-07)

The `_aggregate_to_30min` function builds a `by_minute` dict keyed by `hr*60+min` (UTC-based, 0–1439). It then iterates `start_min = 0, 30, 60, …, 1410` (Dublin-local minutes from midnight) and looked up `by_minute[start_min]`. In BST these differ by 60:

| start_min | Dublin slot | interval_start (correct, UTC) | Keys looked up (old code) | UTC time of data fetched (old) | Keys looked up (fixed) | UTC time of data fetched (fixed) |
|-----------|-------------|-------------------------------|---------------------------|-------------------------------|------------------------|----------------------------------|
| 0         | 00:00 Dublin | UTC 23:00 May 6 (prev day)   | 0–29                      | UTC 00:00–00:29 May 7 ← **WRONG** | –60–(–31) (none) | (empty — data is in prev day's API) |
| 360       | 06:00 Dublin | UTC 05:00 May 7               | 360–389                   | UTC 06:00–06:29 = **07:00 Dublin boost** ← **WRONG** | 300–329 | UTC 05:00–05:29 (correct, no boost) |
| 420       | 07:00 Dublin | UTC 06:00 May 7               | 420–449                   | UTC 07:00–07:29 (empty, no boost) ← **WRONG** | 360–389 | UTC 06:00–06:29 = **07:00 Dublin boost** ✓ |

**Measured with live data (2026-05-07, BST):**
- Old code: 07:00 Dublin slot h1b = 0; 06:00 Dublin slot h1b = **5,317,015 J** (boost was here, 1 h early)
- Fixed code: 07:00 Dublin slot h1b = **5,317,015 J** ✓; 06:00 Dublin slot h1b = 0 ✓

**Fix** (`deployment/myenergi_poller.py`, applied 2026-05-07):
```python
# Compute UTC offset once per call (not inside the slot loop)
utc_offset_min = int(local_midnight.utcoffset().total_seconds() / 60)  # 0=GMT, 60=BST

# Use UTC-aligned key for by_minute lookup
utc_start = start_min - utc_offset_min
slot_samples = [by_minute[m] for m in range(utc_start, utc_start + 30) if m in by_minute]
```

### Impact on daily totals vs ESB

The slot-alignment bug shifts **timestamps** by 1 hour in BST but does **not** change **total daily kWh** — every UTC minute is still counted exactly once. Monthly cross-validation totals are unaffected.

What the fix changes for totals: in BST, the first 2 slots of each Dublin day (00:00–01:00 Dublin = UTC 23:00–00:00 of prev UTC day) are now correctly left empty — that energy belongs to the previous Dublin day's last 2 slots (which do include it via their own API response). Without the fix, each day received tomorrow's midnight data in its last 2 slots AND also read the current UTC midnight data in its first 2 slots — a subtle double-count at the day boundary. Impact: ≤ 2 slots × ~0.2 kWh each = **~0.4 kWh per summer day** over-count eliminated.

### ESB comparison: date alignment

The ESB smart meter CSV uses **Dublin local date boundaries** for its daily totals. The corrected MyEnergi daily total now also covers Dublin 00:00–23:59 (via the UTC-aligned lookup). Monthly totals from both sources should align to the same calendar month.

**When querying `myenergi_readings` for ESB comparison, always convert `interval_start` to Dublin time:**
```sql
DATE(interval_start AT TIME ZONE 'Europe/Dublin')  -- correct local date
-- NOT: DATE(interval_start)                        -- UTC date, off by 1h in summer
```

### Carry-over midnight entry

The last entry in each day's API response is the next UTC day's midnight minute (`dom=D+1, no hr/min → defaults to key 0`). This overwrites the current day's `hr=0, min=0` entry in `by_minute[0]`. Impact: one minute's `imp` value is replaced by the carry-over entry's value (difference ≈ a few hundred Joules, < 0.0001 kWh). Negligible.

---

## h1d and imp — Energy Flow Clarification

This is important for understanding why `eddi_kwh` is **not** double-counted in `import_kwh`.

### Energy sources for each field

| Field | Energy source | Flows through ESB meter? | Included in `import_kwh`? |
|-------|--------------|--------------------------|--------------------------|
| `imp` | Grid → house (all circuits) | Yes (import) | Yes — this IS `import_kwh` |
| `h1b` | Grid → Eddi immersion heater | Yes (import, part of `imp`) | Yes — h1b is a **subset** of imp |
| `h1d` | Solar panels → Eddi immersion heater | No (self-consumption) | **No** |
| `exp` | Solar panels → grid | Yes (export, negative) | No |

### Physical proof (2026-05-07 live data)

During solar diversion (09:43 Dublin BST, UTC 08:43):
```
hr=8 min=43:  exp=8,673 J,  h1d=4,189 J,  imp=ABSENT(=0)
hr=8 min=44:  exp=6,420 J,  h1d=6,480 J,  imp=1,440 J
hr=8 min=45:  exp=6,018 J,  h1d=6,195 J,  imp=ABSENT(=0)
```

`imp = 0` while `h1d > 0` → `imp` does **not** include h1d. The solar panels are generating, surplus goes to Eddi (h1d) and grid (exp), grid import is zero (or near-zero for background loads).

During grid boost (07:00 Dublin BST, UTC 06:00):
```
hr=6 min=2:  imp=184,860 J,  h1b=181,680 J
```
`imp ≈ h1b + 3,180 J` (53 W household background load). Grid boost is fully captured in `imp`. ✓

### Overlap between `import_kwh` and `eddi_kwh`

`eddi_kwh` = (h1b + h1d) / 3,600,000 — total Eddi energy from **all sources**.
`import_kwh` = imp / 3,600,000 — total grid import.

The `h1b` portion of `eddi_kwh` is already inside `import_kwh` (grid-sourced boost = grid import). The `h1d` portion is **not** in `import_kwh` (solar source). These columns measure different things — do not add them together.

**Cross-validation rule**: compare `import_kwh` ↔ ESB `import_kwh` only. Do not add `eddi_kwh` to `import_kwh` for ESB comparison.

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

### The fix (hsk → h1b+h1d, April 2026)

```python
# Before (wrong — hsk is a status counter, not energy):
avg_eddi_cw = sum(s.get("hsk", 0) for s in slot_samples) / len(slot_samples)

# After (correct field selection, but unit formula later found to be wrong too — see below):
# h1b = grid boost (Joules/min), h1d = solar diversion (Joules/min).
# hsk is a heat-sink status counter, NOT energy — do not use it here.
eddi_kwh = sum(s.get("h1b", 0) + s.get("h1d", 0) for s in slot_samples) / 3_600_000
```

Verification (after both fixes applied): dry-run on April 28 produced `eddi_kwh=2.248 kWh` (using old cW formula). With the correct Joules formula the true value would be ~3.75 kWh (two 3 kW boosts × 30 min + solar diversion).

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

*Updated 2026-05-13 — full pipeline confirmed working.*

```
myenergi_poller (00:15)   → myenergi_readings.export_kwh  (exp field, Joules → kWh)
                          → solar_actuals.eddi_kwh
                          → solar_actuals.ghi_actual       (Open-Meteo archive, yesterday)

_sync_solar_actuals (00:45) via db_repository.upsert_solar_actuals:
  Step 1a: meter_readings.export_kwh  → solar_actuals.export_kwh  (ESB CSV — authoritative)
  Step 1b: myenergi_readings.export_kwh → solar_actuals.export_kwh (fallback when no ESB data)
  Step 2:  advisory_log.ghi_forecast  → solar_actuals.ghi_forecast
  Step 3:  recompute panel_factor_obs = (export_kwh + eddi_kwh) / ghi_actual
```

**Priority:** ESB CSV > MyEnergi for `export_kwh`. ESB data is never overwritten by MyEnergi.

**Key fix (2026-05-13):** The deployment directory was not volume-mounted in docker-compose —
container was running stale image. Fixed by adding `./deployment:/app/deployment` volume mount.
All code changes to `deployment/` now take effect on `docker restart`, no rebuild needed.

**Result (May 2026 panel_factor_obs):**
| Date | eddi_kwh | export_kwh | ghi_actual | panel_factor_obs |
|------|----------|------------|------------|-----------------|
| May 12 | 4.27 | 2.68 | 4.97 | 1.397 |
| May 11 | 3.61 | 1.90 | 4.17 | 1.323 |
| May 10 | 6.68 | 1.96 | 5.72 | 1.511 |
| May 9  | 9.57* | 1.41 | 7.17 | 1.532 |
| May 8  | 3.41 | 0.97 | 4.08 | 1.074 |

*May 9 = Free Energy Saturday. eddi_kwh inflated by free grid boost — factor slightly overstated.

**Structural limitation:** `panel_factor_obs` = (eddi + export) / GHI still excludes house
self-consumption (solar used directly by appliances). True solar generation > what we track.
A generation CT would be required to measure house self-consumption directly.

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
| `h1b + h1d` for Eddi energy | Sum both fields | `h1b` = grid-sourced boost (Joules/min); `h1d` = solar diversion (Joules/min). Neither is double-counted in `import_kwh`: h1b is a subset of `imp` (same grid import), h1d is solar self-consumption (not grid, not in `imp`). | `hsk` (status counter, not energy) — was the original bug |
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

**Running on NUC** (scripts dir isn't in the Docker image, use `docker cp` + background exec):
```bash
# Step 1 — sync latest script from Mac to NUC (run on Mac):
rsync -av ~/building-energy-load-forecast/scripts/myenergi_backfill.py \
    dan@192.168.68.119:~/sparc/scripts/myenergi_backfill.py

# Step 2 — copy into running container (run on NUC host or via ssh):
ssh dan@192.168.68.119 \
    "docker cp ~/sparc/scripts/myenergi_backfill.py sparc-api:/app/scripts/myenergi_backfill.py"

# Step 3 — run in background, log to /tmp/backfill.log (1,202 days ≈ 24 min):
ssh dan@192.168.68.119 \
    "docker exec -d sparc-api sh -c 'python /app/scripts/myenergi_backfill.py \
     --start-date 2023-01-20 > /tmp/backfill.log 2>&1'"
# Eddi installed 2023-01-20 — use this as canonical start date for full history

# Step 4 — check progress:
ssh dan@192.168.68.119 "docker exec sparc-api tail -10 /tmp/backfill.log"

# DATABASE_URL is automatically picked up from the container env (db:5432).
# Safe to re-run: skips dates already with ≥40 slots (ON CONFLICT DO UPDATE).
```

**Expected output per day:**
```
20:06:32  INFO  [myenergi_poller] Done for 2023-01-22 — 48 30-min slots, Eddi 0.58 kWh, GHI 0.264 kWh/m²
20:06:32  INFO  ✓ 2023-01-22  [3/1202 done, 0 skipped, 0 failed]
```

### Grafana Free Saturday panels now query `myenergi_readings`
Panels 22 and 25 in `household_intelligence.json` query `myenergi_readings.import_kwh` (hub `imp` field).
The JOIN was broken until migration 008 (2026-05-07): `hardware_id` (MPRN = `10306822417`) ≠ `hub_serial` (MyEnergi serial = `21509692`). Fixed by adding `myenergi_serial` column to `households`.

### BST slot-alignment bug fixed (2026-05-07)

The `_aggregate_to_30min` function used `start_min` (Dublin-local offset) as a direct index into `by_minute` (keyed by UTC `hr*60+min`). In BST (UTC+1) these differ by 60 minutes — every slot was pulling data from 1 hour too late in UTC. The 07:00 Dublin boost appeared in the 06:00 Dublin slot in the DB; all BST-season data was shifted 1 hour early. Also caused a subtle double-count at the UTC day boundary (~0.4 kWh/day in summer).

**Fix**: compute `utc_offset_min = int(local_midnight.utcoffset().total_seconds() / 60)` once, then use `utc_start = start_min - utc_offset_min` for the `by_minute` range lookup. `interval_start` calculation (Dublin midnight anchor) is unchanged and was always correct.

**Action taken 2026-05-07**: the force-backfill was restarted from scratch after this fix was applied, logging to `/tmp/backfill_fix2.log`. All 1,203 historical days will be re-populated with both the Joules correction and the correct BST timestamps.

### API unit bug — values are Joules, not centi-Watts (discovered 2026-05-07)
The API field documentation (community sources, previous session notes) described `imp`, `exp`, `h1b`, `h1d` as instantaneous centi-Watts. This was **wrong**. The values are **Joules per 1-minute interval**.

Evidence: at a boost minute, `h1b = 181,680` → as Joules: 181,680 J ÷ 60 s = **3,028 W** (standard 3 kW Irish immersion heater ✓). As cW: 1,817 W (non-standard). Confirmed against live MyEnergi app readings (all fields matched within ~5%).

**Impact**: all `import_kwh` and `eddi_kwh` values in `myenergi_readings` (and `solar_actuals.eddi_kwh`) are underestimated by factor **1.667×** for all historical data.

**Fix**: `myenergi_poller.py` `_aggregate_to_30min` updated 2026-05-07:
```python
# Before (wrong):
avg_cw = sum(s.get("imp", 0) for s in slot_samples) / len(slot_samples)
import_kwh = avg_cw * 0.5 / 100 / 1000   # underestimates 1.667×

# After (correct):
import_kwh = sum(s.get("imp", 0) for s in slot_samples) / 3_600_000
```
`myenergi_backfill.py` delegates to `run_daily_poll` → fixed by poller fix.

**Action required**: re-run `myenergi_backfill.py --start-date 2023-01-20` on NUC to correct all historical rows.

### LP Thermal Dispatcher uses myEnergi context
`lp_dispatcher.py` receives `solar_surplus_kw` input (future: from `solar_actuals.eddi_kwh`
and `SolarBaselineModel`). Currently zero until enough data accumulates. The LP also
schedules grid boosts to complement the Eddi's automatic solar diversion — it only controls
grid-sourced heating, never overrides the hub's solar diversion logic.

---

---

## Import Overcount vs ESB — Investigation (2026-05-07, pick up when Harvi arrives)

### The numbers

Full cross-validation after Joules + BST timestamp backfill (Jun 2024 – Apr 2026, 23 complete months):

| Period | ME avg/mo | ESB avg/mo | Ratio | Avg delta/day |
|--------|-----------|-----------|-------|---------------|
| Aug–Dec 2024 | ~332 kWh | ~306 kWh | ~108% | 0.66–1.03 kWh |
| 2025 | ~257 kWh | ~219 kWh | ~116% | 0.90–1.44 kWh |
| Jan–Apr 2026 | ~309 kWh | ~252 kWh | ~122% | 1.52–2.08 kWh |

**Upward trend**: the overcount has grown from ~107% in Aug 2024 to ~122–124% in early 2026.

### What was ruled out

**Solar self-consumption**: The overcount was checked by GHI band:

| GHI band | Days | ME % of ESB |
|----------|------|-------------|
| Near-zero (<200 Wh/m²) | 12 | **115.4%** |
| Low (200–1000) | 183 | 112.3% |
| Medium (1000–3000) | 219 | 114.1% |
| High (>3000) | 283 | 118.4% |

The overcount is **essentially the same on completely overcast days** as on sunny ones. Solar self-consumption is not the cause (and confirmed by `imp=0` during peak solar export hours — the CT is correctly at the grid boundary).

**Formula/data pipeline errors**: ruled out. The Joules fix + BST timestamp fix are applied. ESB data coverage is complete (first-to-last day for every month).

**CT position (after solar inverter)**: ruled out. When you run a 0.6 kW appliance while exporting 1 kW solar surplus, the app shows 0.4 kW export and 0 import — correct net-grid behaviour.

### Current best hypothesis

The raw `cgi-jday` API `imp` field is **~8% lower** than what the MyEnergi app shows (API: 3.609 kWh vs app: 3.9 kWh at the same point in the day, 2026-05-07). The app aggregates from more CT sources than the jday endpoint exposes. The ~8% gap = circuits the hub's internal CT doesn't see. Installing the **Harvi CT on the main supply tails** will close this gap.

However, 8% undercount in API `imp` vs app doesn't explain why the cross-validation shows `import_kwh` 12–22% OVER ESB. This deeper discrepancy (likely 3-phase phase netting: ESB nets all phases per 30-min period, MyEnergi may count positive phases independently) is left for investigation once Harvi provides clean whole-house CT data.

**To verify after Harvi installation**:
```sql
-- Run after first month of Harvi data — expect ~100% if Harvi fixes the measurement
SELECT TO_CHAR(DATE_TRUNC('month', interval_start AT TIME ZONE 'Europe/Dublin'), 'Mon YYYY'),
       ROUND(SUM(import_kwh)::NUMERIC,1) AS me_kwh
FROM myenergi_readings WHERE hub_serial = '21509692' AND interval_start >= 'HARVI_DATE'
GROUP BY 1 ORDER BY 1;
```

---

## Idle / Standby Baseload (2026-05-07)

From `myenergi_readings` slots where `ghi_wh_m2 = 0` (no solar) and `eddi_kwh < 0.01` (no Eddi activity):

| Dublin hour | Median kWh/slot | Power equiv. | p10 "true idle" |
|-------------|-----------------|--------------|-----------------|
| 02:00–05:00 | ~0.100 kWh | **200 W** | 172 W |
| 18:00–23:00 | ~0.155 kWh | **310 W** | ~200 W |

**Pure standby ≈ 172–200 W** (p10 to median at 2–5am). Daily idle baseline ≈ **4.1–4.8 kWh/day** for always-on devices (fridge, router, standby electronics, etc.).

This baseline is derived from the hub CT (`imp`) which undershoots by ~8% vs the MyEnergi app. True standby is likely ~4.4–5.2 kWh/day once Harvi covers all circuits.

**Potential future use**: standby estimation is a stepping stone to Behind-the-Meter (BTM) asset identification — inferring what appliances a household owns and when they run from the load curve alone (NILM / Jalal's paper approach). Track in Linear once Harvi data is available.

---

## References

- `deployment/myenergi_poller.py` — poller implementation
- `deployment/scheduler.py` — APScheduler job registrations (poller at 00:15, solar_actuals at 00:45)
- `scripts/backfill_myenergi_eddi.py` — historical correction script (hsk bug, one-time use)
- `scripts/myenergi_backfill.py` — general gap-fill backfill script
- `scripts/calibrate_panel_factor.py` — PANEL_FACTOR recalibration (run after backfill)
- `docs/explainers/SOLAR_ADVISORY_EXPLAINED.md` — how PANEL_FACTOR is used in the advisory
- `docs/explainers/LP_DISPATCH_EXPLAINED.md` — LP thermal dispatcher design and pricing model
