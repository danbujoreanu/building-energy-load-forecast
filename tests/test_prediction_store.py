"""
tests.test_prediction_store
============================
Tests for ``src/energy_forecast/api/prediction_store.py`` — E-27.

Coverage:
  - JSONL fallback always writes regardless of DB configuration
  - Record contains expected keys and correct data types
  - Multiple writes produce multiple JSONL lines (append, not overwrite)
  - Building ID → UUID mapping is deterministic
  - Module imports cleanly without psycopg2
"""

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from energy_forecast.api import prediction_store as ps

# ─── Fixtures ────────────────────────────────────────────────────────────────

ISSUED_AT = datetime(2026, 4, 16, 16, 0, 0, tzinfo=timezone.utc)
P10 = [v * 0.85 for v in range(24)]
P50 = [float(v) for v in range(24)]
P90 = [v * 1.15 for v in range(24)]


@pytest.fixture()
def tmp_jsonl(tmp_path):
    """Redirect JSONL writes to a temp file."""
    target = tmp_path / "prediction_history.jsonl"
    with patch.object(ps, "_JSONL_PATH", target):
        yield target


# ─── JSONL fallback ───────────────────────────────────────────────────────────


def test_jsonl_write_creates_file(tmp_jsonl):
    ps.store_prediction("building_1", ISSUED_AT, P10, P50, P90, "LightGBM-test")
    assert tmp_jsonl.exists()


def test_jsonl_record_has_expected_keys(tmp_jsonl):
    ps.store_prediction("building_1", ISSUED_AT, P10, P50, P90, "LightGBM-test")
    line = tmp_jsonl.read_text().strip()
    record = json.loads(line)
    assert set(record) == {
        "building_id",
        "issued_at",
        "forecast_date",
        "p10_kwh",
        "p50_kwh",
        "p90_kwh",
        "model_version",
    }


def test_jsonl_record_values(tmp_jsonl):
    ps.store_prediction("building_42", ISSUED_AT, P10, P50, P90, "v1.2.3")
    record = json.loads(tmp_jsonl.read_text().strip())
    assert record["building_id"] == "building_42"
    assert record["forecast_date"] == "2026-04-16"
    assert record["model_version"] == "v1.2.3"
    assert len(record["p50_kwh"]) == 24


def test_jsonl_appends_multiple_records(tmp_jsonl):
    ps.store_prediction("b1", ISSUED_AT, P10, P50, P90)
    ps.store_prediction("b2", ISSUED_AT, P10, P50, P90)
    lines = tmp_jsonl.read_text().strip().split("\n")
    assert len(lines) == 2
    records = [json.loads(line) for line in lines]
    assert records[0]["building_id"] == "b1"
    assert records[1]["building_id"] == "b2"


def test_jsonl_model_version_defaults_to_unknown(tmp_jsonl):
    ps.store_prediction("building_1", ISSUED_AT, P10, P50, P90)
    record = json.loads(tmp_jsonl.read_text().strip())
    assert record["model_version"] == "unknown"


# ─── UUID mapping ─────────────────────────────────────────────────────────────


def test_building_id_to_uuid_is_deterministic():
    uuid1 = ps._building_id_to_uuid("building_42")
    uuid2 = ps._building_id_to_uuid("building_42")
    assert uuid1 == uuid2


def test_different_building_ids_produce_different_uuids():
    u1 = ps._building_id_to_uuid("building_1")
    u2 = ps._building_id_to_uuid("building_2")
    assert u1 != u2


def test_uuid_is_valid_format():
    import uuid

    raw = ps._building_id_to_uuid("any_building")
    # Should not raise
    parsed = uuid.UUID(raw)
    assert parsed.version == 5


# ─── No DB scenario ───────────────────────────────────────────────────────────


def test_store_does_not_crash_without_db(tmp_jsonl):
    """store_prediction never raises regardless of DB config."""
    with patch.object(ps, "_DB_URL", ""):
        ps.store_prediction("b1", ISSUED_AT, P10, P50, P90)
    assert tmp_jsonl.exists()


def test_postgres_write_skipped_when_no_db_url(tmp_jsonl):
    """PostgreSQL path is skipped when DATABASE_URL is not set."""
    with patch.object(ps, "_DB_URL", ""), patch.object(ps, "_PSYCOPG2_AVAILABLE", True):
        ps.store_prediction("b1", ISSUED_AT, P10, P50, P90)
    # JSONL still written
    assert tmp_jsonl.exists()


def test_postgres_write_skipped_when_no_psycopg2(tmp_jsonl):
    """PostgreSQL path is skipped when psycopg2 is not installed."""
    with (
        patch.object(ps, "_DB_URL", "postgresql://fake/db"),
        patch.object(ps, "_PSYCOPG2_AVAILABLE", False),
    ):
        ps.store_prediction("b1", ISSUED_AT, P10, P50, P90)
    # JSONL still written, no exception raised
    assert tmp_jsonl.exists()
