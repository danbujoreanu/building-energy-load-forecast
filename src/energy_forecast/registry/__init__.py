"""energy_forecast.registry
==========================
File-backed model registry with lineage tracking, promotion gating, and rollback.

Public API::

    from energy_forecast.registry import (
        ModelRegistry,
        ModelVersion,
        ModelMetrics,
        ModelStatus,
        RegistryError,
        ModelRegressionError,
    )

Typical usage::

    from pathlib import Path
    from energy_forecast.registry import ModelRegistry, ModelVersion, ModelMetrics, ModelStatus

    registry = ModelRegistry(Path("outputs/registry"))

    version = registry.register(
        ModelVersion(
            version_id="",            # auto-generated
            city="drammen",
            model_name="LightGBM",
            artifact_path="/abs/path/model.joblib",
            trained_at="2026-04-15T16:00:00+00:00",
            git_commit="",            # auto-populated from git HEAD
            feature_names=["lag_1h", "hour_sin", "temp"],
            train_metrics=ModelMetrics(MAE=3.2, RMSE=5.1, R2=0.98),
            val_metrics=ModelMetrics(MAE=3.8, RMSE=6.0, R2=0.97),
            test_metrics=ModelMetrics(MAE=4.0, RMSE=6.5, R2=0.975),
            status=ModelStatus.CANDIDATE,   # forced to CANDIDATE by register()
            config_snapshot={"n_estimators": 800},
        )
    )

    active = registry.promote_to_active(version.version_id)
    print(registry.summary())
"""

from energy_forecast.registry.model_registry import (
    ModelMetrics,
    ModelRegressionError,
    ModelRegistry,
    ModelStatus,
    ModelVersion,
    RegistryError,
)

__all__ = [
    "ModelRegistry",
    "ModelVersion",
    "ModelMetrics",
    "ModelStatus",
    "RegistryError",
    "ModelRegressionError",
]
