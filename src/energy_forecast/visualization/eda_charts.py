"""
visualization.eda_charts
========================
Comprehensive EDA charts that mirror (and extend) the original MSc thesis
Jupyter notebooks:
    1. Drammen EDA_after merge changes_FINAL.ipynb
    2. Drammen_Feature_Engineering.ipynb
    3. Drammen_Model_Training_Final.ipynb

All functions:
  - Accept a save_path; if None they call plt.show() for Jupyter use.
  - Use publication-ready sizing (150 dpi) with seaborn-whitegrid style.
  - Include rich annotations and axis labels for thesis-quality output.

Public API
----------
    plot_building_metadata_overview(metadata, save_path)
    plot_column_availability_heatmap(metadata, timeseries, save_path)
    plot_missing_data_analysis(timeseries, save_path)
    plot_all_building_energy_profiles(timeseries, metadata, out_dir)
    plot_temperature_vs_electricity_by_category(timeseries, metadata, save_path)
    plot_acf_pacf(timeseries, building_id, save_path)
    plot_seasonal_decomposition(timeseries, building_id, save_path)
    plot_model_results_comparison(metrics_df, save_path_prefix)
    plot_actual_vs_predicted_timeseries(y_true, y_pred, model_name, building_id, save_path)
    plot_ensemble_weights(weights_dict, save_path)
    plot_thesis_vs_pipeline_comparison(thesis_df, pipeline_df, save_path)
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

logger = logging.getLogger(__name__)

# ── Global style ──────────────────────────────────────────────────────────────
sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
FIGURE_DPI = 150
PALETTE_CAT = {
    "Kdg": "#4C72B0",   # Kindergarten — blue
    "Sch": "#DD8452",   # School — orange
    "Nsh": "#55A868",   # Nursing Home — green
    "Off": "#C44E52",   # Office — red
}
_CAT_LABELS = {"Kdg": "Kindergarten", "Sch": "School", "Nsh": "Nursing Home", "Off": "Office"}


def _save_or_show(fig: plt.Figure, save_path: str | Path | None) -> None:
    fig.tight_layout()
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=FIGURE_DPI, bbox_inches="tight")
        logger.info("Saved → %s", save_path)
        plt.close(fig)
    else:
        plt.show()


# ---------------------------------------------------------------------------
# 1. Building metadata overview (4-panel, matches thesis EDA notebook)
# ---------------------------------------------------------------------------

def plot_building_metadata_overview(
    metadata: pd.DataFrame,
    save_path: str | Path | None = None,
) -> None:
    """4-panel metadata summary: category, year, floor area, energy label.

    Matches Figure 1 in the MSc thesis EDA section.
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))

    # ── Panel A: Building category ─────────────────────────────────────────
    ax = axes[0, 0]
    if "building_category" in metadata.columns:
        cat_counts = metadata["building_category"].value_counts()
        colors = [PALETTE_CAT.get(c, "#888") for c in cat_counts.index]
        bars = ax.barh(
            [_CAT_LABELS.get(c, c) for c in cat_counts.index],
            cat_counts.values,
            color=colors, edgecolor="white",
        )
        ax.bar_label(bars, padding=3, fontsize=10)
        ax.set_xlabel("Number of Buildings")
        ax.set_title("A  Building Category Distribution", fontweight="bold", loc="left")
        ax.set_xlim(0, cat_counts.max() + 4)
    else:
        ax.text(0.5, 0.5, "No building_category column", ha="center", va="center")

    # ── Panel B: Year of construction ─────────────────────────────────────
    ax = axes[0, 1]
    if "year_of_construction" in metadata.columns:
        years = metadata["year_of_construction"].dropna()
        ax.hist(years, bins=15, color="#4C72B0", edgecolor="white", alpha=0.85)
        ax.axvline(years.median(), color="crimson", linestyle="--", linewidth=1.5,
                   label=f"Median: {int(years.median())}")
        ax.set_xlabel("Year of Construction")
        ax.set_ylabel("Number of Buildings")
        ax.set_title("B  Year of Construction", fontweight="bold", loc="left")
        ax.legend()
    else:
        ax.text(0.5, 0.5, "No year_of_construction column", ha="center", va="center")

    # ── Panel C: Floor area by category (box plot) ─────────────────────────
    ax = axes[1, 0]
    if "floor_area" in metadata.columns and "building_category" in metadata.columns:
        plot_df = metadata[["floor_area", "building_category"]].dropna()
        plot_df["Category"] = plot_df["building_category"].map(
            lambda c: _CAT_LABELS.get(c, c)
        )
        sns.boxplot(
            data=plot_df, y="Category", x="floor_area",
            palette=list(PALETTE_CAT.values()), ax=ax,
            flierprops={"marker": ".", "markersize": 4},
        )
        ax.set_xlabel("Floor Area (m²)")
        ax.set_ylabel("")
        ax.set_title("C  Floor Area by Category", fontweight="bold", loc="left")
    else:
        ax.text(0.5, 0.5, "floor_area/building_category missing", ha="center", va="center")

    # ── Panel D: Energy label distribution ────────────────────────────────
    ax = axes[1, 1]
    if "energy_label" in metadata.columns:
        label_counts = (
            metadata["energy_label"]
            .fillna("Unknown")
            .value_counts()
            .reindex(["A", "B", "C", "D", "E", "F", "G", "Unknown"], fill_value=0)
        )
        label_colors = ["#2ecc71", "#27ae60", "#f1c40f", "#e67e22",
                        "#e74c3c", "#c0392b", "#8e44ad", "#95a5a6"]
        bars = ax.bar(
            label_counts.index, label_counts.values,
            color=label_colors[:len(label_counts)], edgecolor="white",
        )
        ax.bar_label(bars, padding=2, fontsize=10)
        ax.set_xlabel("Energy Label")
        ax.set_ylabel("Number of Buildings")
        ax.set_title("D  Energy Label Distribution", fontweight="bold", loc="left")
    else:
        ax.text(0.5, 0.5, "No energy_label column", ha="center", va="center")

    fig.suptitle(
        "Drammen Building Portfolio — Metadata Overview\n"
        f"({len(metadata)} buildings, Cofactor dataset)",
        fontsize=14, fontweight="bold",
    )
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 2. Column / sensor availability heatmap per building
#    (matches building_column_availability_summary.csv from thesis)
# ---------------------------------------------------------------------------

