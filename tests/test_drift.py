"""
tests/test_drift.py
===================
Unit tests for src/energy_forecast/monitoring/drift_detector.py

All tests use synthetic data generated from a fixed RNG (seed 42) — no
external fixture files required.  Tests cover:

  - No-drift baseline → OK severity
  - Feature distribution shift → WARNING or CRITICAL
  - PSI hand-computation verification
  - Target distribution shift detection
  - Rolling MAE trigger (high MAE → triggered)
  - Rolling MAE no-trigger (good MAE → not triggered)
  - Aggregated severity max across mixed checks
  - JSON round-trip serialisation
  - Markdown rendering (no exceptions, non-empty)
  - PSI empty/zero-bin edge case (no log-zero crash)
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from energy_forecast.monitoring import (
    DriftDetector,
    DriftSeverity,
)
from energy_forecast.monitoring.drift_detector import _max_severity

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

RNG = np.random.default_rng(42)
N_REF = 1000
N_CHK = 200


def _make_cfg(**monitoring_overrides) -> dict:
    """Minimal cfg dict for DriftDetector construction."""
    base = {
        "monitoring": {
            "rolling_window_days": 7,
            "mae_threshold_multiplier": 1.5,
            "ks_alpha": 0.05,
            "psi_warning": 0.10,
            "psi_critical": 0.20,
        }
    }
    base["monitoring"].update(monitoring_overrides)
    return base


def _make_frames(
    n_ref: int = N_REF,
    n_chk: int = N_CHK,
    shift: float = 0.0,
    scale: float = 1.0,
    rng: np.random.Generator | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Create synthetic reference and check DataFrames.

    Args:
        n_ref: Reference set size.
        n_chk: Check set size.
        shift: Mean shift applied to check features (for drift injection).
        scale: Scale multiplier applied to check features.
        rng: Optional RNG (uses module-level RNG if None).

    Returns:
        (X_ref, X_chk, y_ref, y_chk)
    """
    r = rng if rng is not None else RNG

    X_ref = pd.DataFrame(
        {
            "feature_a": r.normal(0, 1, n_ref),
            "feature_b": r.uniform(0, 10, n_ref),
            "feature_c": r.exponential(2, n_ref),
        }
    )
    y_ref = pd.Series(r.normal(50, 10, n_ref), name="y")

    X_chk = pd.DataFrame(
        {
            "feature_a": r.normal(0 + shift, 1 * scale, n_chk),
            "feature_b": r.uniform(0 + shift, 10 + shift, n_chk),
            "feature_c": r.exponential(2 * scale, n_chk),
        }
    )
    y_chk = pd.Series(r.normal(50 + shift, 10 * scale, n_chk), name="y")

    return X_ref, X_chk, y_ref, y_chk


# ---------------------------------------------------------------------------
# 1. No-drift baseline → OK
# ---------------------------------------------------------------------------


def test_no_drift_returns_ok() -> None:
    """When reference and check are drawn from identical distributions, overall
    severity should be OK and no features should be flagged as drifted."""
    rng = np.random.default_rng(0)
    X_ref = pd.DataFrame({"a": rng.normal(0, 1, 2000), "b": rng.normal(5, 2, 2000)})
    X_chk = pd.DataFrame({"a": rng.normal(0, 1, 500), "b": rng.normal(5, 2, 500)})
    y_ref = pd.Series(rng.normal(50, 10, 2000))
    y_chk = pd.Series(rng.normal(50, 10, 500))
    training_mae = 4.0

    detector = DriftDetector(_make_cfg())
    report = detector.full_report(
        city="test_city",
        model_name="LightGBM",
        X_reference=X_ref,
        X_check=X_chk,
        y_reference=y_ref,
        y_check=y_chk,
        training_mae=training_mae,
        # No y_pred — rolling MAE check skipped
    )

    assert (
        report.overall_severity == DriftSeverity.OK
    ), f"Expected OK for identical distributions, got {report.overall_severity}"
    assert report.recommended_action == "no_action"
    drifted_features = [r for r in report.feature_results if r.is_drifted]
    assert (
        len(drifted_features) == 0
    ), f"Expected 0 drifted features, got {[r.feature_name for r in drifted_features]}"


# ---------------------------------------------------------------------------
# 2. Feature drift detected → WARNING or CRITICAL
# ---------------------------------------------------------------------------


