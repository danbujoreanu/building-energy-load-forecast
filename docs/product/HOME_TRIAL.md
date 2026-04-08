# Dan's Home Trial — Maynooth, Co Kildare

*Real-world validation of the building energy forecast pipeline on a residential Irish home.*
*Created: 2026-03-15 (Session 31)*

---

## Home Setup

| Item | Detail |
|------|--------|
| **Address** | Maynooth, Co Kildare, W23H7T1 |
| **Electricity supplier** | Bord Gáis Energy (BGE) |
| **Tariff** | BGE Free Time Saturday + 20% Affinity discount (to 15 June 2026) |
| **Smart meter** | ESB Networks smart meter (30-min interval data via My Account CSV export) |
| **Solar PV** | Yes — panels installed; no CT clamp on generation |
| **Hot water diverter** | myenergi **Eddi** (hub serial: **HUB_SERIAL_REDACTED**) |
| **CT clamp (grid)** | myenergi **Harvi** (serial: **13541598**) — measures grid incomer |
| **Occupants** | 2 people |
| **Shower time** | ~09:30 (gym days vary) |

---

## Tariff — BGE Free Time Saturday (with 20% Affinity Discount)

| Slot | Rate (after discount) | When |
|------|-----------------------|------|
| Day | 40.34 c/kWh | Mon–Sun outside other slots |
| Night | 29.65 c/kWh | 23:00–08:00 |
| Peak | 49.28 c/kWh | Mon–Fri 17:00–19:00 **only** |
| Free Time (Saturday) | 0 c/kWh | Sat 09:00–17:00 |
| Export | 18.5 c/kWh | Net export to grid |
| Standing charge | 61.52 c/day | Always |

> Contract expires: **15 June 2026** — flag renewal 90 / 30 / 7 days before.
> Free Time Saturday is the primary driver of plan optimality (~815 kWh/year free).

---

## Devices

### myenergi Eddi (hot water diverter)
- Hub serial: `HUB_SERIAL_REDACTED` — server: `s18.myenergi.net` (confirmed from CORS header)
- **API key**: stored in `.env` file (gitignored). See `.env` for `MYENERGI_API_KEY`.
  - To load: `export $(cat .env | xargs)` or `source .env` — then run any script.
  - Key reference: stored in `.env` only — never commit to repo. Regenerate in myenergi app if exposed.
- API: Reverse-engineered REST, HTTP Digest auth (username = hub serial, password = API key)
- **Live status confirmed working 2026-03-15**: `sta=1` (paused), `che=2.13 kWh` today, `grd=223 W` import, `frq=49.94 Hz`
- `div` = W currently going to tank; `grd` = grid flow (positive=import, negative=export)
- `che` = kWh diverted to tank today (reliable — use this, not history API, for daily total)

**Confirmed Eddi boost schedule (live from API, 2026-03-15):**

| Slot | Time | Duration | Days | Notes |
|------|------|----------|------|-------|
| 11 | 07:00 | +30min | Mon+Tue+Wed+Thu+Fri+Sun | Morning grid boost (night rate) |
| 12 | 19:45 | +30min | Mon+Tue+Wed+Thu+Fri+Sun | Evening grid boost (day rate) |
| 13 | 09:15 | +3h | **Saturday only** | FREE window (0c, ends 12:15) |
| 14 | 14:00 | +3h | **Saturday only** | FREE window (0c, ends 17:00 exactly) |
| 21-64 | various | until-setpoint | various | Heater 2 / other programs — not actively used |

Key observations:
- Saturday is NOT covered by slots 11/12 (bdd="01111101" excludes Saturday). Instead, slots 13+14 cover 6h of the FREE window. Optimal.
- 19:45 boost is needed: water must be hot for 09:30 showers next day. If tank already full from solar, the boost self-suppresses — no action needed.
- No temperature probe fitted (tp1=127°C = sentinel/disconnected value).

### myenergi Harvi (CT clamp)
- Serial: `13541598`
- Measuring: **Grid incomer** (not solar panels directly)
- This enables Eddi's solar divert logic — Harvi sees export, Eddi diverts

### Solar PV
- No CT clamp on solar generation circuit
- **Total solar = ESB net export + Eddi diversion (`che`)**
  - ESB "export" figure = net (after Eddi has already consumed what it could)
  - To reconstruct total generation: `export_kwh + eddi_diverted_kwh`

---

## Plan Optimisation Score — Computed 2026-03-15

