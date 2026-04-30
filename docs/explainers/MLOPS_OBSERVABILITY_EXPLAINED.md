# MLOps Observability — Complete Technical Walkthrough
*Part of the Explainers/ series. Local only — not tracked in git.*
*Covers: DAN-115 (/metrics endpoint), DAN-116 (correlation IDs + sanity checks)*
*Last updated: 2026-04-30*

---

## What This Document Is

A technical walkthrough of Sparc's production observability layer — the `/metrics` endpoint that gives a structured health picture of the entire pipeline, and the correlation ID + sanity check system that makes individual inference requests traceable and validated. Written for an engineer who needs to debug a pipeline failure, interpret a health alert, or add new monitoring dimensions.

---

## Why This Exists — The Interview Question

> "A model trains and validates fine. Three weeks into production, forecasts start drifting high on Friday evenings. How do you find out?"

Without observability, the answer is: you wait for a user complaint. With it:
- The `/metrics` endpoint flags `7d_mae > 1.5× training_mae` — the drift alert fires
- Correlation IDs in the logs let you pull every prediction from Friday evenings specifically
- Sanity checks confirm the issue isn't a stuck model (all-identical predictions) or a data gap (negative kWh)

DAN-115 and DAN-116 are the infrastructure that makes this debugging workflow possible. They're not features a user sees — they're the instruments an engineer reaches for when something goes wrong.

---

## DAN-116: Correlation IDs and Prediction Sanity Checks

### Correlation IDs — the `request_id` field

Every prediction request now gets a UUID at the API boundary:

```python
# In app.py, /predict endpoint
request_id = str(uuid4())
```

This `request_id` is:
1. Returned in the API response body (`PredictionResponse.request_id`)
2. Injected into every log line for that request using the `[{request_id}]` prefix pattern
3. Available to the caller to include in their own logs, enabling end-to-end tracing

**What a traced request looks like in logs:**

```
2026-04-30 16:00:02  INFO  [3f2a1c] Loading features for household 'a998f9b7...'
2026-04-30 16:00:02  INFO  [3f2a1c] LightGBM inference: 24 predictions generated
2026-04-30 16:00:02  INFO  [sanity|3f2a1c] Checks passed (24 predictions, no warnings)
2026-04-30 16:00:02  INFO  [3f2a1c] Stored predictions for 2026-05-01
```

The abbreviated prefix `[3f2a1c]` (first 6 chars of the UUID) is enough to filter a specific request from a log stream:
```bash
grep '\[3f2a1c\]' app.log
```

Without this, debugging "the 16:00 forecast on April 30 was wrong" requires reading every log line from that minute and manually correlating which household, which model run, which storage call.

### The `ControlResponse` also gets `request_id`

The `/control` endpoint (which calls live inference and makes scheduling decisions) also returns a `request_id`. Control decisions are higher stakes than predictions — if the controller decides to flag a peak-hour conflict, you want to be able to trace exactly which forecast drove that decision.

```python
class ControlResponse(BaseModel):
    request_id: str
    building_id: str
    city: str
    forecast_origin: str
    decisions: list[HourDecision]
    morning_brief: str
```

### Sanity checks — `_sanity_check_predictions()`

```python
def _sanity_check_predictions(request_id: str, preds: list[float]) -> list[str]:
    warnings = []
    if any(math.isnan(p) or math.isinf(p) for p in preds):
        warnings.append("NaN or Inf values in predictions")
    if any(p < 0 for p in preds):
        warnings.append(f"{sum(1 for p in preds if p < 0)} negative prediction(s)")
    if any(p > 500 for p in preds):
        warnings.append(f"{sum(1 for p in preds if p > 500)} prediction(s) > 500 kWh")
    if len(preds) > 1 and len(set(preds)) == 1:
        warnings.append("All predictions identical — possible stuck model")
    for w in warnings:
        logger.warning("[sanity|%s] %s", request_id, w)
    return warnings
```

**What each check catches:**

