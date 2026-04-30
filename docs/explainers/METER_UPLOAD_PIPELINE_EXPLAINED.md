# Meter Upload Pipeline — Complete Technical Walkthrough
*Part of the Explainers/ series. Local only — not tracked in git.*
*Covers: DAN-104 (CSV parser), DAN-105 (TimescaleDB upsert), DAN-147 (ESB vs MyEnergi reconciliation)*
*Last updated: 2026-04-30*

---

## What This Document Is

A technical walkthrough of how electricity meter data enters the Sparc system — from the raw CSV file downloaded from ESB Networks My Account, through validation and parsing, into TimescaleDB, and finally surfaced in the reconciliation dashboard. Written for an engineer who needs to debug an upload failure, understand a parsing edge case, or extend the pipeline to accept a new file format.

---

## Why Meter Data Is the Foundation of Everything

Every Sparc feature downstream depends on clean, correctly-timestamped meter readings:

- **Load forecasting** — LightGBM trains on `meter_readings.import_kwh` at 30-min resolution
- **Tariff cost breakdown** — Grafana panels multiply `import_kwh` by slot rates per interval
- **Plan comparison** — replays every interval in `meter_readings` against alternative tariff plans
- **Export revenue** — sums `meter_readings.export_kwh` × 18.5c/kWh
- **ESB vs MyEnergi reconciliation** — compares `meter_readings` daily totals vs `myenergi_readings`

If the data is wrong — wrong timezone, duplicated rows, kW instead of kWh — every downstream output is silently wrong. The parser (DAN-104) is the gate that prevents bad data from entering. The upsert (DAN-105) ensures the gate stays clean on re-uploads.

---

## The ESB HDF CSV Format

ESB Networks My Account exports meter data as HDF (Half-Hour Data) CSV files. The filename follows this pattern:

```
HDF_calckWh_{MPRN}_{DD-MM-YYYY}.csv
```

Example: `HDF_calckWh_10306822417_20-04-2026.csv` — meter 10306822417, downloaded 20 April 2026.

### Columns

| Column | Example | Notes |
|--------|---------|-------|
| `MPRN` | `10306822417` | Meter Point Reference Number — the household identifier |
| `Meter Serial Number` | `08E00001234` | Physical meter hardware ID |
| `Read Value` | `0.082` | kWh value for this 30-min interval |
| `Read Type` | `Active Import Interval (kW)` | See note below |
| `Read Date and End Time` | `01-04-2026 00:30` | **End** of the 30-min interval, Dublin local time |

**Critical note on `Read Type`:** The column name says `(kW)` but the file named `calckWh` contains values that are already in **kWh** (cumulative per interval), not kW. The `HDF_calckWh_` prefix is the signal that this is the kWh-format export. ESB also provides `HDF_calcPower_` files with instantaneous kW values — those require `× 0.5` to convert to kWh. The parser validates the filename prefix to avoid silent unit errors.

### Read Types

Two rows appear per timestamp — one for import, one for export:

- `"Active Import Interval (kW)"` → `meter_readings.import_kwh`
- `"Active Export Interval (kW)"` → `meter_readings.export_kwh`

The parser pivots these two Read Types into two columns aligned on the same timestamp.

### Date format

`"01-04-2026 00:30"` — day-month-year, 24-hour time, Dublin local time. This is **not** ISO 8601 and **not** UTC. The parser converts using:

```python
pd.to_datetime(col, format="%d-%m-%Y %H:%M", utc=False).dt.tz_localize("Europe/Dublin", ambiguous="infer")
```

`ambiguous="infer"` handles the DST autumn clock-change night (last Sunday of October). During that night, 01:00–02:00 occurs twice. Pandas infers which occurrence is pre-DST and which is post-DST from the surrounding sequence. This avoids one of the two common DST pitfalls (the other — the spring "spring forward" gap — leaves a missing 30-min interval at 01:00 which is correct and expected).

---

## DAN-104: CSV Parser and Schema Validation

**File:** `src/energy_forecast/api/meter_store.py` (parser section)

