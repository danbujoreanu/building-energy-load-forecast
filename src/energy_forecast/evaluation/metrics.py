"""
evaluation.metrics
==================
Consistent metric computation for every model in the project.

All metrics are computed both **globally** (across all buildings) and
**per-building**, giving a complete picture of model performance.

Metrics
-------
MAE   Mean Absolute Error           — primary metric (config: evaluation.primary_metric)
RMSE  Root Mean Squared Error       — penalises large errors
MAPE  Mean Absolute Percentage Err  — scale-free, interpretable as %
R²    Coefficient of Determination  — variance explained

Public API
----------
    evaluate(y_true, y_pred, model_name, building_ids) -> dict
    compare_models(results_dict) -> pd.DataFrame
    metrics_to_dataframe(results_list) -> pd.DataFrame
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logger = logging.getLogger(__name__)

# Small epsilon to avoid divide-by-zero in MAPE
_EPS = 1e-8


def evaluate(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray,
    model_name: str = "model",
    building_ids: np.ndarray | pd.Series | None = None,
) -> dict[str, Any]:
    """Compute MAE, RMSE, MAPE, R² globally and optionally per building.

    Parameters
    ----------
    y_true : Ground-truth electricity consumption.
    y_pred : Model predictions (same length as y_true).
    model_name : Label used in the returned dict.
    building_ids : If provided, also computes per-building metrics.

    Returns
    -------
    dict with keys: model, MAE, RMSE, MAPE, R2, per_building (optional)
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    result: dict[str, Any] = {
        "model": model_name,
        "MAE":   _mae(y_true, y_pred),
        "RMSE":  _rmse(y_true, y_pred),
        "MAPE":  _mape(y_true, y_pred),
        "R2":    _r2(y_true, y_pred),
        "n_samples": len(y_true),
    }

    if building_ids is not None:
        building_ids = np.asarray(building_ids)
        per_building: list[dict] = []
        for bid in np.unique(building_ids):
            mask = building_ids == bid
            if mask.sum() < 2:
                continue
            per_building.append({
                "building_id": int(bid),
                "MAE":  _mae(y_true[mask], y_pred[mask]),
                "RMSE": _rmse(y_true[mask], y_pred[mask]),
                "MAPE": _mape(y_true[mask], y_pred[mask]),
                "R2":   _r2(y_true[mask], y_pred[mask]),
                "n_samples": int(mask.sum()),
            })
        result["per_building"] = per_building

    _log_result(result)
    return result


def compare_models(results: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert a list of evaluate() outputs into a comparison DataFrame.

    Sorted by primary metric (MAE ascending).
    """
    rows = [
        {
            "Model": r["model"],
            "MAE":   round(r["MAE"],  4),
            "RMSE":  round(r["RMSE"], 4),
            "MAPE":  round(r["MAPE"], 4),
            "R²":    round(r["R2"],   4),
            "n_samples": r["n_samples"],
        }
        for r in results
    ]
    df = pd.DataFrame(rows).sort_values("MAE").reset_index(drop=True)
    df.index += 1   # 1-indexed ranking
    return df


def metrics_to_dataframe(results: list[dict[str, Any]]) -> pd.DataFrame:
    """Alias for compare_models for external scripts."""
    return compare_models(results)


# ---------------------------------------------------------------------------
# Private metric helpers
# ---------------------------------------------------------------------------

def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(mean_absolute_error(y_true, y_pred))


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs((y_true - y_pred) / (np.abs(y_true) + _EPS))) * 100)


def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(r2_score(y_true, y_pred))


def _log_result(r: dict) -> None:
    logger.info(
        "%-22s | MAE=%7.3f | RMSE=%7.3f | MAPE=%6.2f%% | R²=%6.4f",
        r["model"], r["MAE"], r["RMSE"], r["MAPE"], r["R2"],
    )