| Check | What it detects | Likely cause |
|-------|----------------|--------------|
| NaN / Inf | Model returned non-numeric output | Feature pipeline produced NaN inputs (missing data gap, division by zero in feature engineering) |
| Negative values | kWh < 0 | Model has seen poor training data or is extrapolating far outside training range |
| > 500 kWh/hour | Physically impossible residential load | Unit error (W vs kWh), feature scaling bug, model wildly out of distribution |
| All identical | Model output is constant | Stuck model — model file may be corrupted or feature inputs are all-zero |

**Warnings are returned in the response.** `PredictionResponse.warnings` is a `list[str]` that contains any triggered checks. The API caller can log or surface these:

```json
{
  "request_id": "3f2a1c...",
  "building_id": "a998f9b7",
  "predictions": [0.42, 0.51, ...],
  "inference_mode": "live",
  "warnings": ["2 negative prediction(s)"]
}
```

Warnings do not cause the request to fail — predictions are still returned. This is intentional: a partially-degraded prediction is better than a 500 error that leaves the morning advisory without a cost forecast. The warning is the signal to investigate; the prediction is the best available output.

---

## DAN-115: The `/metrics` Endpoint

### Design philosophy

`/health` answers one question: "is the server up?" (`{"status": "ok"}`).

`/metrics` answers the engineering question: "is the **pipeline** healthy?" A server can be up while:
- The last meter reading was 8 days ago (upload failure)
- The model has run zero predictions this week (scheduler missed)
- Seven of the last fourteen daily MAEs exceed the drift threshold (model degradation)
- All four models are running in mock mode (live model file missing)

None of these are visible from `/health`. All of them are visible from `/metrics`.

### The response schema

```json
{
  "timestamp": "2026-04-30T16:00:00Z",
  "status": "degraded",
  "models": {
    "lightgbm": "live",
    "all_mocked": false
  },
  "data": {
    "households_count": 1,
    "meter_readings_total": 34624,
    "meter_readings_last_ts": "2026-04-28T23:30:00Z",
    "meter_readings_staleness_hours": 40.5,
    "myenergi_days_last_30d": 28,
    "myenergi_missing_days_last_30d": 2,
    "predictions_last_7d": 7,
    "advisories_last_7d": 7
  },
  "alerts": [
    {
      "level": "warning",
      "field": "meter_readings_staleness_hours",
      "message": "No meter readings in 40h (threshold: 168h) — ESB upload may be overdue"
    }
  ]
}
```

**`status` summary values:**
- `"ok"` — no alerts triggered
- `"degraded"` — one or more warnings
- `"critical"` — any alert at critical level (e.g., all models mocked, zero predictions in 7 days)

### Alert thresholds

| Metric | Threshold | Level | Meaning |
|--------|-----------|-------|---------|
| `meter_readings_staleness_hours` | > 168h (7 days) | Warning | ESB CSV not uploaded in over a week |
| `myenergi_missing_days_last_30d` | > 3 | Warning | MyEnergi poller has missed >3 nights |
| `predictions_last_7d` | = 0 | Critical | 16:00 scheduler has not run at all this week |
| `advisories_last_7d` | = 0 | Warning | 08:00 morning advisory has not fired all week |
| `all_mocked` | = true | Critical | Live model file missing — all inference is mock |

**Why 168h for meter staleness?** ESB data is uploaded manually from the ESB Networks My Account portal. Monthly uploads are the current cadence (mid-2026 SMDS will automate this). A 168-hour (7-day) window catches missed uploads without falsely alerting during normal monthly cycles.

**Why separate thresholds for predictions and advisories?** They can fail independently. The 16:00 inference job writes `predictions`; the 08:00 advisory reads `predictions` and writes `advisory_log`. If the scheduler fires but the advisory fails, `predictions_last_7d > 0` but `advisories_last_7d = 0`. The independent checks pinpoint which stage broke.

### The SQL queries behind `/metrics`

