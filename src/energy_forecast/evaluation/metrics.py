"""
evaluation.metrics
==================
Consistent metric computation for every model in the project.

All metrics are computed both **globally** (across all buildings) and
**per-building**, giving a complete picture of model performance.

Metrics
-------
MAE              Mean Absolute Error           — primary metric
RMSE             Root Mean Squared Error       — penalises large errors
MAPE             Mean Absolute Percentage Err  — scale-free, interpretable as %
R²               Coefficient of Determination  — variance explained
Daily Peak MAE   MAE of daily maximum values   — grid operator metric (MISS-1)

Public API
----------
    evaluate(y_true, y_pred, model_name, building_ids, timestamps) -> dict
    daily_peak_mae(y_true, y_pred, timestamps, building_ids) -> float
    save_per_building_metrics(results_list, output_path) -> pd.DataFrame
    compare_models(results_dict) -> pd.DataFrame
    metrics_to_dataframe(results_list) -> pd.DataFrame
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logger = logging.getLogger(__name__)

# MAPE is undefined when y_true = 0 (metering artefacts in hourly data).
# Standard practice in energy forecasting literature: exclude zero-target
# rows from the MAPE denominator rather than adding an infinitesimally small
# epsilon, which inflates MAPE to millions of percent.
_MAPE_MIN_TRUE = 0.1   # kWh — rows below this threshold are excluded from MAPE


def evaluate(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray,
    model_name: str = "model",
    building_ids: np.ndarray | pd.Series | None = None,
    timestamps: pd.Index | pd.Series | None = None,
    city: str = "",
) -> dict[str, Any]:
    """Compute MAE, RMSE, MAPE, R² globally and optionally per building.

    Handles both H+1 (1-D) and H+24 (2-D) prediction shapes:
      - H+1 : y_pred shape (n_samples,)   → single-step evaluation
      - H+24: y_pred shape (n_samples, 24) → multi-horizon evaluation;
              global MAE is averaged over all 24 steps; per-horizon MAE
              is stored under key ``horizon_mae`` (list of 24 floats).

    Parameters
    ----------
    y_true : Ground-truth electricity consumption.
    y_pred : Model predictions.  1-D for H+1; 2-D (n_samples, H) for H+24.
    model_name : Label used in the returned dict.
    building_ids : If provided, also computes per-building metrics.
    timestamps : If provided alongside building_ids, also computes Daily Peak MAE.

    Returns
    -------
    dict with keys: model, MAE, RMSE, MAPE, R2, n_samples,
                    horizon_mae (H+24 only), daily_peak_mae (if timestamps given),
                    per_building (if building_ids given)
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    # ── Multi-horizon (H+24) handling ────────────────────────────────────────
    if y_pred.ndim == 2:
        horizon = y_pred.shape[1]
        # For global metrics: flatten both arrays (all 24 steps, all samples)
        y_true_eval = y_true.flatten() if y_true.ndim == 2 else y_true
        y_pred_flat = y_pred.flatten()
        # Align lengths — y_true may be the full 1-D test series
        if len(y_true_eval) != len(y_pred_flat):
            # Use the leading n_samples from y_true to build the matrix
            n_samples = y_pred.shape[0]
            y_true_matrix = np.stack([y_true_eval[i:i + horizon] for i in range(n_samples)])
            y_true_eval = y_true_matrix.flatten()
        # Per-horizon MAE (crucial for paper: shows error growth from H+1 to H+24)
        if y_true.ndim == 2 and y_true.shape == y_pred.shape:
            horizon_mae = [float(_mae(y_true[:, h], y_pred[:, h])) for h in range(horizon)]
        else:
            horizon_mae = None  # shape mismatch — skip per-horizon
        result: dict[str, Any] = {
            "model":       model_name,
            "MAE":         _mae(y_true_eval, y_pred_flat),
            "RMSE":        _rmse(y_true_eval, y_pred_flat),
            "MAPE":        _mape(y_true_eval, y_pred_flat),
            "R2":          _r2(y_true_eval, y_pred_flat),
            "n_samples":   len(y_pred),
            "horizon":     horizon,
            "horizon_mae": horizon_mae,
        }
        if city:
            result["city"] = city
        _log_result(result)
        return result

    # ── Standard H+1 evaluation ──────────────────────────────────────────────
    result = {
        "model":     model_name,
        "MAE":       _mae(y_true, y_pred),
        "RMSE":      _rmse(y_true, y_pred),
        "MAPE":      _mape(y_true, y_pred),
        "R2":        _r2(y_true, y_pred),
        "n_samples": len(y_true),
    }
    if city:
        result["city"] = city

    # ── Daily Peak MAE (MISS-1) ───────────────────────────────────────────────
    if building_ids is not None and timestamps is not None:
        try:
            result["daily_peak_mae"] = daily_peak_mae(
                y_true, y_pred, timestamps, building_ids
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("daily_peak_mae skipped for %s: %s", model_name, exc)

    # ── Per-building metrics (MISS-2) ─────────────────────────────────────────
    if building_ids is not None:
        building_ids_arr = np.asarray(building_ids)
        per_building: list[dict] = []
        for bid in np.unique(building_ids_arr):
            mask = building_ids_arr == bid
            if mask.sum() < 2:
                continue
            pb_entry = {
                "building_id": int(bid),
                "MAE":       _mae(y_true[mask], y_pred[mask]),
                "RMSE":      _rmse(y_true[mask], y_pred[mask]),
                "MAPE":      _mape(y_true[mask], y_pred[mask]),
                "R2":        _r2(y_true[mask], y_pred[mask]),
                "n_samples": int(mask.sum()),
            }
            if city:
                pb_entry["city"] = city
            per_building.append(pb_entry)
        result["per_building"] = per_building

    _log_result(result)
    return result


def daily_peak_mae(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray,
    timestamps: pd.Index | pd.Series,
    building_ids: np.ndarray | pd.Series,
) -> float:
    """MAE of daily peak load predictions (MISS-1).

    For each (building_id, date), finds the daily maximum of y_true and the
    daily maximum of y_pred, then computes MAE between these two series.

    Grid operators care about peak demand for capacity planning and grid
    stability.  A model that predicts average load well but misses the daily
    peak is of limited operational value.

    Parameters
    ----------
    y_true : Ground-truth hourly electricity consumption.
    y_pred : Model hourly predictions.
    timestamps : DatetimeIndex or Series of timestamps aligned with y_true/y_pred.
    building_ids : Array of building IDs aligned with y_true/y_pred.

    Returns
    -------
    float : MAE between daily max(y_true) and daily max(y_pred), in kWh.
    """
    ts = pd.DatetimeIndex(timestamps) if not isinstance(timestamps, pd.DatetimeIndex) else timestamps
    df = pd.DataFrame({
        "y_true":      np.asarray(y_true, dtype=float),
        "y_pred":      np.asarray(y_pred, dtype=float),
        "building_id": np.asarray(building_ids),
        "date":        ts.normalize(),          # floor to midnight — date bucket
    })
    daily_true = df.groupby(["building_id", "date"])["y_true"].max()
    daily_pred = df.groupby(["building_id", "date"])["y_pred"].max()
    # Inner join ensures both series cover identical (building, date) pairs
    aligned = pd.concat([daily_true.rename("true"), daily_pred.rename("pred")], axis=1).dropna()
    return float(mean_absolute_error(aligned["true"].values, aligned["pred"].values))


def save_per_building_metrics(
    results: list[dict[str, Any]],
    output_path: str | Path,
) -> pd.DataFrame:
    """Save per-building metrics for all models to a CSV file (MISS-2).

    Enables statements like: "LightGBM performed best on Schools (MAE 1.2 kWh)
    while XGBoost performed best on Nursing Homes (MAE 1.4 kWh)."

    Parameters
    ----------
    results : List of dicts returned by evaluate() with building_ids provided.
    output_path : Destination CSV path (e.g. outputs/results/per_building_metrics.csv).

    Returns
    -------
    pd.DataFrame with columns: model, building_id, MAE, RMSE, MAPE, R2, n_samples.
    """
    rows: list[dict] = []
    for r in results:
        if "per_building" not in r:
            logger.debug("No per_building data for model '%s' — skipping.", r.get("model", "?"))
            continue
        for pb in r["per_building"]:
            row_dict = {
                "model":       r["model"],
                "building_id": pb["building_id"],
                "MAE":         round(pb["MAE"],  4),
                "RMSE":        round(pb["RMSE"], 4),
                "MAPE":        round(pb["MAPE"], 4),
                "R2":          round(pb["R2"],   4),
                "n_samples":   pb["n_samples"],
            }
            if "city" in pb:
                row_dict["city"] = pb["city"]
            rows.append(row_dict)

    if not rows:
        logger.warning("save_per_building_metrics: no per_building data in any result.")
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values(["building_id", "MAE"]).reset_index(drop=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(
        "Per-building metrics saved → %s  (%d buildings × %d models)",
        output_path,
        df["building_id"].nunique(),
        df["model"].nunique(),
    )
    return df


def compare_models(results: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert a list of evaluate() outputs into a comparison DataFrame.

    Sorted by primary metric (MAE ascending).  Includes Daily Peak MAE column
    when available (requires timestamps + building_ids passed to evaluate()).
    """
    rows = []
    for r in results:
        row = {
            "Model":    r["model"],
            "MAE":      round(r["MAE"],  4),
            "RMSE":     round(r["RMSE"], 4),
            "MAPE":     round(r["MAPE"], 4),
            "R²":       round(r["R2"],   4),
            "n_samples": r["n_samples"],
        }
        if "daily_peak_mae" in r:
            row["Daily_Peak_MAE"] = round(r["daily_peak_mae"], 4)
        rows.append(row)
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
    """MAPE excluding rows where y_true < _MAPE_MIN_TRUE (metering artefacts)."""
    mask = y_true >= _MAPE_MIN_TRUE
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(r2_score(y_true, y_pred))


def _log_result(r: dict) -> None:
    peak_str = (
        f" | DailyPeak_MAE={r['daily_peak_mae']:7.3f}"
        if "daily_peak_mae" in r else ""
    )
    logger.info(
        "%-22s | MAE=%7.3f | RMSE=%7.3f | MAPE=%6.2f%% | R²=%6.4f%s",
        r["model"], r["MAE"], r["RMSE"], r["MAPE"], r["R2"], peak_str,
    )
