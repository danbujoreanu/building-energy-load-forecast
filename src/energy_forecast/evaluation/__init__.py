"""Model evaluation: consistent metrics + SHAP explainability."""

from .metrics import evaluate, compare_models, metrics_to_dataframe, daily_peak_mae, save_per_building_metrics
from .explainability import SHAPExplainer, explain_model

__all__ = [
    "evaluate",
    "compare_models",
    "metrics_to_dataframe",
    "daily_peak_mae",
    "save_per_building_metrics",
    "SHAPExplainer",
    "explain_model",
]
