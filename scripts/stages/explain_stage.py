"""
explain_stage.py
================
Stage 4: SHAP explainability on the top-3 tree-based models.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run(cfg: dict) -> None:
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

    proc_dir = Path(cfg["paths"]["processed"]) / cfg["city"] / "splits"
    fig_dir = Path(cfg["paths"]["outputs"]["figures"])

    logger.info("── Stage 4: SHAP Explainability ────────────────────")

    X_train = pd.read_parquet(proc_dir / "X_train_fs.parquet")  # noqa: N806
    y_train = pd.read_parquet(proc_dir / "y_train.parquet").squeeze()
    X_val = pd.read_parquet(proc_dir / "X_val_fs.parquet")  # noqa: N806
    y_val = pd.read_parquet(proc_dir / "y_val.parquet").squeeze()
    X_test = pd.read_parquet(proc_dir / "X_test_fs.parquet")  # noqa: N806

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
            n_samples=500,  # subsample for speed; increase for publication
        )

    logger.info("Stage 4 complete. SHAP plots → %s/shap/", fig_dir)
