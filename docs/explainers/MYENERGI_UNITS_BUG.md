# MyEnergi API Units Bug — Root Cause, Fix, and Validation
*Discovered: 2026-05-07 | Severity: High — all historical import_kwh values affected*
*Local only — not tracked in git.*

---

## The Bug in One Line

The MyEnergi `cgi-jday` API returns energy values in **Joules per 1-minute interval**, not instantaneous centi-Watts. The poller treated them as cW, causing a systematic **1.667× undercount** on all `import_kwh` and `eddi_kwh` values from the Eddi installation date (2023-01-20) onwards.

---

## How It Was Discovered

Cross-checking today's live API data against the MyEnergi app reading:

| Field | Old cW formula | Correct Joules formula | MyEnergi app |
|-------|---------------|----------------------|--------------|
| Import | 2.165 kWh | **3.608 kWh** | 3.9 kWh |
| Export | 0.808 kWh | **1.356 kWh** | 1.3 kWh |
| Eddi grid (h1b) | 0.917 kWh | **1.528 kWh** | ~1.51 kWh ✓ |
| Eddi solar (h1d) | 0.754 kWh | **1.267 kWh** | 1.19 kWh ✓ |
| Eddi total | 1.671 kWh | **2.794 kWh** | 2.7 kWh ✓ |

*Joules formula matches app within 3–5%. Remaining ~8% import gap is due to Harvi CT not yet installed (will close once Harvi is live).*

---

## Physical Proof (Units Verification)

At the morning grid boost minute (07:02 Dublin, `h1b = 181,680`):

```
As centi-Watts:  181,680 cW = 1,817 W  ← no standard Irish immersion heater is 1.8 kW
As Joules/min:   181,680 J ÷ 60 s = 3,028 W  ← standard 3 kW Irish immersion heater ✓
```

This is definitive. The unit is Joules per minute.

---

## The Wrong Formula (and Why It Underestimated)

The poller averaged the raw values across a 30-min slot, then multiplied by the slot duration:

```python
# WRONG — treats values as instantaneous cW
avg_cw    = sum(s.get("imp", 0) for s in slot_samples) / len(slot_samples)
import_kwh = avg_cw * 0.5 / 100 / 1000   # 0.5h × /100 cW→W × /1000 W→kW
```

For a full 30-sample slot, the correct formula is:

```python
# RIGHT — values are Joules per minute
import_kwh = sum(s.get("imp", 0) for s in slot_samples) / 3_600_000
```

**Why 1.667×?** For a 30-sample slot:

```
wrong:   avg_J * 0.5 / 100 / 1000  =  avg_J / 200,000
correct: sum_J / 3,600,000         =  avg_J * 30 / 3,600,000 = avg_J / 120,000

ratio: 200,000 / 120,000 = 1.667
```

**Important nuance**: for sparse slots (fewer than 30 active minutes logged), the ratio is `n/18`. For fully-populated slots (typical), it is 1.667.

---

## ESB vs MyEnergi Cross-Validation

*Run after force backfill completes. Expect corrected MyEnergi to be within ~8% of ESB (the remaining gap is the Harvi-limited CT coverage).*

```sql
-- Run on NUC after backfill finishes:
WITH me AS (
  SELECT DATE_TRUNC('month', interval_start AT TIME ZONE 'Europe/Dublin') AS month,
         ROUND(SUM(import_kwh)::NUMERIC, 1) AS me_kwh
  FROM myenergi_readings WHERE hub_serial = '21509692' AND interval_start >= '2024-06-01'
  GROUP BY 1
),
esb AS (
  SELECT DATE_TRUNC('month', recorded_at AT TIME ZONE 'Europe/Dublin') AS month,
         ROUND(SUM(import_kwh)::NUMERIC, 1) AS esb_kwh
  FROM meter_readings mr JOIN households h ON h.id = mr.household_id
  WHERE h.myenergi_serial = '21509692' AND recorded_at >= '2024-06-01'
  GROUP BY 1
)
SELECT TO_CHAR(e.month, 'Mon YYYY'), e.esb_kwh, m.me_kwh,
       ROUND((m.me_kwh / e.esb_kwh * 100)::NUMERIC, 1) AS me_pct_of_esb
FROM esb e JOIN me m USING (month) ORDER BY 1;
```

Expected result after fix: MyEnergi ≈ **90–95% of ESB** (the ~5–10% gap closes once Harvi is installed).

---

## What Was Fixed

### `deployment/myenergi_poller.py`