```python
# Data health queries (run in parallel via asyncio.gather)
households_q     = "SELECT COUNT(*) FROM households"
readings_q       = """
    SELECT COUNT(*) AS total,
           MAX(recorded_at) AS last_ts
    FROM meter_readings
    WHERE household_id = ANY(SELECT id FROM households)
"""
myenergi_q       = """
    SELECT
        COUNT(DISTINCT DATE(interval_start AT TIME ZONE 'Europe/Dublin')) AS days_present
    FROM myenergi_readings
    WHERE interval_start >= NOW() - INTERVAL '30 days'
      AND hub_serial = '21509692'
"""
predictions_q    = """
    SELECT COUNT(DISTINCT forecast_date)
    FROM predictions
    WHERE issued_at >= NOW() - INTERVAL '7 days'
"""
advisories_q     = """
    SELECT COUNT(*)
    FROM advisory_log
    WHERE issued_at >= NOW() - INTERVAL '7 days'
"""
```

All five queries run concurrently. The endpoint's p50 latency target is <200ms on a local TimescaleDB instance. With parallel queries against indexed tables, this is achievable with typical data volumes.

### The `models` section

```python
"models": {
    "lightgbm": "live" | "mock",
    "all_mocked": bool
}
```

The `inference_mode` field (added to `PredictionResponse` in DAN-116) propagates from `live_inference.py` — the model loader sets `"live"` when it successfully loads a `.pkl` file and `"mock"` when it falls back to random walk or population average. `/metrics` aggregates this: if any model is `"mock"`, `all_mocked` is true (or at minimum one model is degraded).

**Why is `/health` not enough?** The `/health` endpoint confirms the server process is alive and the database connection is open. It does not know whether `model_lgbm.pkl` was successfully loaded. A deployment where the model file was corrupted or wasn't copied would pass `/health` but fail `/metrics`.

---

## Reading `/metrics` in Practice

### Healthy pipeline

```json
{
  "status": "ok",
  "models": { "lightgbm": "live", "all_mocked": false },
  "alerts": []
}
```
Nothing to do.

### Stale meter data

```json
{
  "status": "degraded",
  "data": { "meter_readings_staleness_hours": 192 },
  "alerts": [{ "level": "warning", "field": "meter_readings_staleness_hours",
               "message": "No meter readings in 192h..." }]
}
```
Action: upload a fresh ESB CSV via `POST /upload`.

### Scheduler missed runs

```json
{
  "status": "critical",
  "data": { "predictions_last_7d": 0 },
  "alerts": [{ "level": "critical", "field": "predictions_last_7d",
               "message": "Zero predictions in 7d — APScheduler may have stopped" }]
}
```
Action: check `docker logs sparc-api` for scheduler errors. Restart the service if needed. The APScheduler logs `[scheduler]` prefixed lines on each job fire and failure.

### All models mocked

```json
{
  "status": "critical",
  "models": { "lightgbm": "mock", "all_mocked": true },
  "alerts": [{ "level": "critical", "field": "all_mocked",
               "message": "Live model not loaded — all inference is mock data" }]
}
```
Action: check `MODEL_PATH` env var, verify `model_lgbm.pkl` exists and is readable, check for unpickling errors in startup logs.

---

## Grafana Integration

The `/metrics` endpoint is designed to be scraped by Grafana via the JSON datasource plugin (or a simple n8n webhook poller). Each `alerts[]` entry maps to a Grafana alert condition. The recommended integration:

1. n8n polls `GET /metrics` every 5 minutes
2. n8n checks `response.status != "ok"` or `response.alerts.length > 0`
3. If triggered, n8n POSTs to the Grafana alert webhook → Pushover notification

This is the same alert chain used by the greenhouse project (Grafana → n8n → Pushover). The `/metrics` endpoint replaces Grafana's native alerting queries for these pipeline-level checks because the queries involve multi-table aggregations that are awkward to express in Grafana's alert rule editor.

---

## Adding New Metrics

To add a metric to `/metrics`:

1. Write the SQL query as a coroutine
2. Add it to the `asyncio.gather()` call in the endpoint
3. Add the result to the response dict under the appropriate section (`data` or `models`)
4. Optionally add an alert threshold with a corresponding entry in `alerts[]`

Example: adding a 7-day rolling MAE drift check:

