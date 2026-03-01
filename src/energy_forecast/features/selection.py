"""
features.selection
==================
Three-stage feature selection pipeline (matching the MSc thesis approach):

    Stage 1  Variance threshold — removes zero/near-zero variance features
    Stage 2  Correlation filter  — removes highly correlated duplicates
    Stage 3  LightGBM importance — keeps top-N most predictive features

Computational complexity note (from MSc NP lecture):
    Adding feature selection is O(n·p) extra work but reduces downstream
    model complexity significantly, justified by accuracy preservation.

Public API
----------
    select_features(X_train, y_train, X_val, X_test, cfg) -> tuple
"""

from __future__ import annotations

import logging
import re
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_selection import VarianceThreshold

logger = logging.getLogger(__name__)


def select_features(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    X_test: pd.DataFrame,
    cfg: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    """Run the three-stage feature selection pipeline.

    Parameters
    ----------
    X_train, y_train, X_val, X_test:
        Split DataFrames from ``data.splits``.
    cfg:
        Full config dict.

    Returns
    -------
    X_train_fs, X_val_fs, X_test_fs : pd.DataFrame
        Feature-selected versions of each split.
    selected_features : list[str]
        Names of the retained feature columns.
    """
    sel_cfg = cfg["features"]["selection"]
    var_threshold  = sel_cfg.get("variance_threshold", 0.0)
    corr_threshold = sel_cfg.get("correlation_threshold", 0.99)
    n_keep         = sel_cfg.get("n_features_lgbm", 35)

    logger.info("Starting feature selection with %d initial features", X_train.shape[1])

    # ── Stage 1: Variance threshold ────────────────────────────────────────────
    X_train, X_val, X_test, kept = _variance_filter(
        X_train, X_val, X_test, threshold=var_threshold
    )
    logger.info("After variance filter: %d features", len(kept))

    # ── Stage 2: Correlation filter ────────────────────────────────────────────
    X_train, X_val, X_test, kept = _correlation_filter(
        X_train, X_val, X_test, threshold=corr_threshold
    )
    logger.info("After correlation filter: %d features", len(kept))

    # ── Stage 3: LightGBM importance ──────────────────────────────────────────
    X_train, X_val, X_test, kept = _lgbm_importance_filter(
        X_train, y_train, X_val, X_test, n_keep=n_keep, cfg=cfg
    )
    logger.info("After LightGBM importance filter: %d features retained", len(kept))

    return X_train, X_val, X_test, kept


# ---------------------------------------------------------------------------
# Stage 1: Variance threshold
# ---------------------------------------------------------------------------

def _variance_filter(
    X_train: pd.DataFrame,
    X_val: pd.DataFrame,
    X_test: pd.DataFrame,
    threshold: float = 0.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    selector = VarianceThreshold(threshold=threshold)
    selector.fit(X_train)
    kept = X_train.columns[selector.get_support()].tolist()
    return X_train[kept], X_val[kept], X_test[kept], kept


# ---------------------------------------------------------------------------
# Stage 2: Correlation filter
# ---------------------------------------------------------------------------

def _correlation_filter(
    X_train: pd.DataFrame,
    X_val: pd.DataFrame,
    X_test: pd.DataFrame,
    threshold: float = 0.99,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    """Remove features that are pairwise-correlated above ``threshold``.

    **Tie-breaking rule (deterministic):**
    The Pearson correlation matrix is computed on the training set and the
    *upper triangle* (k=1) is examined.  For any pair (A, B) where
    ``|corr(A, B)| > threshold``, column **B** (the *later* column in the
    DataFrame column order) is marked for removal.

    This means the *first* column of any correlated pair is always retained
    and the *second* is dropped.  The rule is deterministic — no random
    tie-breaking — and depends only on the order in which features appear in
    the DataFrame (which is fixed by ``features/temporal.py``).

    Practically, this tends to retain the *raw* or *earlier-engineered*
    feature (e.g. ``lag_24h``) and drop a redundant variant (e.g.
    ``lag_25h`` if they are near-perfectly correlated for a given dataset).
    """
    corr_matrix = X_train.corr().abs()
    upper = corr_matrix.where(
        np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
    )
    to_drop = [col for col in upper.columns if any(upper[col] > threshold)]
    kept = [c for c in X_train.columns if c not in to_drop]
    logger.debug("Correlation filter dropped: %s", to_drop[:10])
    return X_train[kept], X_val[kept], X_test[kept], kept


# ---------------------------------------------------------------------------
# Stage 3: LightGBM importance
# ---------------------------------------------------------------------------

def _lgbm_importance_filter(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    X_test: pd.DataFrame,
    n_keep: int,
    cfg: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    """Train a quick LightGBM and keep the top-N features by importance."""
    try:
        import lightgbm as lgb
    except ImportError as e:
        raise ImportError("lightgbm is required for feature selection.") from e

    # Sanitise column names (LightGBM dislikes special characters)
    clean_names = _sanitise_names(X_train.columns.tolist())
    X_tr = X_train.copy()
    X_tr.columns = clean_names

    model = lgb.LGBMRegressor(
        n_estimators=200,
        learning_rate=0.1,
        max_depth=6,
        num_leaves=31,
        n_jobs=-1,
        random_state=cfg.get("seed", 42),
        verbosity=-1,
    )
    model.fit(X_tr, y_train.values)

    importance = pd.Series(model.feature_importances_, index=clean_names)
    top_clean = importance.nlargest(n_keep).index.tolist()

    # Map back to original names
    name_map = dict(zip(clean_names, X_train.columns.tolist()))
    kept = [name_map[c] for c in top_clean]

    return X_train[kept], X_val[kept], X_test[kept], kept


def _sanitise_names(names: list[str]) -> list[str]:
    """Remove special characters that LightGBM cannot handle in column names."""
    return [re.sub(r"[^\w]", "_", n) for n in names]