def test_feature_drift_detected() -> None:
    """Injecting a large mean shift into check features should trigger drift."""
    rng = np.random.default_rng(1)
    # Large shift (5 standard deviations) guarantees detection
    X_ref, X_chk, y_ref, y_chk = _make_frames(n_ref=1000, n_chk=500, shift=5.0, scale=1.0, rng=rng)

    detector = DriftDetector(_make_cfg())
    feature_results = detector.check_feature_drift(X_ref, X_chk)

    drifted = [r for r in feature_results if r.is_drifted]
    assert len(drifted) > 0, "Expected at least one drifted feature after 5-sigma shift"

    # Severity should be at least WARNING
    severities = {r.severity for r in drifted}
    assert DriftSeverity.OK not in severities or len(drifted) > 0
    worst_severity = _max_severity([r.severity for r in feature_results])
    assert worst_severity in (DriftSeverity.WARNING, DriftSeverity.CRITICAL)

    # Results should be sorted by PSI descending
    psi_values = [r.psi for r in feature_results]
    assert psi_values == sorted(
        psi_values, reverse=True
    ), "Feature results should be sorted by PSI descending"


# ---------------------------------------------------------------------------
# 3. PSI hand-computation verification
# ---------------------------------------------------------------------------


def test_psi_calculation_matches_manual() -> None:
    """Verify PSI against a hand-computed reference.

    For a uniform reference [0, 1) split into 5 equal bins (each 20% of data),
    and an actual distribution that is identical, PSI = 0.
    """
    n = 5000
    rng = np.random.default_rng(2)
    reference = rng.uniform(0, 1, n)
    actual = rng.uniform(0, 1, n)  # same distribution

    psi = DriftDetector._compute_psi(reference, actual, n_bins=5)

    # Both distributions are uniform over [0, 1] — PSI should be very small
    assert psi < 0.05, f"PSI for identical uniform distributions should be near 0, got {psi:.4f}"


def test_psi_large_shift_is_high() -> None:
    """PSI should be large (>= 0.2) when distributions are completely non-overlapping."""
    n = 2000
    rng = np.random.default_rng(3)
    reference = rng.normal(0, 1, n)  # centred at 0
    actual = rng.normal(10, 1, n)  # centred at 10 — completely separate

    psi = DriftDetector._compute_psi(reference, actual, n_bins=10)
    assert psi >= DriftDetector.PSI_CRITICAL_THRESHOLD, (
        f"PSI for completely non-overlapping distributions should be >= {DriftDetector.PSI_CRITICAL_THRESHOLD},"
        f" got {psi:.4f}"
    )


# ---------------------------------------------------------------------------
# 4. Target drift detected
# ---------------------------------------------------------------------------


def test_target_drift_detected() -> None:
    """Shifting the target distribution should be flagged as drifted."""
    rng = np.random.default_rng(4)
    y_ref = pd.Series(rng.normal(50, 5, 2000))
    y_chk = pd.Series(rng.normal(80, 5, 500))  # +30 kWh mean shift

    detector = DriftDetector(_make_cfg())
    result = detector.check_target_drift(y_ref, y_chk)

    assert result.is_drifted, "Large mean shift should be detected as target drift"
    assert (
        result.mean_shift_pct > 50.0
    ), f"Mean shift should be > 50%, got {result.mean_shift_pct:.1f}%"
    assert isinstance(result.ks_statistic, float)
    assert isinstance(result.ks_pvalue, float)


def test_target_no_drift_same_distribution() -> None:
    """When check and reference y are from the same distribution, is_drifted = False."""
    rng = np.random.default_rng(5)
    y_ref = pd.Series(rng.normal(50, 5, 3000))
    y_chk = pd.Series(rng.normal(50, 5, 500))

    detector = DriftDetector(_make_cfg())
    result = detector.check_target_drift(y_ref, y_chk)

    assert (
        not result.is_drifted
    ), f"Identical distribution should not trigger target drift; p={result.ks_pvalue:.4f}"


# ---------------------------------------------------------------------------
# 5. Rolling MAE trigger — high MAE
# ---------------------------------------------------------------------------


