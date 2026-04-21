"""
build_horizon_table.py
======================
Merges H+1 and H+24 model results into a single horizon-sensitivity table.

Sources
-------
  outputs/results/h1_metrics.csv   — H+1 results (MSc 35-feature pipeline)
  outputs/results/final_metrics.csv — H+24 Paradigm Parity results

Output
------
  outputs/results/horizon_sensitivity.csv
    Columns: model, setup, paradigm, mae_h1, r2_h1, mae_h24, r2_h24,
             degradation_factor, note

Usage
-----
    python scripts/build_horizon_table.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "outputs" / "results"

# ---------------------------------------------------------------------------
# Name-mapping tables
# ---------------------------------------------------------------------------

# H+1 CSV uses these model name strings → canonical key
H1_NAME_MAP: dict[str, str] = {
    "LightGBM": "LightGBM",
    "XGBoost": "XGBoost",
    "RandomForest": "RandomForest",
    "Ridge": "Ridge",
    "Lasso": "Lasso",
    "LSTM": "LSTM",
    "GRU": "GRU",
    "CNN-LSTM": "CNN-LSTM",
    "Stacking Ensemble (Ridge meta)": "Stacking",
    "Mean Baseline": "Mean Baseline",
}

# H+24 CSV uses these model name strings → canonical key
H24_NAME_MAP: dict[str, str] = {
    "LightGBM_SetupA": "LightGBM",
    "XGBoost_SetupA": "XGBoost",
    "RandomForest_SetupA": "RandomForest",
    "Ridge_SetupA": "Ridge",
    "Lasso_SetupA": "Lasso",
    "LSTM_SetupB": "LSTM",
    "GRU_SetupB": "GRU",
    "CNN-LSTM_SetupB": "CNN-LSTM",
    "Mean Baseline": "Mean Baseline",
}

# Metadata for each canonical model
MODEL_META: dict[str, dict] = {
    "LightGBM": {"setup": "A", "paradigm": "Trees + Features"},
    "XGBoost": {"setup": "A", "paradigm": "Trees + Features"},
    "RandomForest": {"setup": "A", "paradigm": "Trees + Features"},
    "Ridge": {"setup": "A", "paradigm": "Linear + Features"},
    "Lasso": {"setup": "A", "paradigm": "Linear + Features"},
    "Stacking": {"setup": "A", "paradigm": "Ensemble (Setup A)"},
    "LSTM": {"setup": "B", "paradigm": "DL + Features (Negative Control)"},
    "GRU": {"setup": "B", "paradigm": "DL + Features (Negative Control)"},
    "CNN-LSTM": {"setup": "B", "paradigm": "DL + Features (Negative Control)"},
    "Mean Baseline": {"setup": "—", "paradigm": "Baseline"},
}

# Notes for special cases
MODEL_NOTES: dict[str, str] = {
    "LSTM": "Convergence failure at H+24 (loss diverged)",
    "RandomForest": "H+1 champion; largest tree degradation factor",
    "LightGBM": "H+24 champion; most horizon-robust tree",
    "Stacking": "H+1 stacking champion; H+24 not evaluated (Setup A only)",
    "Mean Baseline": "Reference baseline",
}

# Display order
DISPLAY_ORDER = [
    "LightGBM",
    "XGBoost",
    "RandomForest",
    "Ridge",
    "Lasso",
    "Stacking",
    "CNN-LSTM",
    "GRU",
    "LSTM",
    "Mean Baseline",
]


def _get_r2(row: pd.Series) -> float:
    """Return R² from either 'R²' or 'R2' column, whichever is present and non-NaN."""
    for col in ("R²", "R2"):
        if col in row.index and pd.notna(row[col]):
            return float(row[col])
    return np.nan


def load_h1() -> dict[str, dict]:
    """Load H+1 metrics and return {canonical_key: {mae, r2}}."""
    df = pd.read_csv(RESULTS_DIR / "h1_metrics.csv", index_col=0)
    out: dict[str, dict] = {}
    for _, row in df.iterrows():
        raw = str(row.get("Model", row.get("model", ""))).strip()
        key = H1_NAME_MAP.get(raw)
        if key:
            out[key] = {"mae_h1": float(row["MAE"]), "r2_h1": _get_r2(row)}
    return out


def load_h24() -> dict[str, dict]:
    """Load H+24 metrics and return {canonical_key: {mae, r2}}."""
    df = pd.read_csv(RESULTS_DIR / "final_metrics.csv", index_col=0)
    out: dict[str, dict] = {}
    for _, row in df.iterrows():
        raw = str(row.get("model", "")).strip()
        key = H24_NAME_MAP.get(raw)
        if key:
            out[key] = {"mae_h24": float(row["MAE"]), "r2_h24": _get_r2(row)}
    return out


def build_table() -> pd.DataFrame:
    h1 = load_h1()
    h24 = load_h24()

    rows = []
    for key in DISPLAY_ORDER:
        meta = MODEL_META.get(key, {"setup": "?", "paradigm": "?"})
        h1d = h1.get(key, {})
        h24d = h24.get(key, {})

        mae_h1 = h1d.get("mae_h1", np.nan)
        mae_h24 = h24d.get("mae_h24", np.nan)
        r2_h1 = h1d.get("r2_h1", np.nan)
        r2_h24 = h24d.get("r2_h24", np.nan)

        if pd.notna(mae_h1) and pd.notna(mae_h24) and mae_h1 > 0:
            degradation = round(mae_h24 / mae_h1, 2)
        else:
            degradation = np.nan

        rows.append(
            {
                "model": key,
                "setup": meta["setup"],
                "paradigm": meta["paradigm"],
                "mae_h1": round(mae_h1, 3) if pd.notna(mae_h1) else np.nan,
                "r2_h1": round(r2_h1, 4) if pd.notna(r2_h1) else np.nan,
                "mae_h24": round(mae_h24, 3) if pd.notna(mae_h24) else np.nan,
                "r2_h24": round(r2_h24, 4) if pd.notna(r2_h24) else np.nan,
                "degradation_factor": degradation,
                "note": MODEL_NOTES.get(key, ""),
            }
        )

    return pd.DataFrame(rows)


def print_table(df: pd.DataFrame) -> None:
    print("\n" + "=" * 100)
    print("HORIZON SENSITIVITY TABLE — MAE (kWh) H+1 vs H+24 (Drammen, 44 buildings)")
    print("=" * 100)
    print(
        f"{'Model':<22} {'Setup':<5} {'H+1 MAE':>8} {'H+1 R²':>8} {'H+24 MAE':>9} "
        f"{'H+24 R²':>9} {'Degrad.':>8}  Note"
    )
    print("-" * 100)
    for _, row in df.iterrows():
        h1_mae = f"{row['mae_h1']:.3f}" if pd.notna(row["mae_h1"]) else "  —  "
        h1_r2 = f"{row['r2_h1']:.4f}" if pd.notna(row["r2_h1"]) else "  —  "
        h24_mae = f"{row['mae_h24']:.3f}" if pd.notna(row["mae_h24"]) else "  —  "
        h24_r2 = f"{row['r2_h24']:.4f}" if pd.notna(row["r2_h24"]) else "  —  "
        degrad = (
            f"{row['degradation_factor']:.2f}×" if pd.notna(row["degradation_factor"]) else "  —  "
        )
        note = row["note"][:40] if row["note"] else ""
        print(
            f"{row['model']:<22} {row['setup']:<5} {h1_mae:>8} {h1_r2:>8} "
            f"{h24_mae:>9} {h24_r2:>9} {degrad:>8}  {note}"
        )
    print("=" * 100)

    # Key statistics
    tree_mask = df["setup"] == "A"
    dl_mask = df["setup"] == "B"
    tree_dg = df.loc[tree_mask & df["degradation_factor"].notna(), "degradation_factor"]
    dl_dg = df.loc[dl_mask & df["degradation_factor"].notna(), "degradation_factor"]
    # Exclude LSTM convergence failure from DL stats
    dl_dg_sane = df.loc[
        dl_mask & df["degradation_factor"].notna() & (df["degradation_factor"] < 5),
        "degradation_factor",
    ]

    print(
        f"\nSetup A (Trees):      degradation range {tree_dg.min():.2f}× – {tree_dg.max():.2f}×  "
        f"(mean {tree_dg.mean():.2f}×)"
    )
    print(
        f"Setup B (DL, sane):   degradation range {dl_dg_sane.min():.2f}× – {dl_dg_sane.max():.2f}×  "
        f"(mean {dl_dg_sane.mean():.2f}×)  [LSTM convergence failure excluded]"
    )
    print(
        f"LSTM at H+24:         {df.loc[df['model'] == 'LSTM', 'degradation_factor'].values[0]:.1f}×  "
        f"(catastrophic convergence failure)"
    )


if __name__ == "__main__":
    df = build_table()
    out_path = RESULTS_DIR / "horizon_sensitivity.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved → {out_path}")
    print_table(df)