### Validation gates

The parser applies three layers of validation before writing a single row to the database.

**Gate 1: Required columns**
```python
REQUIRED_COLS = {
    "MPRN", "Read Value", "Read Type", "Read Date and End Time"
}
missing = REQUIRED_COLS - set(df.columns)
if missing:
    raise ValueError(f"Missing columns: {missing}. Got: {list(df.columns)}")
```

This fires with a clear error message before any parsing attempt. A common failure mode is downloading the wrong export type from ESB Networks (power vs energy) — this check catches it immediately.

**Gate 2: Read Type values**
```python
VALID_READ_TYPES = {
    "Active Import Interval (kW)",
    "Active Export Interval (kW)"
}
unexpected = set(df["Read Type"].unique()) - VALID_READ_TYPES
if unexpected:
    raise ValueError(f"Unexpected Read Types: {unexpected}")
```

ESB occasionally changes export format. If a new Read Type appears in the file, this gate fires rather than silently dropping rows.

**Gate 3: Minimum rows**
```python
if len(df) < 48:
    raise ValueError(f"File contains only {len(df)} rows — expected ≥ 48 (one full day)")
```

Partial uploads (the user accidentally downloaded only a partial month) fail here rather than being partially ingested and causing gaps in the time series.

### The pivot

After validation, the parser pivots import and export into aligned columns:

```python
pivoted = (
    df.assign(recorded_at=parsed_timestamps)
    .pivot_table(
        index=["MPRN", "recorded_at"],
        columns="Read Type",
        values="Read Value",
        aggfunc="first"
    )
    .rename(columns={
        "Active Import Interval (kW)": "import_kwh",
        "Active Export Interval (kW)": "export_kwh",
    })
    .reset_index()
)
```

`aggfunc="first"` handles the edge case where a row appears twice for the same (MPRN, timestamp, Read Type) — taking the first value rather than raising.

### MPRN → household_id resolution

`meter_readings` uses a UUID `household_id`, not the MPRN string. The parser resolves this:

```python
row = await conn.fetchrow(
    "SELECT id FROM households WHERE hardware_id = $1",
    mprn
)
if row is None:
    # Auto-provision: create a new household for this MPRN
    household_id = str(uuid4())
    await conn.execute(
        "INSERT INTO households (id, hardware_id, city, has_solar) VALUES ($1, $2, $3, $4)",
        household_id, mprn, "ireland", True
    )
else:
    household_id = str(row["id"])
```

Auto-provisioning means the `/upload` endpoint is self-contained — a new household doesn't require a separate registration step. The household record is created on first upload with sensible defaults (`city="ireland"`, `has_solar=True`). These can be updated later via the admin interface.

---

## DAN-105: TimescaleDB Upsert

**The constraint:**
```sql
PRIMARY KEY (household_id, recorded_at)
```

Every row in `meter_readings` is uniquely identified by `(household_id, recorded_at)`. Uploading the same file twice must be a no-op, not a duplication.

### The `ON CONFLICT DO NOTHING` pattern

```python
await conn.executemany(
    """
    INSERT INTO meter_readings (household_id, recorded_at, import_kwh, export_kwh)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (household_id, recorded_at) DO NOTHING
    """,
    rows
)
```

`DO NOTHING` is the correct choice over `DO UPDATE` here. If a row already exists, the existing value is correct — ESB calibrated meter readings don't change retroactively. `DO UPDATE` would silently overwrite correct historical data with an identical value (wasteful) or with a different value (dangerous if data was manually corrected).

### Counting inserted vs skipped rows

`executemany` doesn't natively return per-row affected counts. The pattern used is:

```python
count_before = await conn.fetchval(
    "SELECT COUNT(*) FROM meter_readings WHERE household_id = $1 AND recorded_at = ANY($2::TIMESTAMPTZ[])",
    household_id, [r[1] for r in rows[:100]]  # sample check
)
await conn.executemany(INSERT_SQL, rows)
count_after = await conn.fetchval(...)
rows_inserted = count_after - count_before
rows_skipped  = len(rows) - rows_inserted
```

