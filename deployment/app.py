import json
import logging
import math
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb  # noqa: F401 — imported to verify lightweight dep
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

# ── Path setup (src/ package available inside the container) ──────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from energy_forecast.api import schemas as _feature_schemas
from energy_forecast.api.prediction_store import store_prediction
from energy_forecast.control.actions import EnvironmentState, ForecastBundle
from energy_forecast.control.controller import ControlEngine
from deployment.connectors import MockDeviceConnector, MockPriceConnector
from deployment.mock_data import MOCK_SOLAR_24H

logger = logging.getLogger(__name__)

# Global model cache — loaded once at startup, reused across requests
models: dict[str, Any] = {}

# Shared ControlEngine instance (stateless — safe to share)
_control_engine = ControlEngine()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class PredictionRequest(BaseModel):
    building_id: str
    timestamp: str
    features: dict[str, float]
    """35 pre-engineered features (see temporal.py).

    When a real LightGBM model is loaded, the exact key set is validated
    against ``model.feature_name_`` at request time — wrong or missing feature
    names return a 422 with the full expected list.

    In mock / no-model mode, any non-empty dict is accepted.
    """

    @field_validator("features")
    @classmethod
    def features_must_be_valid(cls, v: dict[str, float]) -> dict[str, float]:
        if not v:
            raise ValueError("features dict cannot be empty")
        if len(v) > 500:
            raise ValueError(f"features dict too large ({len(v)} keys); expected ~35")
        # E-19: strict model-derived validation (no-op when running in mock mode)
        return _feature_schemas.validate_features(v)


class PredictionResponse(BaseModel):
    building_id: str
    timestamp: str
    horizon: int
    predictions: list[float]
    inference_mode: str  # "real" or "mock"


_KNOWN_CITIES = {"drammen", "oslo", "dublin"}


class ControlRequest(BaseModel):
    building_id: str
    city: str = "drammen"
    target_hours: list[int] = list(range(6, 23))
    """Hours of the day (0–23) to produce control decisions for (default: 6–22)."""
    dry_run: bool = True
    """When True, use mock solar/price data. Set to False once live connectors are active."""

    @field_validator("city")
    @classmethod
    def city_must_be_known(cls, v: str) -> str:
        if v not in _KNOWN_CITIES:
            raise ValueError(f"city must be one of {sorted(_KNOWN_CITIES)}, got '{v}'")
        return v


class HourDecision(BaseModel):
    hour: int
    action: str
    confidence: float
    reasoning: str
    p50_kwh: float
    solar_wh_m2: float
    price_eur_kwh: float


class ControlResponse(BaseModel):
    building_id: str
    city: str
    forecast_origin: str
    decisions: list[HourDecision]
    morning_brief: str


