"""Pydantic request/response schemas for the Energy Forecast API."""

from datetime import date

from pydantic import BaseModel, field_validator

# ── Path setup must happen in app.py before this is imported ──────────────────
# schemas.py relies on energy_forecast.api.schemas being importable.
from energy_forecast.api import schemas as _feature_schemas


_KNOWN_CITIES = {"drammen", "oslo", "dublin"}


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
    request_id: str
    building_id: str
    timestamp: str
    horizon: int
    predictions: list[float]
    inference_mode: str  # "real" or "mock"
    warnings: list[str] = []  # DAN-116: prediction sanity warnings (empty = OK)


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
    request_id: str
    building_id: str
    city: str
    forecast_origin: str
    decisions: list[HourDecision]
    morning_brief: str


class UploadResponse(BaseModel):
    household_id: str
    rows_inserted: int
    date_from: str | None
    date_to: str | None
    skipped: int


class ForecastEntry(BaseModel):
    forecast_date: str
    issued_at: str | None
    p10_kwh: list[float]
    p50_kwh: list[float]
    p90_kwh: list[float]


class ForecastResponse(BaseModel):
    household_id: str
    forecasts: list[ForecastEntry]


class ComparePlansRequest(BaseModel):
    household_id: str
    date_from: str | None = None   # ISO date string, e.g. "2024-03-15"
    date_to: str | None = None
    plan_keys: list[str] | None = None  # defaults to all plans


class SlotBreakdownResponse(BaseModel):
    day_kwh: float
    night_kwh: float
    peak_kwh: float
    free_kwh: float
    free_cap_exceeded_kwh: float
    free_cap_months_affected: int = 0   # DAN-157


class PlanResultResponse(BaseModel):
    plan_key: str
    plan_name: str
    supplier: str
    notes: str
    product_url: str = ""              # DAN-157
    last_verified: str | None = None   # DAN-157: ISO date string
    days_analysed: int
    total_import_kwh: float
    total_export_kwh: float
    import_cost_eur: float
    export_credit_eur: float
    standing_charge_eur: float
    net_cost_eur: float
    annualised_cost_eur: float
    cap_impact_note: str = ""          # DAN-157
    slots: SlotBreakdownResponse


class ComparePlansResponse(BaseModel):
    household_id: str
    date_from: str
    date_to: str
    days_analysed: int
    total_import_kwh: float
    total_export_kwh: float
    results: list[PlanResultResponse]   # sorted cheapest first
    cheapest_plan: str
    current_plan: str = "BGE_FTS_AFFINITY"
    savings_vs_current_eur: float       # annual savings if switching to cheapest
