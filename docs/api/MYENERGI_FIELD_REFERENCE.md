# MyEnergi API Field Reference
**Comprehensive guide to all known MyEnergi API field codes**

**Last updated:** 2026-04-30  
**Data sources:** Official API docs (MyEnergi_API_Docs/), community reverse-engineering (twonk, myenergi.info forum), live confirmations from deployment code

---

## Overview

MyEnergi devices (Eddi, Zappi, Harvi, Libbi) expose data via two main endpoint families:

1. **cgi-jday** — minute-level historical data (1441 entries/day): grid import, diversion, voltage, frequency
2. **cgi-jstatus** — instantaneous device status (real-time snapshot): power flows, modes, temperatures
3. **cgi-boost-time** — time-scheduled boost configuration (per-device boost schedules)

All fields use **short ASCII acronyms** (e.g., `imp`, `h1b`, `hsk`). Units vary: Joules in history endpoints, Watts in status, Celsius for temperature.

---

## Table 1: cgi-jday (Minute-Level Historical Data)

Endpoint: `GET /cgi-jday-E{hub_serial}-{YYYY}-{MM}-{DD}`  
Response format: `{"U{hub_serial}": [entry0, entry1, ..., entry1440]}`  
Total entries per day: 1441 (1 header + 1440 minute snapshots)

| Field | Full Name | Units | Range | Description | Validation |
|-------|-----------|-------|-------|-------------|------------|
| **yr** | Year | - | 2020–2050 | Calendar year | CONFIRMED |
| **mon** | Month | - | 1–12 | Calendar month | CONFIRMED |
| **dom** | Day of Month | - | 1–31 | Day of month | CONFIRMED |
| **dow** | Day of Week | - | 0=Monday, 6=Sunday | Day name (index) | CONFIRMED |
| **hr** | Hour | - | 0–23 | Hour of day in local time | CONFIRMED |
| **min** | Minute | - | 0–59 | Minute within hour (omitted in header entry) | CONFIRMED |
| **v1** | Voltage Phase 1 | V × 10 | ~2150–2450 | Supply voltage (divide by 10 for display V) | COMMUNITY |
| **frq** | Frequency | Hz × 100 | ~4950–5050 | Supply frequency (divide by 100 for display Hz) | COMMUNITY |
| **imp** | Grid Import | J × 15 | 0–300,000+ cW | Instantaneous grid power import (centi-Watts, NOT cumulative). Represents draw from grid during this minute snapshot. Use for real-time power analysis. | CONFIRMED |
| **exp** | Grid Export | J × 15 | 0–50,000+ cW | Instantaneous grid power export (centi-Watts). Positive when exporting to grid. | COMMUNITY |
| **gen** | Generation | J × 15 | 0–300,000+ cW | PV generation (context: solar production if CT available) | COMMUNITY |
| **h1b** | Heater 1 Boost Power | J × 15 | 0–180,000 cW | Eddi heater 1: instantaneous boost power (grid-powered heating during boost mode). 0 when not boosting. | CONFIRMED |
| **h1d** | Heater 1 Divert Power | J × 15 | 0–180,000 cW | Eddi heater 1: instantaneous solar divert power. Active when surplus PV available and diverting mode enabled. | CONFIRMED |
| **h2b** | Heater 2 Boost Power | J × 15 | 0–180,000 cW | Eddi heater 2: instantaneous boost power (if second heater installed) | COMMUNITY |
| **h2d** | Heater 2 Divert Power | J × 15 | 0–180,000 cW | Eddi heater 2: instantaneous solar divert power | COMMUNITY |
| **h3b** | Heater 3 Boost Power | J × 15 | 0–180,000 cW | Eddi heater 3: instantaneous boost power (rare, triple heater config) | COMMUNITY |
| **h3d** | Heater 3 Divert Power | J × 15 | 0–180,000 cW | Eddi heater 3: instantaneous solar divert power | COMMUNITY |
| **hsk** | Heat Sink Status | counter | 0–1000+ per day | **NOT energy.** Cumulative heat-sink temperature gauge counter (rises ~373–503/day). Used internally for thermal shutdown logic. Do NOT use as energy metric. | CONFIRMED |
| **gep** | Generation Export Positive | J × 15 | 0–300,000+ cW | PV export (surplus generation going to grid) | COMMUNITY |
| **nect1** | Net CT1 | J × 15 | varies | Net power from CT connection 1 (context-dependent) | COMMUNITY |