Data: ESB HDF file `HDF_calckWh_10306822417_22-10-2025.csv` (Oct 2023 → Oct 2025, 730 days)

| Metric | Value |
|--------|-------|
| **Overall Score** | **62/100** |
| Total import (period) | 6,521 kWh |
| Total export (period) | 871 kWh |
| Total via Free Saturday | 1,347 kWh (54% of 2,500 kWh cap) |
| Average per Saturday | 12.9 kWh (cap: 100 kWh/month) |
| **Monthly headroom unused** | **~46 kWh/month** |
| **Annual saving potential** | **€178.65/year** (unused free allowance at day rate) |
| Peak rate exposure | 3.0% of total import (good) |
| Night rate usage | 31.2% of total import (excellent) |

**Score breakdown:**
- Free Saturday utilisation: 54/100 (weight 50%) — 54% of monthly 100 kWh cap used
- Peak avoidance: 55/100 (weight 30%) — 3% peak exposure; 22% premium vs day rate
- Night shift: 94/100 (weight 20%) — 31% of consumption at night rate

**Monthly free window utilisation:**
- Best months: Nov 2023 (98.5 kWh), Feb 2024 (97.9 kWh) — near cap
- Worst months: Oct 2023 (18 kWh, partial month), Jun 2025 (20 kWh), Jul 2024 (32 kWh)
- Summer drop (May–Sep): Eddi diverts solar instead of grid → less grid import on Saturdays → lower free kWh reading. **This is correct behaviour — solar is free too.** The score understates performance in summer.

**Recommendations generated:**
1. Shift laundry, dishwasher to Saturday 09:00–17:00 (46 kWh headroom/month)
2. 7.8 kWh/month at peak rate — shift away from Mon–Fri 17:00–19:00

**Script**: `python scripts/score_home_plan.py --csv <path/to/HDF.csv>`
**Output**: `outputs/results/home_plan_score.json`

---

## Key Discoveries from ESB Data Analysis

| Observation | Explanation |
|-------------|-------------|
| Spike at 07:00 (~0.55 kWh) | Eddi morning boost — not cooking/kettle |
| Spike at 19:45 (~0.55 kWh) | Eddi evening boost — not cooking/kettle |
| Eddi active almost all day Saturday | Free Time Saturday window (0c) — correct and optimal |
| ESB export is NET | Subtract Eddi diversion to get true solar generation |

---

## Current Integration Status

| Component | Status | Notes |
|-----------|--------|-------|
| ESB CSV import | Working | `scripts/run_home_demo.py` — pivot, resample, DST-safe |
| BGE tariff model | Working | Day/Night/Peak (Mon–Fri only)/Free Sat/Export rates |
| Open-Meteo live weather | Working | Split archive + forecast endpoints, `ambiguous="NaT"` |
| LightGBM H+24 forecast | Working | Drammen model, morning brief P10/P50/P90 |
| Eddi live status (monitor) | Working | `deployment/connectors.py` MyEnergiConnector |
| Eddi control commands | **NOT ACTIVE** | Monitor-only until app recommends, user approves |
| Eddi history API | **Working** | URL: `/cgi-jday-E{serial}-{Y}-{MM}-{DD}` confirmed. Units: instantaneous cW. |
| Eddi schedule API | **Working** | `/cgi-boost-time-E{serial}` returns `boost_times[]` with `bdd` day-string |
| Ecowitt weather station | Pending | Hardware not yet purchased |

---

## P1 Port — Physical Connection Guide

The ESB smart meter has a **P1 customer port** on its front face. This is a standard optical or
RJ12 serial port that provides real-time (1-second resolution) data to the customer side without
utility permission.

### How to connect a Raspberry Pi Zero 2W

1. **Open the meter box** (the grey plastic enclosure on the outside wall, usually beside the front
   door or in a utility area). You do not need to touch the meter itself or the sealed utility section.

2. **Locate the P1 port** — it is the small connector on the **customer-facing side** of the smart
   meter (not the utility side). On ESB Networks meters it is typically labelled "P1" or "Customer
   Port". It may be covered by a small plastic cap.

3. **Choose your adapter**:
   - **Optical (recommended for Irish ESB meters)**: A small optical probe clips over the port.
     Products: DSMR P1 dongle (Dutch/Irish compatible), Slimmelezer+, or similar.
   - **RJ12 cable** (some meter models): 6-pin RJ12 → USB adapter → Pi USB port.

