"""
models.ensemble
===============
Ensemble methods that combine predictions from multiple base learners.

Two implementations aligned with the H+24 Paradigm Split:

StackingEnsemble (Intra-Paradigm Stacking for Setup A)
    Base learners → meta-features → meta-learner trained on those features.
    Final prediction = meta_learner(base_preds on test).

    **Out-of-Fold (OOF)** (default, ``oof_folds: 5``) is the gold standard used
    for Setup A (Tree models). TimeSeriesSplit is used on the training set.
    Base models are cloned, retrained on the fold's training portion, and
    predict on the validation portion to prevent overfitting.

    Because Tree models are extremely fast, building 5 OOF folds is computationally
    cheap. It allows the Ridge meta-learner to unbiasedly learn exactly how much
    to trust LightGBM vs. XGBoost. Deep Learning models are computationally
    infeasible for OOF stacking without a cluster.

WeightedAverageEnsemble (Cross-Paradigm Grand Ensemble for A + C)
    Weights predictions based on a predefined or inversely-proportional metric.
    This includes Alpha-blending (e.g., 0.9 Setup A + 0.1 Setup C).

    This approach is mathematically necessary when computationally heavy models
    (like PatchTST / TFT) cannot be generated via 5-fold OOF. By sweeping
    alpha weights, we establish the 'trust spectrum' between domain-engineered
    tabular features and raw autonomous pattern representations.

This implements the Task Orchestration pattern: each ensemble coordinates
independent base models without them knowing about each other.
"""  # noqa: W291

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from .base import BaseForecaster

logger = logging.getLogger(__name__)


_META_LABELS: dict[str, str] = {
    "ridge": "Ridge",
    "lightgbm": "LGBM",
}


