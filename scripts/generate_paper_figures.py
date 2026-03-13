"""
generate_paper_figures.py
=========================
Produces publication-quality figures for the journal paper.

Figures generated
-----------------
  fig1_paradigm_parity.png      Main result: all models, grouped and coloured by Setup A/B/C
  fig2_ensemble_blend.png       GrandEnsemble alpha sweep — MAE and R² vs % Setup-A weight
  fig3_oslo_generalization.png  Drammen vs Oslo side-by-side (MAE and R²)
  fig4_quantile_calibration.png Coverage rate and Winkler score — probabilistic evaluation
  fig5_per_horizon_mae.png      H+1 to H+24 per-step MAE for CNN-LSTM SetupB/C models
  fig6_methodology_overview.png Text/patch diagram of the three-paradigm pipeline

All figures saved to outputs/figures/paper/ at 300 dpi (journal submission quality).

Usage
-----
    python scripts/generate_paper_figures.py
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR  = PROJECT_ROOT / "outputs" / "results"
FIG_DIR      = PROJECT_ROOT / "outputs" / "figures" / "paper"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
PALETTE = {
    "A":        "#2166ac",   # deep blue — trees+features
    "B":        "#d6604d",   # warm red — DL+features (negative control)
    "C":        "#4dac26",   # green — DL+raw sequences
    "Ensemble": "#762a83",   # purple — ensembles
    "Baseline": "#999999",   # grey — baselines
}

plt.rcParams.update({
    "font.family":        "sans-serif",
    "font.size":          10,
    "axes.titlesize":     11,
    "axes.labelsize":     10,
    "xtick.labelsize":    9,
    "ytick.labelsize":    9,
    "legend.fontsize":    9,
    "figure.dpi":         150,
    "savefig.dpi":        300,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.alpha":         0.35,
    "grid.linestyle":     "--",
})


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_drammen() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_DIR / "final_metrics.csv", index_col=0)
    return df


def load_oslo() -> pd.DataFrame:
    return pd.read_csv(RESULTS_DIR / "oslo_final_metrics.csv", index_col=0)


def load_quantile() -> pd.DataFrame:
    return pd.read_csv(RESULTS_DIR / "quantile_results.csv")


# ---------------------------------------------------------------------------
# Figure 1 — Paradigm Parity Horizontal Bar Chart
# ---------------------------------------------------------------------------

def fig1_paradigm_parity() -> None:
    """All H+24 Drammen models, grouped by paradigm, sorted by MAE."""
    df = load_drammen()

    # Tag each row with its paradigm
    def tag(name: str) -> tuple[str, str]:
        n = str(name)
        if "Ensemble" in n or "Stacking" in n:
            return ("Ensemble", "Ensemble")
        if any(x in n for x in ["Naive", "Baseline", "Mean", "Seasonal"]):
            return ("Baseline", "Baseline")
        if "SetupB" in n:
            return ("B", "Setup B\n(DL + Features)")
        if "SetupC" in n:
            return ("C", "Setup C\n(DL + Raw)")
        if any(x in n for x in ["LightGBM", "XGBoost", "RandomForest", "Ridge", "Lasso"]):
            return ("A", "Setup A\n(Trees + Features)")
        return ("C", "Setup C\n(DL + Raw)")

    # Filter to informative rows (no grand ensemble sweep rows, only A0_C100 and A90_C10 and A100_C0)
    keep_patterns = [
        "LightGBM_SetupA", "XGBoost_SetupA", "RandomForest_SetupA",
        "Ridge_SetupA", "Lasso_SetupA",
        "LSTM_SetupB", "CNN-LSTM_SetupB", "GRU_SetupB",
        "PatchTST_SetupC", "CNN-LSTM_SetupC", "LSTM_SetupC", "GRU_SetupC",
        "GrandEnsemble_A90_C9",
        "Mean Baseline",
    ]
    # Flexible matching
    sel = df[df["model"].apply(lambda m: any(p in str(m) for p in keep_patterns))].copy()

    # Use R² column — handle both "R²" and "R2"
    r2_col = "R²" if "R²" in sel.columns else "R2"
    mae_col = "MAE"

    sel["paradigm"] = sel["model"].apply(lambda m: tag(m)[0])
    sel["label"] = sel["model"].apply(lambda m: (
        str(m).replace("_SetupA", "").replace("_SetupB", "").replace("_SetupC", "")
             .replace("GrandEnsemble_A90_C9", "Grand Ens. A90/C10")
    ))

    # Sort: within each paradigm, sort by MAE ascending
    order = ["A", "B", "C", "Ensemble", "Baseline"]
    sel["porder"] = sel["paradigm"].map({k: i for i, k in enumerate(order)})
    sel = sel.sort_values(["porder", mae_col], ascending=[True, True])

    # Colours per row
    colors = [PALETTE[p] for p in sel["paradigm"]]

    fig, ax = plt.subplots(figsize=(8, 6))
    y_pos = range(len(sel))
    bars = ax.barh(list(y_pos), sel[mae_col].values, color=colors, edgecolor="white",
                   linewidth=0.6, height=0.7)

    # Value labels
    for bar, val in zip(bars, sel[mae_col].values):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}", va="center", ha="left", fontsize=8)

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(sel["label"].values, fontsize=9)
    ax.set_xlabel("MAE (kWh)", fontweight="bold")
    ax.set_title("Paradigm Parity: H+24 Drammen Results\n"
                 "Setup A (Trees+Features) vs B (DL+Features) vs C (DL+Raw)",
                 fontweight="bold", pad=10)
    ax.set_xlim(0, sel[mae_col].max() * 1.2)

    # Legend patches
    legend_patches = [
        mpatches.Patch(color=PALETTE["A"], label="Setup A — Trees + Features"),
        mpatches.Patch(color=PALETTE["B"], label="Setup B — DL + Features (negative control)"),
        mpatches.Patch(color=PALETTE["C"], label="Setup C — DL + Raw Sequences"),
        mpatches.Patch(color=PALETTE["Ensemble"], label="Grand Ensemble (A+C blend)"),
        mpatches.Patch(color=PALETTE["Baseline"], label="Mean Baseline"),
    ]
    ax.legend(handles=legend_patches, loc="lower right", framealpha=0.9, fontsize=8)

    # Separator lines between paradigm groups
    group_boundaries = []
    prev = None
    for i, p in enumerate(sel["paradigm"].values):
        if p != prev and prev is not None:
            group_boundaries.append(i - 0.5)
        prev = p
    for b in group_boundaries:
        ax.axhline(b, color="#cccccc", linewidth=0.8, linestyle="-")

    fig.tight_layout()
    out = FIG_DIR / "fig1_paradigm_parity.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved → {out}")


# ---------------------------------------------------------------------------
# Figure 2 — Grand Ensemble Alpha Sweep
# ---------------------------------------------------------------------------

def fig2_ensemble_blend() -> None:
    """MAE and R² as function of Setup-A weight in the Grand Ensemble blend."""
    df = load_drammen()
    ens = df[df["model"].str.startswith("GrandEnsemble_")].copy()

    r2_col = "R2"  # ensemble rows use R2 column

    # Extract alpha from model name e.g. GrandEnsemble_A90_C9 → 90
    def parse_alpha(name: str) -> int:
        import re
        m = re.search(r"A(\d+)_C", name)
        return int(m.group(1)) if m else 0

    ens["alpha"] = ens["model"].apply(parse_alpha)
    ens = ens.sort_values("alpha")

    # Also add LightGBM_SetupA (alpha=100 reference from Setup A)
    lgbm_row = df[df["model"] == "LightGBM_SetupA"]
    lgbm_mae = lgbm_row["MAE"].values[0] if len(lgbm_row) > 0 else None
    lgbm_r2  = lgbm_row["R²"].values[0] if ("R²" in lgbm_row.columns and len(lgbm_row) > 0) else None

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4))

    # MAE
    ax1.plot(ens["alpha"], ens["MAE"], "o-", color=PALETTE["Ensemble"],
             linewidth=2, markersize=6, label="Grand Ensemble blend")
    if lgbm_mae:
        ax1.axhline(lgbm_mae, color=PALETTE["A"], linestyle="--", linewidth=1.5,
                    label=f"LightGBM (Setup A): {lgbm_mae:.3f} kWh")
    ax1.set_xlabel("% Setup-A weight in blend")
    ax1.set_ylabel("MAE (kWh)")
    ax1.set_title("Ensemble Blend — MAE", fontweight="bold")
    ax1.set_xticks([0, 10, 30, 50, 70, 90, 100])
    ax1.legend(fontsize=8)

    # R²
    r2_vals = ens[r2_col].values if r2_col in ens.columns else []
    if len(r2_vals):
        ax2.plot(ens["alpha"], r2_vals, "s-", color=PALETTE["Ensemble"],
                 linewidth=2, markersize=6, label="Grand Ensemble blend")
    if lgbm_r2 is not None:
        ax2.axhline(lgbm_r2, color=PALETTE["A"], linestyle="--", linewidth=1.5,
                    label=f"LightGBM (Setup A): R²={lgbm_r2:.4f}")
    ax2.set_xlabel("% Setup-A weight in blend")
    ax2.set_ylabel("R²")
    ax2.set_title("Ensemble Blend — R²", fontweight="bold")
    ax2.set_xticks([0, 10, 30, 50, 70, 90, 100])
    ax2.legend(fontsize=8)

    fig.suptitle("Grand Ensemble: Weighted Average of Setup A + Setup C Predictions\n"
                 "Monotonic improvement as Setup-A weight increases → trees dominate",
                 fontsize=10, fontweight="bold", y=1.01)
    fig.tight_layout()
    out = FIG_DIR / "fig2_ensemble_blend.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved → {out}")


# ---------------------------------------------------------------------------
# Figure 3 — Oslo Generalisation
# ---------------------------------------------------------------------------

def fig3_oslo_generalisation() -> None:
    """Drammen vs Oslo — MAE and R² side-by-side for common Setup-A models."""
    df_d = load_drammen()
    df_o = load_oslo()

    models_common = ["LightGBM", "XGBoost", "RandomForest", "Ridge", "Lasso",
                     "LightGBM_Quantile", "Mean Baseline"]

    def extract(df: pd.DataFrame, models: list, city: str) -> pd.DataFrame:
        rows = []
        for m in models:
            row = df[df["model"].str.contains(m, regex=False, na=False)]
            if len(row) == 0:
                # Try without Setup suffix
                row = df[df["model"].str.replace("_SetupA", "", regex=False) == m]
            if len(row) > 0:
                r = row.iloc[0]
                r2_val = r.get("R²", r.get("R2", np.nan))
                rows.append({"model": m, "MAE": r["MAE"], "R2": float(r2_val), "city": city})
        return pd.DataFrame(rows)

    d_df = extract(df_d, models_common, "Drammen")
    o_df = extract(df_o, models_common, "Oslo")
    combined = pd.concat([d_df, o_df], ignore_index=True)

    # Rename for display
    label_map = {
        "LightGBM": "LightGBM", "XGBoost": "XGBoost",
        "RandomForest": "Random Forest", "Ridge": "Ridge",
        "Lasso": "Lasso", "LightGBM_Quantile": "LGBM Quantile",
        "Mean Baseline": "Mean Baseline",
    }
    combined["label"] = combined["model"].map(label_map).fillna(combined["model"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))
    bar_width = 0.35
    models_ordered = ["LightGBM", "XGBoost", "RandomForest", "Ridge", "Lasso", "Mean Baseline"]
    labels_ordered = [label_map.get(m, m) for m in models_ordered]

    d_mae = [combined[(combined["model"] == m) & (combined["city"] == "Drammen")]["MAE"].values[0]
             if len(combined[(combined["model"] == m) & (combined["city"] == "Drammen")]) > 0
             else np.nan for m in models_ordered]
    o_mae = [combined[(combined["model"] == m) & (combined["city"] == "Oslo")]["MAE"].values[0]
             if len(combined[(combined["model"] == m) & (combined["city"] == "Oslo")]) > 0
             else np.nan for m in models_ordered]
    d_r2 = [combined[(combined["model"] == m) & (combined["city"] == "Drammen")]["R2"].values[0]
            if len(combined[(combined["model"] == m) & (combined["city"] == "Drammen")]) > 0
            else np.nan for m in models_ordered]
    o_r2 = [combined[(combined["model"] == m) & (combined["city"] == "Oslo")]["R2"].values[0]
            if len(combined[(combined["model"] == m) & (combined["city"] == "Oslo")]) > 0
            else np.nan for m in models_ordered]

    x = np.arange(len(models_ordered))

    # MAE bars
    b1 = ax1.bar(x - bar_width / 2, d_mae, bar_width, label="Drammen (training city)",
                 color=PALETTE["A"], alpha=0.85, edgecolor="white")
    b2 = ax1.bar(x + bar_width / 2, o_mae, bar_width, label="Oslo (unseen city)",
                 color=PALETTE["C"], alpha=0.85, edgecolor="white")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels_ordered, rotation=30, ha="right")
    ax1.set_ylabel("MAE (kWh)")
    ax1.set_title("Geographic Generalisation — MAE\n(lower is better)", fontweight="bold")
    ax1.legend()
    for bar in list(b1) + list(b2):
        h = bar.get_height()
        if not np.isnan(h):
            ax1.text(bar.get_x() + bar.get_width() / 2, h + 0.2, f"{h:.1f}",
                     ha="center", va="bottom", fontsize=7)

    # R² bars
    b3 = ax2.bar(x - bar_width / 2, d_r2, bar_width, label="Drammen",
                 color=PALETTE["A"], alpha=0.85, edgecolor="white")
    b4 = ax2.bar(x + bar_width / 2, o_r2, bar_width, label="Oslo",
                 color=PALETTE["C"], alpha=0.85, edgecolor="white")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels_ordered, rotation=30, ha="right")
    ax2.set_ylabel("R²")
    ax2.set_ylim(0.8, 1.0)
    ax2.set_title("Geographic Generalisation — R²\n(higher is better)", fontweight="bold")
    ax2.legend()
    for bar in list(b3) + list(b4):
        h = bar.get_height()
        if not np.isnan(h):
            ax2.text(bar.get_x() + bar.get_width() / 2, h + 0.002, f"{h:.3f}",
                     ha="center", va="bottom", fontsize=7)

    fig.suptitle("Setup A Pipeline: Zero-Shot Generalisation Drammen → Oslo\n"
                 "Same pipeline retrained on Oslo; R² maintained >0.96 across all tree models",
                 fontsize=10, fontweight="bold", y=1.01)
    fig.tight_layout()
    out = FIG_DIR / "fig3_oslo_generalisation.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved → {out}")


# ---------------------------------------------------------------------------
# Figure 4 — Quantile Calibration
# ---------------------------------------------------------------------------

def fig4_quantile_calibration() -> None:
    """Coverage rate and Winkler score for Drammen and Oslo."""
    try:
        q_df = load_quantile()
    except FileNotFoundError:
        print("quantile_results.csv not found — run quantile_evaluation.py first")
        return

    fig, axes = plt.subplots(1, 3, figsize=(11, 4))

    cities   = q_df["city"].str.capitalize().values
    cov      = q_df["coverage_rate"].values * 100
    winkler  = q_df["winkler_score"].values
    pi_width = q_df["mean_pi_width"].values
    colors   = [PALETTE["A"], PALETTE["C"]]

    # Coverage rate
    ax = axes[0]
    bars = ax.bar(cities, cov, color=colors[:len(cities)], edgecolor="white", width=0.5)
    ax.axhline(80, color="#e31a1c", linestyle="--", linewidth=1.5, label="Target: 80%")
    ax.set_ylabel("Coverage Rate (%)")
    ax.set_title("P10–P90 Coverage Rate\n(target = 80%)", fontweight="bold")
    ax.set_ylim(70, 90)
    for bar, val in zip(bars, cov):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.3, f"{val:.1f}%",
                ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.legend(fontsize=8)

    # Winkler score
    ax = axes[1]
    bars = ax.bar(cities, winkler, color=colors[:len(cities)], edgecolor="white", width=0.5)
    ax.set_ylabel("Winkler Score (kWh)")
    ax.set_title("Winkler Score\n(lower = sharper + better calibrated)", fontweight="bold")
    for bar, val in zip(bars, winkler):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.3, f"{val:.1f}",
                ha="center", va="bottom", fontsize=10, fontweight="bold")

    # Mean PI width
    ax = axes[2]
    bars = ax.bar(cities, pi_width, color=colors[:len(cities)], edgecolor="white", width=0.5)
    ax.set_ylabel("Mean PI Width (kWh)")
    ax.set_title("Mean Interval Width P90−P10\n(sharpness)", fontweight="bold")
    for bar, val in zip(bars, pi_width):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.3, f"{val:.1f}",
                ha="center", va="bottom", fontsize=10, fontweight="bold")

    # Add P50 MAE as annotation
    if "p50_mae" in q_df.columns:
        for ax2, row in zip([axes[0], axes[1]], q_df.itertuples()):
            pass  # could annotate but keep it clean

    fig.suptitle("LightGBM Quantile Forecaster (P10/P50/P90) — Probabilistic Evaluation\n"
                 "80% Prediction Interval: calibration maintained across two cities",
                 fontsize=10, fontweight="bold", y=1.01)
    fig.tight_layout()
    out = FIG_DIR / "fig4_quantile_calibration.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved → {out}")


# ---------------------------------------------------------------------------
# Figure 5 — Per-Horizon MAE (DL models)
# ---------------------------------------------------------------------------

def fig5_per_horizon_mae() -> None:
    """Per-step MAE across the 24-hour prediction window for DL H+24 models."""
    df = load_drammen()

    # Filter DL models with per-horizon MAE (stored as JSON list in horizon_mae column)
    dl_rows = df[df["horizon_mae"].notna()].copy()
    if len(dl_rows) == 0:
        print("No per-horizon MAE data available — skipping fig5")
        return

    import ast
    fig, ax = plt.subplots(figsize=(8, 4))

    for _, row in dl_rows.iterrows():
        try:
            mae_list = ast.literal_eval(str(row["horizon_mae"]))
            hours = list(range(1, len(mae_list) + 1))
            setup = "B" if "SetupB" in str(row["model"]) else "C" if "SetupC" in str(row["model"]) else "B"
            label_name = (str(row["model"])
                          .replace("_SetupB", " (B)").replace("_SetupC", " (C)"))
            color = PALETTE["B"] if setup == "B" else PALETTE["C"]
            ax.plot(hours, mae_list, "o-", color=color, markersize=3, linewidth=1.5,
                    label=label_name, alpha=0.85)
        except Exception:
            continue

    # Reference: LightGBM flat line (its single H+24 MAE)
    lgbm_row = df[df["model"] == "LightGBM_SetupA"]
    if len(lgbm_row) > 0:
        lgbm_mae = lgbm_row["MAE"].values[0]
        ax.axhline(lgbm_mae, color=PALETTE["A"], linestyle="--", linewidth=2,
                   label=f"LightGBM Setup A (H+24 MAE = {lgbm_mae:.2f} kWh)")

    ax.set_xlabel("Forecast Horizon Step (hours ahead)")
    ax.set_ylabel("MAE (kWh)")
    ax.set_title("Per-Horizon MAE across the 24-Hour Prediction Window\n"
                 "DL models vs LightGBM Setup A reference", fontweight="bold")
    ax.legend(fontsize=8, ncol=2)
    ax.set_xticks(range(1, 25))
    fig.tight_layout()
    out = FIG_DIR / "fig5_per_horizon_mae.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved → {out}")


# ---------------------------------------------------------------------------
# Figure 6 — Methodology Overview (text diagram)
# ---------------------------------------------------------------------------

def fig6_methodology_overview() -> None:
    """Schematic overview of the three-paradigm pipeline architecture."""
    fig = plt.figure(figsize=(13, 7))

    # Background colour
    fig.patch.set_facecolor("#f8f9fa")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7)
    ax.axis("off")

    # ── Helper: rounded box ────────────────────────────────────────────────
    def box(cx, cy, w, h, text, color="#2c7bb6", text_color="white",
            fontsize=9, bold=False):
        rect = mpatches.FancyBboxPatch(
            (cx - w / 2, cy - h / 2), w, h,
            boxstyle="round,pad=0.1",
            linewidth=1.2, edgecolor="#333333",
            facecolor=color, zorder=3,
        )
        ax.add_patch(rect)
        ax.text(cx, cy, text, ha="center", va="center",
                fontsize=fontsize, color=text_color,
                fontweight="bold" if bold else "normal",
                zorder=4, wrap=True)

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color="#555555", lw=1.5), zorder=2)

    # ── Input data ─────────────────────────────────────────────────────────
    box(1.5, 5.8, 2.2, 0.7, "Raw Smart Meter\nDrammen / Oslo", "#4a4a4a", "white", 8, True)
    box(1.5, 4.7, 2.2, 0.7, "Weather Data\n(Temp, Solar, Wind)", "#4a4a4a", "white", 8)
    arrow(2.6, 5.8, 3.5, 5.8)
    arrow(2.6, 4.7, 3.5, 5.2)

    # ── Stage 1 ────────────────────────────────────────────────────────────
    box(4.4, 5.5, 1.7, 1.1, "Stage 1\nPreprocessing\n(MICE imputation)", "#5e4fa2", "white", 8)
    arrow(5.25, 5.5, 6.1, 5.5)

    # ── Stage 2 ────────────────────────────────────────────────────────────
    box(7.0, 5.5, 1.7, 1.1, "Stage 2\nFeature Engineering\n(35 features)", "#5e4fa2", "white", 8)
    arrow(7.85, 5.5, 8.6, 5.5)

    # ── Stage 3 split ─────────────────────────────────────────────────────
    box(9.5, 5.5, 1.7, 1.1, "Stage 3\nChronological Split\nTrain / Val / Test", "#5e4fa2", "white", 8)

    # Three paths down from Stage 3
    arrow(9.5, 4.95, 9.5, 4.4)
    ax.plot([9.5, 4.5], [4.4, 4.4], "-", color="#555555", lw=1.5, zorder=2)
    ax.plot([9.5, 9.5], [4.4, 2.8], "-", color="#555555", lw=1.5, zorder=2)
    ax.plot([9.5, 12.0], [4.4, 4.4], "-", color="#555555", lw=1.5, zorder=2)
    ax.annotate("", xy=(4.5, 3.8), xytext=(4.5, 4.4),
                arrowprops=dict(arrowstyle="->", color="#555555", lw=1.5), zorder=2)
    ax.annotate("", xy=(9.5, 2.8), xytext=(9.5, 3.5),
                arrowprops=dict(arrowstyle="->", color="#555555", lw=1.5), zorder=2)
    ax.annotate("", xy=(12.0, 3.8), xytext=(12.0, 4.4),
                arrowprops=dict(arrowstyle="->", color="#555555", lw=1.5), zorder=2)

    # ── Setup A ────────────────────────────────────────────────────────────
    box(4.5, 3.2, 2.2, 1.1, "SETUP A\nLightGBM / XGBoost\nRF / Ridge / Lasso", PALETTE["A"], "white", 8, True)
    box(4.5, 1.8, 2.2, 0.7,
        "R²=0.975  MAE=4.03 kWh\nOslo: R²=0.963  MAE=7.42", "#e0f3f8", "#2166ac", 8)
    arrow(4.5, 2.65, 4.5, 2.15)

    # ── Setup B ────────────────────────────────────────────────────────────
    box(9.5, 3.2, 2.2, 1.1, "SETUP B (Neg. Control)\nLSTM / CNN-LSTM / GRU\n+ 35 Tabular Features", PALETTE["B"], "white", 8, True)
    box(9.5, 1.8, 2.2, 0.7,
        "LSTM: R²=−0.004  (failure)\nCNN-LSTM: R²=0.877", "#fee8d6", "#d6604d", 8)
    arrow(9.5, 2.65, 9.5, 2.15)

    # ── Setup C ────────────────────────────────────────────────────────────
    box(12.0, 3.2, 1.8, 1.1, "SETUP C\nPatchTST\nCNN-LSTM / GRU\n(Raw Sequences)", PALETTE["C"], "white", 8, True)
    box(12.0, 1.8, 1.8, 0.7,
        "PatchTST: R²=0.910\nMAE=6.96 kWh", "#e6f4e0", "#4dac26", 8)
    arrow(12.0, 2.65, 12.0, 2.15)

    # ── Grand Ensemble ─────────────────────────────────────────────────────
    ax.plot([4.5, 12.0], [1.1, 1.1], "-", color="#555555", lw=1.5, zorder=2)
    ax.plot([4.5, 4.5], [1.1, 1.44], "-", color="#555555", lw=1.5, zorder=2)
    ax.plot([12.0, 12.0], [1.1, 1.44], "-", color="#555555", lw=1.5, zorder=2)
    ax.plot([8.25, 8.25], [1.1, 0.7], "-", color="#555555", lw=1.5, zorder=2)
    ax.annotate("", xy=(8.25, 0.7), xytext=(8.25, 1.1),
                arrowprops=dict(arrowstyle="->", color="#555555", lw=1.5), zorder=2)
    box(8.25, 0.4, 3.5, 0.6,
        "Grand Ensemble  α·A + (1−α)·C  →  best at α=1.0 (pure A)", PALETTE["Ensemble"], "white", 8, True)

    # ── Title ──────────────────────────────────────────────────────────────
    ax.text(6.5, 6.75, "Three-Paradigm Pipeline Architecture",
            ha="center", va="center", fontsize=14, fontweight="bold", color="#1a1a1a")
    ax.text(6.5, 6.35, "Municipal Buildings (H+24 Day-Ahead Forecasting)",
            ha="center", va="center", fontsize=10, color="#555555")

    out = FIG_DIR / "fig6_methodology_overview.png"
    fig.savefig(out, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved → {out}")


# ---------------------------------------------------------------------------
# Run all
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Generating paper figures...")
    fig6_methodology_overview()
    fig1_paradigm_parity()
    fig2_ensemble_blend()
    fig3_oslo_generalisation()
    fig4_quantile_calibration()
    fig5_per_horizon_mae()
    print(f"\nAll figures saved to {FIG_DIR}")