The response includes both:
```json
{
  "household_id": "a998f9b7-...",
  "rows_inserted": 1440,
  "rows_skipped": 0,
  "date_from": "2026-03-01",
  "date_to": "2026-03-30"
}
```

A `rows_skipped > 0` on a first upload indicates the file was uploaded before (normal). A `rows_skipped = rows_inserted = 0` means the file had no data rows — check the validation gates for what went wrong.

### TimescaleDB hypertable considerations

`meter_readings` is a TimescaleDB hypertable partitioned by `recorded_at`. The `ON CONFLICT` clause requires the primary key to include the partitioning column (`recorded_at`), which it does. Standard PostgreSQL `ON CONFLICT` behaviour applies inside each chunk — TimescaleDB doesn't change the conflict semantics.

**Bulk insert performance:** For a 2-year ESB CSV (17,280 rows at 30-min resolution), `executemany` completes in approximately 0.4–0.8 seconds on a local TimescaleDB instance. For very large uploads (multi-year, multi-household batch), consider `COPY` instead of `executemany` — but the overhead is acceptable for the current single-household MVP.

---

## DAN-147: ESB vs MyEnergi Import Reconciliation

**What it is:** Three Grafana panels in the Solar Data Pipeline dashboard that cross-validate ESB meter data against MyEnergi hub data. Both independently measure grid import for the same household at 30-min resolution. In a correctly functioning system, their daily sums should agree within ±5%.

### Why the two sources exist

| Source | Table | Granularity | Coverage | Truth type |
|--------|-------|-------------|----------|------------|
| ESB smart meter | `meter_readings` | 30-min | Upload-dependent (monthly) | **Billing truth** |
| MyEnergi hub | `myenergi_readings` | 30-min | Nightly poll, rolling 2 weeks | **Operational truth** |

**ESB is the billing truth** — it's what BGE charges you for. **MyEnergi is the operational truth** — it's what Sparc uses for live-cycle monitoring and Eddi scheduling. If they diverge systematically, there's either:
1. A timezone offset error in one source
2. A partial circuit measurement (MyEnergi hub only monitors circuits physically wired through it)
3. A meter calibration issue

### The reconciliation query

```sql
SELECT
  esb.day AS time,
  esb.daily_import_kwh AS "ESB Import (kWh)",
  COALESCE(me.daily_import_kwh, 0) AS "MyEnergi Import (kWh)",
  ROUND((esb.daily_import_kwh - COALESCE(me.daily_import_kwh, 0))::NUMERIC, 3) AS "Difference (kWh)"
FROM (
  SELECT
    DATE(recorded_at AT TIME ZONE 'Europe/Dublin') AS day,
    ROUND(SUM(import_kwh)::NUMERIC, 3) AS daily_import_kwh
  FROM meter_readings
  WHERE household_id = '$household_id'::uuid
    AND $__timeFilter(recorded_at)
  GROUP BY 1
) esb
LEFT JOIN (
  SELECT
    DATE(interval_start AT TIME ZONE 'Europe/Dublin') AS day,
    ROUND(SUM(import_kwh)::NUMERIC, 3) AS daily_import_kwh
  FROM myenergi_readings
  WHERE hub_serial = '21509692'
  GROUP BY 1
) me ON me.day = esb.day
ORDER BY esb.day
```

**`LEFT JOIN` on ESB:** ESB is the primary source — days where ESB has data but MyEnergi doesn't (polling gap) appear with MyEnergi showing 0. A `FULL JOIN` would also show MyEnergi-only days, but since ESB is billing truth, ESB-only is the direction that matters.

**`AT TIME ZONE 'Europe/Dublin'`:** Both sources store timestamps in UTC (TimescaleDB convention). The timezone conversion happens at query time. Both subqueries apply the same timezone, ensuring they group on the same calendar days.

### Three panels

**Panel 11 — Overlay time series:** ESB import (blue), MyEnergi import (orange), Difference (red dashed). The eye immediately spots systematic bias (one line consistently above the other) vs day-specific spikes (difference appears on specific dates).

