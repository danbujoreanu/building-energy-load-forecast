"""
evaluation.explainability
=========================
SHAP-based model explainability for tree-based forecasters.

Produces both *global* and *local* explanations — answering:

    Global: Which features drive electricity load the most, and in which direction?
            (e.g., high lag_24h → high load; high temperature → lower load in winter)

    Local:  Why did the model predict 180 kWh at 09:00 on a cold Monday?
            (SHAP force / waterfall plot — auditable breakdown for a single hour)

Supported models
----------------
Works with any model that has a `.estimator` attribute exposing a tree-based
scikit-learn / XGBoost / LightGBM regressor:

    SklearnForecaster(RandomForestRegressor)
    SklearnForecaster(XGBRegressor)
    SklearnForecaster(LGBMRegressor)

Reference (from MSc thesis Follow-up Q7)
-----------------------------------------
Mitchell et al. (2019) — Model Cards for Model Reporting. FAccT 2019.
Lundberg & Lee (2017)  — A Unified Approach to Interpreting Model Predictions.

Public API
----------
    SHAPExplainer(model, X_background)
    SHAPExplainer.compute(X)               -> shap.Explanation
    SHAPExplainer.plot_beeswarm(...)       -> global feature importance + direction
    SHAPExplainer.plot_waterfall(...)      -> local explanation for one sample
    SHAPExplainer.plot_bar(...)            -> mean |SHAP| bar chart (simpler global view)
    SHAPExplainer.plot_heatmap(...)        -> SHAP values across samples as heatmap
    SHAPExplainer.save_values(...)         -> persist SHAP arrays for later analysis
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SHAPExplainer:
    """SHAP TreeExplainer wrapper for SklearnForecaster models.

    Parameters
    ----------
    model:
        A fitted ``SklearnForecaster`` (or any object with an ``.estimator``
        attribute that is a tree-based model).
    X_background:
        Background dataset used by SHAP to compute expected values.
        Pass ``X_train`` (or a shap.sample of it for large datasets).
    """

    def __init__(self, model: Any, X_background: pd.DataFrame) -> None:  # noqa: N803
        try:
            import shap
        except ImportError as exc:
            raise ImportError(
                "shap is required for explainability: pip install shap"
            ) from exc

        # Unwrap SklearnForecaster if needed
        estimator = getattr(model, "estimator", model)
        self.model_name: str = getattr(model, "name", type(estimator).__name__)

        logger.info("Building SHAP TreeExplainer for %s ...", self.model_name)
        self.explainer_ = shap.TreeExplainer(
            estimator,
            data=shap.sample(X_background, min(200, len(X_background))),
        )
        self.feature_names_: list[str] = list(X_background.columns)
        self._shap_values: shap.Explanation | None = None

    # ------------------------------------------------------------------
    # Core compute
    # ------------------------------------------------------------------

    def compute(self, X: pd.DataFrame, check_additivity: bool = False) -> shap.Explanation:  # noqa: F821, N803
        """Compute SHAP values for the given dataset.

        Parameters
        ----------
        X:
            Feature matrix (typically X_test or a subset).
        check_additivity:
            Verify that SHAP values sum to model output.
            Disable for speed on large datasets.

        Returns
        -------
        shap.Explanation object — pass directly to plot functions.
        """
        logger.info("Computing SHAP values for %s on %d samples ...", self.model_name, len(X))
        self._shap_values = self.explainer_(X, check_additivity=check_additivity)
        logger.info("SHAP values computed. Shape: %s", self._shap_values.values.shape)
        return self._shap_values

    # ------------------------------------------------------------------
    # Plot functions
    # ------------------------------------------------------------------

    def plot_beeswarm(
        self,
        shap_values: shap.Explanation | None = None,  # noqa: F821
        max_display: int = 20,
        save_path: str | Path | None = None,
    ) -> None:
        """Global feature importance beeswarm plot.

        Shows not just *which* features matter, but *how* each feature's value
        (high vs low — colour) affects the model output (SHAP value direction).

        Example insight: high `lag_24h` values → positive SHAP → higher predicted load.

        Parameters
        ----------
        shap_values:
            Output of ``compute()``. Uses last computed values if None.
        max_display:
            Number of top features to show.
        save_path:
            If provided, saves the figure instead of showing it.
        """
        import matplotlib.pyplot as plt
        import shap

        sv = shap_values or self._shap_values
        if sv is None:
            raise RuntimeError("Call compute() before plotting.")

        fig, ax = plt.subplots(figsize=(10, 8))
        shap.plots.beeswarm(sv, max_display=max_display, show=False)
        plt.title(f"SHAP Beeswarm — {self.model_name}\n(feature impact on predicted load)", fontsize=13)
        plt.tight_layout()
        _save_or_show(fig, save_path, f"shap_beeswarm_{self.model_name.lower()}.png")

    def plot_waterfall(
        self,
        shap_values: shap.Explanation | None = None,  # noqa: F821
        idx: int = 0,
        save_path: str | Path | None = None,
    ) -> None:
        """Local explanation waterfall plot for a single prediction.

        Answers: "Why did the model predict X kWh for building B at time T?"
        Each bar shows one feature's additive contribution to the final prediction.

        Parameters
        ----------
        shap_values:
            Output of ``compute()``. Uses last computed values if None.
        idx:
            Row index within the SHAP values to explain (0-indexed).
        save_path:
            If provided, saves the figure.
        """
        import matplotlib.pyplot as plt
        import shap

        sv = shap_values or self._shap_values
        if sv is None:
            raise RuntimeError("Call compute() before plotting.")

        fig, _ = plt.subplots(figsize=(10, 7))
        shap.plots.waterfall(sv[idx], show=False)
        plt.title(
            f"SHAP Waterfall — {self.model_name}\n(local explanation for sample #{idx})",
            fontsize=13,
        )
        plt.tight_layout()
        _save_or_show(fig, save_path, f"shap_waterfall_{self.model_name.lower()}_{idx}.png")

    def plot_bar(
        self,
        shap_values: shap.Explanation | None = None,  # noqa: F821
        max_display: int = 20,
        save_path: str | Path | None = None,
    ) -> None:
        """Global mean |SHAP| bar chart — simpler alternative to beeswarm.

        Shows feature importance without the direction information.
        Use beeswarm for full insight, bar chart for a clean portfolio figure.
        """
        import matplotlib.pyplot as plt
        import shap

        sv = shap_values or self._shap_values
        if sv is None:
            raise RuntimeError("Call compute() before plotting.")

        fig, _ = plt.subplots(figsize=(10, 7))
        shap.plots.bar(sv, max_display=max_display, show=False)
        plt.title(f"SHAP Feature Importance — {self.model_name}\n(mean |SHAP value|)", fontsize=13)
        plt.tight_layout()
        _save_or_show(fig, save_path, f"shap_bar_{self.model_name.lower()}.png")

    def plot_heatmap(
        self,
        shap_values: shap.Explanation | None = None,  # noqa: F821
        max_display: int = 20,
        save_path: str | Path | None = None,
    ) -> None:
        """SHAP heatmap — feature contributions across all samples.

        Reveals how SHAP values vary across the test set (e.g., seasonal patterns
        in the contribution of temperature or time-of-day features).
        """
        import matplotlib.pyplot as plt
        import shap

        sv = shap_values or self._shap_values
        if sv is None:
            raise RuntimeError("Call compute() before plotting.")

        fig, _ = plt.subplots(figsize=(12, 8))
        shap.plots.heatmap(sv, max_display=max_display, show=False)
        plt.title(f"SHAP Heatmap — {self.model_name}", fontsize=13)
        plt.tight_layout()
        _save_or_show(fig, save_path, f"shap_heatmap_{self.model_name.lower()}.png")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_values(
        self,
        shap_values: shap.Explanation | None = None,  # noqa: F821
        save_dir: str | Path = "outputs/results/shap",
    ) -> Path:
        """Save SHAP values, feature names, and expected value to disk.

        Useful for post-hoc analysis in notebooks without re-running the model.

        Returns
        -------
        Path to the saved .npz file.
        """
        sv = shap_values or self._shap_values
        if sv is None:
            raise RuntimeError("Call compute() before saving.")

        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        fname = save_dir / f"shap_values_{self.model_name.lower().replace(' ', '_')}.npz"
        np.savez_compressed(
            fname,
            values=sv.values,
            base_values=sv.base_values,
            feature_names=np.array(self.feature_names_),
        )
        logger.info("SHAP values saved → %s", fname)
        return fname

    def get_top_features(
        self,
        shap_values: shap.Explanation | None = None,  # noqa: F821
        n: int = 10,
    ) -> pd.DataFrame:
        """Return a DataFrame of top-N features ranked by mean |SHAP|.

        Useful for printing a table in a notebook or report.

        Returns
        -------
        pd.DataFrame with columns: feature, mean_abs_shap
        """
        sv = shap_values or self._shap_values
        if sv is None:
            raise RuntimeError("Call compute() before get_top_features().")

        mean_abs = np.abs(sv.values).mean(axis=0)
        df = pd.DataFrame({
            "feature": self.feature_names_,
            "mean_abs_shap": mean_abs,
        }).sort_values("mean_abs_shap", ascending=False).head(n).reset_index(drop=True)
        df.index += 1
        return df


# ---------------------------------------------------------------------------
# Module-level convenience function (matches the pattern in visualization/plots.py)
# ---------------------------------------------------------------------------

def explain_model(
    model: Any,
    X_train: pd.DataFrame,  # noqa: N803
    X_test: pd.DataFrame,  # noqa: N803
    model_name: str | None = None,
    save_dir: str | Path | None = None,
    n_samples: int = 500,
) -> SHAPExplainer:
    """One-shot: build explainer, compute SHAP, save all four plots.

    Parameters
    ----------
    model:
        Fitted model (SklearnForecaster or any object with `.estimator`).
    X_train:
        Training features — used as SHAP background distribution.
    X_test:
        Test features — SHAP values computed on this set.
    model_name:
        Override auto-detected model name (used in filenames).
    save_dir:
        Directory for saving plots and SHAP values.
        If None, plots are displayed interactively.
    n_samples:
        Max test samples to compute SHAP for (subsample for speed).

    Returns
    -------
    Fitted SHAPExplainer (with .shap_values_ accessible for further analysis).
    """
    explainer = SHAPExplainer(model, X_train)

    # Subsample for speed — SHAP is O(n * features * trees)
    X_explain = X_test.sample(min(n_samples, len(X_test)), random_state=42)  # noqa: N806
    shap_values = explainer.compute(X_explain)

    if save_dir is not None:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        shap_dir = save_dir / "shap"
        shap_dir.mkdir(exist_ok=True)

        explainer.plot_beeswarm(shap_values, save_path=shap_dir)
        explainer.plot_bar(shap_values, save_path=shap_dir)
        explainer.plot_waterfall(shap_values, idx=0, save_path=shap_dir)
        explainer.plot_heatmap(shap_values, save_path=shap_dir)
        explainer.save_values(shap_values, save_dir=shap_dir)

    logger.info("SHAP analysis complete for %s", explainer.model_name)
    return explainer


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _save_or_show(fig: Any, save_path: str | Path | None, default_name: str) -> None:
    """Save figure to save_path or show interactively."""
    import matplotlib.pyplot as plt

    if save_path is not None:
        p = Path(save_path)
        # If save_path is a directory, use default_name as filename
        if p.is_dir():
            p = p / default_name
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, dpi=150, bbox_inches="tight")
        logger.info("Figure saved → %s", p)
        plt.close(fig)
    else:
        plt.show()
