#!/usr/bin/env python
"""
run_grand_ensemble.py
=====================
Executes the Grand Ensemble of the two best paradigms:
- Setup A Champion: LightGBM (Engineered Tabular Features)
- Setup C Champion: PatchTST (Raw Sequence Data)

This script aligns predictions by (building_id, timestamp) for a fair point-to-point stack.
"""

import logging
from pathlib import Path

import joblib
import pandas as pd
from neuralforecast import NeuralForecast
from neuralforecast.models import PatchTST

from energy_forecast.data.raw_sequence import build_raw_sequences
from energy_forecast.data.splits import make_splits
from energy_forecast.evaluation import evaluate
from energy_forecast.features.selection import select_features
from energy_forecast.features.temporal import build_temporal_features
from energy_forecast.utils import load_config, set_global_seed

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Calculate project root (assuming script is in project_root/scripts/)
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

def main():
    # Use absolute paths relative to PROJECT_ROOT
    cfg = load_config(PROJECT_ROOT / "config/config.yaml")
    set_global_seed(cfg.get("seed", 42))

    city = cfg.get("city", "drammen")
    lookback = cfg["sequence"]["lookback"]
    horizon = cfg["sequence"]["horizon"]
    target_col = cfg["data"]["target_column"]

    # Paths
    proc_dir = PROJECT_ROOT / Path(cfg["paths"]["processed"])
    model_ready_path = proc_dir / "model_ready.parquet"
    model_dir = PROJECT_ROOT / "outputs/models"
    results_dir = PROJECT_ROOT / "outputs/results"

    logger.info("--- Phase 1: Data Preparation ---")
    if not model_ready_path.exists():
        logger.error(f"Processed data not found at {model_ready_path}. Please run pipeline first.")
        return
    df = pd.read_parquet(model_ready_path)
    ts = df.index.get_level_values("timestamp")
    train_end = pd.Timestamp(cfg["splits"]["train_end"], tz="Europe/Oslo")
    val_end   = pd.Timestamp(cfg["splits"]["val_end"],   tz="Europe/Oslo")

    # --- MODEL A: LightGBM (Setup A) ---
    logger.info("--- Phase 2: Generating Setup A Predictions (LightGBM) ---")
    df_feat = build_temporal_features(df, cfg)
    splits_a = make_splits(df_feat, cfg, target_col)
    X_tr_a = splits_a["X_train"]  # noqa: N806
    y_tr_a = splits_a["y_train"]
    X_v_a  = splits_a["X_val"]  # noqa: N806
    X_te_a = splits_a["X_test"]  # noqa: N806
    y_te_a = splits_a["y_test"]

    _, _, X_te_fs, _ = select_features(X_tr_a, y_tr_a, X_v_a, X_te_a, cfg)  # noqa: N806

    lgbm_model_path = model_dir / f"{city}_LightGBM_{cfg.get('date_suffix', '2026-03-05')}.joblib"
    if not lgbm_model_path.exists():
        # Fallback to look for ANY LightGBM joblib
        logger.warning(f"LightGBM model not found at {lgbm_model_path}. Searching for fallback...")
        matches = list(model_dir.glob(f"{city}_LightGBM_*.joblib"))
        if matches:
            lgbm_model_path = sorted(matches)[-1]
            logger.info(f"Using fallback: {lgbm_model_path}")
        else:
            logger.error("No LightGBM model found.")
            return

    lgbm = joblib.load(lgbm_model_path)
    preds_raw_a = lgbm.predict(X_te_fs)

    # Create a DataFrame for aligned predictions
    # y_te_a is pd.Series with MultiIndex (building_id, timestamp)
    df_preds_a = pd.DataFrame({
        "pred_a": preds_raw_a,
        "y": y_te_a.values
    }, index=y_te_a.index)

    # --- MODEL C: PatchTST (Setup C) ---
    logger.info("--- Phase 3: Generating Setup C Predictions (Patch_TST) ---")
    feature_cols = [target_col, "Temperature_Outdoor_C", "Global_Solar_Horizontal_Radiation_W_m2"]
    df_train_c = df[ts <= train_end].copy()
    df_val_c   = df[(ts > train_end) & (ts <= val_end)].copy()
    df_test_c  = df[ts > val_end].copy()

    for col in feature_cols:
        med = df_train_c[col].median()
        df_train_c[col] = df_train_c[col].fillna(med)
        df_val_c[col]   = df_val_c[col].fillna(med)
        df_test_c[col]  = df_test_c[col].fillna(med)

    res = build_raw_sequences(df_train_c, df_val_c, df_test_c, target_col, feature_cols, lookback, horizon)
    # Scalers needed for inverse
    scaler_y = res[7]

    def _prep_nf(df_data):
        df_scaled = df_data.copy()
        # Scale X columns
        df_scaled[feature_cols] = res[6].transform(df_scaled[feature_cols].values)
        df_nf = df_scaled.reset_index()
        df_nf = df_nf.rename(columns={"building_id": "unique_id", "timestamp": "ds", target_col: "y"})
        cols = ["unique_id", "ds", "y"] + [c for c in feature_cols if c != target_col]
        return df_nf[cols].sort_values(by=["unique_id", "ds"]).reset_index(drop=True)

    nf_train = _prep_nf(df_train_c)
    nf_test = _prep_nf(df_test_c)
    nf_full = pd.concat([nf_train, nf_test]).reset_index(drop=True)

    patch_model = PatchTST(h=horizon, input_size=lookback, max_steps=500, batch_size=64, scaler_type="identity")
    nf = NeuralForecast(models=[patch_model], freq="h")
    nf.fit(df=nf_train, val_size=24)

    b_ids = df_test_c.index.get_level_values("building_id").unique()
    num_test_steps = len(df_test_c.xs(b_ids[0], level="building_id"))
    n_windows = num_test_steps - horizon + 1

    cv_df = nf.cross_validation(df=nf_full, step_size=1, n_windows=n_windows, refit=0)

    # cv_df has columns: [unique_id, ds, cutoff, PatchTST, y]
    # unique_id is building_id, ds is timestamp
    # IMPORTANT: We take the first predicted step of the window to align with point forecasts
    cv_df = cv_df.rename(columns={"unique_id": "building_id", "ds": "timestamp"})
    cv_df["pred_c_raw"] = cv_df["PatchTST"]

    # Scale back
    cv_df["pred_c"] = scaler_y.inverse_transform(cv_df[["pred_c_raw"]].values)

    # Align by join
    logger.info("Aligning predictions by join...")
    df_final = df_preds_a.join(cv_df.set_index(["building_id", "timestamp"])[["pred_c"]], how="inner")

    logger.info(f"Aligned samples: {len(df_final)}")

    p_a = df_final["pred_a"].values
    p_c = df_final["pred_c"].values
    y_gold = df_final["y"].values

    # --- Phase 4: Ensemble ---
    # We include 0.0 (Pure PatchTST) and 1.0 (Pure LGBM) as baselines
    weights = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
    ensemble_results = []

    for alpha in weights:
        p_ens = alpha * p_a + (1 - alpha) * p_c
        metrics = evaluate(y_gold, p_ens, model_name=f"GrandEnsemble_A{int(alpha*100)}_C{int((1-alpha)*100)}")
        ensemble_results.append(metrics)
        logger.info(f"Alpha {alpha}: MAE {metrics['MAE']:.3f} | R2 {metrics['R2']:.3f}")

    df_ens = pd.DataFrame(ensemble_results)
    metrics_file = results_dir / "final_metrics.csv"
    if metrics_file.exists():
        existing = pd.read_csv(metrics_file, index_col=0)
        combined = pd.concat([existing, df_ens], ignore_index=True).drop_duplicates(subset=["model"], keep="last")
        combined.to_csv(metrics_file)
    else:
        df_ens.to_csv(metrics_file)

    logger.info("Grand Ensemble finished! Index-aligned results saved.")

if __name__ == "__main__":
    main()
