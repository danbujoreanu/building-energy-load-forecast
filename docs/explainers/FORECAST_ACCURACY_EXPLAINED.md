# Forecast Accuracy Evaluation — Explainer
*Sparc Energy Ltd — how we measure whether the system's predictions are any good*
*Created: 2026-05-07 | Linked issues: DAN-168 (evaluation pipeline)*

---

## Overview

Forecast accuracy evaluation in this system covers **two coupled tracks**:

| Track | What we forecast | Ground truth | Why it matters |
|-------|-----------------|--------------|----------------|
| **1 — Solar / GHI** | Tomorrow's global horizontal irradiance (kWh/m²) | Open-Meteo archive API, written nightly by `run_daily_poll` | Drives the Eddi boost advisory — wrong forecast = wrong decision |
| **2 — Load forecast** | Half-hourly household electricity consumption (kWh) | ESB smart meter half-hourly readings (`meter_readings`) | Core of the thesis — the model's predictive value |

These two tracks are linked: a good load forecast combined with a good solar forecast produces the optimal heating dispatch decision. Evaluating them separately and together is the full picture.

---

## Database Schema — Tables Involved

```
advisory_log          — one row per advisory sent (date, action, ghi_forecast, est_solar)
solar_actuals         — one row per day (ghi_actual, eddi_kwh, export_kwh, panel_factor_obs)
weather_log           — hourly rows, data_type = 'forecast' | 'actual'
predictions           — one row per (household, prediction_time, target_interval) — load forecast
meter_readings        — one row per half-hour, actual ESB consumption (kWh)
model_drift_log       — weekly MAE snapshots written by _check_drift_sunday
```

### Key relationships

```
advisory_log.advisory_date  ──► solar_actuals.solar_date        (daily GHI + advisory accuracy)
weather_log (forecast)      ──► weather_log (actual)             (hourly GHI forecast vs actual)
predictions.target_interval ──► meter_readings.interval_start   (load forecast vs actual)
model_drift_log             ──► predictions / meter_readings     (drift monitoring)
```

---

## Track 1 — Solar / GHI Forecast Accuracy

### 1a. Daily advisory accuracy

Compares the GHI forecast used to generate the Pushover advisory against the actual GHI recorded the following evening.

```sql
SELECT
    a.advisory_date,
    a.recommendation,
    ROUND(a.ghi_forecast::numeric, 2)                              AS ghi_forecast_kwh,
    ROUND(s.ghi_actual::numeric, 2)                                AS ghi_actual_kwh,
    ROUND(((s.ghi_actual - a.ghi_forecast)
           / NULLIF(a.ghi_forecast, 0) * 100)::numeric, 1)        AS ghi_error_pct,
    ROUND(s.eddi_kwh::numeric, 2)                                  AS eddi_kwh_actual,
    a.acted_on,
    -- Was the advisory correct in hindsight?
    CASE
        WHEN a.recommendation = 'SKIP_BOOST' AND s.ghi_actual >= 2.0 THEN 'CORRECT'
        WHEN a.recommendation = 'SKIP_BOOST' AND s.ghi_actual <  2.0 THEN 'FALSE_SKIP'
        WHEN a.recommendation = 'KEEP_BOOST' AND s.ghi_actual <  2.0 THEN 'CORRECT'
        WHEN a.recommendation = 'KEEP_BOOST' AND s.ghi_actual >= 2.0 THEN 'MISSED_SKIP'
        ELSE 'PARTIAL'
    END                                                            AS advisory_verdict
FROM advisory_log a
JOIN solar_actuals s ON s.solar_date = a.advisory_date
WHERE a.advisory_date < CURRENT_DATE
ORDER BY a.advisory_date DESC;
```

**Interpreting `ghi_error_pct`:**
- ±20% is typical for a next-day Open-Meteo forecast in Ireland
- Errors > +50% (forecast underestimated sunshine) = potential missed skip opportunity
- Errors < −50% (forecast overestimated sunshine) = false skip — tank may not have heated

