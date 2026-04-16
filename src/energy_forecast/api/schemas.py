"""
energy_forecast.api.schemas
============================
Model-derived feature validation for the FastAPI ``/predict`` endpoint.

Problem
-------
``PredictionRequest.features`` was a bare ``dict`` — any key, any count.
A caller sending 2 wrong-named features would get a silent 500 from the model
rather than an informative 400.

Solution
--------
1. At server startup the active LightGBM model's ``feature_name_`` list is
   registered here via ``register_features()``.
2. ``validate_features()`` is called from the Pydantic field_validator —
   it checks exact key set match and returns a clear error message on mismatch.
3. When no model is loaded (mock / test mode), validation is lenient so
   demo mode is unaffected.

Usage (in ``deployment/app.py`` lifespan)::

    from energy_forecast.api import schemas

    if hasattr(model, "feature_name_"):
        schemas.register_features(model.feature_name_)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Module-level registry — populated during FastAPI lifespan startup
_expected_features: list[str] = []
_validation_active: bool = False


def register_features(feature_names: list[str]) -> None:
    """Register the exact feature names the active model expects.

    Call once during server startup after loading the LightGBM model.
    Subsequent ``/predict`` requests are validated against this list.

    Args:
        feature_names: ``model.feature_name_`` from the loaded LGBMRegressor.
    """
    global _expected_features, _validation_active
    _expected_features = list(feature_names)
    _validation_active = True
    logger.info(
        "[schemas] Strict feature validation active: %d features registered "
        "(first: %s, last: %s).",
        len(_expected_features),
        _expected_features[0] if _expected_features else "—",
        _expected_features[-1] if _expected_features else "—",
    )


def clear_features() -> None:
    """Reset the registry (used in tests to restore lenient mode)."""
    global _expected_features, _validation_active
    _expected_features = []
    _validation_active = False


def expected_feature_names() -> list[str]:
    """Return a copy of the registered feature name list (read-only view)."""
    return list(_expected_features)


def validate_features(features: dict[str, float]) -> dict[str, float]:
    """Validate that ``features`` matches the registered feature schema exactly.

    Passes through unchanged when no model is registered (mock / test mode).

    Args:
        features: Feature dict from a ``PredictionRequest``.

    Returns:
        The unchanged ``features`` dict if validation passes.

    Raises:
        ValueError: On any mismatch — missing keys, extra keys, or wrong count.
            The message names the unexpected / missing features explicitly.
    """
    if not _validation_active:
        return features  # lenient pass-through in mock/test mode

    expected = set(_expected_features)
    received = set(features.keys())

    missing = sorted(expected - received)
    extra = sorted(received - expected)

    if not missing and not extra:
        return features

    parts: list[str] = [
        f"Expected {len(expected)} features: {_expected_features}."
    ]
    if missing:
        parts.append(f"Missing {len(missing)}: {missing}.")
    if extra:
        parts.append(f"Unexpected {len(extra)}: {extra}.")
    raise ValueError(" ".join(parts))