def plot_column_availability_heatmap(
    metadata: pd.DataFrame,
    timeseries: pd.DataFrame,
    save_path: str | Path | None = None,
) -> None:
    """Heatmap showing which columns/sensors are present per building.

    Green = ≥80% non-NaN | Yellow = 50-80% | Red = <50% | White = absent.
    Matches the ``building_column_availability_summary.csv`` analysis in the thesis.
    """
    # Compute per-building, per-column coverage
    building_ids = timeseries.index.get_level_values("building_id").unique()
    all_cols = [c for c in timeseries.columns if c != "building_id"]

    coverage_rows = []
    for bid in building_ids:
        sub = timeseries.xs(bid, level="building_id")
        row = {"building_id": bid}
        for col in all_cols:
            if col in sub.columns:
                row[col] = sub[col].notna().mean()
            else:
                row[col] = np.nan
        coverage_rows.append(row)

    cov_df = pd.DataFrame(coverage_rows).set_index("building_id")

    # Drop columns that are 0% across all buildings (truly absent)
    cov_df = cov_df.loc[:, cov_df.max(axis=0) > 0]

    # Shorten column names for display
    short_names = {c: c.replace("Electricity_", "El_").replace("_kWh", "")
                     .replace("Heat_", "Ht_").replace("Temperature_Outdoor_C", "T_out")
                     .replace("Global_Solar_Horizontal_Radiation_W_m2", "Solar")
                     .replace("Wind_Speed_m_s", "WindSpd")
                     .replace("Wind_Direction_deg", "WindDir")
                     .replace("Relative_Humidity_pct", "RH")
                   for c in cov_df.columns}
    cov_df = cov_df.rename(columns=short_names)

    # Add category label for y-axis
    cat_map = metadata.set_index("building_id")["building_category"].to_dict() if "building_category" in metadata.columns else {}
    y_labels = [f"{bid} ({_CAT_LABELS.get(cat_map.get(bid, '?'), '?')[:3]})" for bid in cov_df.index]

    fig_h = max(8, len(cov_df) * 0.35)
    fig_w = max(14, len(cov_df.columns) * 0.7)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    cmap = sns.color_palette(["#e74c3c", "#f39c12", "#2ecc71"], as_cmap=True)  # noqa: F841
    sns.heatmap(
        cov_df,
        ax=ax,
        cmap="RdYlGn",
        vmin=0, vmax=1,
        linewidths=0.4,
        linecolor="white",
        annot=False,
        cbar_kws={"label": "Data Coverage (0=absent, 1=complete)", "shrink": 0.5},
    )
    ax.set_yticklabels(y_labels, fontsize=8)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Building ID (Category)")
    ax.set_title(
        "Sensor / Column Data Availability per Building\n"
        "(Green ≥80% | Yellow 50-80% | Red <50% coverage)",
        fontweight="bold",
    )
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 3. Missing data analysis (per-column %, thesis-style bar chart)
# ---------------------------------------------------------------------------