**Key conversion formulas:**
- centi-Watts to kWh: `cW / 10 / 3,600 / 1,000` = `cW / 36,000,000`
- One minute snapshot: energy = power (cW) ÷ 3,600,000 kWh

**Critical discovery (Session 32):** `hsk` was initially believed to track cumulative heating energy (like `h1d` + `h1b`). Live data analysis revealed it is a **heat-sink temperature counter**, not energy. Using `hsk` as energy inflates Eddi diversion by ~3.2x. Only use `h1d`, `h2d`, `h3d` for actual diversion energy tracking.

---

## Table 2: cgi-jstatus (Instantaneous Device Status)

Endpoint: `GET /cgi-jstatus-*` or `/cgi-jstatus-E{hub_serial}`  
Response format: device array or single object (varies by device type)  
Update frequency: real-time (hub → cloud gateway)

### Global/Hub Fields

| Field | Full Name | Units | Range | Description | Validation |
|-------|-----------|-------|-------|-------------|------------|
| **sno** | Serial Number | - | numeric | Device or hub serial number | CONFIRMED |
| **sta** | Status | - | 1, 3, 4, 5, 6 | Device mode: 1=Paused, 3=Diverting/Charging, 4=Boost, 5=Max Temp Reached, 6=Stopped (device-type dependent) | CONFIRMED |
| **dat** | Date | - | YYYY-MM-DD | Current date (UTC or local, context-dependent) | COMMUNITY |
| **tim** | Time | - | HH:MM:SS | Current time (UTC or local) | COMMUNITY |
| **frq** | Frequency | Hz | 49.5–50.5 | Grid supply frequency (instantaneous) | COMMUNITY |
| **vol** | Voltage | V | 220–240 | Supply voltage (divided by 10 in some endpoints) | COMMUNITY |
| **pha** | Phase | - | 1–3 | Number of phases (1=single, 3=three-phase) | COMMUNITY |
| **fwv** | Firmware Version | - | semantic | Device firmware version string (e.g. "5.12.2") | COMMUNITY |
| **cmt** | Command Timer | - | 0–10, 253–255 | Counts 1–10 when command sent. 254=success, 253=failure, 255=never received | COMMUNITY |

### Eddi-Specific Status Fields

