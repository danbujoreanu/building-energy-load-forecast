"""
data.splits
===========
Produces chronological train / validation / test splits that respect
building boundaries — no data leakage across time or buildings.

Split strategy (from config.yaml)
----------------------------------
    train : everything up to ``train_end``
    val   : ``train_end`` < t ≤ ``val_end``
    test  : everything after ``val_end``

Public API
----------
    make_splits(df, cfg, target, processed_dir) -> dict
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def make_splits(
    df: pd.DataFrame,
    cfg: dict[str, Any],
    target: str | None = None,
    processed_dir: str | Path | None = None,
) -> dict[str, pd.DataFrame | np.ndarray | StandardScaler]:
    """Create train / val / test splits and fit a StandardScaler on train.

    Parameters
    ----------
    df:
        Model-ready MultiIndex (building_id, timestamp) DataFrame.
    cfg:
        Full config dict.
    target:
        Target column name.  Defaults to ``cfg["data"]["target_column"]``.
    processed_dir:
        If provided, persists all split artefacts (CSV + scaler.pkl) here.

    Returns
    -------
    dict with keys:
        X_train, y_train, X_val, y_val, X_test, y_test, scaler
    """
    target = target or cfg["data"]["target_column"]
    train_end = pd.Timestamp(cfg["splits"]["train_end"], tz="Europe/Oslo")
    val_end   = pd.Timestamp(cfg["splits"]["val_end"],   tz="Europe/Oslo")

    ts = df.index.get_level_values("timestamp")

    train_mask = ts <= train_end
    val_mask   = (ts > train_end) & (ts <= val_end)
    test_mask  = ts > val_end

    for label, mask in [("train", train_mask), ("val", val_mask), ("test", test_mask)]:
        count = mask.sum()
        if count == 0:
            logger.warning("Split '%s' is empty — check dates in config.yaml", label)
        else:
            logger.info("Split %-6s: %d rows", label, count)

    # ── Feature / target separation ───────────────────────────────────────────
    # Drop non-numeric or categorical columns that can't be fed to models
    drop_cols = [target, "building_category", "energy_label",
                 "sh_heat_source", "dhw_heat_source", "notes"]
    feature_cols = [c for c in df.columns if c not in drop_cols]

    X_train = df.loc[train_mask, feature_cols]  # noqa: N806
    y_train = df.loc[train_mask, target]
    X_val   = df.loc[val_mask,   feature_cols]  # noqa: N806
    y_val   = df.loc[val_mask,   target]
    X_test  = df.loc[test_mask,  feature_cols]  # noqa: N806
    y_test  = df.loc[test_mask,  target]

    # ── Impute remaining NaN with training-set median (no data leakage) ──────
    # Weather gaps > 3 h and missing metadata are filled with column medians
    # computed from X_train only and then applied to val/test.
    train_medians = X_train.median()
    X_train = X_train.fillna(train_medians)  # noqa: N806
    X_val   = X_val.fillna(train_medians)  # noqa: N806
    X_test  = X_test.fillna(train_medians)  # noqa: N806

    # ── Fit scaler on train only (avoid data leakage) ─────────────────────────
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(  # noqa: N806
        scaler.fit_transform(X_train),
        index=X_train.index,
        columns=X_train.columns,
    )
    X_val_scaled = pd.DataFrame(  # noqa: N806
        scaler.transform(X_val),
        index=X_val.index,
        columns=X_val.columns,
    )
    X_test_scaled = pd.DataFrame(  # noqa: N806
        scaler.transform(X_test),
        index=X_test.index,
        columns=X_test.columns,
    )

    splits = {
        "X_train": X_train_scaled,
        "y_train": y_train,
        "X_val":   X_val_scaled,
        "y_val":   y_val,
        "X_test":  X_test_scaled,
        "y_test":  y_test,
        "scaler":  scaler,
    }

    # ── Persist ───────────────────────────────────────────────────────────────
    if processed_dir is not None:
        out = Path(processed_dir) / "splits"
        out.mkdir(parents=True, exist_ok=True)
        for name, obj in splits.items():
            if isinstance(obj, pd.DataFrame):
                obj.to_parquet(out / f"{name}.parquet")
            elif isinstance(obj, pd.Series):
                # Series.to_parquet() not available in all pandas versions
                obj.to_frame().to_parquet(out / f"{name}.parquet")
            elif isinstance(obj, StandardScaler):
                with open(out / "scaler.pkl", "wb") as fh:
                    pickle.dump(obj, fh)
        logger.info("Splits saved → %s", out)

    return splits


def load_splits(processed_dir: str | Path) -> dict:
    """Re-load persisted splits without rerunning the pipeline."""
    out = Path(processed_dir) / "splits"
    splits = {}
    for name in ["X_train", "y_train", "X_val", "y_val", "X_test", "y_test"]:
        splits[name] = pd.read_parquet(out / f"{name}.parquet")
    with open(out / "scaler.pkl", "rb") as fh:
        splits["scaler"] = pickle.load(fh)  # noqa: S301
    return splits
