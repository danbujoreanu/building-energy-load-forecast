#!/usr/bin/env python
"""
run_pipeline.py
===============
Full end-to-end pipeline orchestrator.

Usage
-----
    # Full run on Drammen (all models)
    python scripts/run_pipeline.py --city drammen

    # Skip slow models (CNN-LSTM, TFT) — fast development run
    python scripts/run_pipeline.py --city drammen --skip-slow

    # Override config city from CLI
    python scripts/run_pipeline.py --city oslo

Architecture note
-----------------
This is the Task Orchestrator (MSc Engineering & AI Systems lecture) —
it coordinates independent pipeline stages without them knowing about each other.
"""

import argparse
import logging
import time
from pathlib import Path

from energy_forecast.utils import load_config, setup_logging, set_global_seed

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Building Energy Load Forecast — full pipeline"
    )
    parser.add_argument(
        "--city",
        choices=["drammen", "oslo"],
        default=None,
        help="Dataset city. Overrides config.yaml if provided.",
    )
    parser.add_argument(
        "--skip-slow",
        action="store_true",
        help="Skip slow models: CNN-LSTM and TFT.",
    )
    parser.add_argument(
        "--stages",
        nargs="+",
        choices=["eda", "features", "training", "explain"],
        default=["eda", "features", "training"],
        help="Which pipeline stages to run (default: all except explain).",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config YAML (default: auto-detected config/config.yaml).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING"],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    cfg = load_config(args.config)
    if args.city:
        cfg["city"] = args.city

    set_global_seed(cfg.get("seed", 42))

    city = cfg["city"]
    logger.info("=" * 60)
    logger.info("Building Energy Load Forecast Pipeline")
    logger.info("City: %s | Skip slow: %s | Stages: %s", city, args.skip_slow, args.stages)
    logger.info("=" * 60)

    t0 = time.perf_counter()

    # ── Stage 1: EDA & Data Loading ───────────────────────────────────────────
    if "eda" in args.stages:
        _run_eda(cfg)

    # ── Stage 2: Feature Engineering ─────────────────────────────────────────
    if "features" in args.stages:
        _run_features(cfg)

    # ── Stage 3: Model Training & Evaluation ─────────────────────────────────
    if "training" in args.stages:
        _run_training(cfg, skip_slow=args.skip_slow)

    # ── Stage 4: SHAP Explainability ─────────────────────────────────────────
    if "explain" in args.stages:
        _run_explain(cfg)

    elapsed = time.perf_counter() - t0
    logger.info("=" * 60)
    logger.info("Pipeline complete in %.1f seconds (%.1f min)", elapsed, elapsed / 60)
    logger.info("Results → outputs/results/final_metrics.csv")
    logger.info("SHAP   → outputs/figures/shap/")
    logger.info("Figures → outputs/figures/")
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Stage runners
# ---------------------------------------------------------------------------

def _run_eda(cfg: dict) -> None:
    """Stage 1: Load raw data, preprocess, and save model-ready parquet."""
    from energy_forecast.data import load_city_data, build_model_ready_data

    city      = cfg["city"]
    raw_dir   = Path(cfg["paths"]["raw_data"][city])
    proc_dir  = Path(cfg["paths"]["processed"])

    logger.info("── Stage 1: EDA (%s) ──────────────────────────", city.upper())
    metadata, timeseries = load_city_data(city, raw_dir, cfg)

    # Save metadata
    meta_path = proc_dir / "metadata.parquet"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    metadata.to_parquet(meta_path)
    logger.info("Metadata saved → %s", meta_path)

    model_ready = build_model_ready_data(timeseries, metadata, cfg, proc_dir)

    # Generate EDA figures
    from energy_forecast.visualization import (
        plot_building_profiles,
        plot_temperature_sensitivity,
        plot_seasonal_patterns,
        plot_missing_data,
    )
    fig_dir = Path(cfg["paths"]["outputs"]["figures"])
    plot_building_profiles(timeseries, save_path=fig_dir / "building_profiles.png")
    plot_temperature_sensitivity(timeseries, save_path=fig_dir / "temperature_sensitivity.png")
    plot_seasonal_patterns(timeseries, save_path=fig_dir / "seasonal_patterns.png")
    plot_missing_data(timeseries, save_path=fig_dir / "missing_data.png")

    logger.info("Stage 1 complete. Model-ready dataset: %d rows, %d cols", *model_ready.shape)


def _run_features(cfg: dict) -> None:
    """Stage 2: Build temporal features and run feature selection."""
    import pandas as pd
    from energy_forecast.features import build_temporal_features, select_features
    from energy_forecast.data import make_splits

    proc_dir = Path(cfg["paths"]["processed"])
    target   = cfg["data"]["target_column"]

    logger.info("── Stage 2: Feature Engineering ──────────────────")
    model_ready = pd.read_parquet(proc_dir / "model_ready.parquet")

    featured = build_temporal_features(model_ready, cfg, target)
    splits   = make_splits(featured, cfg, target, proc_dir)

    X_tr, y_tr = splits["X_train"], splits["y_train"]
    X_v,  y_v  = splits["X_val"],   splits["y_val"]
    X_te, y_te = splits["X_test"],  splits["y_test"]

    X_tr, X_v, X_te, kept = select_features(X_tr, y_tr, X_v, X_te, cfg)

    # Re-save selected splits
    splits_dir = proc_dir / "splits"
    splits_dir.mkdir(exist_ok=True)
    for name, obj in [("X_train_fs", X_tr), ("X_val_fs", X_v), ("X_test_fs", X_te),
                      ("y_train", y_tr), ("y_val", y_v), ("y_test", y_te)]:
        # Series.to_parquet() not available in all pandas versions — use to_frame()
        if isinstance(obj, pd.Series):
            obj.to_frame().to_parquet(splits_dir / f"{name}.parquet")
        else:
            obj.to_parquet(splits_dir / f"{name}.parquet")

    logger.info("Stage 2 complete. Selected %d features.", len(kept))


def _run_training(cfg: dict, skip_slow: bool = False) -> None:
    """Stage 3: Train all models, evaluate, and save results."""
    import pandas as pd
    from energy_forecast.models import NaiveModel, SeasonalNaiveModel, MeanModel, SklearnForecaster, StackingEnsemble
    from energy_forecast.models.sklearn_models import build_sklearn_models
    from energy_forecast.evaluation import compare_models, evaluate
    from energy_forecast.evaluation.metrics import save_per_building_metrics
    from energy_forecast.visualization import plot_model_comparison, plot_predictions_vs_actual

    proc_dir  = Path(cfg["paths"]["processed"]) / "splits"
    res_dir   = Path(cfg["paths"]["outputs"]["results"])
    fig_dir   = Path(cfg["paths"]["outputs"]["figures"])
    res_dir.mkdir(parents=True, exist_ok=True)

    logger.info("── Stage 3: Model Training ────────────────────────")

    X_train = pd.read_parquet(proc_dir / "X_train_fs.parquet")
    y_train = pd.read_parquet(proc_dir / "y_train.parquet").squeeze()
    X_val   = pd.read_parquet(proc_dir / "X_val_fs.parquet")
    y_val   = pd.read_parquet(proc_dir / "y_val.parquet").squeeze()
    X_test  = pd.read_parquet(proc_dir / "X_test_fs.parquet")
    y_test  = pd.read_parquet(proc_dir / "y_test.parquet").squeeze()

    # Extract building_ids and timestamps for daily-peak and per-building metrics.
    # y_test has a MultiIndex (building_id, timestamp); both levels are needed by
    # evaluate() to compute daily_peak_mae and per-building breakdowns.
    test_bids = y_test.index.get_level_values("building_id")
    test_ts   = y_test.index.get_level_values("timestamp")

    results = []
    fitted_models: dict = {}
    train_times: dict = {}   # {model_name: training_seconds}

    # ── Baselines ─────────────────────────────────────────────────────────────
    for model in [NaiveModel(), SeasonalNaiveModel(), MeanModel()]:
        t0 = time.time()
        model.fit(X_train, y_train)
        train_times[model.name] = round(time.time() - t0, 1)
        preds = model.predict(X_test)
        results.append(evaluate(y_test, preds, model.name,
                                building_ids=test_bids, timestamps=test_ts))
        fitted_models[model.name] = model

    # ── Sklearn models ────────────────────────────────────────────────────────
    for name, model in build_sklearn_models(cfg).items():
        t0 = time.time()
        model.fit(X_train, y_train, X_val, y_val)
        train_times[model.name] = round(time.time() - t0, 1)
        preds = model.predict(X_test)
        results.append(evaluate(y_test, preds, model.name,
                                building_ids=test_bids, timestamps=test_ts))
        fitted_models[model.name] = model

    # ── Deep learning (optional, slow) ────────────────────────────────────────
    slow_models = cfg.get("slow_models", ["cnn_lstm", "tft"])
    if not skip_slow or "lstm" not in slow_models:
        _train_dl_model("lstm", cfg, X_train, y_train, X_val, y_val, X_test, y_test, results, fitted_models, train_times)
    if not skip_slow:
        _train_dl_model("cnn_lstm", cfg, X_train, y_train, X_val, y_val, X_test, y_test, results, fitted_models, train_times)
        _train_dl_model("gru", cfg, X_train, y_train, X_val, y_val, X_test, y_test, results, fitted_models, train_times)

    # ── TFT (very slow) ───────────────────────────────────────────────────────
    # Condition simplifies to: run TFT when not skip_slow
    if not skip_slow:
        try:
            from energy_forecast.models.tft import TFTForecaster
            tft = TFTForecaster(cfg)
            t0 = time.time()
            tft.fit(X_train, y_train, X_val, y_val)
            train_times["TFT"] = round(time.time() - t0, 1)
            preds = tft.predict(X_test)

            # TFT may return full-length preds (it uses training history as
            # encoder context) or trimmed preds (if encoder context is limited
            # to the test window).  Handle both cases.
            lookback = cfg.get("sequence", {}).get("lookback", 72)
            if len(preds) == len(y_test):
                y_tft = y_test
            else:
                y_tft = _trim_dl_targets(y_test, lookback)
                if len(preds) != len(y_tft):
                    raise ValueError(
                        f"TFT prediction length {len(preds)} does not match "
                        f"y_test ({len(y_test)}) or trimmed y_test ({len(y_tft)})."
                    )

            tft_bids = y_tft.index.get_level_values("building_id")
            tft_ts   = y_tft.index.get_level_values("timestamp")
            results.append(evaluate(y_tft, preds, "TFT",
                                    building_ids=tft_bids, timestamps=tft_ts))
            fitted_models["TFT"] = tft
            logger.info("TFT  n_eval=%d", len(y_tft))
        except Exception as exc:
            logger.warning("TFT training/evaluation failed: %s", exc)

    # ── Stacking ensemble ─────────────────────────────────────────────────────
    # Sklearn models only — DL models return trimmed-length predictions that
    # are incompatible with X_val for meta-feature generation.
    _DL_NAMES = {"LSTM", "GRU", "CNN-LSTM", "TFT"}
    _BASELINE_NAMES = {"Naive", "Seasonal Naive (24 h)", "Mean Baseline"}
    ensemble_base = {
        k: v for k, v in fitted_models.items()
        if k not in _BASELINE_NAMES and k not in _DL_NAMES
    }
    if len(ensemble_base) >= 2:
        try:
            ensemble = StackingEnsemble(ensemble_base, cfg)
            t0 = time.time()
            ensemble.fit(X_train, y_train, X_val, y_val)
            train_times[ensemble.name] = round(time.time() - t0, 1)
            preds = ensemble.predict(X_test)
            results.append(evaluate(y_test, preds, ensemble.name,
                                    building_ids=test_bids, timestamps=test_ts))
        except Exception as exc:
            logger.warning("Stacking ensemble failed: %s", exc)

    # ── Save results ──────────────────────────────────────────────────────────
    # Merge with existing final_metrics.csv if it exists to preserve Setup C / other runs
    metrics_path = res_dir / "final_metrics.csv"
    
    # Standardize column naming: our new results use 'model' (lowercase)
    comparison_to_save = comparison.copy()
    if "Model" in comparison_to_save.columns:
        comparison_to_save = comparison_to_save.rename(columns={"Model": "model"})
        
    if metrics_path.exists() and metrics_path.stat().st_size > 0:
        try:
            old_metrics = pd.read_csv(metrics_path, index_col=0)
            # Find the model column (might be 'model' or 'Model')
            model_col = "model" if "model" in old_metrics.columns else "Model"
            
            # Remove existing entries for the models we just ran to update them
            new_model_names = comparison_to_save["model"].tolist()
            old_metrics = old_metrics[~old_metrics[model_col].isin(new_model_names)]
            
            # Standardize old metrics column to lowercase 'model'
            if model_col == "Model":
                old_metrics = old_metrics.rename(columns={"Model": "model"})
            
            combined = pd.concat([old_metrics, comparison_to_save], ignore_index=True)
            combined.to_csv(metrics_path)
            logger.info("Merged results into %s", metrics_path)
            # Use combined for plot/log below
            comparison_final = combined
        except Exception as e:
            logger.warning("Failed to merge with existing metrics: %s. Overwriting.", e)
            comparison_to_save.to_csv(metrics_path)
            comparison_final = comparison_to_save
    else:
        comparison_to_save.to_csv(metrics_path)
        comparison_final = comparison_to_save
    
    logger.info("\n%s", comparison_final.to_string())

    # Per-building breakdown CSV (MISS-2): enables building-type analysis
    save_per_building_metrics(results, res_dir / "per_building_metrics.csv")

    # ── Plots ─────────────────────────────────────────────────────────────────
    plot_model_comparison(comparison, metric="MAE", save_path=fig_dir / "model_comparison_mae.png")
    plot_model_comparison(comparison, metric="RMSE", save_path=fig_dir / "model_comparison_rmse.png")

    # ── Save fitted models (MISS-9) ───────────────────────────────────────────
    # Persist model artefacts so predictions can be regenerated without
    # retraining.  Pattern varies by model family:
    #   TFT        → Lightning .ckpt  (trainer_.save_checkpoint)
    #   Keras DL   → .keras file      (model_.save)
    #   Sklearn    → .joblib          (joblib.dump of model.estimator)
    #   Ensemble   → .joblib          (joblib.dump of meta_learner_)
    import datetime
    import joblib as _joblib

    _today = datetime.date.today().isoformat()
    model_dir = Path(cfg["paths"]["outputs"]["models"])
    model_dir.mkdir(parents=True, exist_ok=True)
    city = cfg["city"]

    for mname, model in fitted_models.items():
        try:
            safe_name = mname.replace(" ", "_").replace("(", "").replace(")", "")
            stem = f"{city}_{safe_name}_{_today}"

            if hasattr(model, "trainer_") and model.trainer_ is not None:
                # TFT: Lightning trainer checkpoint — preserves weights + epoch
                ckpt_path = model_dir / f"{stem}.ckpt"
                model.trainer_.save_checkpoint(str(ckpt_path))
                logger.info("Saved Lightning checkpoint → %s", ckpt_path)

            elif hasattr(model, "model_") and model.model_ is not None:
                # Keras DL (LSTM / CNN-LSTM / GRU)
                keras_path = model_dir / f"{stem}.keras"
                model.model_.save(str(keras_path))
                logger.info("Saved Keras model → %s", keras_path)

            elif hasattr(model, "estimator"):
                # SklearnForecaster (Ridge, Lasso, RF, LightGBM, XGBoost)
                pkl_path = model_dir / f"{stem}.joblib"
                _joblib.dump(model.estimator, pkl_path)
                logger.info("Saved sklearn estimator → %s", pkl_path)

            elif hasattr(model, "meta_learner_") and model.meta_learner_ is not None:
                # Stacking / WeightedAverage ensemble — save meta-learner
                pkl_path = model_dir / f"{stem}_meta.joblib"
                _joblib.dump(model.meta_learner_, pkl_path)
                logger.info("Saved ensemble meta-learner → %s", pkl_path)

            else:
                # Baseline models (Naive, Seasonal Naive, Mean) are trivially
                # re-fittable and have no persisted state worth saving.
                logger.debug(
                    "No save handler for '%s' (type=%s) — skipping.",
                    mname, type(model).__name__,
                )

        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not save model '%s': %s", mname, exc)

    logger.info("Model artefacts saved → %s", model_dir)

    logger.info("Stage 3 complete. Results → %s", res_dir / "final_metrics.csv")


def _trim_dl_targets(y, lookback: int):
    """Drop the first ``lookback`` rows per building from y.

    Used for H+1 only. For H+24 multi-step evaluation, use
    _build_y_true_matrix() instead, which correctly handles building
    boundaries and returns a 2-D (n_samples, horizon) target matrix.
    """
    import pandas as pd  # noqa: PLC0415 (deferred import OK here)

    parts = []
    for bid in y.index.get_level_values("building_id").unique():
        y_b = y.xs(bid, level="building_id")
        parts.append(y_b.iloc[lookback:])
    return pd.concat(parts)


def _build_y_true_matrix(y, lookback: int, horizon: int) -> "np.ndarray":
    """Build 2-D y_true matrix aligned with DL sliding-window predictions.

    For multi-step (H+24) evaluation, each prediction window k at position
    ``lookback + k`` within building b covers horizon steps ahead::

        y_true_matrix[global_k, h] = y_b[lookback + k + h]   h = 0..horizon-1

    Building boundaries are strictly respected — windows never cross buildings.
    The returned shape (n_samples, horizon) matches the shape returned by
    LSTMForecaster.predict() / GRUForecaster.predict() / CNNLSTMForecaster.predict()
    when horizon > 1, so evaluate() can directly compute per-horizon MAE.

    Parameters
    ----------
    y        : MultiIndex Series (building_id, timestamp) — full y_test
    lookback : Encoder look-back length (rows per building to skip at start)
    horizon  : Number of future steps predicted per window
    """
    import numpy as np  # noqa: PLC0415
    parts = []
    for bid in y.index.get_level_values("building_id").unique():
        y_b = y.xs(bid, level="building_id").values
        n = len(y_b)
        # Valid window starts: i = lookback .. n - horizon (inclusive)
        for i in range(lookback, n - horizon + 1):
            parts.append(y_b[i: i + horizon])
    return np.array(parts, dtype=np.float32)  # (n_samples, horizon)


def _train_dl_model(arch, cfg, X_tr, y_tr, X_v, y_v, X_te, y_te, results, fitted_models, train_times=None):
    """Helper to train a single DL architecture with error handling.

    DL models use a sliding-window approach (see build_sequences) and cannot
    predict for the first ``lookback`` timesteps of each building.  We trim
    ``y_te`` to match the number of predictions before calling evaluate().
    """
    from energy_forecast.models.deep_learning import LSTMForecaster, CNNLSTMForecaster, GRUForecaster
    from energy_forecast.evaluation import evaluate

    cls_map = {"lstm": LSTMForecaster, "cnn_lstm": CNNLSTMForecaster, "gru": GRUForecaster}
    cls = cls_map.get(arch)
    if cls is None:
        return
    try:
        model = cls(cfg)
        t0 = time.time()
        model.fit(X_tr, y_tr, X_v, y_v)
        if train_times is not None:
            train_times[model.name] = round(time.time() - t0, 1)
        preds = model.predict(X_te)

        lookback = cfg.get("sequence", {}).get("lookback", 72)
        horizon  = cfg.get("sequence", {}).get("horizon",  1)

        if horizon > 1:
            # H+24 multi-step: build a 2-D y_true matrix (n_samples, horizon)
            # that respects building boundaries. evaluate() handles 2-D vs 2-D
            # correctly — computes global MAE + per-horizon MAE list.
            y_true_2d = _build_y_true_matrix(y_te, lookback, horizon)
            if y_true_2d.shape != preds.shape:
                logger.warning(
                    "%s shape mismatch: y_true=%s, preds=%s — skipping.",
                    arch.upper(), y_true_2d.shape, preds.shape,
                )
                return
            # building_ids/timestamps cannot be trivially aligned to the 2-D
            # window grid, so daily_peak_mae and per-building metrics are
            # skipped for DL H+24 (primary metrics MAE/RMSE/R² are still computed).
            results.append(evaluate(y_true_2d, preds, model.name))
            fitted_models[model.name] = model
            logger.info(
                "%s  n_windows=%d  horizon=%d  (2-D evaluation, building boundaries respected)",
                model.name, len(preds), horizon,
            )
        else:
            # H+1 single-step: trim leading lookback rows per building.
            y_te_aligned = _trim_dl_targets(y_te, lookback)
            if len(y_te_aligned) != len(preds):
                logger.warning(
                    "%s prediction length mismatch: y=%d, preds=%d — skipping.",
                    arch.upper(), len(y_te_aligned), len(preds),
                )
                return
            dl_bids = y_te_aligned.index.get_level_values("building_id")
            dl_ts   = y_te_aligned.index.get_level_values("timestamp")
            results.append(evaluate(y_te_aligned, preds, model.name,
                                    building_ids=dl_bids, timestamps=dl_ts))
            fitted_models[model.name] = model
            logger.info("%s  n_eval=%d (trimmed %d lookback rows per building)",
                        model.name, len(y_te_aligned), lookback)
    except Exception as exc:
        logger.warning("%s training failed: %s", arch.upper(), exc)


def _run_explain(cfg: dict) -> None:
    """Stage 4: SHAP explainability on the top-3 tree-based models.

    Produces four plots per model:
        - beeswarm  (global: feature importance + direction)
        - bar       (global: mean |SHAP|, cleaner for reports)
        - waterfall (local: single-prediction breakdown)
        - heatmap   (all-samples: patterns across test set)

    Also saves SHAP values as .npz for notebook post-analysis.

    Run independently after training:
        python scripts/run_pipeline.py --stages explain
    """
    import pandas as pd
    from energy_forecast.evaluation.explainability import explain_model
    from energy_forecast.models.sklearn_models import build_sklearn_models

    proc_dir = Path(cfg["paths"]["processed"]) / "splits"
    fig_dir  = Path(cfg["paths"]["outputs"]["figures"])

    logger.info("── Stage 4: SHAP Explainability ────────────────────")

    X_train = pd.read_parquet(proc_dir / "X_train_fs.parquet")
    y_train = pd.read_parquet(proc_dir / "y_train.parquet").squeeze()
    X_val   = pd.read_parquet(proc_dir / "X_val_fs.parquet")
    y_val   = pd.read_parquet(proc_dir / "y_val.parquet").squeeze()
    X_test  = pd.read_parquet(proc_dir / "X_test_fs.parquet")

    # Refit tree models (fast — RF ~2min, XGB/LGBM ~3s each)
    tree_models = {
        name: model
        for name, model in build_sklearn_models(cfg).items()
        if name in ("random_forest", "xgboost", "lightgbm")
    }

    for name, model in tree_models.items():
        logger.info("Fitting %s for SHAP analysis ...", name)
        model.fit(X_train, y_train, X_val, y_val)
        explain_model(
            model,
            X_train,
            X_test,
            save_dir=fig_dir,
            n_samples=500,   # subsample for speed; increase for publication
        )

    logger.info("Stage 4 complete. SHAP plots → %s/shap/", fig_dir)


if __name__ == "__main__":
    main()