**Panel 12 — % Difference time series:** `(ESB - MyEnergi) / MyEnergi × 100`. Threshold bands:
- Green: < 5% — acceptable agreement
- Yellow: 5–15% — investigate
- Orange: > 15% — likely a systematic issue

**Panel 13 — Summary stats (stat panel):**
- Mean daily difference (kWh)
- Max daily difference (kWh)
- Days compared

### Interpreting the results

**Consistent positive bias (ESB > MyEnergi by 5–15%):** Normal. The ESB smart meter is the authoritative billing meter — it measures total house consumption. The MyEnergi hub only sees consumption from circuits wired through it. If the office, secondary fridge, or external lights are not wired through the MyEnergi hub, those loads appear in ESB but not MyEnergi.

**Consistent negative bias (MyEnergi > ESB):** Unusual. Could indicate a CT clamp calibration error in the MyEnergi hub, or a metering configuration issue.

**Large spikes on specific dates:** Check whether those dates correspond to:
- DST transitions (01:00–02:00 ambiguity in the autumn changeover)
- Days with unusual loads (electric vehicle charger, heat gun, etc.)
- Upload boundaries (the ESB file was uploaded mid-day, creating a partial day)

**Zero MyEnergi rows for a date:** The nightly poller missed that day. Check `docker logs sparc-scheduler` for the relevant date. MyEnergi polling uses the Sparc internal `poller.py` running at 23:30.

---

## The Full Upload Flow

```
User downloads HDF CSV from ESB Networks My Account
    │
    ▼
POST /upload (multipart form, file + optional household_id)
    │
    ├── DAN-104: Validate columns, Read Types, row count
    ├── DAN-104: Parse timestamps (Europe/Dublin, DST-aware)
    ├── DAN-104: Pivot import/export by (MPRN, recorded_at)
    ├── DAN-104: Resolve MPRN → household_id (auto-provision if new)
    │
    ├── DAN-105: INSERT ON CONFLICT DO NOTHING into meter_readings
    │
    └── Return: {household_id, rows_inserted, rows_skipped, date_from, date_to}

Later, nightly:
    APScheduler → aggregate daily export from meter_readings → solar_actuals.export_kwh
    (this job does not yet exist — see SOLAR_ADVISORY_EXPLAINED.md for the gap)
```

---

## Troubleshooting

### "Missing columns" on upload

The file is probably the wrong export type. Confirm the filename starts with `HDF_calckWh_` (not `HDF_calcPower_` or a different prefix). Re-download from ESB Networks My Account, selecting the "Energy" export option.

### All rows skipped on a known-fresh upload

Check whether the (household_id, recorded_at) combination already exists. This can happen if the same CSV was uploaded previously under a different household_id — the timestamps are in the DB but under a different UUID. Query:
```sql
SELECT DISTINCT household_id FROM meter_readings
WHERE recorded_at BETWEEN '2026-03-01' AND '2026-03-02'
ORDER BY 1;
```

### Reconciliation panel shows no MyEnergi data

The MyEnergi nightly poll stores data in `myenergi_readings`. If the panel shows only ESB bars with no orange overlay, check:
```sql
SELECT MAX(interval_start) FROM myenergi_readings WHERE hub_serial = '21509692';
```
If this is more than 2 days ago, the nightly poller has stopped. Check `docker ps` and the scheduler logs.

### DST-related 1-row gap in spring upload

On the last Sunday of March, clocks move from 01:00 to 02:00. ESB CSV files have no row for 01:30 that night — this is correct. The parser `tz_localize("Europe/Dublin", ambiguous="infer")` handles this gracefully; the gap is expected and will not cause an error.

### `rows_inserted` is much lower than expected

If uploading a 2-year file but only 500 rows insert, the file likely covers dates already in the DB. The `rows_skipped` count will be high. This is correct idempotent behaviour. Use `date_from` and `date_to` in the response to confirm which date range was covered.

---

## Future: SMDS API Integration

