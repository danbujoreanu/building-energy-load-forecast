"""Prediction, control, and plan comparison endpoints."""

import logging
import math
from datetime import date, datetime, timezone
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, HTTPException, Request

from deployment.connectors import MockDeviceConnector, MockPriceConnector
from deployment.mock_data import MOCK_SOLAR_24H
from deployment.schemas import (
    ComparePlansRequest,
    ComparePlansResponse,
    ControlRequest,
    ControlResponse,
    HourDecision,
    PlanResultResponse,
    PredictionRequest,
    PredictionResponse,
    SlotBreakdownResponse,
)
from energy_forecast.api.plan_comparison import PLANS, compare_plans
from energy_forecast.api.prediction_store import store_prediction
from energy_forecast.control.actions import EnvironmentState, ForecastBundle

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# DAN-116: Prediction sanity checks
# ---------------------------------------------------------------------------

def _sanity_check_predictions(request_id: str, preds: list[float]) -> list[str]:
    """Return list of warning strings. Empty list means predictions look sane."""
    warnings: list[str] = []
    if any(math.isnan(v) or math.isinf(v) for v in preds):
        warnings.append("NaN or Inf values detected in predictions")
    if any(v < 0 for v in preds):
        warnings.append(f"Negative predictions detected: min={min(preds):.3f}")
    if any(v > 500 for v in preds):
        warnings.append(f"Implausibly large predictions: max={max(preds):.1f} kWh/h")
    if len(preds) > 1 and len(set(round(v, 3) for v in preds)) == 1:
        warnings.append(f"All predictions identical ({preds[0]:.3f}) — possible stuck model")
    for w in warnings:
        logger.warning("[sanity|%s] %s", request_id, w)
    return warnings


# ---------------------------------------------------------------------------
# DAN-143: Compute tomorrow's predicted cost from stored forecast
# ---------------------------------------------------------------------------