4. **Connect the adapter to the Raspberry Pi Zero 2W**:
   - USB adapter → Pi USB port (via micro-USB OTG adapter on Pi Zero)
   - OR Wi-Fi dongle (many P1 adapters have built-in Wi-Fi and publish MQTT or HTTP)

5. **Power the Pi**: A USB phone charger plugged into a nearby socket. The meter box typically has
   a socket nearby, or run a cable from indoors. Pi Zero draws ~1W idle.

6. **Place the Pi**: Inside the meter box (if space allows) or just outside it. Weatherproofing:
   place Pi in a small waterproof ABS enclosure (~€5) mounted next to the meter box.

7. **Software**: Run `scripts/log_eddi.py` (to be built) or a standard DSMR reader. Data streams
   at 1-second resolution — aggregated to 1-minute for tank state estimation.

> **Key benefit over 30-min ESB CSV**: 1-second P1 data enables proper NILM
> (appliance fingerprinting). The Eddi boost signature (1.1 kW sustained) is clearly identifiable
> and separable from other loads. Enables real tank state estimation.

---

## Action Items

### Phase 1 — Monitor (Current)

| Item | Priority | Status |
|------|----------|--------|
| Run `scripts/run_home_demo.py` daily — morning brief | High | Working |
| Build `scripts/log_eddi.py` — 1-min polling → CSV | High | **TODO** |
| Accumulate daily `che` values from Eddi API → local CSV | High | **TODO** |
| Validate total solar = ESB export + Eddi diversion | Medium | **TODO** |
| Flag BGE contract renewal 90 days before 15 June 2026 (= 17 March 2026) | **URGENT** | **TODO** — renewal window is NOW |

### Phase 2 — Recommend (App)

| Item | Priority | Status |
|------|----------|--------|
| Morning brief push notification via app | High | Not started |
| "Should I boost now or wait for solar?" recommendation | High | Control engine ready |
| BGE tariff comparison — validate Free Time Saturday is still optimal on renewal | High | Not started |
| Tank state estimation from Eddi polling + load profile | Medium | Not started |
| Suppress unnecessary grid boosts when solar is sufficient (LEARN first) | Medium | Not started |

### Phase 3 — Automate (Hardware)

| Item | Priority | Status |
|------|----------|--------|
| Install P1 port adapter + Raspberry Pi Zero 2W | High | Pending hardware |
| Activate MyEnergiConnector `send_command()` — user approves each action first | Medium | Connector built, not wired to demo |
| Ecowitt GW1100 weather station installation | Low | Hardware not purchased |
| SEAI grant check — P1 adapter may qualify under smart meter programme | Low | Not investigated |

---

## Workflow — Monitor-First Approach

1. **Now**: Read Eddi status every minute (log_eddi.py), accumulate diversion data, run daily morning brief
2. **App launch**: Present recommendations in UI — user approves or rejects each action
3. **Learn from feedback**: Track which recommendations were accepted/rejected → improve rules
4. **Automate**: Only after confidence threshold reached, implement automated commands with user override always available

> Do NOT draw from the grid when solar surplus can cover both house load and hot water.
> Do NOT send commands to Eddi without user approval via the app.

---

## BGE Contract Renewal — URGENT

The 20% Affinity discount expires **15 June 2026** — the renewal window opens ~90 days before,
which is approximately **17 March 2026 (this week)**.

Actions before renewal:
1. Pull latest 12 months of ESB data and re-run tariff comparison
2. Compare BGE Free Time Saturday against: Energia NightSaver, Electric Ireland Smart, Flogas Smart
3. Key metric: annual cost given actual usage pattern (heavy Saturday Eddi, light evenings, solar export)
4. Free Time Saturday is likely still best — but verify against any new 2026 plans

---

---

## P1 Port Adapter Hardware — What to Buy

### Netherlands origin (DSMR standard)
The P1 port was standardised in the Netherlands as part of the **DSMR** (Dutch Smart Meter
Requirements) specification, first published ~2012. The ecosystem is very mature there.

| Device | Origin | Price | Protocol | Notes |
|--------|--------|-------|----------|-------|
| **Slimmelezer+** | NL (Marcel Zuidwijk) | ~€25 | Wi-Fi, MQTT, HTTP | Most popular; ESP8266-based; plug-and-play with Home Assistant; best choice |
| P1 Dongle (PDAStore) | NL | ~€15–20 | USB | Connects to Pi via USB; simple, no Wi-Fi |
| DSMR-logger v4 | NL | ~€30–40 | Wi-Fi + SD | Advanced; microSD for local storage; overkill for MVP |
| P1 Reader (Wemos D1) | NL/DIY | ~€10–15 | Wi-Fi | DIY ESP8266 build; requires soldering |

