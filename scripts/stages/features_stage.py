"""
features_stage.py
=================
Stage 2: Build temporal features and run feature selection.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run(cfg: dict) -> None:
    """Stage 2: Build temporal features and run feature selection."""
    import pandas as pd

    from energy_forecast.data import make_splits
    from energy_forecast.features import build_temporal_features, select_features

    proc_dir = Path(cfg["paths"]["processed"]) / cfg["city"]
    target   = cfg["data"]["target_column"]

    logger.info("── Stage 2: Feature Engineering ──────────────────")
    model_ready = pd.read_parquet(proc_dir / "model_ready.parquet")

    featured = build_temporal_features(model_ready, cfg, target)
    splits   = make_splits(featured, cfg, target, proc_dir)

    X_tr, y_tr = splits["X_train"], splits["y_train"]  # noqa: N806
    X_v,  y_v  = splits["X_val"],   splits["y_val"]  # noqa: N806
    X_te, y_te = splits["X_test"],  splits["y_test"]  # noqa: N806

    X_tr, X_v, X_te, kept = select_features(X_tr, y_tr, X_v, X_te, cfg)  # noqa: N806

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