**Advisory verdict definitions:**
| Verdict | Meaning | Cost |
|---------|---------|------|
| `CORRECT` | Right call — saved money or correctly ran boost | €0 opportunity cost |
| `FALSE_SKIP` | Skipped boost, but solar was insufficient — tank cold | ~€0.13 (0.55 kWh × night rate) |
| `MISSED_SKIP` | Ran boost, but solar would have covered it | ~€0.13 wasted |
| `PARTIAL` | Partial boost cases | Context-dependent |

The threshold `ghi_actual >= 2.0 kWh/m²` aligns with `build_advisory()` SKIP_BOOST logic. Adjust if the threshold changes.

---

### 1b. Hourly GHI forecast vs actual

Now that `weather_log` captures both `data_type='forecast'` (persisted daily at 06:00) and `data_type='actual'` (written nightly by `run_daily_poll`), we can compare at hourly resolution.

```sql
SELECT
    f.hour_utc,
    ROUND(f.ghi_wh_m2::numeric, 1)                                AS ghi_forecast_wh,
    ROUND(a.ghi_wh_m2::numeric, 1)                                AS ghi_actual_wh,
    ROUND((a.ghi_wh_m2 - f.ghi_wh_m2)::numeric, 1)               AS error_wh,
    ROUND(ABS(a.ghi_wh_m2 - f.ghi_wh_m2)
          / NULLIF(a.ghi_wh_m2, 0) * 100, 1)                     AS abs_pct_error
FROM weather_log f
JOIN weather_log a
    ON  a.hour_utc   = f.hour_utc
    AND a.location   = f.location
    AND a.data_type  = 'actual'
WHERE f.data_type  = 'forecast'
  AND f.location   = 'maynooth'
  AND f.hour_utc   < NOW()
ORDER BY f.hour_utc DESC
LIMIT 168;   -- last 7 days
```

**Aggregate by month (MAPE):**

```sql
SELECT
    DATE_TRUNC('month', f.hour_utc AT TIME ZONE 'Europe/Dublin') AS month,
    COUNT(*)                                                       AS n_hours,
    ROUND(AVG(ABS(a.ghi_wh_m2 - f.ghi_wh_m2)
              / NULLIF(a.ghi_wh_m2, 0) * 100)::numeric, 1)       AS mape_pct,
    ROUND(AVG(ABS(a.ghi_wh_m2 - f.ghi_wh_m2))::numeric, 1)      AS mae_wh_m2
FROM weather_log f
JOIN weather_log a
    ON  a.hour_utc = f.hour_utc AND a.location = f.location AND a.data_type = 'actual'
WHERE f.data_type = 'forecast' AND f.location = 'maynooth'
  AND a.ghi_wh_m2 > 10   -- exclude night hours from MAPE (division by near-zero)
GROUP BY 1
ORDER BY 1 DESC;
```

> **Note:** MAPE excludes night hours (ghi < 10 Wh/m²) to avoid division by near-zero dominating the metric. Use MAE for a night-inclusive view.

---

## Track 2 — Load Forecast Accuracy

This is the **core of the thesis**: does the LightGBM H+24 model predict residential electricity consumption accurately enough to support energy management decisions?

### Schema

```sql
-- Forecast (written by live_inference.py / APScheduler at 16:00 daily)
predictions (
    household_id    UUID,
    prediction_time TIMESTAMPTZ,   -- when the forecast was generated
    target_interval TIMESTAMPTZ,   -- the half-hour being forecast (H+1 to H+48)
    predicted_kwh   NUMERIC(8,4),
    p10_kwh         NUMERIC(8,4),  -- lower bound (10th percentile)
    p90_kwh         NUMERIC(8,4)   -- upper bound (90th percentile)
)

-- Actuals (uploaded from ESB CSV or live smart meter)
meter_readings (
    household_id    UUID,
    interval_start  TIMESTAMPTZ,
    kwh             NUMERIC(8,4)
)
```

