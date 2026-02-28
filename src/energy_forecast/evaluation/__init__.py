"""Model evaluation: consistent metrics + SHAP explainability."""

from .metrics import evaluate, compare_models, metrics_to_dataframe
from .explainability import SHAPExplainer, explain_model

__all__ = [
    "evaluate",
    "compare_models",
    "metrics_to_dataframe",
    "SHAPExplainer",
    "explain_model",
]