# ---------------------------------------------------------------------------
# Lifespan — load models on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading Machine Learning models into memory...")
    try:
        models_dir = _REPO_ROOT / "outputs" / "models"

        lgbm_path = next(models_dir.glob("*_LightGBM_*.joblib"), None)
        stacking_path = next(models_dir.glob("*_Stacking_Ensemble_*.joblib"), None)

        if lgbm_path and lgbm_path.exists():
            models["LightGBM"] = joblib.load(lgbm_path)
            logger.info("Loaded LightGBM from %s", lgbm_path)
            # E-19: register feature names for /predict validation.
            # Uses register_model_features() which detects generic Column_N names
            # (models trained on numpy arrays) and keeps validation lenient until
            # the model is retrained via scripts/run_pipeline.py.
            feature_names = getattr(models["LightGBM"], "feature_name_", None)
            if feature_names is not None:
                _feature_schemas.register_model_features(feature_names)
        else:
            logger.warning("LightGBM model not found in outputs/models/. Inference will be mocked.")
            models["LightGBM"] = "MOCK_LGBM"

        if stacking_path and stacking_path.exists():
            models["Stacking_Ensemble"] = joblib.load(stacking_path)
            logger.info("Loaded Stacking Ensemble from %s", stacking_path)
        else:
            logger.warning("Stacking Ensemble not found. Inference will be mocked.")
            models["Stacking_Ensemble"] = "MOCK_STACKING"

    except Exception as exc:
        logger.error("Failed to load models during startup: %s", exc)

    yield

    logger.info("Shutting down model inference service...")
    models.clear()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Building Energy Load Forecast API",
    description=(
        "Day-ahead electricity load forecasting and demand-response control "
        "for Norwegian public buildings. H+24 horizon, LightGBM + Stacking Ensemble."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ── Intel module routes (/intel/query, /intel/status, /intel/tiers) ──────────
try:
    from intel.routes import router as _intel_router  # noqa: E402
    app.include_router(_intel_router)
    logger.info("Intel routes registered at /intel/*")
except ImportError as _intel_err:
    logger.warning("Intel module not available — /intel/* routes disabled: %s", _intel_err)


# ---------------------------------------------------------------------------
# Drift report helper
# ---------------------------------------------------------------------------

def _load_latest_drift_report(city: str) -> dict:
    """Load the most recent drift report JSON for a city.

    Looks for files matching ``outputs/results/drift_reports/drift_{city}_*.json``
    and returns the last one in sorted filename order (most recent by filename).

    Returns a minimal dict with the fields relevant to the health endpoint.
    Falls back to a safe default dict on any error so the /health endpoint
    never fails because of drift reporting.

    Args:
        city: City identifier, e.g. "drammen".

    Returns:
        Dict with keys: severity, recommended_action, checked_at, rolling_mae_triggered.
    """
    try:
        drift_dir = _REPO_ROOT / "outputs" / "results" / "drift_reports"
        candidates = sorted(drift_dir.glob(f"drift_{city}_*.json"))
        if not candidates:
            return {
                "severity": "unknown",
                "recommended_action": "run scripts/run_drift_check.py",
                "checked_at": None,
                "rolling_mae_triggered": None,
            }
        latest = candidates[-1]
        with open(latest, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        rolling = data.get("rolling_mae_result") or {}
        return {
            "severity": data.get("overall_severity", "unknown"),
            "recommended_action": data.get("recommended_action", "unknown"),
            "checked_at": data.get("checked_at"),
            "rolling_mae_triggered": rolling.get("is_triggered"),
        }
    except Exception as exc:
        logger.debug("Could not load drift report for city='%s': %s", city, exc)
        return {
            "severity": "unknown",
            "recommended_action": "run scripts/run_drift_check.py",
            "checked_at": None,
            "rolling_mae_triggered": None,
        }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """Liveness check — returns model status (real or mock) for each loaded model."""
    model_status = {
        name: ("mock" if isinstance(obj, str) and obj.startswith("MOCK") else "real")
        for name, obj in models.items()
    }
    # Read latest drift report if available (failure-safe — health endpoint must not fail)
    drift_status = _load_latest_drift_report(city="drammen")
    return {
        "status": "healthy",
        "models": model_status,
        "inference_ready": any(v == "real" for v in model_status.values()),
        "drift": drift_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest, model_name: str = "LightGBM"):
    """Run H+24 inference from a pre-engineered 35-feature vector.

    The caller is responsible for computing the 35 features using the
    same pipeline as training (see ``src/energy_forecast/features/temporal.py``).
    For end-to-end inference from raw data, use the ``/control`` endpoint instead.
    """
    if model_name not in models:
        raise HTTPException(status_code=400, detail=f"Model '{model_name}' not loaded.")

    model = models[model_name]

    try:
        df_features = pd.DataFrame([request.features])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid feature format: {exc}")

    is_mock = isinstance(model, str) and model.startswith("MOCK")
    try:
        if is_mock:
            logger.info("Using mocked inference for %s", model_name)
            preds = [150.0 + i for i in range(24)]
        else:
            raw = model.predict(df_features)
            preds = raw[0].tolist() if hasattr(raw[0], "__len__") else [float(raw[0])] * 24

    except Exception as exc:
        logger.error("Inference failed: %s", exc)
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
                f"got {len(request.features)}. "
            )
            if has_generic:
                detail += (
                    "This model was trained without named features (Column_0..N). "
                    "Re-run scripts/run_pipeline.py to retrain with semantic names, "
                    "then send features like {'lag_24h': ..., 'hour_of_day': ...}."
                )
            raise HTTPException(status_code=422, detail=detail)
        raise HTTPException(status_code=500, detail=f"Model inference failed: {exc_str}")

    # E-27: persist prediction to history store (JSONL + optional PostgreSQL)
    store_prediction(
        building_id=request.building_id,
        issued_at=datetime.now(timezone.utc),
        p10=[v * 0.85 for v in preds],
        p50=preds,
        p90=[v * 1.15 for v in preds],
        model_version=model_name,
    )

    return PredictionResponse(
        building_id=request.building_id,
        timestamp=request.timestamp,
        horizon=len(preds),
        predictions=preds,
        inference_mode="mock" if is_mock else "real",
    )


@app.post("/control", response_model=ControlResponse)
def control(request: ControlRequest):
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
        #   history = CSVConnector().fetch_last_n_hours(request.building_id, 72, request.city)
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
    if request.dry_run:
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
        building_id=request.building_id,
    )

    # ── Step 3: Control decisions ──────────────────────────────────────────
    target_hours = [h for h in request.target_hours if 0 <= h < 24]
    if not target_hours:
        raise HTTPException(
            status_code=400,
            detail="target_hours must contain at least one value in [0, 23].",
        )
    actions = _control_engine.decide(forecast, env, target_hours=target_hours)

    # ── Step 4: Send to mock device ────────────────────────────────────────
    device = MockDeviceConnector()
    for a in actions:
        if a.action.value in {"DEFER_HEATING", "ALERT_HIGH_DEMAND"}:
            device.send_command(a.action.value, building_id=request.building_id)

    return ControlResponse(
        building_id=request.building_id,
        city=request.city,
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
        morning_brief=_control_engine.explain(actions),
    )