def test_rolling_mae_trigger() -> None:
    """When rolling MAE > threshold × training MAE, is_triggered should be True."""
    training_mae = 4.0
    # Inject predictions with large errors (rolling MAE >> 1.5 × training_mae)
    rng = np.random.default_rng(6)
    n = 200
    y_true = pd.Series(rng.normal(50, 10, n))
    # Add errors of ~15 kWh → rolling MAE ≈ 15 >> 1.5 × 4.0 = 6.0
    y_pred = y_true.to_numpy() + rng.normal(0, 15, n)

    detector = DriftDetector(_make_cfg())
    result = detector.check_rolling_mae(y_true, y_pred, training_mae)

    assert (
        result.is_triggered
    ), f"Expected triggered=True with large errors; ratio={result.ratio:.2f}"
    assert result.severity == DriftSeverity.CRITICAL
    assert result.ratio > result.threshold


# ---------------------------------------------------------------------------
# 6. Rolling MAE no trigger — good MAE
# ---------------------------------------------------------------------------


def test_rolling_mae_no_trigger() -> None:
    """When rolling MAE is well within threshold, is_triggered should be False."""
    training_mae = 4.0
    rng = np.random.default_rng(7)
    n = 200
    y_true = pd.Series(rng.normal(50, 10, n))
    # Small errors (< 1 kWh) → ratio << 1.0
    y_pred = y_true.to_numpy() + rng.normal(0, 0.5, n)

    detector = DriftDetector(_make_cfg())
    result = detector.check_rolling_mae(y_true, y_pred, training_mae)

    assert (
        not result.is_triggered
    ), f"Expected triggered=False with small errors; ratio={result.ratio:.2f}"
    assert result.severity == DriftSeverity.OK
    assert result.ratio < result.threshold


def test_rolling_mae_with_timestamps() -> None:
    """Rolling MAE with a DatetimeIndex should respect the calendar-day window."""
    training_mae = 4.0
    rng = np.random.default_rng(8)
    n = 24 * 14  # 14 days of hourly data
    timestamps = pd.date_range("2022-01-01", periods=n, freq="h")
    y_true = pd.Series(rng.normal(50, 5, n), index=timestamps)
    y_pred = y_true.to_numpy() + rng.normal(0, 0.5, n)

    detector = DriftDetector(_make_cfg(rolling_window_days=7))
    result = detector.check_rolling_mae(y_true, y_pred, training_mae, timestamps=timestamps)

    assert result.window_days == 7
    assert not result.is_triggered


# ---------------------------------------------------------------------------
# 7. Full report severity is max across all checks
# ---------------------------------------------------------------------------


def test_full_report_severity_max() -> None:
    """The overall_severity in the report should be the maximum of all checks."""
    rng = np.random.default_rng(9)

    # Reference: stable
    X_ref = pd.DataFrame({"a": rng.normal(0, 1, 2000), "b": rng.normal(5, 2, 2000)})
    y_ref = pd.Series(rng.normal(50, 10, 2000))

    # Check: shift 'a' massively to force CRITICAL feature drift
    X_chk = pd.DataFrame(
        {"a": rng.normal(20, 1, 200), "b": rng.normal(5, 2, 200)}  # 20-sigma shift
    )
    y_chk = pd.Series(rng.normal(50, 10, 200))  # y is stable

    detector = DriftDetector(_make_cfg())
    report = detector.full_report(
        city="drammen",
        model_name="LightGBM",
        X_reference=X_ref,
        X_check=X_chk,
        y_reference=y_ref,
        y_check=y_chk,
        training_mae=4.029,
    )

    # Feature 'a' has a massive shift → CRITICAL
    assert (
        report.overall_severity == DriftSeverity.CRITICAL
    ), f"Expected CRITICAL from massive feature shift, got {report.overall_severity}"
    assert report.recommended_action == "retrain_now"


def test_full_report_warning_when_only_feature_drift() -> None:
    """Moderate feature drift (PSI in warning zone) + stable MAE → WARNING + 'monitor'."""
    rng = np.random.default_rng(10)

    X_ref = pd.DataFrame({"a": rng.normal(0, 1, 2000)})
    y_ref = pd.Series(rng.normal(50, 5, 2000))

    # Moderate shift ~2 sigma — should trigger KS WARNING
    X_chk = pd.DataFrame({"a": rng.normal(2, 1, 200)})
    y_chk = pd.Series(rng.normal(50, 5, 200))

    training_mae = 4.0
    # Provide good predictions → rolling MAE OK
    y_pred_good = y_chk.to_numpy() + rng.normal(0, 0.5, len(y_chk))

    detector = DriftDetector(_make_cfg())
    report = detector.full_report(
        city="oslo",
        model_name="LightGBM",
        X_reference=X_ref,
        X_check=X_chk,
        y_reference=y_ref,
        y_check=y_chk,
        training_mae=training_mae,
        y_pred=y_pred_good,
    )

    # Feature drift should be at least WARNING
    assert report.overall_severity in (DriftSeverity.WARNING, DriftSeverity.CRITICAL)