### 2a. Point forecast accuracy — rolling MAE/RMSE

```sql
SELECT
    DATE_TRUNC('week', p.target_interval AT TIME ZONE 'Europe/Dublin') AS week,
    COUNT(*)                                                             AS n_intervals,
    ROUND(AVG(ABS(m.kwh - p.predicted_kwh))::numeric, 4)               AS mae_kwh,
    ROUND(SQRT(AVG(POWER(m.kwh - p.predicted_kwh, 2)))::numeric, 4)    AS rmse_kwh,
    ROUND(AVG(ABS(m.kwh - p.predicted_kwh)
              / NULLIF(m.kwh, 0) * 100)::numeric, 1)                   AS mape_pct
FROM predictions p
JOIN meter_readings m
    ON  m.household_id   = p.household_id
    AND m.interval_start = p.target_interval
WHERE p.target_interval < NOW()
  AND m.kwh > 0.01   -- exclude near-zero intervals from MAPE
GROUP BY 1
ORDER BY 1 DESC;
```

### 2b. Accuracy by forecast horizon

The model produces H+1 through H+48 forecasts. Accuracy degrades with horizon.

```sql
SELECT
    EXTRACT(EPOCH FROM (p.target_interval - p.prediction_time)) / 3600 AS horizon_h,
    COUNT(*)                                                             AS n,
    ROUND(AVG(ABS(m.kwh - p.predicted_kwh))::numeric, 4)               AS mae_kwh,
    ROUND(AVG(ABS(m.kwh - p.predicted_kwh)
              / NULLIF(m.kwh, 0) * 100)::numeric, 1)                   AS mape_pct
FROM predictions p
JOIN meter_readings m
    ON  m.household_id = p.household_id AND m.interval_start = p.target_interval
WHERE p.target_interval < NOW() AND m.kwh > 0.01
GROUP BY 1
ORDER BY 1;
```

**Benchmark targets (from AICS 2025 paper, Norwegian building data):**
| Horizon | MAE target | MAPE target |
|---------|-----------|-------------|
| H+1     | < 0.08 kWh | < 12% |
| H+6     | < 0.10 kWh | < 15% |
| H+24    | < 0.12 kWh | < 18% |

Irish household results will differ — the primary goal of DAN-167 is to establish the Irish baseline.

### 2c. Prediction interval coverage (P10/P90)

The model outputs a P10–P90 interval (80% confidence). We expect ~80% of actuals to fall within it.

```sql
SELECT
    DATE_TRUNC('month', p.target_interval AT TIME ZONE 'Europe/Dublin') AS month,
    COUNT(*)                                                              AS n,
    ROUND(100.0 * SUM(CASE WHEN m.kwh BETWEEN p.p10_kwh AND p.p90_kwh
                           THEN 1 ELSE 0 END) / COUNT(*), 1)            AS coverage_pct,
    ROUND(AVG(p.p90_kwh - p.p10_kwh)::numeric, 4)                       AS avg_interval_width_kwh
FROM predictions p
JOIN meter_readings m
    ON  m.household_id = p.household_id AND m.interval_start = p.target_interval
WHERE p.target_interval < NOW()
GROUP BY 1
ORDER BY 1 DESC;
```

**Target:** `coverage_pct` ≈ 80%. If significantly > 80%, the model is over-cautious (wide intervals). If < 80%, it is over-confident. `avg_interval_width_kwh` should be < 0.3 kWh to be actionable.

### 2d. Baseline comparison (same-hour-last-week naive)

