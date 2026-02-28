"""
visualization.plots
===================
All plotting functions used across notebooks and scripts.
Every function saves to ``outputs/figures/`` if ``save_path`` is provided,
and optionally displays inline (Jupyter compatible).

Style: seaborn-v0_8, consistent colour palette, publication-ready sizing.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")   # non-interactive backend — safe for scripts & CI
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

logger = logging.getLogger(__name__)

# ── Global style ──────────────────────────────────────────────────────────────
sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
FIGURE_DPI = 150
FIGURE_SIZE = (12, 5)


def _save_or_show(fig: plt.Figure, save_path: str | Path | None, tight: bool = True) -> None:
    if tight:
        fig.tight_layout()
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=FIGURE_DPI, bbox_inches="tight")
        logger.info("Figure saved → %s", save_path)
        plt.close(fig)
    else:
        plt.show()


# ---------------------------------------------------------------------------
# EDA plots
# ---------------------------------------------------------------------------

def plot_building_profiles(
    timeseries: pd.DataFrame,
    building_ids: list[int] | None = None,
    target: str = "Electricity_Imported_Total_kWh",
    resample: str = "1D",
    save_path: str | Path | None = None,
) -> None:
    """Daily electricity profiles for selected buildings."""
    building_ids = building_ids or (
        timeseries.index.get_level_values("building_id").unique()[:6].tolist()
    )
    fig, axes = plt.subplots(
        len(building_ids), 1,
        figsize=(FIGURE_SIZE[0], 3 * len(building_ids)),
        sharex=True,
    )
    if len(building_ids) == 1:
        axes = [axes]

    for ax, bid in zip(axes, building_ids):
        series = timeseries.xs(bid, level="building_id")[target]
        series.resample(resample).mean().plot(ax=ax, linewidth=0.8)
        ax.set_title(f"Building {bid} — Daily Mean Electricity (kWh)")
        ax.set_ylabel("kWh")
        ax.xaxis.set_major_locator(mticker.MaxNLocator(8))

    fig.suptitle("Building Electricity Profiles", fontsize=14, fontweight="bold", y=1.01)
    _save_or_show(fig, save_path)


def plot_temperature_sensitivity(
    timeseries: pd.DataFrame,
    target: str = "Electricity_Imported_Total_kWh",
    temp_col: str = "Temperature_Outdoor_C",
    sample_n: int = 5000,
    save_path: str | Path | None = None,
) -> None:
    """Scatter plot of electricity vs outdoor temperature."""
    df = timeseries[[target, temp_col]].dropna()
    if len(df) > sample_n:
        df = df.sample(sample_n, random_state=42)

    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    ax.scatter(df[temp_col], df[target], alpha=0.3, s=10, color="steelblue")
    ax.set_xlabel("Outdoor Temperature (°C)")
    ax.set_ylabel("Electricity Imported (kWh)")
    ax.set_title("Temperature Sensitivity of Electricity Consumption")

    # Trend line
    z = np.polyfit(df[temp_col].dropna(), df[target].dropna(), 2)
    p = np.poly1d(z)
    x_line = np.linspace(df[temp_col].min(), df[temp_col].max(), 200)
    ax.plot(x_line, p(x_line), "r--", linewidth=2, label="Quadratic trend")
    ax.legend()
    _save_or_show(fig, save_path)


def plot_seasonal_patterns(
    timeseries: pd.DataFrame,
    target: str = "Electricity_Imported_Total_kWh",
    save_path: str | Path | None = None,
) -> None:
    """Box plots of electricity by month and hour-of-day."""
    df = timeseries[[target]].copy().dropna()
    ts_idx = df.index.get_level_values("timestamp")
    df["month"]       = ts_idx.month
    df["hour_of_day"] = ts_idx.hour

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5))

    sns.boxplot(data=df, x="month", y=target, ax=ax1, palette="Blues", fliersize=2)
    ax1.set_title("Monthly Distribution")
    ax1.set_xlabel("Month")
    ax1.set_ylabel("kWh")

    sns.boxplot(data=df, x="hour_of_day", y=target, ax=ax2, palette="Oranges", fliersize=2)
    ax2.set_title("Hourly Distribution (all months)")
    ax2.set_xlabel("Hour of Day")
    ax2.set_ylabel("kWh")

    fig.suptitle("Seasonal & Diurnal Electricity Patterns", fontsize=14, fontweight="bold")
    _save_or_show(fig, save_path)


def plot_missing_data(
    timeseries: pd.DataFrame,
    save_path: str | Path | None = None,
) -> None:
    """Missing data heatmap using missingno."""
    try:
        import missingno as msno
    except ImportError:
        logger.warning("missingno not installed — skipping missing data plot")
        return

    # Sample for readability
    sample = timeseries.sample(min(500, len(timeseries)), random_state=42)
    fig = plt.figure(figsize=FIGURE_SIZE)
    ax = fig.add_subplot(111)
    msno.matrix(sample, ax=ax, sparkline=False)
    ax.set_title("Missing Data Pattern (random sample of 500 rows)")
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# Feature importance
# ---------------------------------------------------------------------------

def plot_feature_importance(
    feature_names: list[str],
    importances: np.ndarray,
    top_n: int = 20,
    model_name: str = "LightGBM",
    save_path: str | Path | None = None,
) -> None:
    """Horizontal bar chart of feature importances."""
    imp_series = pd.Series(importances, index=feature_names).nlargest(top_n)
    fig, ax = plt.subplots(figsize=(10, top_n * 0.4 + 1))
    imp_series.sort_values().plot(kind="barh", ax=ax, color="steelblue", edgecolor="white")
    ax.set_title(f"Top {top_n} Feature Importances — {model_name}")
    ax.set_xlabel("Importance")
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# Training history (deep learning)
# ---------------------------------------------------------------------------

def plot_training_history(
    history: Any,
    model_name: str = "Model",
    save_path: str | Path | None = None,
) -> None:
    """Training and validation loss curves from a Keras History object."""
    fig, ax = plt.subplots(figsize=(10, 4))
    epochs = range(1, len(history.history["loss"]) + 1)
    ax.plot(epochs, history.history["loss"],     label="Train loss",      linewidth=2)
    ax.plot(epochs, history.history["val_loss"], label="Val loss",        linewidth=2, linestyle="--")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("MSE Loss")
    ax.set_title(f"{model_name} — Training History")
    ax.legend()
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# Prediction quality
# ---------------------------------------------------------------------------

def plot_predictions_vs_actual(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray,
    model_name: str = "Model",
    sample_n: int = 3000,
    save_path: str | Path | None = None,
) -> None:
    """Scatter of predicted vs actual values with a 45-degree reference line."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    if len(y_true) > sample_n:
        idx = np.random.default_rng(42).choice(len(y_true), sample_n, replace=False)
        y_true, y_pred = y_true[idx], y_pred[idx]

    vmin = min(y_true.min(), y_pred.min())
    vmax = max(y_true.max(), y_pred.max())

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(y_true, y_pred, alpha=0.3, s=12, color="steelblue")
    ax.plot([vmin, vmax], [vmin, vmax], "r--", linewidth=2, label="Perfect prediction")
    ax.set_xlabel("Actual (kWh)")
    ax.set_ylabel("Predicted (kWh)")
    ax.set_title(f"{model_name} — Predicted vs Actual")
    ax.legend()
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# Model comparison
# ---------------------------------------------------------------------------

def plot_model_comparison(
    comparison_df: pd.DataFrame,
    metric: str = "MAE",
    save_path: str | Path | None = None,
) -> None:
    """Horizontal bar chart comparing all models on a chosen metric."""
    df = comparison_df.sort_values(metric, ascending=True)
    colours = ["#2ecc71" if i == 0 else "steelblue" for i in range(len(df))]

    fig, ax = plt.subplots(figsize=(10, max(4, len(df) * 0.6)))
    bars = ax.barh(df["Model"], df[metric], color=colours, edgecolor="white")
    ax.bar_label(bars, fmt="%.3f", padding=4)
    ax.set_xlabel(metric)
    ax.set_title(f"Model Comparison — {metric} (lower is better)")
    ax.invert_yaxis()
    _save_or_show(fig, save_path)