```python
drift_q = """
    SELECT
        AVG(ABS(p.p50 - m.import_kwh)) / 0.171 AS mae_ratio
    FROM predictions p
    JOIN meter_readings m
      ON m.household_id = p.household_id
     AND DATE(m.recorded_at AT TIME ZONE 'Europe/Dublin') = p.forecast_date
    WHERE p.issued_at >= NOW() - INTERVAL '7 days'
"""
# ... in gather():
mae_ratio = await conn.fetchval(drift_q)
if mae_ratio and mae_ratio > 1.5:
    alerts.append({"level": "warning", "field": "mae_drift",
                   "message": f"7d MAE {mae_ratio:.1f}× training MAE (threshold: 1.5×)"})
```

The training MAE of `0.171 kWh/hour` is from the Drammen/Home dataset H+1 LightGBM result. Once household-specific models are retrained monthly, this denominator should come from the model's stored training metadata rather than a hardcoded constant.

---

## The Observability Mental Model

Think of the Sparc pipeline as three layers, each with its own failure modes:

```
Layer 1: Data ingestion
    meter_readings (ESB upload) — can go stale
    myenergi_readings (nightly poller) — can miss nights
    weather_log (Open-Meteo) — can 429 or return stale forecast

Layer 2: Inference
    16:00 APScheduler job — can fail silently
    LightGBM model file — can be missing or corrupted
    Feature pipeline — can produce NaN (missing data gap)

Layer 3: Advisory delivery
    08:00 advisory job — can fail to find predictions
    Pushover API — can be rate-limited or misconfigured
```

`/metrics` monitors Layer 1 (staleness) and Layer 2 (predictions count, model mode).  
DAN-116 sanity checks monitor Layer 2 (NaN/range in predictions).  
`advisory_log` count monitors Layer 3.

No single endpoint monitors all three simultaneously — they're checked together in the `/metrics` response and compared against thresholds.

---

## Decision Log

| Decision | What we chose | Why | Alternatives rejected |
|----------|--------------|-----|----------------------|
| Warnings returned in response, not errors | `PredictionResponse.warnings: list[str]` | A partially-degraded prediction (e.g. 2 negative values out of 24) is more useful than a 500 error that leaves the morning advisory without a cost forecast. The warning is a signal to investigate, not a hard stop. | Raise 422/500 on any sanity failure — breaks the morning advisory chain for recoverable issues |
| 6-char UUID prefix in logs | `[predict|3f2a1c]` abbreviated prefix | Enough entropy to disambiguate concurrent requests in a single-household deployment. Full UUIDs in every log line make grepping harder without adding value at current scale. | Full UUID in logs — verbose; not needed until multi-tenant at high concurrency |
| `/metrics` independent of `/health` | Separate endpoints | `/health` is a liveness probe — it must respond in <50ms and never fail. `/metrics` may take 200ms+ with five DB queries. Mixing them would cause liveness probes to time out under DB load. | Single enriched `/health` — overloaded semantics, risks timing out infrastructure health checks |
| `asyncio.gather()` for five metrics queries | Parallel DB queries | Each query is independent. Running them sequentially would add 5× query latency. At the expected query speed (20–50ms each), parallel execution cuts total time from ~250ms to ~60ms. | Sequential queries — 5× slower; unacceptable for an endpoint that may be polled every 60s |
| Advisory count independent of prediction count | Separate `advisories_last_7d` metric | The two jobs can fail independently. If inference runs but the advisory fails (Pushover misconfigured, advisory job crashed), `predictions_last_7d > 0` but `advisories_last_7d = 0`. The independent metrics pinpoint which stage broke. | Single "pipeline ran" flag — can't distinguish where in the chain the failure occurred |
| 168-hour staleness threshold for ESB data | 7 days | ESB CSV is uploaded manually, currently monthly. A 7-day alert gives a warning if the user has missed a week, without false-alerting during a normal monthly cycle. | 24h threshold — false-alerts every day until SMDS automates the upload. 30d threshold — misses a missed upload for too long. |

## References

- `deployment/app.py` — `/metrics` endpoint, `_sanity_check_predictions()`, `request_id` injection
- `deployment/live_inference.py` — `inference_mode: str` field set on model load
- `docs/engineering/BEST_PRACTICES.md` — logging conventions and structured log format
- `docs/infra/services/` — APScheduler configuration and job schedule
- Linear: [DAN-115](https://linear.app/danbujoreanu/issue/DAN-115) · [DAN-116](https://linear.app/danbujoreanu/issue/DAN-116)
