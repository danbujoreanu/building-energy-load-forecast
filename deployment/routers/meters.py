"""Meter data upload, forecast retrieval, and advisory outcome endpoints."""

import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel

from deployment.schemas import ForecastEntry, ForecastResponse, UploadResponse
from energy_forecast.api.esb_parser import ESBParseError, parse_esb_csv
from deployment import db_repository as db
from energy_forecast.api.meter_store import (
    fetch_forecasts,
    household_exists,
    resolve_or_create_household,
    upsert_meter_readings,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_meter_data(
    request: Request,
    file: UploadFile = File(...),
    household_id: str | None = Form(None),
):
    """Ingest an ESB Networks HDF CSV file into the meter_readings hypertable.

    Accepts both kW and kWh ESB export formats (auto-detected).  Re-uploads are
    idempotent — duplicate timestamps are silently skipped.

    If household_id is not provided, the MPRN in the file is used to look up or
    create the household automatically.
    """
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        mprn, rows = parse_esb_csv(contents)
    except ESBParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if household_id is None:
        try:
            household_id = await resolve_or_create_household(pool, mprn)
        except Exception as exc:
            logger.error("Household resolution failed: %s", exc)
            raise HTTPException(status_code=500, detail="Could not resolve household.")

    total = len(rows)
    try:
        inserted = await upsert_meter_readings(pool, household_id, rows)
    except Exception as exc:
        logger.error("Meter reading upsert failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"DB write failed: {exc}")

    skipped = total - inserted
    timestamps = [r["recorded_at"] for r in rows if r.get("recorded_at")]
    date_from = str(min(timestamps)) if timestamps else None
    date_to = str(max(timestamps)) if timestamps else None

    return UploadResponse(
        household_id=household_id,
        rows_inserted=inserted,
        date_from=date_from,
        date_to=date_to,
        skipped=skipped,
    )


@router.get("/forecast/{household_id}", response_model=ForecastResponse)
async def get_forecast(
    household_id: str,
    request: Request,
    days: int = Query(default=7, ge=1, le=30),
):
    """Return the most recent stored H+24 forecasts for a household.

    Query parameter ``days`` controls how many forecast records to return
    (default 7, max 30).  Returns 404 if the household_id is not registered.
    """
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    try:
        exists = await household_exists(pool, household_id)
    except Exception as exc:
        logger.error("Household lookup failed: %s", exc)
        raise HTTPException(status_code=500, detail="DB error.")

    if not exists:
        raise HTTPException(
            status_code=404,
            detail=f"Household '{household_id}' not found. Upload meter data first.",
        )

    try:
        forecasts = await fetch_forecasts(pool, household_id, days)
    except Exception as exc:
        logger.error("Forecast fetch failed: %s", exc)
        raise HTTPException(status_code=500, detail="DB error.")

    return ForecastResponse(
        household_id=household_id,
        forecasts=[ForecastEntry(**f) for f in forecasts],
    )


# ---------------------------------------------------------------------------
# DAN-P1: Advisory outcome feedback (behaviour change evidence)
# ---------------------------------------------------------------------------

class AdvisoryOutcomeResponse(BaseModel):
    advisory_date: str
    acted_on: bool
    recorded_at: str


@router.post("/advisory/{advisory_date}/outcome", response_model=AdvisoryOutcomeResponse)
async def record_advisory_outcome(
    advisory_date: date,
    request: Request,
    acted: bool = Query(default=True, description="True = user acted on the advisory (e.g. skipped boost)"),
):
    """Record whether the user acted on the advisory for a given date.

    Called via the Pushover deep-link: tap '✅ I skipped the boost' to record acted=True.
    Single-household MVP — unauthenticated. Add auth before multi-household rollout (ADR note).

    To verify:
        curl -X POST "http://192.168.68.119:8000/advisory/2026-05-08/outcome?acted=true"
    """
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    now = datetime.now(timezone.utc)

    # Resolve first household (single-household MVP)
    try:
        households = await db.fetch_household_ids(pool)
        if not households:
            raise HTTPException(status_code=404, detail="No households registered.")
        hid = str(households[0]["id"])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Household lookup failed: %s", exc)
        raise HTTPException(status_code=500, detail="DB error.")

    try:
        await pool.execute(
            """
            UPDATE advisory_log
               SET acted_on = $1, outcome_recorded_at = $2
             WHERE household_id = $3::uuid AND advisory_date = $4
            """,
            acted, now, hid, advisory_date,
        )
    except Exception as exc:
        logger.error("Outcome update failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"DB write failed: {exc}")

    logger.info("[advisory] Outcome recorded: date=%s acted=%s hid=%s", advisory_date, acted, hid)
    return AdvisoryOutcomeResponse(
        advisory_date=str(advisory_date),
        acted_on=acted,
        recorded_at=now.isoformat(),
    )