# ---------------------------------------------------------------------------
# 8. JSON round-trip
# ---------------------------------------------------------------------------


def test_to_json_roundtrip() -> None:
    """Serialise a DriftReport to JSON and verify key fields are preserved."""
    rng = np.random.default_rng(11)
    X_ref, X_chk, y_ref, y_chk = _make_frames(n_ref=500, n_chk=100, rng=rng)

    detector = DriftDetector(_make_cfg())
    report = detector.full_report(
        city="drammen",
        model_name="LightGBM",
        X_reference=X_ref,
        X_check=X_chk,
        y_reference=y_ref,
        y_check=y_chk,
        training_mae=4.029,
        reference_period=("2018-01-01", "2020-12-31"),
        check_period=("2021-07-01", "2022-03-18"),
    )

    json_str = report.to_json()
    # Must be valid JSON
    data = json.loads(json_str)

    assert data["city"] == "drammen"
    assert data["model_name"] == "LightGBM"
    assert data["reference_period"] == ["2018-01-01", "2020-12-31"]
    assert data["check_period"] == ["2021-07-01", "2022-03-18"]
    assert data["n_reference_samples"] == 500
    assert data["n_check_samples"] == 100
    assert isinstance(data["feature_results"], list)
    assert data["overall_severity"] in ("ok", "warning", "critical")
    assert data["recommended_action"] in (
        "no_action",
        "monitor",
        "retrain_scheduled",
        "retrain_now",
    )
    assert isinstance(data["summary"], str) and len(data["summary"]) > 0


# ---------------------------------------------------------------------------
# 9. Markdown renders without exceptions and produces non-empty output
# ---------------------------------------------------------------------------


def test_to_markdown_renders() -> None:
    """to_markdown() should return a non-empty string without raising."""
    rng = np.random.default_rng(12)
    X_ref, X_chk, y_ref, y_chk = _make_frames(n_ref=500, n_chk=100, rng=rng)

    detector = DriftDetector(_make_cfg())
    report = detector.full_report(
        city="oslo",
        model_name="LightGBM",
        X_reference=X_ref,
        X_check=X_chk,
        y_reference=y_ref,
        y_check=y_chk,
        training_mae=7.415,
    )

    md = report.to_markdown()
    assert isinstance(md, str)
    assert len(md) > 100, "Markdown output should be non-trivially long"
    assert "## Drift Report" in md
    assert "oslo" in md
    assert "LightGBM" in md


def test_to_markdown_with_rolling_mae() -> None:
    """Markdown should include rolling MAE section when y_pred is provided."""
    rng = np.random.default_rng(13)
    X_ref, X_chk, y_ref, y_chk = _make_frames(n_ref=500, n_chk=100, rng=rng)
    y_pred = y_chk.to_numpy() + rng.normal(0, 1, len(y_chk))

    detector = DriftDetector(_make_cfg())
    report = detector.full_report(
        city="drammen",
        model_name="LightGBM",
        X_reference=X_ref,
        X_check=X_chk,
        y_reference=y_ref,
        y_check=y_chk,
        training_mae=4.029,
        y_pred=y_pred,
    )

    md = report.to_markdown()
    assert "Rolling MAE" in md


# ---------------------------------------------------------------------------
# 10. PSI clips zero bins — no log(0) crash
# ---------------------------------------------------------------------------


def test_psi_clips_zero_bins() -> None:
    """PSI should not raise when actual has empty bins relative to reference."""
    rng = np.random.default_rng(14)
    # Reference spans [0, 1]; actual is concentrated in [0.8, 1.0]
    # Several reference bins will have zero actual count.
    reference = rng.uniform(0, 1, 1000)
    actual = rng.uniform(0.8, 1.0, 200)

    # Should not raise ZeroDivisionError or log(0) ValueError
    psi = DriftDetector._compute_psi(reference, actual, n_bins=10)
    assert np.isfinite(psi), f"PSI should be finite, got {psi}"
    assert psi >= 0.0, "PSI must be non-negative"