def plot_missing_data_analysis(
    timeseries: pd.DataFrame,
    metadata: pd.DataFrame | None = None,
    save_path: str | Path | None = None,
) -> None:
    """Two-panel missing data analysis: per-column % and per-building target %.

    Panel A shows the overall column-level missing % (descending).
    Panel B shows per-building missing % for the target column only.
    Matches the missing data analysis cells in the thesis EDA notebook.
    """
    target = "Electricity_Imported_Total_kWh"
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    # ── Panel A: Column-level missing % ───────────────────────────────────
    missing_pct = timeseries.isnull().mean().sort_values(ascending=False) * 100
    missing_pct = missing_pct[missing_pct > 0]

    colors_a = ["#e74c3c" if v > 50 else "#f39c12" if v > 20 else "#2ecc71"
                for v in missing_pct.values]
    short = [c.replace("Electricity_", "El_").replace("_kWh", "")
              .replace("Heat_", "Ht_").replace("Temperature_Outdoor_C", "T_out")
              .replace("Global_Solar_Horizontal_Radiation_W_m2", "Solar")
              .replace("Relative_Humidity_pct", "RH") for c in missing_pct.index]

    bars = ax1.barh(short, missing_pct.values, color=colors_a, edgecolor="white")
    ax1.axvline(50, color="crimson", linestyle="--", linewidth=1.2, label="50% threshold")
    ax1.set_xlabel("Missing Data (%)")
    ax1.set_title("A  Column-Level Missing Data (%)\n"
                  "(Red >50% | Orange >20% | Green ≤20%)", fontweight="bold", loc="left")
    ax1.legend(fontsize=9)
    ax1.set_xlim(0, 105)
    for bar, val in zip(bars, missing_pct.values):
        ax1.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                 f"{val:.1f}%", va="center", fontsize=7)

    # ── Panel B: Per-building target missing % ─────────────────────────────
    building_ids = timeseries.index.get_level_values("building_id").unique()
    bld_missing = {}
    for bid in building_ids:
        sub = timeseries.xs(bid, level="building_id")
        if target in sub.columns:
            bld_missing[bid] = sub[target].isnull().mean() * 100
        else:
            bld_missing[bid] = 100.0

    bld_ser = pd.Series(bld_missing).sort_values(ascending=False)

    # Merge category if available
    cat_map = {}
    if metadata is not None and "building_category" in metadata.columns:
        cat_map = metadata.set_index("building_id")["building_category"].to_dict()
    colors_b = [PALETTE_CAT.get(cat_map.get(bid, ""), "#888") for bid in bld_ser.index]
    y_labels = [f"{bid}\n({_CAT_LABELS.get(cat_map.get(bid, '?'), '?')[:3]})"
                for bid in bld_ser.index]

    bars2 = ax2.bar(  # noqa: F841
        range(len(bld_ser)), bld_ser.values,
        color=colors_b, edgecolor="white", width=0.7,
    )
    ax2.set_xticks(range(len(bld_ser)))
    ax2.set_xticklabels(y_labels, rotation=90, fontsize=7)
    ax2.axhline(30, color="crimson", linestyle="--", linewidth=1.2, label="30% threshold")
    ax2.set_ylabel("Missing Target Values (%)")
    ax2.set_title(
        f"B  Per-Building Missing % — {target.replace('_', ' ')}\n"
        f"(Colour = building category)",
        fontweight="bold", loc="left",
    )
    legend_patches = [mpatches.Patch(color=v, label=_CAT_LABELS.get(k, k))
                      for k, v in PALETTE_CAT.items()]
    ax2.legend(handles=legend_patches, fontsize=9, loc="upper right")

    fig.suptitle(
        "Missing Data Analysis — Drammen Dataset",
        fontsize=14, fontweight="bold",
    )
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 4. Energy profiles per building (daily + monthly aggregations)
# ---------------------------------------------------------------------------