async def _compute_tomorrow_cost(pool, household_id: str, target_date: date) -> float | None:
    """Fetch the latest H+24 P50 forecast for target_date and apply BGE tariff rates."""
    try:
        from energy_forecast.tariff import rate_for_slot
        import pytz
        dublin = pytz.timezone("Europe/Dublin")

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT p50_kwh, issued_at FROM predictions
                WHERE household_id = $1
                  AND forecast_date = $2
                ORDER BY issued_at DESC LIMIT 1
                """,
                household_id,
                target_date,
            )
        if not row or not row["p50_kwh"]:
            return None

        p50: list[float] = list(row["p50_kwh"])
        cost = 0.0
        for hour_idx, kwh in enumerate(p50[:24]):
            ts = pd.Timestamp(
                dublin.localize(
                    datetime(target_date.year, target_date.month, target_date.day, hour_idx)
                )
            )
            _, rate = rate_for_slot(ts)
            cost += kwh * rate

        from energy_forecast.tariff import BGE
        cost += BGE["standing_daily"]
        return round(cost, 2)
    except Exception as exc:
        logger.debug("Could not compute tomorrow cost: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/predict", response_model=PredictionResponse)
def predict(request: Request, body: PredictionRequest, model_name: str = "LightGBM"):
    """Run H+24 inference from a pre-engineered 35-feature vector.

    The caller is responsible for computing the 35 features using the
    same pipeline as training (see ``src/energy_forecast/features/temporal.py``).
    For end-to-end inference from raw data, use the ``/control`` endpoint instead.
    """
    models = getattr(request.app.state, "models", {})
    if model_name not in models:
        raise HTTPException(status_code=400, detail=f"Model '{model_name}' not loaded.")

    model = models[model_name]

    try:
        df_features = pd.DataFrame([body.features])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid feature format: {exc}")

    request_id = str(uuid4())
    logger.info("[predict|%s] building_id=%s model=%s", request_id, body.building_id, model_name)

    is_mock = isinstance(model, str) and model.startswith("MOCK")
    try:
        if is_mock:
            logger.info("[predict|%s] Using mocked inference", request_id)
            preds = [150.0 + i for i in range(24)]
        else:
            raw = model.predict(df_features)
            preds = raw[0].tolist() if hasattr(raw[0], "__len__") else [float(raw[0])] * 24

    except Exception as exc:
        logger.error("[predict|%s] Inference failed: %s", request_id, exc)
        exc_str = str(exc)
        # Detect feature-count / feature-name mismatch — give a helpful 422 rather than 500
        if "number of features" in exc_str or "feature names" in exc_str.lower():
            expected_n = len(getattr(model, "feature_name_", []))
            model_names = getattr(model, "feature_name_", [])
            has_generic = expected_n > 0 and all(
                n.startswith("Column_") for n in model_names
            )
            detail = (
                f"Feature mismatch: model expects {expected_n} features, "
                f"got {len(body.features)}. "
            )
            if has_generic:
                detail += (
                    "This model was trained without named features (Column_0..N). "
                    "Re-run scripts/run_pipeline.py to retrain with semantic names, "
                    "then send features like {'lag_24h': ..., 'hour_of_day': ...}."
                )
            raise HTTPException(status_code=422, detail=detail)
        raise HTTPException(status_code=500, detail=f"Model inference failed: {exc_str}")

    # DAN-116: sanity check before persisting
    warnings = _sanity_check_predictions(request_id, preds)

    # E-27: persist prediction to history store (JSONL + optional PostgreSQL)
    store_prediction(
        building_id=body.building_id,
        issued_at=datetime.now(timezone.utc),
        p10=[v * 0.85 for v in preds],
        p50=preds,
        p90=[v * 1.15 for v in preds],
        model_version=model_name,
    )

    return PredictionResponse(
        request_id=request_id,
        building_id=body.building_id,
        timestamp=body.timestamp,
        horizon=len(preds),
        predictions=preds,
        inference_mode="mock" if is_mock else "real",
        warnings=warnings,
    )


@router.post("/control", response_model=ControlResponse)
def control(request: Request, body: ControlRequest):
    """Run H+24 forecast and return per-hour demand-response decisions.

    This endpoint chains:
      1. Load forecast (LightGBM or mock)
      2. Solar irradiance + price signals (mock or live connectors)
      3. ControlEngine decision per requested hour

    Returns a ``ControlResponse`` with per-hour actions and a human-readable
    morning brief suitable for display or logging.

    Live connectors (OpenMeteoConnector, SEMOConnector) are activated by
    setting ``dry_run: false`` once the API keys are configured.
    """
    models = getattr(request.app.state, "models", {})
    control_engine = request.app.state.control_engine

    # ── Step 1: P10/P50/P90 forecast ──────────────────────────────────────
    model = models.get("LightGBM")
    if model is None:
        raise HTTPException(status_code=503, detail="LightGBM model not loaded.")

    if isinstance(model, str) and model.startswith("MOCK"):
        # Mock 24h load profile
        p50 = [20.0 + 15 * math.sin(math.pi * h / 12) for h in range(24)]
    else:
        # No live historical data in this path — use recent model output
        # For a production endpoint backed by a DataConnector, replace with:
        #   history = CSVConnector().fetch_last_n_hours(body.building_id, 72, body.city)
        #   X_scaled, _ = _build_inference_features(history, cfg, scaler_path)
        #   raw = model.predict(X_scaled.iloc[[-1]])
        p50 = [20.0 + 15 * math.sin(math.pi * h / 12) for h in range(24)]
        logger.info(
            "Model loaded but live DataConnector not configured — using P50 heuristic. "
            "Set up CSVConnector or OpenMeteoConnector in deployment/connectors.py."
        )

    p50 = [max(0.0, v) for v in p50]  # load is non-negative; clamp before PI scaling
    p10 = [v * 0.85 for v in p50]
    p90 = [v * 1.15 for v in p50]
    forecast = ForecastBundle(p10=p10, p50=p50, p90=p90)

    # ── Step 2: Environmental signals ─────────────────────────────────────
    if body.dry_run:
        solar_24h = MOCK_SOLAR_24H
        prices_24h = MockPriceConnector().get_day_ahead_prices()
    else:
        # Live connectors — add OpenMeteoConnector + SEMOConnector here
        # when API tokens are available (see deployment/connectors.py)
        raise HTTPException(
            status_code=501,
            detail=(
                "Live mode not yet enabled. "
                "Configure OpenMeteoConnector and SEMOConnector in connectors.py, "
                "then remove this guard. Use dry_run=true for demo mode."
            ),
        )

    env = EnvironmentState(
        solar_forecast_wh_m2=solar_24h,
        grid_price_eur_kwh=prices_24h,
        timestamp=datetime.now(timezone.utc),
        building_id=body.building_id,
    )

    # ── Step 3: Control decisions ──────────────────────────────────────────
    target_hours = [h for h in body.target_hours if 0 <= h < 24]
    if not target_hours:
        raise HTTPException(
            status_code=400,
            detail="target_hours must contain at least one value in [0, 23].",
        )
    actions = control_engine.decide(forecast, env, target_hours=target_hours)

    # ── Step 4: Send to mock device ────────────────────────────────────────
    device = MockDeviceConnector()
    for a in actions:
        if a.action.value in {"DEFER_HEATING", "ALERT_HIGH_DEMAND"}:
            device.send_command(a.action.value, building_id=body.building_id)

    ctrl_request_id = str(uuid4())
    logger.info("[control|%s] building_id=%s city=%s", ctrl_request_id, body.building_id, body.city)

    return ControlResponse(
        request_id=ctrl_request_id,
        building_id=body.building_id,
        city=body.city,
        forecast_origin=datetime.now(timezone.utc).isoformat(),
        decisions=[
            HourDecision(
                hour=a.target_hour,
                action=a.action.value,
                confidence=a.confidence,
                reasoning=a.reasoning,
                p50_kwh=a.p50_kwh,
                solar_wh_m2=a.solar_wh_m2,
                price_eur_kwh=a.price_eur_kwh,
            )
            for a in actions
        ],
        morning_brief=control_engine.explain(actions),
    )


@router.post("/compare-plans", response_model=ComparePlansResponse)
async def compare_tariff_plans(request: Request, body: ComparePlansRequest):
    """DAN-131: Replay meter_readings history against multiple tariff plans.

    Answers: "Which plan would have been cheapest given my actual consumption?"
    Results are sorted by annualised net cost (cheapest first).

    Available plan keys:
      BGE_FTS_AFFINITY    — current BGE Free Time Saturday with 20% Affinity discount
      BGE_FTS_STANDARD    — BGE FTS without discount (post-June-15 scenario)
      BGE_STANDARD_NOSAT  — BGE with discount but no free Saturday (shows Saturday value)
      ENERGIA_NIGHT_BOOST — Energia Night Boost (approx Q1 2026 rates)
      SSE_ONE_RATE        — SSE Airtricity flat single rate
      ELECTRIC_IRELAND_SMART — Electric Ireland Smart TOU (approx)

    Note: Non-BGE rates are approximate. Verify at supplier websites before contract decisions.
    """
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    date_from = None
    date_to = None
    try:
        if body.date_from:
            date_from = date.fromisoformat(body.date_from)
        if body.date_to:
            date_to = date.fromisoformat(body.date_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid date format: {exc}")

    plan_keys = body.plan_keys or list(PLANS.keys())
    unknown = [k for k in plan_keys if k not in PLANS]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown plan keys: {unknown}. Valid: {list(PLANS.keys())}",
        )

    try:
        results, meta = await compare_plans(pool, body.household_id, date_from, date_to, plan_keys)
    except Exception as exc:
        logger.error("Plan comparison failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Comparison failed: {exc}")

    if not results:
        raise HTTPException(status_code=404, detail="No meter readings found for this household and date range.")

    cheapest = results[0].plan_key
    current_result = next((r for r in results if r.plan_key == "BGE_FTS_AFFINITY"), results[-1])
    cheapest_result = results[0]
    savings = round(current_result.annualised_cost_eur - cheapest_result.annualised_cost_eur, 2)

    return ComparePlansResponse(
        household_id=body.household_id,
        date_from=meta.get("date_from", ""),
        date_to=meta.get("date_to", ""),
        days_analysed=meta.get("days_analysed", 0),
        total_import_kwh=meta.get("total_import_kwh", 0.0),
        total_export_kwh=meta.get("total_export_kwh", 0.0),
        cheapest_plan=cheapest,
        savings_vs_current_eur=savings,
        results=[
            PlanResultResponse(
                plan_key=r.plan_key,
                plan_name=r.plan_name,
                supplier=r.supplier,
                notes=r.notes,
                product_url=r.product_url,
                last_verified=str(r.last_verified) if r.last_verified else None,
                days_analysed=r.days_analysed,
                total_import_kwh=r.total_import_kwh,
                total_export_kwh=r.total_export_kwh,
                import_cost_eur=r.import_cost_eur,
                export_credit_eur=r.export_credit_eur,
                standing_charge_eur=r.standing_charge_eur,
                net_cost_eur=r.net_cost_eur,
                annualised_cost_eur=r.annualised_cost_eur,
                cap_impact_note=r.cap_impact_note,
                slots=SlotBreakdownResponse(
                    day_kwh=r.slots.day_kwh,
                    night_kwh=r.slots.night_kwh,
                    peak_kwh=r.slots.peak_kwh,
                    free_kwh=r.slots.free_kwh,
                    free_cap_exceeded_kwh=r.slots.free_cap_exceeded_kwh,
                    free_cap_months_affected=r.slots.free_cap_months_affected,
                ),
            )
            for r in results
        ],
    )
