"""Model evaluation: consistent metrics + SHAP explainability."""

from .explainability import SHAPExplainer, explain_model
from .metrics import (
    compare_models,
    daily_peak_mae,
    evaluate,
    metrics_to_dataframe,
    save_per_building_metrics,
)

__all__ = [
    "evaluate",
    "compare_models",
    "metrics_to_dataframe",
    "daily_peak_mae",
    "save_per_building_metrics",
    "SHAPExplainer",
    "explain_model",
]