| Field | Full Name | Units | Range | Description | Validation |
|-------|-----------|-------|-------|-------------|------------|
| **grd** | Grid Power | W | −50,000 to +50,000 | Instantaneous grid power (negative = export, positive = import). Live power draw/feed. | CONFIRMED |
| **che** | Charge Session Total | kWh | 0–100+ | Total energy diverted or boosted in current session (today's running total from 00:00 local) | CONFIRMED |
| **rbt** | Remaining Boost Time | s | 0–10,800 | Seconds left in active boost session (0 if not boosting) | CONFIRMED |
| **bsm** | Boost Mode | - | 0, 1 | 1=actively boosting now, 0=not boosting | COMMUNITY |
| **hno** | Heater Number | - | 1, 2 | Currently active heater (if multi-heater config). Undefined if single heater. | COMMUNITY |
| **ht1** | Heater 1 Name | - | string | User-friendly name for heater 1 (e.g. "Tank 1", "Immersion") | COMMUNITY |
| **ht2** | Heater 2 Name | - | string | User-friendly name for heater 2 | COMMUNITY |
| **tp1** | Temperature Probe 1 | °C | −20 to 100 | Tank temperature (divide by 10 for display). ~360 = 36°C, ~700 = 70°C | COMMUNITY |
| **tp2** | Temperature Probe 2 | °C | −20 to 100 | Second temperature probe (if installed) | COMMUNITY |
| **div** | Diversion Amount | W | 0–180,000 | Current active diversion power (instantaneous) | COMMUNITY |
| **ectp1** | CT Connection 1 Power | W | varies | Physical CT connection reading (grid or gen, context-dependent) | COMMUNITY |
| **ectt1** | CT Type 1 | - | string | CT1 label (e.g. "Grid", "Generation") | COMMUNITY |
| **ectp2** | CT Connection 2 Power | W | varies | Physical CT connection 2 reading | COMMUNITY |
| **ectt2** | CT Type 2 | - | string | CT2 label | COMMUNITY |
| **r1a** | Relay 1 Status | - | 0, 1 | Relay state (purpose unclear; may indicate active heater circuit) | COMMUNITY |
| **r2a** | Relay 2A Status | - | 0, 1 | Relay 2A state | COMMUNITY |
| **r2b** | Relay 2B Status | - | 0, 1 | Relay 2B state | COMMUNITY |
| **pri** | Priority | - | numeric | Heater priority setting (1=highest) | COMMUNITY |

### Zappi-Specific Status Fields

| Field | Full Name | Units | Range | Description | Validation |
|-------|-----------|-------|-------|-------------|------------|
| **sta** | Charge Status | - | 1, 3, 5 | 1=Paused, 3=Diverting/Charging, 5=Complete | CONFIRMED |
| **zmo** | Zappi Mode | - | 1–4 | 1=Fast, 2=Eco, 3=Eco+, 4=Stopped | COMMUNITY |
| **che** | Charge Added | kWh | 0–100+ | Energy added in this charging session | COMMUNITY |
| **pst** | Plug Status | - | A, B1, B2, C1, C2, F | A=EV Disconnected, B1=Connected, B2=Waiting for EV, C1=Ready, C2=Charging, F=Fault | COMMUNITY |
| **mgl** | Minimum Green Level | % | 0–100 | Charging threshold (% surplus generation below which grid power used) | COMMUNITY |
| **lck** | Lock Status | - | bitfield | 4-bit field: [locked_now][lock_on_plug][lock_on_unplug][charge_when_locked] | COMMUNITY |
| **div** | Diversion | W | 0–7,000 | Current charging power (instantaneous, pre-boost) | COMMUNITY |
| **ectp1–6** | CT Connections 1–6 | W | varies | Six CT inputs for multi-phase/multi-source setups | COMMUNITY |

### Libbi-Specific Status Fields

| Field | Full Name | Units | Range | Description | Validation |
|-------|-----------|-------|-------|-------------|------------|
| **soc** | State of Charge | % | 0–100 | Battery charge percentage | COMMUNITY |
| **lmo** | Load Mode | - | string | Operating mode (e.g. "BALANCE", "EXPORT", "IMPORT") | COMMUNITY |
| **isp** | In Service Period | - | boolean | Active service period flag | COMMUNITY |
| **mbc** | Max Battery Charge | W | 0–10,000 | Maximum charging power limit | COMMUNITY |
| **mic** | Max Import Current | A | 0–100 | Maximum grid import current allowed | COMMUNITY |
| **ect1p/2p/3p** | CT Phase Status | - | 0, 1 | Phase connection indicator (1=connected) | COMMUNITY |

### Harvi-Specific Status Fields

| Field | Full Name | Units | Range | Description | Validation |
|-------|-----------|-------|-------|-------------|------------|
| **ectp1** | CT Connection 1 | W | varies | Generation or consumption reading | COMMUNITY |
| **ectt1/2/3** | CT Types 1–3 | - | string | CT labels (e.g. "Generation", "Consumption", "EV") | COMMUNITY |
| **ect1p/2p/3p** | CT Phase Status | - | 0, 1 | Phase connection status per CT | COMMUNITY |

---

## Table 3: cgi-boost-time (Scheduled Boost Configuration)

Endpoint: `GET /cgi-boost-time-E{hub_serial}` or `GET /cgi-boost-time-E{device_sno}`  
Response format: `{"boost_times": [slot0, slot1, ..., slotN]}`

| Field | Full Name | Units | Range | Description | Validation |
|-------|-----------|-------|-------|-------------|------------|
| **slt** | Slot Index | - | 0–9 | Boost schedule slot number (10 slots max) | COMMUNITY |
| **bsh** | Boost Start Hour | h | 0–23 | Boost start hour of day | COMMUNITY |
| **bsm** | Boost Start Minute | m | 0–59 | Boost start minute | COMMUNITY |
| **bdh** | Boost Duration Hour | h | 0–23 | Boost duration hour component | COMMUNITY |
| **bdm** | Boost Duration Minute | m | 0–59 | Boost duration minute component | COMMUNITY |
| **bdd** | Boost Day Description | - | 8-char string | Days active: position 1–7 = Mon–Sun (0=inactive, 1=active). Position 0 unused. E.g., "01111100" = Mon–Fri active. | COMMUNITY |

**Example:** `bdd = "01111100"` → Monday (pos 1)=0, Tuesday (pos 2)=1, ..., Sunday (pos 7)=0 → active Tue–Fri.

---

## Validation Key

| Status | Meaning | Source |
|--------|---------|--------|
| **CONFIRMED** | Verified against live device data (Session 32+: /deployment/connectors.py, /tests/test_connectors.py) | Live hub API calls, production pipeline |
| **COMMUNITY** | Documented in community sources (twonk GitHub, myenergi.info forum) but not yet verified against real data | Reverse-engineering, user documentation |
| **UNKNOWN** | Mentioned in official docs but not yet field-tested | API docs only |

---

## Critical Findings & Recommendations

### 1. **hsk (Heat Sink) Discovery — Major Bug Fix**

**Finding:** `hsk` is NOT an energy counter. It is a heat-sink temperature gauge (cumulative thermal state, ~373–503 increments/day).

**Impact:** Using `hsk` as diversion energy inflates values by ~3.2x.

**Action:** Use ONLY `h1d`, `h2d`, `h3d` for diversion energy tracking. Never sum `hsk`.

**Confirmed:** Session 32 (2026-03-28), live hub data vs. manual ESB readings.

---

### 2. **centi-Watt (cW) Units in cgi-jday**

All power fields in minute history (`imp`, `h1b`, `h1d`, `exp`) are in **centi-Watts** (100 cW = 1 W).

- Range: 0–300,000+ cW (0–3000+ W grid import)
- Eddi boost: ~180,000 cW typical = 1,800 W
- Eddi divert: variable, up to 180,000 cW depending on PV available

To convert to kWh for one-minute interval:
```
energy_kwh = power_cW / 10 / 3600 / 1000 = power_cW / 36,000,000
```

---

### 3. **Instantaneous vs. Cumulative Data**

| Endpoint | Nature | Use Case |
|----------|--------|----------|
| cgi-jday (minute snapshots) | **Instantaneous power** per minute | Real-time power analysis, minute-level granularity |
| cgi-jstatus → `che` | **Cumulative energy** since 00:00 local | Daily total energy tracking, session summaries |
| cgi-jday → `h1d` per minute | **Instantaneous divert power** | Minute-by-minute solar utilization analysis |
| cgi-jstatus → (no daily total field) | — | For daily Eddi total, manually aggregate cgi-jday |

---

### 4. **Device Status Enumeration**

**sta (Status) Field:**
- 1 = Paused (user-disabled or standby)
- 3 = Diverting (Eddi) or Charging (Zappi)
- 4 = Boost active (Eddi)
- 5 = Max temperature reached (Eddi: thermal cutoff)
- 6 = Stopped (device disabled or faulted)

**Eddi-specific interpretation:**
- If `sta=3` and `h1d>0`: actively diverting PV
- If `sta=4` and `h1b>0`: actively boosting from grid
- If `sta=5`: tank at setpoint, no heating happening (despite ambient demand)

---

### 5. **Temperature Probes (tp1, tp2)**

Values are in **tenths of Celsius** (divide by 10 for display).
- `tp1 = 360` → 36.0°C
- `tp1 = 700` → 70.0°C
- Typical range: −20 to 100 (−2.0 to 100.0°C)

---

### 6. **Timezone Handling**

All date/time fields (`yr`, `mon`, `dom`, `hr`, `min`) are in **local time** of the hub's configured timezone.

The hub's timezone is set during initial pairing and cannot be queried via API.
Assumption: Irish devices → Europe/Dublin (UTC+0 winter, UTC+1 summer DST).

---

### 7. **Rate Limiting & Response Format**

- **cgi-jday:** 1441 entries per call (~300 KB JSON), takes ~2–5 sec. No documented rate limit, but recommend ≤1 call/min to avoid hub load.
- **cgi-jstatus:** ~50 KB, instant response. Safe to poll every 5 sec.
- **cgi-boost-time:** ~10 KB, instant. Safe to poll.

---

### 8. **Missing Fields from Official Docs**

Several fields in community sources (`exp`, `gen`, `gep`, `div`) are **not documented** in the official MyEnergi API docs. They appear to be legacy or internal fields. Use community sources as supplementary reference only.

---

### 9. **Firmware Version Dependency**

Status `-14` in cgi-jday response means **history API unsupported** by hub firmware.

Workaround: Use `log_eddi.py --once` via nightly cron to bypass API and log directly from hub storage.

---

## Endpoint Summary

| Endpoint | Purpose | Frequency | Sample Size | Fields |
|----------|---------|-----------|-------------|--------|
| `/cgi-jday-E{serial}-{YYYY}-{MM}-{DD}` | Minute-level history | Once/day per date | 1441 entries | time, power (cW), temperature, voltage, frequency |
| `/cgi-jstatus-*` | Real-time status | Poll 5–60s | 1 snapshot | mode, temperature, power, diversion, boost state |
| `/cgi-boost-time-E{serial}` | Boost schedule config | Once at startup | 10 slots max | start time, duration, days active |

---

## API Inconsistencies Observed

This section documents discrepancies between official documentation, community sources, and live production data. Each was discovered during development of `myenergi_poller.py` and `scripts/backfill_myenergi_eddi.py`.

---

### I-1: "J × 15" Unit Label is Misleading (Critical)

**Community docs state:** Fields `imp`, `exp`, `h1b`, `h1d`, `gen` are in "Joules × 15."  
**Observed in production:** Values are **instantaneous centi-Watts**, not cumulative Joules.

Evidence:
- An Eddi boost at ~1,700 W shows `h1b ≈ 170,000` per minute snapshot — consistent with 1,700 × 100 (cW), not 1,700 J × 15 = 25,500
- Aggregating across 1440 minutes using the "J × 15" formula produces physically impossible daily totals (>100 kWh on a low-use day)
- Cross-validated: summing `h1b + h1d` converted as `avg_cW × 0.5 / 100 / 1000` (30-min kWh) matches `che` (daily kWh total) to within ~5%

**Conclusion:** Treat all power fields in `cgi-jday` as **instantaneous centi-Watts**. The "J × 15" label in community docs is incorrect or refers to an older firmware encoding.

---

### I-2: `hsk` Labelled as Energy but is a Thermal Counter (Critical)

**Community docs state:** `hsk` = "Heat Sink" — some sources imply it tracks heating energy alongside `h1d`.  
**Observed in production:** `hsk` is a **cumulative thermal state counter** that rises monotonically throughout the day (~373–503 increments/day, context-dependent). It is NOT correlated with diversion energy.

Evidence:
- Days with no Eddi activity show `hsk` still rising steadily to ~400
- Substituting `hsk` for `h1d + h1b` as energy yielded `panel_factor_obs = 0.37` vs the physically expected 1.6
- After correcting to `h1b + h1d`, 846 days of history produced `mean panel_factor_obs = 1.62` — consistent with the physical constant

**Conclusion:** Never use `hsk` as an energy metric. Its purpose appears to be internal thermal management, possibly linked to heatsink temperature monitoring for device shutdown protection.

---

### I-3: `cgi-jday` Response Wrapped in Hub Serial Key (Production Bug)

**Community docs and twonk GitHub state:** Response is a JSON array of minute entries.  
**Observed in production:** Response is `{"U{hub_serial}": [...]}` — the array is nested under a hub-keyed object.

Evidence:
- Bug in `_fetch_day_minutes()`: iterating over `data` (a dict) instead of `data.get(f"U{HUB_SERIAL}", [])` caused `"string indices must be integers"` error at runtime
- Fix: `data.get(f"U21509692", [])` → returns the 1441-entry list correctly

**Conclusion:** Always extract the array via `data.get(f"U{serial}", [])`. The top-level key format is `U` + hub serial number (NOT device serial).

---

### I-4: `bdd` Day Indexing Inconsistency

**Community sources disagree** on the `bdd` field (boost day description) indexing:
- Some sources: position 0 = Sunday, positions 1–6 = Mon–Sat
- Other sources: position 0 = unused, positions 1–7 = Mon–Sun

**Observed in production:** Cross-referencing the MyEnergi app UI schedule against the raw `bdd` string:
- `bdd` = `"01111100"` → app shows Mon–Fri active (not including weekend)
- Position 0 is **unused** (always `0`); positions 1–7 = Mon–Sun

**Conclusion:** Use positions 1–7 for Mon–Sun. Position 0 has no meaning. This is consistent with the Sparc `get_schedule()` parser.

---

### I-5: `che` is a Daily Total, NOT a Per-Session Total

**Field name:** "Charge Session Total" — implies it resets per boost session.  
**Observed in production:** `che` resets at **00:00 local time**, not per boost session.

Evidence:
- Two boost sessions in a single day both contribute to `che` (it accumulates across sessions)
- `che` seen at 3.2 kWh when both a 07:00 boost and a solar diversion occurred the same day
- After midnight `che` = 0.0 regardless of previous session state

**Conclusion:** `che` is the best field for "how much energy did Eddi use today?" but cannot distinguish grid boost energy from solar diversion energy. Use `cgi-jday h1b/h1d` for that breakdown.

---

### I-6: `exp`, `gen`, `gep` Absent from Official Documentation

**Official MyEnergi API docs** (scraped in `docs/api/MyEnergi_API_Docs/`) do not document: `exp` (grid export), `gen` (generation), `gep` (generation export positive).

**Community sources** (twonk, myenergi.info) document these fields as present in cgi-jday responses when a CT clamp or Harvi is installed.

**Implication for Sparc:** Dan's setup has no CT clamp, so these fields return 0 or are absent. Export energy is sourced from ESB meter data (more accurate). If a CT clamp is installed in future, `exp` and `gen` will populate and should be reconciled against ESB export readings.

---

### I-7: Hub Serial vs Device Serial in Endpoint Paths

**Community docs** sometimes use device serial (e.g., Eddi serial `22XXXXXXX`) in endpoint paths.  
**Observed in production:** `cgi-jday` and `cgi-boost-time` require the **hub serial** (`21509692`), prefixed with `E`.

Evidence:
- `GET /cgi-jday-E21509692-2026-04-30` → returns data
- `GET /cgi-jday-E22XXXXXXX-2026-04-30` → returns empty or error

**Conclusion:** Use hub serial (`sno` from `cgi-jstatus-*` root object) for all `cgi-jday` calls. Eddi device serial is only needed for `cgi-boost-time-E{eddi_serial}`.

---

## References

**Official Documentation:**
- `/Users/danalexandrubujoreanu/building-energy-load-forecast/docs/api/MyEnergi_API_Docs/Device/*.md` — official API endpoint specs

**Community Sources:**
- https://github.com/twonk/MyEnergi-App-Api — comprehensive reverse-engineered API guide
- https://myenergi.info/api-acronyms-t3154.html — community forum acronym table
- https://github.com/bisand/myenergi-api — Node.js client library with field definitions

**Live Confirmations:**
- `/Users/danalexandrubujoreanu/building-energy-load-forecast/deployment/connectors.py` — production connector code (Session 32+)
- `/Users/danalexandrubujoreanu/building-energy-load-forecast/tests/test_connectors.py` — test cases with live data
- `/Users/danalexandrubujoreanu/building-energy-load-forecast/deployment/myenergi_poller.py` — minute-level data aggregation (hsk bug fix documented)

---

**Document Version:** 1.1 (API Inconsistencies section added)  
**Validation Date:** 2026-04-30  
**Compiler:** Claude Code (Sessions 38 + 51)