**Recommended for Maynooth: Slimmelezer+** — Wi-Fi built-in, MQTT out of the box,
no Raspberry Pi needed at all. €25 delivered from the Netherlands (EU shipping ~3-5 days).
Plugs into P1 port, connects to home Wi-Fi, publishes data to local MQTT broker or
directly to `log_eddi.py`-style receiver.

### Country compatibility
| Country | Meter standard | P1 compatible | Notes |
|---------|---------------|---------------|-------|
| **Ireland** | ESMR 5.0 (ESB Networks) | Yes, with minor config | Same physical port, telegram format slightly differs from NL DSMR P1 but the dsmr-parser Python library handles it |
| Netherlands | DSMR P1 (v5.0) | Native | Origin of the standard |
| Belgium | FLUVIUS P1 | Yes | Same connector, same library |
| Luxembourg | SML P1 | Mostly | Minor parsing differences |
| Sweden | Kamstrup P1 | Partial | Format varies by meter manufacturer |
| Germany | SML (no P1 port) | No | German meters use optical IR port (different) |
| UK | SMETS2 (no P1) | No | UK uses DCC/SMETS2 — no customer P1 port |
| Norway | AMS P1 (Kamstrup, Aidon) | Yes | Same DSMR-derived standard; research pipeline buildings used this |

> **Key note for Ireland**: The ESB Networks ESMR 5.0 telegram is DSMR-compatible.
> The `dsmr-parser` Python library (pip install dsmr-parser) works with minor config:
> set `telegram_specification = P1_DOUBLE_ELECTRICITY_METER` for Irish meters.
> The Slimmelezer+ also works with Irish meters.

### Raspberry Pi vs ESP32-based dongle
| Option | Hardware cost | Complexity | Best for |
|--------|--------------|------------|---------|
| Slimmelezer+ (ESP8266) | ~€25 all-in | Zero (plug-and-play) | MVP, fast setup, MQTT → `log_eddi.py` |
| Pi Zero 2W + USB P1 dongle | ~€18 + €15 = €33 | Low (set up once) | More flexible; can run full inference locally |
| Pi Zero 2W + Slimmelezer+ | ~€18 + €25 = €43 | Low | Future: local inference on Pi |
| Pi 4 (4GB) + dongle | ~€55 + €15 = €70 | Low | Full pipeline on-device (Phase 3) |

**MVP recommendation**: Slimmelezer+ only (~€25). No Pi needed at this stage. MQTT data goes
straight to the cloud/local endpoint. Upgrade to Pi when on-device inference is needed.

---

## Data Strategy — Smart Meter + Eddi

### Regular user perspective (always the priority)
A regular residential customer has: a smart meter, possibly solar, possibly an Eddi.
They will NOT set up a Raspberry Pi, configure MQTT, or run a polling script.
The app must work entirely without hardware for the majority of users.

### Tier 1 — Works for every ESB customer today (no hardware)
```
ESB My Account → Download CSV → drag into app
```
Manual export, 30-min resolution. Works for 100% of Irish smart meter customers.
This is the MVP onboarding path. Repeat monthly (or when user opens app).

### Tier 2 — Eddi historical data via cloud API (no hardware, Eddi users only)
```
scripts/log_eddi.py --history 30    # pulls last 30 days via myenergi cloud
```
The myenergi app already shows historical Eddi data — we retrieve the same data
via the cloud API. No continuous polling, no hardware. Works on demand.
Status: `get_history_day()` has been fixed in connectors.py to use the Eddi device
serial (not hub serial). Testing needed to confirm the -14 response is resolved.
If the hub firmware doesn't support history: workaround is a nightly cron at 23:55
to record `today_kwh` before midnight reset (one row/day, requires Mac to be on).

### Tier 3 — Once-daily snapshot via cron (low-effort, for data completeness)
```bash
# Add to crontab: crontab -e
55 23 * * * export MYENERGI_SERIAL=HUB_SERIAL_REDACTED && export MYENERGI_API_KEY=<key> && \
  /Users/danalexandrubujoreanu/miniconda3/envs/ml_lab1/bin/python \
  /Users/danalexandrubujoreanu/building-energy-load-forecast/scripts/log_eddi.py --once
```
Captures `today_kwh` at 23:55 each night before it resets.
Records one CSV row per day. No continuous running required. Mac must be on at 23:55.

