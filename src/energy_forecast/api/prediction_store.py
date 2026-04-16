"""
energy_forecast.api.prediction_store
=====================================
Persist H+24 forecast output after every ``/predict`` or ``/control`` call.

Two-tier storage (Phase 1 → Phase 2):

  Tier 1 — JSONL fallback (always available):
    Appends one line per prediction to ``outputs/logs/prediction_history.jsonl``.
    Same append-only, never-fail pattern as the ControlEngine audit log.

  Tier 2 — PostgreSQL (when DATABASE_URL + psycopg2-binary are available):
    Upserts into the ``predictions`` TimescaleDB hypertable defined in
    ``infra/db/init.sql``.  Household rows are auto-created in the ``households``
    table on first write (minimal onboarding record), so the API can store
    predictions before full user registration is implemented (Phase 2).

In both cases, write failures are non-fatal — they are logged but the
calling endpoint continues normally.

Usage::

    from energy_forecast.api.prediction_store import store_prediction

    store_prediction(
        building_id="building_42",
        issued_at=datetime.now(timezone.utc),
        p10=[...],
        p50=[...],
        p90=[...],
        model_version="LightGBM-drammen-20260416",
    )
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
_JSONL_PATH = Path(__file__).resolve().parents[4] / "outputs" / "logs" / "prediction_history.jsonl"
_DB_URL = os.environ.get("DATABASE_URL", "")

# Lazy-import psycopg2 so the module loads cleanly when the driver is absent
try:
    import psycopg2
    import psycopg2.extras  # for execute_values
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False


# ── Public API ─────────────────────────────────────────────────────────────────

def store_prediction(
    building_id: str,
    issued_at: datetime,
    p10: list[float],
    p50: list[float],
    p90: list[float],
    model_version: str | None = None,
) -> None:
    """Persist one H+24 prediction.  Non-blocking — all failures are logged only.

    Args:
        building_id: Unique identifier for the building / household.
        issued_at:   UTC datetime when the model ran.
        p10:         24-element P10 forecast (kWh).
        p50:         24-element P50 forecast (kWh).
        p90:         24-element P90 forecast (kWh).
        model_version: ModelRegistry version string, e.g. "LightGBM-drammen-20260416".
    """
    forecast_date = issued_at.date().isoformat()
    record = {
        "building_id": building_id,
        "issued_at": issued_at.isoformat(),
        "forecast_date": forecast_date,
        "p10_kwh": p10,
        "p50_kwh": p50,
        "p90_kwh": p90,
        "model_version": model_version or "unknown",
    }

    # Tier 1: JSONL (always)
    _append_jsonl(record)

    # Tier 2: PostgreSQL (optional — only when DATABASE_URL + psycopg2 available)
    if _DB_URL and _PSYCOPG2_AVAILABLE:
        _upsert_postgres(record)


# ── Tier 1: JSONL ──────────────────────────────────────────────────────────────

def _append_jsonl(record: dict) -> None:
    """Append one JSON line to prediction_history.jsonl.  Flock-safe for concurrency."""
    try:
        _JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_JSONL_PATH, "a", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                fh.write(json.dumps(record, default=str) + "\n")
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
    except Exception as exc:
        logger.warning("[prediction_store] JSONL write failed: %s", exc)


# ── Tier 2: PostgreSQL ─────────────────────────────────────────────────────────

_UPSERT_SQL = """
INSERT INTO predictions
    (household_id, issued_at, forecast_date, p10_kwh, p50_kwh, p90_kwh, model_version)
VALUES
    (%(household_id)s, %(issued_at)s, %(forecast_date)s,
     %(p10_kwh)s, %(p50_kwh)s, %(p90_kwh)s, %(model_version)s)
ON CONFLICT (household_id, forecast_date)
DO UPDATE SET
    issued_at     = EXCLUDED.issued_at,
    p10_kwh       = EXCLUDED.p10_kwh,
    p50_kwh       = EXCLUDED.p50_kwh,
    p90_kwh       = EXCLUDED.p90_kwh,
    model_version = EXCLUDED.model_version;
"""

_ENSURE_HOUSEHOLD_SQL = """
INSERT INTO households (id, user_id, city)
VALUES (%(id)s, %(user_id)s, %(city)s)
ON CONFLICT (id) DO NOTHING;
"""


def _building_id_to_uuid(building_id: str) -> str:
    """Derive a deterministic UUID-v5 from building_id for households.id.

    Uses uuid5(DNS namespace, building_id) so the same building always maps to
    the same UUID without storing a lookup table.
    """
    import uuid
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, building_id))


def _upsert_postgres(record: dict) -> None:
    """Write prediction to PostgreSQL.  Auto-creates household row on first write."""
    try:
        conn = psycopg2.connect(_DB_URL)
        conn.autocommit = False
        with conn, conn.cursor() as cur:
            household_uuid = _building_id_to_uuid(record["building_id"])

            # Ensure household row exists (idempotent — ON CONFLICT DO NOTHING)
            cur.execute(_ENSURE_HOUSEHOLD_SQL, {
                "id": household_uuid,
                "user_id": household_uuid,   # Phase 1: user_id = household_id
                "city": "ireland",
            })

            # Cast Python lists → PostgreSQL ARRAY via psycopg2 adaptation
            p10_arr = record["p10_kwh"]
            p50_arr = record["p50_kwh"]
            p90_arr = record["p90_kwh"]

            cur.execute(_UPSERT_SQL, {
                "household_id": household_uuid,
                "issued_at": record["issued_at"],
                "forecast_date": record["forecast_date"],
                "p10_kwh": p10_arr,
                "p50_kwh": p50_arr,
                "p90_kwh": p90_arr,
                "model_version": record["model_version"],
            })
        logger.debug(
            "[prediction_store] Upserted prediction for %s on %s.",
            record["building_id"], record["forecast_date"],
        )
    except Exception as exc:
        logger.warning("[prediction_store] PostgreSQL write failed: %s", exc)
    finally:
        try:
            conn.close()
        except Exception:
            pass
