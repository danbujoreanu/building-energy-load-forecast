"""
data.raw_sequence
=================
Loader and preprocessor for "Setup C" Paradigm Parity Deep Learning models.
Bypasses feature engineering and directly loads raw sequences (Target, Weather)
scaled properly to prevent temporal data leakage.
"""

import logging

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def build_raw_sequences(
    df_train: pd.DataFrame,
    df_val: pd.DataFrame,
    df_test: pd.DataFrame,
    target_col: str,
    feature_cols: list[str],
    lookback: int,
    horizon: int,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    StandardScaler,
    StandardScaler,
]:
    """Builds 3D raw sliding window sequences for Deep Learning models.

    Crucially, fits the StandardScaler ONLY on the training split to prevent
    data leakage. Then transforms the train, validation, and test splits.
    Respects MultiIndex (building_id) temporal boundaries.
    """  # noqa: W291, W293
    logger.info("Fitting Scalers ONLY on training data to prevent leakage...")

    scaler_X = StandardScaler()  # noqa: N806
    scaler_y = StandardScaler()

    # 1. Extract raw arrays
    X_tr_raw = df_train[feature_cols].values  # noqa: N806
    y_tr_raw = df_train[[target_col]].values

    # 2. Fit and Transform Train
    X_tr_scaled = scaler_X.fit_transform(X_tr_raw)  # noqa: N806
    y_tr_scaled = scaler_y.fit_transform(y_tr_raw).squeeze()

    # 3. Transform Val and Test (NO fitting!)
    X_v_scaled = scaler_X.transform(df_val[feature_cols].values)  # noqa: N806
    y_v_scaled = scaler_y.transform(df_val[[target_col]].values).squeeze()

    X_te_scaled = scaler_X.transform(df_test[feature_cols].values)  # noqa: N806
    y_te_scaled = scaler_y.transform(df_test[[target_col]].values).squeeze()

    def _build_sequences_for_split(
        X_scaled: np.ndarray, y_scaled: np.ndarray, df_index: pd.MultiIndex
    ):  # noqa: N803
        X_seqs, y_seqs = [], []  # noqa: N806

        # Temporarily rebuild DataFrames to use pandas MultiIndex slicing (xs)
        # matches the logic in features/temporal.py and models/deep_learning.py
        df_X = pd.DataFrame(X_scaled, index=df_index, columns=feature_cols)  # noqa: N806
        df_y = pd.Series(y_scaled, index=df_index, name=target_col)

        building_ids = df_index.get_level_values("building_id").unique()

        for bid in building_ids:
            # xs slices the building's data without dropping the timezone/timestamps if present
            X_b = df_X.xs(bid, level="building_id").values  # noqa: N806
            y_b = df_y.xs(bid, level="building_id").values
            n = len(X_b)

            # Sliding window iteration
            for i in range(lookback, n - horizon + 1):
                X_seqs.append(X_b[i - lookback : i])

                # Multi-step prediction (H+N) is 2D, Single-step (H+1) is 1D
                if horizon == 1:
                    y_seqs.append(y_b[i])
                else:
                    y_seqs.append(y_b[i : i + horizon])

        return np.array(X_seqs, dtype=np.float32), np.array(y_seqs, dtype=np.float32)

    logger.info("Building raw sliding window sequences per split...")
    X_train_seq, y_train_seq = _build_sequences_for_split(
        X_tr_scaled, y_tr_scaled, df_train.index
    )  # noqa: N806
    X_val_seq, y_val_seq = _build_sequences_for_split(
        X_v_scaled, y_v_scaled, df_val.index
    )  # noqa: N806
    X_test_seq, y_test_seq = _build_sequences_for_split(
        X_te_scaled, y_te_scaled, df_test.index
    )  # noqa: N806

    logger.info(f"Generated Training Sequences: X={X_train_seq.shape}, y={y_train_seq.shape}")
    logger.info(f"Generated Validation Sequences: X={X_val_seq.shape}, y={y_val_seq.shape}")
    logger.info(f"Generated Test Sequences: X={X_test_seq.shape}, y={y_test_seq.shape}")

    return (
        X_train_seq,
        y_train_seq,
        X_val_seq,
        y_val_seq,
        X_test_seq,
        y_test_seq,
        scaler_X,
        scaler_y,
    )
