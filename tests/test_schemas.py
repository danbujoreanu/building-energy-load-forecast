"""
tests.test_schemas
==================
Unit tests for ``src/energy_forecast/api/schemas.py`` — E-19 strict feature
validation for the FastAPI /predict endpoint.

Coverage:
  - Lenient pass-through when no model is registered (mock / test mode)
  - Strict validation once register_features() is called
  - Missing features → ValueError with specific message
  - Extra (unexpected) features → ValueError with specific message
  - Both missing + extra at once
  - Exact correct set → passes through unchanged
  - clear_features() restores lenient mode
  - expected_feature_names() returns a copy, not the live list
"""

import pytest

from energy_forecast.api import schemas

# ─── Fixtures ────────────────────────────────────────────────────────────────

FEATURE_NAMES = [f"Column_{i}" for i in range(35)]


@pytest.fixture(autouse=True)
def reset_registry():
    """Always start each test in lenient mode; restore after."""
    schemas.clear_features()
    yield
    schemas.clear_features()


# ─── Lenient mode (no model registered) ──────────────────────────────────────


def test_lenient_mode_passes_any_nonempty_dict():
    features = {"anything": 1.0, "goes": 2.0}
    result = schemas.validate_features(features)
    assert result == features


def test_lenient_mode_passes_empty_dict():
    """Empty dict is allowed by the schema module; app.py validator rejects it."""
    result = schemas.validate_features({})
    assert result == {}


# ─── register_features ───────────────────────────────────────────────────────


def test_register_features_activates_strict_mode():
    schemas.register_features(FEATURE_NAMES)
    assert schemas._validation_active is True
    assert schemas.expected_feature_names() == FEATURE_NAMES


def test_expected_feature_names_returns_copy():
    schemas.register_features(FEATURE_NAMES)
    names = schemas.expected_feature_names()
    names.append("injected")
    assert "injected" not in schemas._expected_features


# ─── Strict validation — happy path ──────────────────────────────────────────


def test_exact_correct_features_pass():
    schemas.register_features(FEATURE_NAMES)
    features = {name: float(i) for i, name in enumerate(FEATURE_NAMES)}
    result = schemas.validate_features(features)
    assert result == features


# ─── Strict validation — error cases ─────────────────────────────────────────


def test_missing_features_raises():
    schemas.register_features(FEATURE_NAMES)
    # Only send first 10 features
    partial = {name: 0.0 for name in FEATURE_NAMES[:10]}
    with pytest.raises(ValueError) as exc_info:
        schemas.validate_features(partial)
    msg = str(exc_info.value)
    assert "Missing 25" in msg
    assert "Column_10" in msg  # first missing feature


def test_extra_features_raises():
    schemas.register_features(FEATURE_NAMES)
    features = {name: 0.0 for name in FEATURE_NAMES}
    features["unexpected_feature"] = 99.0
    with pytest.raises(ValueError) as exc_info:
        schemas.validate_features(features)
    msg = str(exc_info.value)
    assert "Unexpected 1" in msg
    assert "unexpected_feature" in msg


def test_both_missing_and_extra_raises():
    schemas.register_features(FEATURE_NAMES)
    # Replace first 3 expected with wrong names
    features = {name: 0.0 for name in FEATURE_NAMES[3:]}  # missing first 3
    features["wrong_a"] = 1.0
    features["wrong_b"] = 2.0
    with pytest.raises(ValueError) as exc_info:
        schemas.validate_features(features)
    msg = str(exc_info.value)
    assert "Missing 3" in msg
    assert "Unexpected 2" in msg


def test_completely_wrong_keys_raises():
    schemas.register_features(FEATURE_NAMES)
    with pytest.raises(ValueError) as exc_info:
        schemas.validate_features({"bad_feature": 1.0})
    msg = str(exc_info.value)
    assert f"Expected {len(FEATURE_NAMES)} features" in msg
    assert "Missing" in msg


def test_error_message_includes_expected_count():
    schemas.register_features(FEATURE_NAMES)
    with pytest.raises(ValueError) as exc_info:
        schemas.validate_features({"wrong": 0.0})
    assert "Expected 35 features" in str(exc_info.value)


# ─── clear_features ──────────────────────────────────────────────────────────


def test_clear_restores_lenient_mode():
    schemas.register_features(FEATURE_NAMES)
    schemas.clear_features()
    assert schemas._validation_active is False
    # Strict validation would raise — in lenient mode it should not
    result = schemas.validate_features({"anything": 1.0})
    assert result == {"anything": 1.0}


def test_clear_empties_expected_list():
    schemas.register_features(FEATURE_NAMES)
    schemas.clear_features()
    assert schemas.expected_feature_names() == []


# ─── Edge cases ──────────────────────────────────────────────────────────────


def test_register_empty_list_activates_strict_mode():
    """Even an empty feature list activates strict mode."""
    schemas.register_features([])
    assert schemas._validation_active is True
    # Any non-empty dict is now 'extra'
    with pytest.raises(ValueError):
        schemas.validate_features({"anything": 1.0})


def test_re_register_replaces_previous():
    schemas.register_features(FEATURE_NAMES)
    new_names = ["feat_a", "feat_b"]
    schemas.register_features(new_names)
    assert schemas.expected_feature_names() == new_names
    # Old feature set should now fail
    with pytest.raises(ValueError):
        schemas.validate_features({name: 0.0 for name in FEATURE_NAMES})