```python
# Before (wrong):
avg_cw    = sum(s.get("imp",  0) for s in slot_samples) / len(slot_samples)
avg_eddi  = sum(s.get("h1b", 0) + s.get("h1d", 0) for s in slot_samples) / len(slot_samples)
import_kwh = round(avg_cw   * 0.5 / 100 / 1000, 6)
eddi_kwh   = round(avg_eddi * 0.5 / 100 / 1000, 6)

# After (correct — values are Joules/minute):
import_kwh = round(sum(s.get("imp", 0) for s in slot_samples) / 3_600_000, 6)
eddi_kwh   = round(sum(s.get("h1b", 0) + s.get("h1d", 0) for s in slot_samples) / 3_600_000, 6)
```

### `scripts/myenergi_backfill.py`

Added `--force` flag to bypass the skip-if-≥40-slots guard. Required to re-fetch all historical dates after a formula fix:

```bash
python scripts/myenergi_backfill.py --start-date 2023-01-20 --force
```

### Historical data correction

Force backfill run 2026-05-07 from 2023-01-20 (Eddi installation date). Runtime ≈ 24 min.
All 1,203 dates re-fetched from MyEnergi API and upserted with corrected kWh values.

---

## Also Fixed in Same Session

| Fix | File | Description |
|-----|------|-------------|
| API `hr`/`min` fields are UTC | `MYENERGI_POLLER_EXPLAINED.md` | Previously documented as "local Dublin time". Boost at 07:00 Dublin appears as `hr=6` (06:00 UTC). Poller handles this correctly via `dublin.localize()` + timedelta. |
| `exp` field missing from docs | `MYENERGI_POLLER_EXPLAINED.md` | Added to field table; note that it is not currently persisted to DB. |
| `has_eddi` flag | households table | Was `false`, corrected to `true` via SQL UPDATE. |
| `myenergi_serial` JOIN fix | migration 008 | Free Saturday panels JOINed on `hardware_id` (MPRN) ≠ `hub_serial` (MyEnergi serial) — never matched. Fixed by adding `myenergi_serial = '21509692'` to households. |
| Grafana panels → myenergi_readings | `household_intelligence.json` | 11 import panels migrated from `meter_readings` to `myenergi_readings`. Export panels retain ESB source. |

---

## Grafana Panel Audit — Final State

| Panel | Source | Notes |
|-------|--------|-------|
| Total Import (kWh) | **myenergi_readings** | ✓ |
| Average Load Profile (hour of day) | **myenergi_readings** | ✓ |
| Average Daily Consumption by Day of Week | **myenergi_readings** | ✓ |
| Consumption by Tariff Slot | **myenergi_readings** | ✓ |
| Monthly Cost by Tariff Slot | **myenergi_readings** | ✓ |
| Shifting Opportunity — Peak → Night | **myenergi_readings** | ✓ |
| High-Power Events by Hour | **myenergi_readings** | ✓ |
| Weekday vs Weekend Load Profile | **myenergi_readings** | ✓ |
| Monthly Import kWh — Year-Over-Year | **myenergi_readings** | ✓ |
| Estimated Monthly Bill — Year-Over-Year | **myenergi_readings** | ✓ |
| Est. Cost stat | **myenergi_readings** | ✓ |
| Free Saturday Utilisation | **myenergi_readings** | ✓ (was already fixed) |
| Free Saturday — This Month | **myenergi_readings** | ✓ (was already fixed) |
| Total Export / Solar (kWh) | meter_readings | Export — ESB is source of truth |
| Import vs Solar Export timeseries | meter_readings | Has export component |
| Monthly Solar Export | meter_readings | Export only |
| Daily Load Decomposition | **hybrid** | ESB for total import/export; MyEnergi for Eddi kWh |
| Daily Tariff Cost Breakdown | meter_readings | Needs export credit calc (ESB) |
| Monthly Solar Export Revenue | meter_readings | Export only |
| Morning Boost vs Solar Overlap | meter_readings | Boost detection + export |
| Monthly: Solar Days vs Boost Overlap | meter_readings | Export-dependent |

**Rule**: any panel with `export_kwh` stays on `meter_readings` until `exp` field is persisted from MyEnergi API.

---

## Outstanding: `exp` Field Not Persisted

The MyEnergi API returns an `exp` field (grid export, Joules/min) but `myenergi_poller.py` does not store it in `myenergi_readings`. When Harvi is installed, persisting `exp` will allow the export panels to also move to MyEnergi data, eliminating the need for manual ESB CSV uploads entirely.

