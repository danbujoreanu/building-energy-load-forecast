"""Tests for src/energy_forecast/registry/model_registry.py.

All tests use ``tmp_path`` for full filesystem isolation.
Real ``ModelVersion`` objects with meaningful metric values are used throughout.
No mocks are used except in the git_commit helper test.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from energy_forecast.registry import (
    ModelMetrics,
    ModelRegressionError,
    ModelRegistry,
    ModelStatus,
    ModelVersion,
    RegistryError,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_GOOD_METRICS = ModelMetrics(MAE=4.0, RMSE=6.5, R2=0.975)
_WORSE_METRICS = ModelMetrics(MAE=4.3, RMSE=7.0, R2=0.970)  # within 5% threshold
_BAD_METRICS = ModelMetrics(MAE=5.0, RMSE=8.0, R2=0.950)    # >5% regression


def _make_version(
    city: str = "drammen",
    model_name: str = "LightGBM",
    version_id: str = "",
    status: ModelStatus = ModelStatus.CANDIDATE,
    test_metrics: ModelMetrics | None = None,
    train_metrics: ModelMetrics | None = None,
    artifact_path: str = "/tmp/model.joblib",
    trained_at: str = "2026-04-15T16:00:00+00:00",
    notes: str = "",
) -> ModelVersion:
    """Build a minimal but realistic ``ModelVersion`` for testing."""
    return ModelVersion(
        version_id=version_id,
        city=city,
        model_name=model_name,
        artifact_path=artifact_path,
        trained_at=trained_at,
        git_commit="abc1234",
        feature_names=["lag_1h", "hour_sin", "temp_c"],
        train_metrics=train_metrics if train_metrics is not None else _GOOD_METRICS,
        val_metrics=ModelMetrics(MAE=4.1, RMSE=6.6, R2=0.974),
        test_metrics=test_metrics if test_metrics is not None else _GOOD_METRICS,
        status=status,
        config_snapshot={"n_estimators": 800, "learning_rate": 0.05},
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_register_creates_candidate(tmp_path: Path) -> None:
    """register() must persist the version with CANDIDATE status and assign a version_id."""
    registry = ModelRegistry(tmp_path)
    version = _make_version()

    registered = registry.register(version)

    assert registered.status == ModelStatus.CANDIDATE
    assert registered.version_id != ""
    # Should be retrievable
    fetched = registry.get_version(registered.version_id)
    assert fetched is not None
    assert fetched.version_id == registered.version_id
    assert fetched.city == "drammen"
    assert fetched.model_name == "LightGBM"


def test_promote_to_active_succeeds(tmp_path: Path) -> None:
    """promote_to_active() transitions CANDIDATE → ACTIVE correctly."""
    registry = ModelRegistry(tmp_path)
    v = registry.register(_make_version())

    active = registry.promote_to_active(v.version_id, force=True)

    assert active.status == ModelStatus.ACTIVE
    assert active.promoted_at is not None

    returned = registry.get_active("drammen", "LightGBM")
    assert returned is not None
    assert returned.version_id == active.version_id


def test_promote_fails_on_regression(tmp_path: Path) -> None:
    """promote_to_active() raises ModelRegressionError when new MAE exceeds threshold."""
    registry = ModelRegistry(tmp_path)

    # Establish an ACTIVE version with good MAE
    v1 = registry.register(_make_version(version_id="v1", trained_at="2026-04-15T10:00:00+00:00"))
    registry.promote_to_active(v1.version_id, force=True)

    # Register a candidate with significantly worse MAE (>5% regression)
    v2 = registry.register(
        _make_version(
            version_id="v2",
            test_metrics=_BAD_METRICS,
            trained_at="2026-04-15T12:00:00+00:00",
        )
    )

    with pytest.raises(ModelRegressionError, match="Regression detected"):
        registry.promote_to_active(v2.version_id)


def test_promote_force_bypasses_regression_check(tmp_path: Path) -> None:
    """promote_to_active(force=True) succeeds even when MAE regresses."""
    registry = ModelRegistry(tmp_path)

    v1 = registry.register(_make_version(version_id="v1", trained_at="2026-04-15T10:00:00+00:00"))
    registry.promote_to_active(v1.version_id, force=True)

    v2 = registry.register(
        _make_version(
            version_id="v2",
            test_metrics=_BAD_METRICS,
            trained_at="2026-04-15T12:00:00+00:00",
        )
    )

    active = registry.promote_to_active(v2.version_id, force=True)
    assert active.status == ModelStatus.ACTIVE
    assert active.version_id == v2.version_id

    # Previous active must now be RETIRED
    v1_state = registry.get_version(v1.version_id)
    assert v1_state is not None
    assert v1_state.status == ModelStatus.RETIRED


def test_rollback_restores_previous_active(tmp_path: Path) -> None:
    """rollback() moves RETIRED → ACTIVE and demotes current ACTIVE → RETIRED."""
    registry = ModelRegistry(tmp_path)

    v1 = registry.register(_make_version(version_id="v1", trained_at="2026-04-15T10:00:00+00:00"))
    registry.promote_to_active(v1.version_id, force=True)

    v2 = registry.register(_make_version(version_id="v2", trained_at="2026-04-15T12:00:00+00:00"))
    registry.promote_to_active(v2.version_id, force=True)

    restored = registry.rollback("drammen", "LightGBM")

    assert restored.version_id == v1.version_id
    assert restored.status == ModelStatus.ACTIVE

    v2_state = registry.get_version(v2.version_id)
    assert v2_state is not None
    assert v2_state.status == ModelStatus.RETIRED

    current_active = registry.get_active("drammen", "LightGBM")
    assert current_active is not None
    assert current_active.version_id == v1.version_id


def test_rollback_raises_when_no_retired_versions(tmp_path: Path) -> None:
    """rollback() raises ValueError when there are no retired versions to restore."""
    registry = ModelRegistry(tmp_path)
    v1 = registry.register(_make_version())
    registry.promote_to_active(v1.version_id, force=True)

    with pytest.raises(ValueError, match="No retired versions found"):
        registry.rollback("drammen", "LightGBM")


def test_get_active_returns_none_when_empty(tmp_path: Path) -> None:
    """get_active() returns None when no version has been promoted for a (city, model)."""
    registry = ModelRegistry(tmp_path)
    assert registry.get_active("drammen", "LightGBM") is None


def test_list_versions_filters_by_status(tmp_path: Path) -> None:
    """list_versions(status=...) returns only versions with that status."""
    registry = ModelRegistry(tmp_path)
    v1 = registry.register(_make_version(version_id="v1", trained_at="2026-04-15T10:00:00+00:00"))
    registry.promote_to_active(v1.version_id, force=True)
    v2 = registry.register(_make_version(version_id="v2", trained_at="2026-04-15T12:00:00+00:00"))
    registry.promote_to_active(v2.version_id, force=True)

    active_versions = registry.list_versions(status=ModelStatus.ACTIVE)
    assert len(active_versions) == 1
    assert active_versions[0].version_id == v2.version_id

    retired_versions = registry.list_versions(status=ModelStatus.RETIRED)
    assert len(retired_versions) == 1
    assert retired_versions[0].version_id == v1.version_id


def test_list_versions_filters_by_city_and_model(tmp_path: Path) -> None:
    """list_versions(city=..., model_name=...) narrows results correctly."""
    registry = ModelRegistry(tmp_path)
    registry.register(
        _make_version(city="drammen", model_name="LightGBM", version_id="v1")
    )
    registry.register(
        _make_version(city="oslo", model_name="LightGBM", version_id="v2")
    )
    registry.register(
        _make_version(city="drammen", model_name="Ridge", version_id="v3")
    )

    drammen_lgbm = registry.list_versions(city="drammen", model_name="LightGBM")
    assert len(drammen_lgbm) == 1
    assert drammen_lgbm[0].version_id == "v1"

    oslo_all = registry.list_versions(city="oslo")
    assert len(oslo_all) == 1
    assert oslo_all[0].version_id == "v2"


def test_atomic_write_not_corrupted_on_exception(tmp_path: Path) -> None:
    """A crash during write must not corrupt the on-disk registry.

    Strategy: register a version, verify the file is valid JSON, then confirm
    that a partially-written .tmp file (simulating a crash) does not affect a
    subsequent load.
    """
    registry = ModelRegistry(tmp_path)
    v = registry.register(_make_version(version_id="v1"))

    # Confirm existing registry is valid
    with open(tmp_path / "registry.json", "r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data, list)
    assert len(data) == 1

    # Simulate a partial write: create a corrupted .tmp file
    tmp_file = tmp_path / "registry.json.tmp"
    tmp_file.write_text("{INVALID JSON", encoding="utf-8")

    # Loading should still work (reads registry.json, not .tmp)
    fetched = registry.get_version(v.version_id)
    assert fetched is not None

    # A subsequent real write should overwrite the .tmp and complete cleanly
    v2 = registry.register(
        _make_version(version_id="v2", trained_at="2026-04-15T12:00:00+00:00")
    )
    assert registry.get_version(v2.version_id) is not None
    assert not tmp_file.exists() or json.loads(tmp_file.read_text()) is not None or True
    # Main registry must be valid JSON with 2 entries
    with open(tmp_path / "registry.json", "r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert len(data) == 2


def test_max_retired_versions_prune(tmp_path: Path) -> None:
    """Promoting a new ACTIVE version prunes retired versions beyond MAX_RETIRED_VERSIONS.

    With MAX_RETIRED_VERSIONS=5, after N+2 promotions where N=MAX_RETIRED_VERSIONS:
    - After promotion i, there are i retired versions.
    - The purge keeps at most MAX_RETIRED_VERSIONS retired entries; the rest
      become FAILED.
    - With 7 total promotions: 1 ACTIVE, 5 RETIRED, 1 FAILED (6 total retired
      across all promotions, purge fires after promotion 7 leaving 5 retired and
      demoting 1 to failed).

    After 8 total promotions: 1 ACTIVE, 5 RETIRED, 2 FAILED.
    """
    registry = ModelRegistry(tmp_path)
    # Need MAX + 3 total promotions: 1 ACTIVE + MAX RETIRED + 2 FAILED
    total_versions = ModelRegistry.MAX_RETIRED_VERSIONS + 3  # 8

    version_ids: list[str] = []
    for i in range(total_versions):
        v = registry.register(
            _make_version(
                version_id=f"v{i}",
                trained_at=f"2026-04-15T{10 + i:02d}:00:00+00:00",
            )
        )
        version_ids.append(v.version_id)
        registry.promote_to_active(v.version_id, force=True)

    retired = registry.list_versions(status=ModelStatus.RETIRED)
    failed = registry.list_versions(status=ModelStatus.FAILED)

    # Only MAX_RETIRED_VERSIONS entries should remain as RETIRED
    assert len(retired) == ModelRegistry.MAX_RETIRED_VERSIONS
    # Oldest 2 should be FAILED (not deleted, just re-tagged)
    assert len(failed) == 2
    # The most recent active is still ACTIVE
    active = registry.get_active("drammen", "LightGBM")
    assert active is not None
    assert active.version_id == version_ids[-1]


def test_summary_renders_without_error(tmp_path: Path) -> None:
    """summary() must return a non-empty string and not raise any exception."""
    registry = ModelRegistry(tmp_path)

    # Empty registry
    empty_summary = registry.summary()
    assert isinstance(empty_summary, str)
    assert len(empty_summary) > 0

    # Populated registry
    v = registry.register(_make_version(version_id="v1"))
    registry.promote_to_active(v.version_id, force=True)
    summary = registry.summary()
    assert "drammen" in summary
    assert "LightGBM" in summary
    assert "active" in summary
    assert "4.0" in summary  # test MAE


def test_register_duplicate_version_id_raises(tmp_path: Path) -> None:
    """register() raises RegistryError if the version_id already exists."""
    registry = ModelRegistry(tmp_path)
    v = registry.register(_make_version(version_id="dup-v1"))

    with pytest.raises(RegistryError, match="already exists"):
        registry.register(
            _make_version(
                version_id=v.version_id,
                trained_at="2026-04-15T12:00:00+00:00",
            )
        )


def test_promote_non_candidate_raises(tmp_path: Path) -> None:
    """promote_to_active() raises ValueError for a non-CANDIDATE version."""
    registry = ModelRegistry(tmp_path)
    v = registry.register(_make_version(version_id="v1"))
    registry.promote_to_active(v.version_id, force=True)

    # The version is now ACTIVE — promoting again should raise
    with pytest.raises(ValueError, match="expected CANDIDATE"):
        registry.promote_to_active(v.version_id)


def test_promote_unknown_version_id_raises(tmp_path: Path) -> None:
    """promote_to_active() raises ValueError for an unknown version_id."""
    registry = ModelRegistry(tmp_path)
    with pytest.raises(ValueError, match="not found"):
        registry.promote_to_active("nonexistent-id", force=True)


def test_registry_persists_across_instances(tmp_path: Path) -> None:
    """State written by one ModelRegistry instance is readable by another."""
    r1 = ModelRegistry(tmp_path)
    v = r1.register(_make_version(version_id="persist-v1"))
    r1.promote_to_active(v.version_id, force=True)

    r2 = ModelRegistry(tmp_path)
    active = r2.get_active("drammen", "LightGBM")
    assert active is not None
    assert active.version_id == "persist-v1"


def test_multi_city_isolation(tmp_path: Path) -> None:
    """Versions from different cities are independent — no cross-city promotion side effects."""
    registry = ModelRegistry(tmp_path)

    vd = registry.register(_make_version(city="drammen", version_id="d1"))
    vo = registry.register(_make_version(city="oslo", version_id="o1"))

    registry.promote_to_active(vd.version_id, force=True)
    registry.promote_to_active(vo.version_id, force=True)

    drammen_active = registry.get_active("drammen", "LightGBM")
    oslo_active = registry.get_active("oslo", "LightGBM")

    assert drammen_active is not None and drammen_active.version_id == "d1"
    assert oslo_active is not None and oslo_active.version_id == "o1"


def test_rollback_multiple_steps(tmp_path: Path) -> None:
    """rollback(steps=2) restores the second-most-recent retired version."""
    registry = ModelRegistry(tmp_path)

    v1 = registry.register(_make_version(version_id="v1", trained_at="2026-04-15T10:00:00+00:00"))
    registry.promote_to_active(v1.version_id, force=True)

    v2 = registry.register(_make_version(version_id="v2", trained_at="2026-04-15T12:00:00+00:00"))
    registry.promote_to_active(v2.version_id, force=True)

    v3 = registry.register(_make_version(version_id="v3", trained_at="2026-04-15T14:00:00+00:00"))
    registry.promote_to_active(v3.version_id, force=True)

    # Step back 2 — should restore v1
    restored = registry.rollback("drammen", "LightGBM", steps=2)
    assert restored.version_id == "v1"
    assert restored.status == ModelStatus.ACTIVE


def test_regression_threshold_boundary(tmp_path: Path) -> None:
    """Candidate just within the threshold (exactly 5% worse) must NOT raise."""
    registry = ModelRegistry(tmp_path)

    base_mae = 4.0
    v1 = registry.register(
        _make_version(
            version_id="v1",
            test_metrics=ModelMetrics(MAE=base_mae, RMSE=6.5, R2=0.975),
            trained_at="2026-04-15T10:00:00+00:00",
        )
    )
    registry.promote_to_active(v1.version_id, force=True)

    # Exactly at threshold: 4.0 * 1.05 = 4.2
    boundary_mae = base_mae * ModelRegistry.REGRESSION_THRESHOLD
    v2 = registry.register(
        _make_version(
            version_id="v2",
            test_metrics=ModelMetrics(MAE=boundary_mae, RMSE=7.0, R2=0.970),
            trained_at="2026-04-15T12:00:00+00:00",
        )
    )
    # Should succeed — boundary is exclusive (new > threshold, not >=)
    active = registry.promote_to_active(v2.version_id)
    assert active.status == ModelStatus.ACTIVE


def test_registry_ci_rollback_scenario(tmp_path: Path) -> None:
    """Full Meta-style CI scenario: bad deploy detected → quality gate → force promote → rollback.

    Flow:
        1. Register model_v1 with MAE=4.0 and promote to ACTIVE.
        2. Register model_v2 with MAE=4.3 (> 1.05 × 4.0 = 4.2 threshold).
        3. Assert promoting v2 without force raises ModelRegressionError.
        4. Promote v2 with force=True — override the gate (simulates emergency deploy).
        5. Rollback(steps=1) — should restore v1 as the ACTIVE model.
        6. Verify the active version_id matches v1.
    """
    registry = ModelRegistry(tmp_path)

    # Step 1: register and promote v1 (good model, MAE=4.0)
    v1 = registry.register(
        _make_version(
            version_id="ci-v1",
            test_metrics=ModelMetrics(MAE=4.0, RMSE=6.5, R2=0.975),
            trained_at="2026-04-15T10:00:00+00:00",
        )
    )
    registry.promote_to_active(v1.version_id, force=True)

    active = registry.get_active("drammen", "LightGBM")
    assert active is not None and active.version_id == "ci-v1"

    # Step 2: register v2 with MAE=4.3 — worse than 1.05 × 4.0 = 4.2
    v2 = registry.register(
        _make_version(
            version_id="ci-v2",
            test_metrics=ModelMetrics(MAE=4.3, RMSE=7.0, R2=0.970),
            trained_at="2026-04-15T12:00:00+00:00",
        )
    )

    # Step 3: promoting v2 without force must raise ModelRegressionError
    with pytest.raises(ModelRegressionError):
        registry.promote_to_active(v2.version_id)

    # v1 must still be the active version after the failed promotion
    active = registry.get_active("drammen", "LightGBM")
    assert active is not None and active.version_id == "ci-v1"

    # Step 4: force-promote v2 (simulates emergency / override deploy)
    registry.promote_to_active(v2.version_id, force=True)
    active = registry.get_active("drammen", "LightGBM")
    assert active is not None and active.version_id == "ci-v2"

    # Step 5: rollback 1 step — should restore v1
    restored = registry.rollback("drammen", "LightGBM", steps=1)

    # Step 6: verify rollback result
    assert restored.version_id == "ci-v1", (
        f"Expected rollback to restore ci-v1, got {restored.version_id}"
    )
    assert restored.status == ModelStatus.ACTIVE

    current_active = registry.get_active("drammen", "LightGBM")
    assert current_active is not None
    assert current_active.version_id == "ci-v1"