class StackingEnsemble(BaseForecaster):
    """Stacking ensemble with a configurable meta-learner.

    The instance ``name`` attribute is set from config at construction time
    so it matches the thesis naming convention:
        - "Stacking Ensemble (Ridge meta)"
        - "Stacking Ensemble (LGBM meta)"

    Meta-feature generation is controlled by ``oof_folds`` in config:
        - ``oof_folds > 0`` → time-aware OOF stacking on X_train (recommended)
        - ``oof_folds == 0`` → legacy fixed-validation stacking on X_val
    """

    def __init__(
        self,
        base_models: dict[str, BaseForecaster],
        cfg: dict[str, Any],
    ) -> None:
        """
        Parameters
        ----------
        base_models:
            Dict of {model_name: fitted BaseForecaster}.  Models must already
            be fitted before passing to the ensemble.
        cfg:
            Full config dict.
        """
        self.base_models = base_models
        self.cfg = cfg
        self.meta_learner_: Any = None
        self._base_names: list[str] = []

        meta_key = cfg["training"]["ensemble"].get("meta_learner", "ridge")
        meta_label = _META_LABELS.get(meta_key, meta_key.capitalize())
        self.name: str = f"Stacking Ensemble ({meta_label} meta)"

    def fit(
        self,
        X_train: pd.DataFrame,  # noqa: N803
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,  # noqa: N803
        y_val: pd.Series | None = None,
        **kwargs: Any,
    ) -> StackingEnsemble:
        """Train the meta-learner.

        Uses OOF stacking if ``oof_folds > 0`` (default), otherwise falls
        back to the legacy fixed-validation approach.

        Parameters
        ----------
        X_train, y_train:
            Full training set.  Required for OOF stacking.
        X_val, y_val:
            Validation set.  Required only when ``oof_folds == 0``.
        """
        ens_cfg = self.cfg["training"]["ensemble"]
        oof_folds = int(ens_cfg.get("oof_folds", 0))

        if oof_folds > 0:
            # ── OOF stacking ──────────────────────────────────────────────────
            logger.info("Stacking ensemble: OOF mode with %d time-aware folds.", oof_folds)
            meta_features, meta_targets = self._oof_meta_features(X_train, y_train, oof_folds)
        else:
            # ── Legacy fixed-validation stacking ──────────────────────────────
            if X_val is None or y_val is None:
                raise ValueError("StackingEnsemble requires X_val and y_val when oof_folds=0.")
            logger.info("Stacking ensemble: fixed-validation mode.")
            meta_features = self._generate_meta_features(X_val)
            meta_targets = y_val.values

        logger.info(
            "Meta-features shape: %s | training meta-learner on %d samples",
            meta_features.shape,
            len(meta_targets),
        )

        # ── Fit meta-learner ──────────────────────────────────────────────────
        if ens_cfg["meta_learner"] == "lightgbm":
            self.meta_learner_ = _build_lgbm_meta(ens_cfg, self.cfg.get("seed", 42))
        else:
            self.meta_learner_ = Ridge(alpha=ens_cfg["ridge_alpha"])

        self.meta_learner_.fit(meta_features, meta_targets)
        mode = "OOF" if oof_folds > 0 else "fixed-val"
        logger.info(
            "Stacking ensemble trained with %s meta-learner (%s).",
            ens_cfg["meta_learner"],
            mode,
        )
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        meta_features = self._generate_meta_features(X)
        return self.meta_learner_.predict(meta_features)

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _generate_meta_features(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        """Stack base model predictions as columns (used for val/test)."""
        preds: dict[str, np.ndarray] = {}
        for name, model in self.base_models.items():
            try:
                preds[name] = model.predict(X)
                self._base_names = list(preds.keys())
            except Exception as exc:  # noqa: BLE001
                logger.warning("Base model '%s' failed to predict: %s", name, exc)
        return np.column_stack(list(preds.values()))

    def _oof_meta_features(
        self,
        X_train: pd.DataFrame,  # noqa: N803
        y_train: pd.Series,
        oof_folds: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate OOF predictions using time-aware expanding-window splits.

        The data is a multi-building panel with a MultiIndex of the form
        ``(building_id, timestamp)``.  All buildings sharing the same timestamp
        are always placed in the same fold, so temporal ordering is fully
        preserved and there is no leakage across time.

        Implementation
        --------------
        1. Extract unique timestamps from ``X_train.index`` (last level).
        2. Apply ``sklearn.model_selection.TimeSeriesSplit`` to those timestamps.
        3. For each fold:
           a. Mask X_train rows by timestamp → fold train / fold val splits.
           b. Clone each sklearn-compatible base model (via ``_clone_forecaster``).
           c. Fit the clone on the fold-train portion.
           d. Predict on the fold-val portion → fill the global OOF array.
        4. Return rows where every model produced a prediction.

        Notes
        -----
        - Only models with a ``.estimator`` attribute (``SklearnForecaster``
          subclasses) can be cloned.  DL models are skipped with a warning.
        - The first fold's training rows are never in any validation set and
          are therefore excluded from the returned meta-features.  This is
          standard OOF practice and typically represents 1/(k+1) ≈ 17% of
          training data.

        Returns
        -------
        meta_features : np.ndarray, shape (n_valid_rows, n_models)
        meta_targets  : np.ndarray, shape (n_valid_rows,)
        """
        from sklearn.model_selection import TimeSeriesSplit

        model_names = list(self.base_models.keys())
        n_models = len(model_names)
        n_rows = len(X_train)

        # Timestamp level is always the last level of the MultiIndex.
        timestamps = X_train.index.get_level_values(-1).unique().sort_values()
        # gap=168: drop 1 week of timestamps between each train/val boundary.
        # Features like lag_168h and rolling_mean_168h are derived from the
        # training window, so the first 168h of each val fold are correlated
        # with the preceding training data. The gap prevents the meta-learner
        # from exploiting this boundary leakage.
        tss = TimeSeriesSplit(n_splits=oof_folds, gap=168)

        oof_preds = np.full((n_rows, n_models), np.nan)

        for fold_idx, (tr_ts_positions, val_ts_positions) in enumerate(tss.split(timestamps)):
            tr_ts = set(timestamps[tr_ts_positions].tolist())
            val_ts = set(timestamps[val_ts_positions].tolist())

            level_vals = X_train.index.get_level_values(-1)
            tr_mask = level_vals.isin(tr_ts)
            val_mask = level_vals.isin(val_ts)

            X_fold_tr = X_train[tr_mask]  # noqa: N806
            y_fold_tr = y_train[tr_mask]
            X_fold_val = X_train[val_mask]  # noqa: N806
            y_fold_val = y_train[val_mask]  # noqa: F841

            logger.info(
                "OOF fold %d/%d: train=%d rows, val=%d rows",
                fold_idx + 1,
                oof_folds,
                len(X_fold_tr),
                len(X_fold_val),
            )

            val_positions = np.where(val_mask)[0]

            for i, (mname, model) in enumerate(self.base_models.items()):
                cloned = _clone_forecaster(model)
                if cloned is None:
                    logger.warning(
                        "OOF: cannot clone model '%s' (not sklearn-compatible) — "
                        "column %d will remain NaN.",
                        mname,
                        i,
                    )
                    continue
                try:
                    # BUG-C6: Do NOT pass val data during OOF fitting.
                    # Passing X_fold_val triggers LightGBM/XGBoost early stopping
                    # optimised on the exact fold we then predict on — artificially
                    # inflating OOF accuracy (classic meta-learner leakage).
                    # AI Studio verdict: use fixed n_estimators, disable early stopping.
                    cloned.fit(X_fold_tr, y_fold_tr)
                    fold_preds = cloned.predict(X_fold_val)
                    oof_preds[val_positions, i] = fold_preds
                except Exception as exc:  # noqa: BLE001
                    logger.warning("OOF fold %d, model '%s' failed: %s", fold_idx + 1, mname, exc)

        # Only keep rows where every column has a valid OOF prediction.
        valid_mask = ~np.isnan(oof_preds).any(axis=1)
        n_valid = int(valid_mask.sum())
        logger.info(
            "OOF complete: %d / %d training rows covered (%.1f%%).",
            n_valid,
            n_rows,
            100.0 * n_valid / n_rows,
        )

        return oof_preds[valid_mask], y_train.values[valid_mask]


class WeightedAverageEnsemble(BaseForecaster):
    """Inverse-MAE weighted average ensemble.

    Weights are computed from each base model's MAE on the validation set:
        weight_i  = (1 / MAE_i) / sum(1 / MAE_j  for all j)

    This replicates the ``Weighted Avg Ensemble`` from the MSc thesis
    (validation MAE 4.081 kWh on the Drammen test set).

    Parameters
    ----------
    base_models:
        Dict of {model_name: fitted BaseForecaster}.
    """

    name = "Weighted Avg Ensemble"

    def __init__(self, base_models: dict[str, BaseForecaster]) -> None:
        self.base_models = base_models
        self.weights_: dict[str, float] = {}

    def fit(
        self,
        X_train: pd.DataFrame,  # noqa: N803
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,  # noqa: N803
        y_val: pd.Series | None = None,
        **kwargs: Any,
    ) -> WeightedAverageEnsemble:
        """Compute inverse-MAE weights from the validation set."""
        if X_val is None or y_val is None:
            raise ValueError("WeightedAverageEnsemble requires X_val and y_val to compute weights.")

        maes: dict[str, float] = {}
        for model_name, model in self.base_models.items():
            try:
                preds = model.predict(X_val)
                mae = float(np.mean(np.abs(preds - y_val.values)))
                maes[model_name] = mae
            except Exception as exc:  # noqa: BLE001
                logger.warning("Model '%s' failed on val set: %s", model_name, exc)

        if not maes:
            raise ValueError("No base models produced valid validation predictions.")

        inv_maes = {k: 1.0 / v for k, v in maes.items() if v > 0}
        total = sum(inv_maes.values())
        self.weights_ = {k: v / total for k, v in inv_maes.items()}

        for name, w in sorted(self.weights_.items(), key=lambda x: -x[1]):
            logger.info("  Weight %-35s = %.4f  (val MAE=%.4f kWh)", name, w, maes[name])

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        """Weighted average of base model predictions."""
        weighted_sum = np.zeros(len(X))
        for model_name, model in self.base_models.items():
            weight = self.weights_.get(model_name, 0.0)
            if weight == 0.0:
                continue
            try:
                weighted_sum += weight * model.predict(X)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Model '%s' failed at predict: %s", model_name, exc)
        return weighted_sum

    @property
    def weights_df(self) -> pd.DataFrame:
        """Return weights as a tidy DataFrame, sorted descending."""
        return (
            pd.DataFrame(
                {
                    "model": list(self.weights_.keys()),
                    "weight": list(self.weights_.values()),
                }
            )
            .sort_values("weight", ascending=False)
            .reset_index(drop=True)
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clone_forecaster(model: BaseForecaster) -> BaseForecaster | None:
    """Return an unfitted clone of a fitted ``SklearnForecaster``.

    Uses ``sklearn.base.clone`` to create a fresh, unfitted copy of the
    underlying estimator.  Returns ``None`` for model types that cannot be
    cloned this way (e.g. DL models, TFT).

    Parameters
    ----------
    model:
        A fitted ``BaseForecaster`` instance.

    Returns
    -------
    BaseForecaster | None
        An unfitted clone, or ``None`` if cloning is not supported.
    """
    if not hasattr(model, "estimator"):
        return None
    try:
        from sklearn.base import clone

        from .sklearn_models import SklearnForecaster  # local import avoids cycles

        cloned_estimator = clone(model.estimator)
        return SklearnForecaster(cloned_estimator, name=model.name)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not clone model '%s': %s", getattr(model, "name", "?"), exc)
        return None


def _build_lgbm_meta(ens_cfg: dict, seed: int) -> Any:
    try:
        import lightgbm as lgb

        return lgb.LGBMRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=4,
            random_state=seed,
            verbosity=-1,
        )
    except ImportError as e:
        raise ImportError("lightgbm required for LightGBM meta-learner.") from e
