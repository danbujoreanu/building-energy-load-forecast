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

    results = []
    fitted_models: dict = {}
    train_times: dict = {}   # {model_name: training_seconds}

    # ── Baselines ─────────────────────────────────────────────────────────────
    for model in [NaiveModel(), SeasonalNaiveModel(), MeanModel()]:
        t0 = time.time()
        model.fit(X_train, y_train)
        train_times[model.name] = round(time.time() - t0, 1)
        preds = model.predict(X_test)
        results.append(evaluate(y_test, preds, model.name))
        fitted_models[model.name] = model

    # ── Sklearn models ────────────────────────────────────────────────────────
    for name, model in build_sklearn_models(cfg).items():
        t0 = time.time()
        model.fit(X_train, y_train, X_val, y_val)
        train_times[model.name] = round(time.time() - t0, 1)
        preds = model.predict(X_test)
        results.append(evaluate(y_test, preds, model.name))
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

            results.append(evaluate(y_tft, preds, "TFT"))
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
            results.append(evaluate(y_test, preds, ensemble.name))
        except Exception as exc:
            logger.warning("Stacking ensemble failed: %s", exc)

    # ── Save results ──────────────────────────────────────────────────────────
    comparison = compare_models(results)
    # Attach training time (seconds) — join on Model name
    comparison["train_time_s"] = comparison["Model"].map(train_times)
    comparison.to_csv(res_dir / "final_metrics.csv")
    logger.info("\n%s", comparison.to_string())

    # ── Plots ─────────────────────────────────────────────────────────────────
    plot_model_comparison(comparison, metric="MAE", save_path=fig_dir / "model_comparison_mae.png")
    plot_model_comparison(comparison, metric="RMSE", save_path=fig_dir / "model_comparison_rmse.png")

    logger.info("Stage 3 complete. Results → %s", res_dir / "final_metrics.csv")


def _trim_dl_targets(y, lookback: int):
    """Drop the first ``lookback`` rows per building from y.

    Sliding-window DL models cannot produce a prediction for the first
    ``lookback`` timesteps of each building (not enough history).  The
    evaluate() call requires y_true and y_pred to have the same length,
    so we trim the corresponding rows from y_true before comparing.
    """
    import pandas as pd  # noqa: PLC0415 (deferred import OK here)

    parts = []
    for bid in y.index.get_level_values("building_id").unique():
        y_b = y.xs(bid, level="building_id")
        parts.append(y_b.iloc[lookback:])
    return pd.concat(parts)


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

        # Align y_te: DL models cannot predict the first `lookback` steps per
        # building — trim those rows so len(y_te_aligned) == len(preds).
        lookback = cfg.get("sequence", {}).get("lookback", 72)
        y_te_aligned = _trim_dl_targets(y_te, lookback)

        if len(y_te_aligned) != len(preds):
            logger.warning(
                "%s prediction length mismatch: y=%d, preds=%d — skipping.",
                arch.upper(), len(y_te_aligned), len(preds),
            )
            return

        results.append(evaluate(y_te_aligned, preds, model.name))
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