### Tier 4 — P1 port (1-second resolution, hardware required)
```
ESB meter → Slimmelezer+ (~€25) → Wi-Fi → MQTT → app
```
One-time hardware install (~5 min). No Pi needed.
Enables: real-time updates, NILM appliance fingerprinting, automatic ESB data (no CSV downloads).
Recommended for power users and app advocates who want to try the pilot.

### How to share smart meter data with the app (onboarding tiers)
| Tier | Method | Hardware | Effort | Resolution | Who |
|------|--------|----------|--------|------------|-----|
| 1 (MVP) | ESB CSV upload | None | 5 min/month | 30 min | All ESB customers |
| 2 | Eddi cloud API history pull | None | API key only | Hourly (history) | Eddi users |
| 3 | Nightly cron (once-daily snapshot) | None | 10 min setup | 1 row/day | Mac-on users |
| 4 | Slimmelezer+ P1 adapter | ~€25 | 5 min install | 1 second | Power users |

> **Key insight**: Tier 1 alone makes the app useful for 100% of users. Tiers 2–4 improve
> data quality incrementally. Never require hardware for core functionality.

---

## Neighbourhood Pilot — Technical Onboarding Plan

When ready to expand beyond Maynooth:
1. Each participant downloads their ESB CSV from My Account → drags into app
2. App ingests, trains a personalised LightGBM model, shows their forecast
3. Optional: Eddi API key entry in app settings (monitor-only initially)
4. Optional: P1 adapter hardware (self-install guide in app)

**Participant diversity target for a useful pilot:**
- Mix of solar/no-solar households
- Mix of heat pumps/gas/oil (Ireland: mostly gas/oil in older estates)
- At least 1–2 with EV (night charging load pattern)
- At least 1 with Eddi or similar diverter

**Key data we learn from the pilot:**
- Does the Drammen-trained model transfer to Irish residential loads? (currently: MAE 0.171 kWh/h on one house)
- Does tariff recommendation accuracy hold across different BGE/Electric Ireland/Energia plans?
- Where does the app break for non-solar / non-Eddi households?

---

## ESB Networks, Bonkers.ie — Competitive Positioning

### ESB Networks
ESB Networks is the regulated distribution network operator — they cannot be a commercial
partner for optimisation services (impartial by law). However:
- **CRU data access framework (expected 2026+)**: Once live, ESB will expose a regulated API for third-party access to half-hourly smart meter data. This removes the CSV download step entirely for all Irish users.
- **B2B angle**: Not ESB Networks (DSO), but **ESB Group subsidiaries** (Electric Ireland, ESB Innovation Labs) could be partners or customers. Different legal entity, no impartiality constraint.

### Bonkers.ie
Bonkers.ie is a **price comparison and switching service** (revenue = referral commission from energy suppliers). Our product is different:
- Bonkers: "Which supplier is cheapest for an average household?" → switch supplier
- Our app: "You're on the right plan — here's how to shift consumption to cut your bill within that plan" → no switching needed, deeper engagement

These are **complementary, not competitive**. Options:
1. Partner: bonkers.ie sends "optimise usage" referrals to our app after a switch
2. Compete on the deeper engagement layer (bonkers can't do this — no real-time data)
3. White-label to bonkers.ie (they embed our forecast widget in their platform)

The stronger long-term moat is the **household energy model** (personalised LightGBM, tank state, solar profile) — bonkers has none of this. They are a comparison table, we are an optimisation engine.

### Residential vs Commercial
| Segment | TAM | Complexity | Revenue model | Notes |
|---------|-----|------------|---------------|-------|
| **Residential (Ireland)** | ~1.5M households | Low | €99 device + €3.99/month | MVP target; heat pump angle strongest |
| **Commercial (SME)** | ~200k businesses | Medium | €15–50/month SaaS | Needs BMS integration |
| **Viotas / DSO aggregation** | ~500 large C&I sites | High | Revenue share / DR contract | B2B; needs certified DR API |
| **Data centres** | ~80 large DCs in Ireland | Very high | Custom | PhD-track |

Start residential. Commercial SME is a natural second market once residential pipeline is proven.

---

*See also: `docs/regulatory/SMART_METER_ACCESS.md` for regulatory/privacy context on data access methods.*
*See also: `ROADMAP.md` Phase 8 — Dan's Home Trial for project-level tracking.*
*Updated: 2026-03-15 (Session 31 — added P1 hardware guide, Netherlands ecosystem, data strategy, neighbourhood pilot plan, ESB/bonkers competitive notes)*
