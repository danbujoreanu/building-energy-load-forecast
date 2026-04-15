"""
validation
==========
Input validation for ML training data.

Call before any model.fit() to catch data quality issues at the boundary
between data preparation and model training — not silently inside sklearn.

Usage
-----
    from energy_forecast.validation import DataValidator
    DataValidator.validate_training_data(X_train, y_train, split_name="train")
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataValidationError(ValueError):
    """Raised when training data fails a hard validation check."""


class DataValidator:
    """Static validation methods for ML training data.

    All methods raise DataValidationError on hard failures (empty arrays,
    shape mismatches, NaN after imputation). Soft warnings (negative values,
    suspicious distributions) are logged at WARNING level but do not raise.
    """

    @staticmethod
    def validate_features(
        X: pd.DataFrame,
        name: str = "X",
        *,
        allow_nan: bool = False,
    ) -> None:
        """Validate a feature DataFrame before model fitting.

        Checks:
        - Not empty
        - No NaN values (unless allow_nan=True)
        - No infinite values
        - At least one feature column

        Args:
            X: Feature DataFrame (MultiIndex or flat)
            name: Name for error messages (e.g. "X_train", "X_val")
            allow_nan: If False (default), NaN raises DataValidationError

        Raises:
            DataValidationError: on hard failures
        """
        if X.empty:
            raise DataValidationError(
                f"{name} is empty (shape={X.shape}). "
                "Check split date boundaries in config.yaml."
            )

        if X.shape[1] == 0:
            raise DataValidationError(
                f"{name} has no feature columns (shape={X.shape})."
            )

        nan_cols = X.columns[X.isna().any()].tolist()
        if nan_cols and not allow_nan:
            raise DataValidationError(
                f"{name} contains NaN after imputation in {len(nan_cols)} column(s): "
                f"{nan_cols[:5]}{'...' if len(nan_cols) > 5 else ''}. "
                "Check the imputation step in splits.py."
            )

        # Check for infinite values (np.isinf only works on numeric data)
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            inf_mask = np.isinf(X[numeric_cols].values)
            if inf_mask.any():
                inf_col_indices = np.where(inf_mask.any(axis=0))[0]
                inf_cols = numeric_cols[inf_col_indices].tolist()
                raise DataValidationError(
                    f"{name} contains infinite values in {len(inf_cols)} column(s): "
                    f"{inf_cols[:5]}{'...' if len(inf_cols) > 5 else ''}."
                )

    @staticmethod
    def validate_target(
        y: pd.Series | np.ndarray,
        name: str = "y",
        *,
        allow_negative: bool = False,
        target_unit: str = "kWh",
    ) -> None:
        """Validate a target array before model fitting.

        Checks:
        - Not empty
        - No NaN values
        - No infinite values
        - Warns (not raises) if >1% values are negative (energy can briefly go
          negative for solar export, but flagging is important)

        Args:
            y: Target Series or ndarray
            name: Name for error messages
            allow_negative: If False, log WARNING when negatives detected
            target_unit: Unit string for log messages
        """
        arr = np.asarray(y, dtype=float)

        if arr.size == 0:
            raise DataValidationError(
                f"{name} is empty (size=0). "
                "Check split date boundaries in config.yaml."
            )

        nan_count = np.isnan(arr).sum()
        if nan_count > 0:
            raise DataValidationError(
                f"{name} contains {nan_count} NaN value(s) "
                f"({nan_count / arr.size:.1%} of {arr.size} samples)."
            )

        inf_count = np.isinf(arr).sum()
        if inf_count > 0:
            raise DataValidationError(
                f"{name} contains {inf_count} infinite value(s)."
            )

        if not allow_negative:
            neg_count = (arr < 0).sum()
            neg_frac = neg_count / arr.size
            if neg_frac > 0.01:
                logger.warning(
                    "%s contains %d negative %s values (%.1f%% of %d samples). "
                    "Solar export can cause brief negatives — verify this is expected.",
                    name, neg_count, target_unit, neg_frac * 100, arr.size,
                )

    @staticmethod
    def validate_shapes(
        X: pd.DataFrame,
        y: pd.Series | np.ndarray,
        name: str = "",
    ) -> None:
        """Check X and y have matching sample counts.

        Raises:
            DataValidationError: if X.shape[0] != len(y)
        """
        prefix = f"[{name}] " if name else ""
        n_X = X.shape[0]
        n_y = len(y)
        if n_X != n_y:
            raise DataValidationError(
                f"{prefix}Shape mismatch: X has {n_X} rows but y has {n_y} samples. "
                "The feature and target arrays must have the same length."
            )

    @staticmethod
    def validate_training_data(
        X_train: pd.DataFrame,
        y_train: pd.Series | np.ndarray,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | np.ndarray | None = None,
        *,
        split_name: str = "train",
    ) -> None:
        """Convenience method: validate all provided splits at once.

        Calls validate_features + validate_target + validate_shapes for
        train (required) and val (optional if provided).

        This is the single call to make from model.fit() before any
        estimator.fit() call.
        """
        DataValidator.validate_features(X_train, name=f"X_train[{split_name}]")
        DataValidator.validate_target(y_train, name=f"y_train[{split_name}]")
        DataValidator.validate_shapes(X_train, y_train, name=split_name)

        if X_val is not None and y_val is not None:
            DataValidator.validate_features(X_val, name=f"X_val[{split_name}]")
            DataValidator.validate_target(y_val, name=f"y_val[{split_name}]")
            DataValidator.validate_shapes(X_val, y_val, name=f"{split_name}/val")