```sql
WITH actuals AS (
    SELECT household_id, interval_start, kwh
    FROM meter_readings
),
naive AS (
    SELECT
        a.household_id,
        a.interval_start,
        a.kwh                                               AS actual_kwh,
        lag(a.kwh) OVER (
            PARTITION BY a.household_id,
                         EXTRACT(DOW  FROM a.interval_start),
                         EXTRACT(HOUR FROM a.interval_start),
                         FLOOR(EXTRACT(MINUTE FROM a.interval_start) / 30)
            ORDER BY a.interval_start
        )                                                   AS naive_kwh
    FROM actuals a
)
SELECT
    ROUND(AVG(ABS(actual_kwh - naive_kwh))::numeric, 4)    AS naive_mae_kwh,
    ROUND(AVG(ABS(actual_kwh - naive_kwh)
              / NULLIF(actual_kwh, 0) * 100)::numeric, 1)  AS naive_mape_pct
FROM naive
WHERE naive_kwh IS NOT NULL AND actual_kwh > 0.01;
```

Run alongside 2a — the LightGBM model must beat this naive baseline to justify the complexity.

---

## Track 3 — Combined Advisory Decision Quality

Did the system make the right call? This bundles the GHI forecast accuracy (Track 1) with the load state (is the tank actually being heated?) and the financial outcome.

```sql
SELECT
    a.advisory_date,
    a.recommendation,
    ROUND(a.ghi_forecast::numeric, 2)                      AS ghi_forecast,
    ROUND(s.ghi_actual::numeric, 2)                        AS ghi_actual,
    ROUND(s.eddi_kwh::numeric, 2)                          AS eddi_actual_kwh,
    s.export_kwh,
    -- Estimated cost saving: skipped boost × night rate
    CASE WHEN a.recommendation LIKE 'SKIP%'
         THEN ROUND((0.55 * 0.2372)::numeric, 3)
         ELSE 0 END                                        AS saving_eur,
    -- Missed saving: ran boost when solar would have covered
    CASE WHEN a.recommendation LIKE 'KEEP%' AND s.ghi_actual >= 2.0
         THEN ROUND((0.55 * 0.2372)::numeric, 3)
         ELSE 0 END                                        AS missed_saving_eur
FROM advisory_log a
LEFT JOIN solar_actuals s ON s.solar_date = a.advisory_date
WHERE a.advisory_date < CURRENT_DATE
ORDER BY a.advisory_date DESC;
```

---

## Grafana — Planned Accuracy Panels (Solar Pipeline Dashboard)

Panels 28–32 are earmarked for accuracy audit. Build these once `advisory_log` has ≥ 14 days of entries with matching `solar_actuals`:

| Panel | Query | Type |
|-------|-------|------|
| 28 | GHI forecast vs actual (timeseries overlay) | Time series |
| 29 | GHI MAPE by month (Track 1b aggregate) | Bar chart |
| 30 | Advisory verdict breakdown (CORRECT/FALSE_SKIP/MISSED_SKIP) | Pie / stat |
| 31 | Load forecast MAE by week (Track 2a) | Time series |
| 32 | P10/P90 coverage % by month (Track 2c) | Gauge |

Panel 32 (`coverage_pct`) is the thesis-critical panel — it directly demonstrates whether the model's uncertainty estimates are well-calibrated.

---

## Dependency Chain

```
DAN-167 (train Irish model)
    └── populates predictions table
            └── enables Track 2 queries (2a–2d)
                    └── enables panels 31–32

advisory_log (running since 2026-05-06)
    └── Track 1a usable after ~14 days
            └── panels 28–30

weather_log forecast persistence (running since 2026-05-07)
    └── Track 1b usable after ~14 days
```

---

## What "Good" Looks Like at Scale

When Sparc moves beyond 1 household, the evaluation framework extends naturally:

- **Per-household accuracy league table** — identify which household types the model fits best (detached vs apartment, storage heater vs Eddi)
- **Seasonal calibration signal** — MAPE drift in summer (load harder to predict during holiday periods) triggers `check_drift_sunday`
- **Advisory ROI** — aggregate `saving_eur` across households = North Star metric for investor updates
- **P10/P90 coverage audit** — if coverage collapses below 70%, the quantile regression is miscalibrated → re-run `run_pipeline.py` with more recent data

---

---

## Day-After Verification — Did the Advisory Get It Right?