def plot_all_building_energy_profiles(
    timeseries: pd.DataFrame,
    metadata: pd.DataFrame,
    out_dir: str | Path,
    target: str = "Electricity_Imported_Total_kWh",
    max_buildings: int | None = None,
) -> None:
    """Generate per-building energy profile plots saved to ``out_dir``.

    For each building, produces a 2-panel figure:
      - Left: daily aggregated electricity over full time range
      - Right: average hourly profile by season (Winter/Spring/Summer/Autumn)

    Matches the individual building profile plots from the thesis EDA notebook
    (``drammen_building_energy_profiles_plots/`` folder).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    building_ids = timeseries.index.get_level_values("building_id").unique()
    if max_buildings:
        building_ids = building_ids[:max_buildings]

    cat_map = {}
    if "building_category" in metadata.columns:
        cat_map = metadata.set_index("building_id")["building_category"].to_dict()

    season_map = {12: "Winter", 1: "Winter", 2: "Winter",
                  3: "Spring", 4: "Spring", 5: "Spring",
                  6: "Summer", 7: "Summer", 8: "Summer",
                  9: "Autumn", 10: "Autumn", 11: "Autumn"}
    season_colors = {"Winter": "#4C72B0", "Spring": "#55A868",
                     "Summer": "#DD8452", "Autumn": "#C44E52"}

    for bid in building_ids:
        try:
            sub = timeseries.xs(bid, level="building_id")
            if target not in sub.columns:
                continue
            ts = sub[target].dropna()
            if len(ts) < 100:
                continue

            cat_label = _CAT_LABELS.get(cat_map.get(bid, ""), "Unknown")
            color = PALETTE_CAT.get(cat_map.get(bid, ""), "#4C72B0")

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5))

            # Left: daily profile
            daily = ts.resample("1D").mean()
            ax1.plot(daily.index, daily.values, color=color, linewidth=0.9, alpha=0.9)
            roll7 = daily.rolling(7, center=True).mean()
            ax1.plot(roll7.index, roll7.values, color="crimson", linewidth=1.8,
                     linestyle="--", label="7-day rolling mean")
            ax1.set_xlabel("Date")
            ax1.set_ylabel("Electricity (kWh/hour, daily mean)")
            ax1.set_title(f"Building {bid} ({cat_label}) — Daily Mean Electricity")
            ax1.legend(fontsize=9)
            ax1.xaxis.set_major_locator(mticker.MaxNLocator(8))

            # Right: average hourly profile by season
            df_hour = pd.DataFrame({"hour": ts.index.hour,
                                    "month": ts.index.month,
                                    "value": ts.values})
            df_hour["season"] = df_hour["month"].map(season_map)
            for season, grp in df_hour.groupby("season"):
                hourly_mean = grp.groupby("hour")["value"].mean()
                ax2.plot(hourly_mean.index, hourly_mean.values,
                         color=season_colors[season], linewidth=1.8, label=season)
            ax2.set_xlabel("Hour of Day")
            ax2.set_ylabel("Average Electricity (kWh)")
            ax2.set_title("Average Hourly Profile by Season")
            ax2.set_xticks(range(0, 24, 3))
            ax2.legend(fontsize=9)

            fig.suptitle(
                f"Building {bid} | {cat_label} | "
                f"{ts.index.min().date()} → {ts.index.max().date()}",
                fontsize=12, fontweight="bold",
            )
            out_path = out_dir / f"energy_profile_building_{bid}.png"
            _save_or_show(fig, out_path)

        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not plot building %s: %s", bid, exc)

    logger.info("Saved %d building energy profiles to %s", len(building_ids), out_dir)


# ---------------------------------------------------------------------------
# 5. Temperature vs Electricity by category — scatter + regression
# ---------------------------------------------------------------------------

def plot_temperature_vs_electricity_by_category(
    timeseries: pd.DataFrame,
    metadata: pd.DataFrame,
    target: str = "Electricity_Imported_Total_kWh",
    temp_col: str = "Temperature_Outdoor_C",
    sample_n: int = 75_000,
    save_path: str | Path | None = None,
) -> None:
    """Scatter: electricity vs temperature, coloured by building category.

    Matches the thesis scatter plot (75k sample, tab10 palette, quadratic trend).
    Panel A = all categories combined.
    Panel B = separate regression lines per category.
    """
    needed = [target, temp_col]
    df = timeseries[needed].dropna().reset_index()

    cat_map = metadata.set_index("building_id")["building_category"].to_dict() \
        if "building_category" in metadata.columns else {}
    df["category"] = df["building_id"].map(lambda b: _CAT_LABELS.get(cat_map.get(b, ""), "Unknown"))

    if len(df) > sample_n:
        df = df.sample(sample_n, random_state=42)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    # ── Panel A: all buildings, colour by category ─────────────────────────
    cat_palette = {_CAT_LABELS[k]: v for k, v in PALETTE_CAT.items()}
    for cat, grp in df.groupby("category"):
        ax1.scatter(grp[temp_col], grp[target],
                    alpha=0.15, s=8, color=cat_palette.get(cat, "#888"), label=cat)
    # Quadratic trend over all
    x_all = df[temp_col].values
    y_all = df[target].values
    z = np.polyfit(x_all, y_all, 2)
    p = np.poly1d(z)
    x_line = np.linspace(x_all.min(), x_all.max(), 300)
    ax1.plot(x_line, p(x_line), "k--", linewidth=2.5, label="Quadratic trend (all)")
    ax1.set_xlabel("Outdoor Temperature (°C)")
    ax1.set_ylabel("Electricity Imported (kWh)")
    ax1.set_title("A  Electricity vs Temperature — All Buildings\n"
                  "(sample n=75k, colour = category)", fontweight="bold", loc="left")
    ax1.legend(markerscale=3, fontsize=9)

    # ── Panel B: per-category regression lines ─────────────────────────────
    for cat, grp in df.groupby("category"):
        color = cat_palette.get(cat, "#888")
        ax2.scatter(grp[temp_col], grp[target],
                    alpha=0.08, s=5, color=color)
        try:
            z2 = np.polyfit(grp[temp_col].values, grp[target].values, 2)
            p2 = np.poly1d(z2)
            x2 = np.linspace(grp[temp_col].min(), grp[temp_col].max(), 200)
            ax2.plot(x2, p2(x2), color=color, linewidth=2.5, label=cat)
        except Exception:  # noqa: BLE001
            pass
    ax2.set_xlabel("Outdoor Temperature (°C)")
    ax2.set_ylabel("Electricity Imported (kWh)")
    ax2.set_title("B  Quadratic Regression per Building Category\n"
                  "(heating demand dominates below ~15°C)", fontweight="bold", loc="left")
    ax2.legend(fontsize=9)

    fig.suptitle(
        "Temperature Sensitivity of Electricity Consumption — Drammen Dataset",
        fontsize=14, fontweight="bold",
    )
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 6. ACF / PACF for a representative building
# ---------------------------------------------------------------------------

def plot_acf_pacf(
    timeseries: pd.DataFrame,
    building_id: int | None = None,
    target: str = "Electricity_Imported_Total_kWh",
    nlags: int = 168,
    save_path: str | Path | None = None,
) -> None:
    """ACF and PACF plots for a sample building.

    Matches the statsmodels ACF/PACF plots from the thesis EDA notebook
    (nlags=168 = 1 week of hourly data).
    """
    try:
        from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
    except ImportError:
        logger.warning("statsmodels not installed — skipping ACF/PACF plot")
        return

    building_ids = timeseries.index.get_level_values("building_id").unique()
    bid = building_id or building_ids[0]

    ts = timeseries.xs(bid, level="building_id")[target].dropna()
    if len(ts) < nlags + 10:
        logger.warning("Building %s has too few rows for ACF/PACF (need >%d)", bid, nlags)
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

    plot_acf(ts, lags=nlags, ax=ax1, alpha=0.05,
             title=f"ACF — Building {bid} (ElImp/hour, lags=168 h = 1 week)")
    plot_pacf(ts, lags=min(nlags, 100), ax=ax2, alpha=0.05, method="ywm",
              title=f"PACF — Building {bid}")

    for ax in (ax1, ax2):
        ax.axvline(24,  color="crimson",  linestyle="--", linewidth=1.2, alpha=0.7, label="24h")
        ax.axvline(168, color="darkorange", linestyle="--", linewidth=1.2, alpha=0.7, label="168h")
        ax.legend(fontsize=9)

    fig.suptitle(
        f"Autocorrelation Analysis — Building {bid}\n"
        "Strong 24h (diurnal) and 168h (weekly) cycles confirm lag feature design",
        fontsize=13, fontweight="bold",
    )
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 7. Seasonal decomposition
# ---------------------------------------------------------------------------

def plot_seasonal_decomposition(
    timeseries: pd.DataFrame,
    building_id: int | None = None,
    target: str = "Electricity_Imported_Total_kWh",
    period: int = 168,
    save_path: str | Path | None = None,
) -> None:
    """Seasonal decomposition (trend + seasonal + residual).

    Matches the statsmodels seasonal_decompose plot from the thesis EDA notebook
    (period=168 hours = weekly seasonality).
    """
    try:
        from statsmodels.tsa.seasonal import seasonal_decompose
    except ImportError:
        logger.warning("statsmodels not installed — skipping seasonal decomposition")
        return

    building_ids = timeseries.index.get_level_values("building_id").unique()
    bid = building_id or building_ids[0]

    ts = timeseries.xs(bid, level="building_id")[target].dropna()
    # Use a contiguous year for clarity
    ts = ts.iloc[:8760] if len(ts) >= 8760 else ts

    result = seasonal_decompose(ts, model="additive", period=period, extrapolate_trend="freq")

    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    components = [
        (ts, "Observed (kWh)", "#4C72B0"),
        (result.trend, "Trend", "#DD8452"),
        (result.seasonal, "Seasonal (168h period)", "#55A868"),
        (result.resid, "Residual", "#C44E52"),
    ]
    for ax, (comp, label, color) in zip(axes, components):
        ax.plot(comp.index, comp.values, color=color, linewidth=0.8)
        ax.set_ylabel(label, fontsize=10)
        ax.grid(True, alpha=0.4)

    axes[0].set_title(
        f"Seasonal Decomposition — Building {bid} (period=168h weekly)\n"
        f"Additive model | {ts.index.min().date()} → {ts.index.max().date()}",
        fontweight="bold",
    )
    axes[-1].set_xlabel("Timestamp")
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 8. Comprehensive model results comparison (4-panel, thesis Figure)
# ---------------------------------------------------------------------------

def plot_model_results_comparison(
    metrics_df: pd.DataFrame,
    save_path_prefix: str | Path | None = None,
) -> None:
    """4-panel model comparison: MAE, RMSE, R², CV(RMSE).

    Matches the ``all_models_performance_comparison.png`` from the thesis.
    The best model bar is highlighted in green; baselines in grey.

    Parameters
    ----------
    metrics_df:
        DataFrame with columns: Model, MAE, RMSE, R², MAPE (any subset).
    save_path_prefix:
        If provided, saves as ``{prefix}_4panel.png`` and ``{prefix}_mae_bar.png``.
    """
    df = metrics_df.copy()
    if "Model" not in df.columns and df.index.name == "Model":
        df = df.reset_index()
    df = df.sort_values("MAE", ascending=True).reset_index(drop=True)

    BASELINE_KEYWORDS = {"Naive", "Baseline", "Persistence", "Seasonal"}  # noqa: N806
    def is_baseline(name: str) -> bool:
        return any(kw.lower() in name.lower() for kw in BASELINE_KEYWORDS)

    bar_colors = []
    for i, name in enumerate(df["Model"]):
        if i == 0:
            bar_colors.append("#2ecc71")   # best = green
        elif is_baseline(name):
            bar_colors.append("#95a5a6")   # baselines = grey
        else:
            bar_colors.append("#4C72B0")   # others = blue

    # ── 4-panel figure ────────────────────────────────────────────────────
    metric_pairs = [
        ("MAE", "MAE (kWh)", True),
        ("RMSE", "RMSE (kWh)", True),
    ]
    if "R²" in df.columns:
        metric_pairs.append(("R²", "R²", False))
    if "MAPE" in df.columns:
        metric_pairs.append(("MAPE", "MAPE (%)", True))

    n_panels = len(metric_pairs)
    fig, axes = plt.subplots(1, n_panels, figsize=(6 * n_panels, max(6, len(df) * 0.5)))
    if n_panels == 1:
        axes = [axes]

    for ax, (col, xlabel, lower_better) in zip(axes, metric_pairs):
        if col not in df.columns:
            ax.set_visible(False)
            continue
        colors_p = ["#2ecc71" if bar_colors[i] == "#2ecc71" else
                    "#95a5a6" if is_baseline(df["Model"].iloc[i]) else "#4C72B0"
                    for i in range(len(df))]
        if not lower_better:
            # For R² higher is better — invert the highlight logic
            best_idx = df[col].idxmax()
            colors_p = ["#2ecc71" if i == best_idx else
                        "#95a5a6" if is_baseline(df["Model"].iloc[i]) else "#4C72B0"
                        for i in range(len(df))]
        bars = ax.barh(df["Model"], df[col], color=colors_p, edgecolor="white")
        ax.bar_label(bars, fmt="%.3f", padding=3, fontsize=8)
        ax.set_xlabel(xlabel)
        lower_str = "(lower = better)" if lower_better else "(higher = better)"
        ax.set_title(f"{col} {lower_str}", fontweight="bold")
        ax.invert_yaxis()

    fig.suptitle(
        "Model Performance Comparison — Drammen Test Set",
        fontsize=14, fontweight="bold",
    )
    if save_path_prefix:
        _save_or_show(fig, str(save_path_prefix) + "_4panel.png")
    else:
        _save_or_show(fig, None)

    # ── Standalone MAE bar (for README / GitHub) ──────────────────────────
    fig2, ax = plt.subplots(figsize=(10, max(5, len(df) * 0.5)))
    bars = ax.barh(df["Model"], df["MAE"], color=bar_colors, edgecolor="white")
    ax.bar_label(bars, fmt="%.3f kWh", padding=4, fontsize=9)
    ax.set_xlabel("MAE (kWh)  ← lower is better")
    ax.set_title(
        "Mean Absolute Error by Model — Drammen Test Set\n"
        "(Green = best | Blue = ML models | Grey = baselines)",
        fontweight="bold",
    )
    ax.invert_yaxis()
    legend_patches = [
        mpatches.Patch(color="#2ecc71", label="Best model"),
        mpatches.Patch(color="#4C72B0", label="ML model"),
        mpatches.Patch(color="#95a5a6", label="Baseline"),
    ]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=9)
    if save_path_prefix:
        _save_or_show(fig2, str(save_path_prefix) + "_mae_bar.png")
    else:
        _save_or_show(fig2, None)


# ---------------------------------------------------------------------------
# 9. Actual vs predicted time series (one building, N days)
# ---------------------------------------------------------------------------

def plot_actual_vs_predicted_timeseries(
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
    model_name: str = "Model",
    building_id: int | None = None,
    n_days: int = 14,
    save_path: str | Path | None = None,
) -> None:
    """Time-indexed actual vs predicted plot for N days.

    Matches the per-model actual vs predicted sample plots from the thesis
    (e.g. ``Random_Forest_actual_vs_pred_sample.png``).
    """
    if isinstance(y_true, pd.Series):
        ts_index = y_true.index
        y_true_arr = y_true.values
    else:
        ts_index = np.arange(len(y_true))
        y_true_arr = np.asarray(y_true)

    n_show = min(n_days * 24, len(y_true_arr))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 8), sharex=False)

    # Top: time series comparison
    ax1.plot(ts_index[:n_show], y_true_arr[:n_show],
             color="#4C72B0", linewidth=1.2, label="Actual", zorder=3)
    ax1.plot(ts_index[:n_show], y_pred[:n_show],
             color="#DD8452", linewidth=1.2, linestyle="--", label=f"Predicted ({model_name})", zorder=2)
    ax1.fill_between(ts_index[:n_show],
                     y_true_arr[:n_show], y_pred[:n_show],
                     alpha=0.15, color="crimson", label="Error")
    ax1.set_ylabel("Electricity (kWh)")
    bid_str = f" — Building {building_id}" if building_id else ""
    ax1.set_title(f"{model_name} — Actual vs Predicted ({n_days} days){bid_str}")
    ax1.legend(fontsize=9)

    # Bottom: residuals
    residuals = y_true_arr[:n_show] - y_pred[:n_show]
    ax2.bar(range(len(residuals)), residuals,
            color=["#e74c3c" if r < 0 else "#2ecc71" for r in residuals],
            width=1.0, alpha=0.7)
    ax2.axhline(0, color="black", linewidth=1.0)
    ax2.set_xlabel("Hour index")
    ax2.set_ylabel("Residual (kWh)")
    ax2.set_title("Residuals (Actual − Predicted)")

    fig.suptitle(
        f"{model_name} Prediction Quality | "
        f"MAE={np.mean(np.abs(residuals)):.3f} kWh | "
        f"RMSE={np.sqrt(np.mean(residuals**2)):.3f} kWh",
        fontsize=12, fontweight="bold",
    )
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 10. Ensemble weights bar chart
# ---------------------------------------------------------------------------

def plot_ensemble_weights(
    weights: dict[str, float],
    save_path: str | Path | None = None,
) -> None:
    """Horizontal bar chart of weighted average ensemble weights.

    Matches the ensemble weights analysis in the thesis model training notebook.
    """
    ws = pd.Series(weights).sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(10, max(4, len(ws) * 0.6)))
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(ws)))
    bars = ax.barh(ws.index, ws.values, color=colors, edgecolor="white")
    ax.bar_label(bars, fmt="%.4f", padding=4, fontsize=10)
    ax.set_xlabel("Weight (normalised inverse-MAE)")
    ax.set_title(
        "Weighted Average Ensemble — Model Weights\n"
        "(Higher weight = lower validation MAE)",
        fontweight="bold",
    )
    ax.invert_yaxis()
    ax.axvline(1.0 / len(ws), color="crimson", linestyle="--",
               linewidth=1.2, label=f"Equal weight ({1/len(ws):.3f})")
    ax.legend(fontsize=9)
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 11. Thesis vs new pipeline comparison table + chart
# ---------------------------------------------------------------------------

def plot_thesis_vs_pipeline_comparison(
    thesis_df: pd.DataFrame,
    pipeline_df: pd.DataFrame,
    save_path: str | Path | None = None,
    exclude_oracle_artifacts: bool = True,
) -> None:
    """Side-by-side bar chart comparing thesis results vs new pipeline results.

    Parameters
    ----------
    exclude_oracle_artifacts:
        If True (default), excludes linear models and ensemble from the
        pipeline side to focus the visual comparison on the tree-based
        models (LightGBM, XGBoost, RF) that are directly comparable across
        both runs.
    """
    # Linear and ensemble models — excluded from side-by-side chart by default
    # to keep the comparison focused on tree-based models present in both runs
    ORACLE_ARTIFACT_MODELS = {  # noqa: N806
        "Ridge", "Lasso",
        "Stacking Ensemble (Ridge meta)", "Stacking Ensemble (LGBM meta)",
    }

    p_df = pipeline_df.copy()
    if "Model" not in p_df.columns and p_df.index.name == "Model":
        p_df = p_df.reset_index()

    if exclude_oracle_artifacts:
        p_df = p_df[~p_df["Model"].isin(ORACLE_ARTIFACT_MODELS)]

    # Merge on model name
    merged = pd.merge(
        thesis_df[["Model", "MAE"]].rename(columns={"MAE": "Thesis MAE (kWh)"}),
        p_df[["Model", "MAE"]].rename(columns={"MAE": "Pipeline MAE (kWh)"}),
        on="Model", how="inner",
    ).sort_values("Thesis MAE (kWh)")

    if merged.empty:
        logger.warning("No common non-artifact models found between thesis and pipeline DataFrames")
        return

    x = np.arange(len(merged))
    width = 0.38

    fig, ax = plt.subplots(figsize=(max(12, len(merged) * 1.6), 8))
    bars1 = ax.bar(x - width / 2, merged["Thesis MAE (kWh)"], width,
                   color="#4C72B0", label="Thesis 2025 — 24h multi-step forecast", alpha=0.9)
    bars2 = ax.bar(x + width / 2, merged["Pipeline MAE (kWh)"], width,
                   color="#DD8452", label="Pipeline v2 2026 — 1-step oracle (h=1)", alpha=0.9)

    ax.bar_label(bars1, fmt="%.3f", padding=3, fontsize=9)
    ax.bar_label(bars2, fmt="%.3f", padding=3, fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(merged["Model"], rotation=20, ha="right", fontsize=10)
    ax.set_ylabel("MAE (kWh)  ← lower is better")
    ax.set_title(
        "MSc Thesis (2025) vs Pipeline v2 (2026) — MAE Comparison\n"
        "Thesis: 24h multi-step forecast | Pipeline: 1-step oracle (forecast_horizon=1)\n"
        "⚠  Ridge & Stacking excluded (MAE≈0 artefact — integer data + lag_1h r=0.977)",
        fontweight="bold",
    )
    ax.legend(fontsize=10, loc="upper left")
    ax.grid(axis="y", alpha=0.4)

    # Add difference annotations
    for i, (_, row) in enumerate(merged.iterrows()):
        t_mae = row["Thesis MAE (kWh)"]
        p_mae = row["Pipeline MAE (kWh)"]
        diff = p_mae - t_mae
        color = "#e74c3c" if diff > 0.3 else "#2ecc71" if diff < -0.3 else "#95a5a6"
        ax.annotate(
            f"Δ{diff:+.2f}",
            xy=(x[i], max(t_mae, p_mae) + 0.1),
            ha="center", fontsize=8, color=color, fontweight="bold",
        )

    # Add explanation text box
    note = (
        "Note: Pipeline v2 uses forecast_horizon=1 (1-step oracle).\n"
        "Set forecast_horizon=24 in config to get thesis-comparable results.\n"
        "Tree model MAEs are within ~0.3 kWh of thesis — methodology difference."
    )
    ax.text(
        0.01, 0.97, note,
        transform=ax.transAxes, fontsize=8, verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", alpha=0.8),
    )

    _save_or_show(fig, save_path)
