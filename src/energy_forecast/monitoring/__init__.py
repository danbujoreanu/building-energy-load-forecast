"""
energy_forecast.monitoring
==========================
Model monitoring and drift detection for the LightGBM load-forecasting pipeline.

Detects covariate drift (feature distribution shift) and concept drift
(target shift + MAE degradation) between a reference dataset and a recent
check dataset.

Public API
----------
    DriftDetector   — main class; construct with cfg dict
    DriftReport     — full drift report dataclass (JSON + Markdown output)
    FeatureDriftResult  — per-feature KS + PSI result
    TargetDriftResult   — target distribution drift result
    RollingMAEResult    — rolling MAE vs training baseline result
    DriftSeverity       — OK / WARNING / CRITICAL enum

Quick start::

    from energy_forecast.monitoring import DriftDetector

    detector = DriftDetector(cfg)
    report = detector.full_report(
        city="drammen",
        model_name="LightGBM",
        X_reference=splits["X_train"],
        X_check=X_recent,
        y_reference=splits["y_train"],
        y_check=y_recent,
        training_mae=4.029,
        y_pred=y_pred_recent,
    )
    print(report.to_markdown())
    report_json = report.to_json()
"""

from energy_forecast.monitoring.drift_detector import (
    DriftDetector,
    DriftReport,
    DriftSeverity,
    FeatureDriftResult,
    RollingMAEResult,
    TargetDriftResult,
)

__all__ = [
    "DriftDetector",
    "DriftReport",
    "DriftSeverity",
    "FeatureDriftResult",
    "RollingMAEResult",
    "TargetDriftResult",
]