The current upload flow is manual — download CSV, POST to `/upload`. This changes when the ESB Smart Meter Data System (SMDS) goes live in mid-2026. At that point:

- Sparc registers as an ESCO under CRU202517 (DAN-66 — user-handled)
- SMDS provides an API: 30-min import/export for the last 24 months, with household consent
- The parser layer will need a new `parse_smds_response()` function alongside `parse_esb_csv()`
- The upsert layer is unchanged — it works on the same `meter_readings` schema regardless of source

The parser's validation gate design (column checks, Read Type checks, minimum rows) should be adapted for the SMDS response format when the time comes. The DAN-104 validation pattern is the right template.

---

## Decision Log

| Decision | What we chose | Why | Alternatives rejected |
|----------|--------------|-----|----------------------|
| `ON CONFLICT DO NOTHING` | Skip duplicate rows silently | ESB meter readings are final — re-uploading the same file must be a no-op. `DO NOTHING` is idempotent and safe. | `DO UPDATE SET import_kwh = EXCLUDED.import_kwh` — silently overwrites if the same timestamp appears twice with different values; also wastes I/O rewriting identical data |
| `ambiguous="infer"` for DST | Pandas timezone-localize with infer | The autumn clock-change night has ambiguous 01:00–01:59 timestamps. `infer` derives the correct pre/post-DST assignment from the surrounding sequence without requiring user intervention. | `ambiguous="NaT"` — drops the ambiguous hour; data gap every October. `ambiguous="raise"` — fails the upload with a confusing error. |
| Auto-provision households on first upload | Create household if MPRN not found | Reduces friction for new users to zero — upload works without a prior registration step. MPRN is a stable household identifier; auto-provisioning with sensible defaults is safe. | Require explicit household creation first — extra setup step, fails silently with 404 if user forgets |
| Left join in reconciliation (ESB primary) | ESB is the outer table | ESB is billing truth. Days where ESB has data but MyEnergi doesn't (polling gap) are more informative than the reverse. The reconciliation panel is primarily asking "does MyEnergi agree with what ESB is billing?" | Full outer join — shows MyEnergi-only rows that have no billing relevance |
| 90-day rolling window for `solar_actuals` sync | `CURRENT_DATE - INTERVAL '90 days'` | Catches any retrospective ESB CSV uploads (user uploading a 3-month file) while staying within a predictable time window. Full-history sync would be slow on large datasets. | 30-day window — misses a user who uploads a 2-month file at the end of the month. Full history — slow and unnecessary, historical export doesn't change. |
| Three separate reconciliation panels (overlay, %, stats) | Three panels in Grafana | Each answers a different question: the overlay shows absolute values and their relationship; the % difference shows systematic bias at a glance; the summary stats give a single-number assessment. A single panel would require the viewer to mentally compute all three. | Single combined panel — works for experts but hides the key "is the bias systematic?" question from less experienced users |
| `aggfunc="first"` in pivot | Take first value on duplicate (MPRN, ts, Read Type) | Handles the edge case where ESB CSV contains a duplicated row (sometimes appears at DST boundaries or file concatenation artefacts) without raising. | `aggfunc="sum"` — would double-count a duplicated row, inflating kWh. `aggfunc="mean"` — correct if both values are identical, but produces non-obvious fractional values if they differ. |

## References

- `src/energy_forecast/api/meter_store.py` — DAN-104 parser + DAN-105 upsert
- `deployment/app.py` — `/upload` endpoint wiring
- `infra/grafana/provisioning/dashboards/solar_pipeline.json` — DAN-147 reconciliation panels
- `docs/SMART_METER_ACCESS.md` — SMDS regulatory timeline and ESCO registration path
- `data/ESB Smart Meter Data/` — canonical location for raw ESB HDF files
- ESB Networks My Account: `myaccount.esbnetworks.ie` — download HDF CSV here
- Linear: [DAN-104](https://linear.app/danbujoreanu/issue/DAN-104) · [DAN-105](https://linear.app/danbujoreanu/issue/DAN-105) · [DAN-147](https://linear.app/danbujoreanu/issue/DAN-147)