Run this each morning after `run_daily_poll` populates `solar_actuals` (23:30–23:45 the previous night):

```sql
SELECT
    a.advisory_date,
    a.recommendation,
    ROUND(a.ghi_forecast::numeric, 2)                                AS ghi_forecast_kwh,
    ROUND(s.ghi_actual::numeric, 2)                                  AS ghi_actual_kwh,
    ROUND(((s.ghi_actual - a.ghi_forecast)
           / NULLIF(a.ghi_forecast, 0) * 100)::numeric, 1)          AS ghi_error_pct,
    ROUND(s.eddi_kwh::numeric, 2)                                    AS eddi_kwh,
    ROUND(s.export_kwh::numeric, 2)                                  AS export_kwh,
    a.acted_on,
    CASE
        WHEN a.recommendation = 'SKIP_BOOST' AND s.ghi_actual >= 2.0 THEN 'CORRECT'
        WHEN a.recommendation = 'SKIP_BOOST' AND s.ghi_actual <  2.0 THEN 'FALSE_SKIP'
        WHEN a.recommendation = 'KEEP_BOOST' AND s.ghi_actual <  2.0 THEN 'CORRECT'
        WHEN a.recommendation = 'KEEP_BOOST' AND s.ghi_actual >= 2.0 THEN 'MISSED_SKIP'
        ELSE 'PARTIAL'
    END                                                              AS verdict
FROM advisory_log a
LEFT JOIN solar_actuals s ON s.solar_date = a.advisory_date
WHERE a.advisory_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY a.advisory_date DESC;
```

**Columns to check:**
- `ghi_error_pct` — was the forecast close? ±20% is typical for next-day Open-Meteo in Ireland
- `eddi_kwh` — how much actually heated (note: ~50% efficiency until second Harvi installed)
- `acted_on` — did the user tap the Pushover deep-link? NULL = no response logged
- `verdict` — CORRECT / FALSE_SKIP / MISSED_SKIP

**Example: checking if today's advisory was vindicated (run tonight after solar_actuals populates):**

```sql
SELECT recommendation, ghi_forecast, ghi_actual, acted_on,
       CASE WHEN recommendation='SKIP_BOOST' AND ghi_actual >= 2.0 THEN 'CORRECT'
            WHEN recommendation='SKIP_BOOST' AND ghi_actual <  2.0 THEN 'FALSE_SKIP'
            WHEN recommendation='KEEP_BOOST' AND ghi_actual >= 2.0 THEN 'MISSED_SKIP'
            ELSE 'CORRECT' END AS verdict
FROM advisory_log a
LEFT JOIN solar_actuals s ON s.solar_date = a.advisory_date
WHERE a.advisory_date = CURRENT_DATE;
```

---

## Notes on Data Sources

**CER Smart Metering Trial (ISSDA, 2009–2010):** Initially considered for Irish model training (DAN-169). Ruled out — no heat pumps existed in Ireland at that time, so the dataset contains no weather-correlated electrical load. It cannot be used to validate the thesis question (does the model transfer to electrically-heated Irish homes?).

**Current approach (DAN-169):** Norwegian Drammen buildings (electric heating, strong weather correlation) as proxy for Irish heat pump households. Validate with Irish calendar features (school term, bank holidays) overlaid on the Norwegian model. Revisit when a more current Irish heat pump dataset becomes available.

**CRU dynamic pricing (June 2026):** The CRU mandates that the five largest suppliers *offer* dynamic 30-minute pricing — it is an optional plan for customers, not mandatory participation. This affects the market sizing estimate (uptake will be gradual, not instant) but does not change the product thesis.

---

*Related: `docs/explainers/SOLAR_ADVISORY_EXPLAINED.md` — how the advisory is generated*
*Related: `docs/explainers/MYENERGI_POLLER_EXPLAINED.md` — data pipeline that feeds solar_actuals*
*Related: `docs/governance/MODEL_CARD.md` — model performance claims and test conditions*
