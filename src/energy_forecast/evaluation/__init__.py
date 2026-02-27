"""Model evaluation: consistent metrics across all model types."""

from .metrics import evaluate, compare_models, metrics_to_dataframe

__all__ = ["evaluate", "compare_models", "metrics_to_dataframe"]