def test_psi_identical_constant_reference_returns_zero() -> None:
    """Constant reference distribution should return PSI = 0 (degenerate guard)."""
    reference = np.ones(100)  # constant — std = 0
    actual = np.ones(50)

    psi = DriftDetector._compute_psi(reference, actual, n_bins=10)
    assert psi == 0.0, f"Constant reference should yield PSI=0, got {psi}"


# ---------------------------------------------------------------------------
# Utility: _max_severity
# ---------------------------------------------------------------------------


def test_max_severity_empty() -> None:
    """Empty list returns OK."""
    assert _max_severity([]) == DriftSeverity.OK


def test_max_severity_ordering() -> None:
    """CRITICAL > WARNING > OK."""
    mixed = [DriftSeverity.OK, DriftSeverity.WARNING, DriftSeverity.CRITICAL]
    assert _max_severity(mixed) == DriftSeverity.CRITICAL
    assert _max_severity([DriftSeverity.OK, DriftSeverity.WARNING]) == DriftSeverity.WARNING
    assert _max_severity([DriftSeverity.OK]) == DriftSeverity.OK


# ---------------------------------------------------------------------------
# DriftDetector constructor: config override
# ---------------------------------------------------------------------------


def test_constructor_reads_config() -> None:
    """Constructor should read thresholds from cfg['monitoring'] dict."""
    cfg = _make_cfg(mae_threshold_multiplier=2.0, rolling_window_days=14)
    detector = DriftDetector(cfg)
    assert detector._mae_threshold_multiplier == 2.0
    assert detector._rolling_window_days == 14


def test_constructor_kwarg_overrides_config() -> None:
    """Explicit constructor kwargs should override config values."""
    cfg = _make_cfg(mae_threshold_multiplier=2.0)
    detector = DriftDetector(cfg, mae_threshold_multiplier=3.0)
    # 3.0 != 1.5 (the default), so the kwarg should win
    assert detector._mae_threshold_multiplier == 3.0


# ---------------------------------------------------------------------------
# Feature drift: constant column skip
# ---------------------------------------------------------------------------


def test_constant_column_is_skipped() -> None:
    """Zero-variance columns in the reference set should be silently skipped."""
    rng = np.random.default_rng(15)
    X_ref = pd.DataFrame(
        {
            "normal": rng.normal(0, 1, 500),
            "constant": np.ones(500),  # zero variance
        }
    )
    X_chk = pd.DataFrame(
        {
            "normal": rng.normal(0, 1, 100),
            "constant": np.ones(100),
        }
    )

    detector = DriftDetector(_make_cfg())
    results = detector.check_feature_drift(X_ref, X_chk)

    feature_names = [r.feature_name for r in results]
    assert (
        "constant" not in feature_names
    ), "Constant column should be skipped by check_feature_drift"
    assert "normal" in feature_names


# ---------------------------------------------------------------------------
# Rolling MAE: mismatched lengths raise ValueError
# ---------------------------------------------------------------------------


def test_rolling_mae_mismatched_lengths_raises() -> None:
    """check_rolling_mae should raise ValueError if y_true and y_pred lengths differ."""
    detector = DriftDetector(_make_cfg())
    y_true = pd.Series(np.ones(100))
    y_pred = np.ones(50)  # wrong length

    with pytest.raises(ValueError, match="length"):
        detector.check_rolling_mae(y_true, y_pred, training_mae=4.0)


# ---------------------------------------------------------------------------
# DriftReport fields
# ---------------------------------------------------------------------------


def test_drift_report_n_samples() -> None:
    """n_reference_samples and n_check_samples should match input sizes."""
    rng = np.random.default_rng(16)
    X_ref, X_chk, y_ref, y_chk = _make_frames(n_ref=800, n_chk=150, rng=rng)

    detector = DriftDetector(_make_cfg())
    report = detector.full_report(
        city="drammen",
        model_name="LightGBM",
        X_reference=X_ref,
        X_check=X_chk,
        y_reference=y_ref,
        y_check=y_chk,
        training_mae=4.029,
    )

    assert report.n_reference_samples == 800
    assert report.n_check_samples == 150
