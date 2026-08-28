"""
RecoveryOS — ML Training Data Builder

Converts a generate_dataset() DataFrame into model-ready numpy arrays.

This module is the single bridge between the synthetic data (Phase 2)
and the XGBoost training pipeline (Phase 4).

Rules:
  - Feature columns are read from ml/features.py FEATURE_COLUMNS (authoritative).
  - Label binarization: success = (p_action >= 0.5). Deterministic, no randomness.
  - Never use post-action information as features.
  - Feature order must be preserved — XGBoost artifacts depend on column order.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.domain.enums import ActionType
from ml.features import FEATURE_COLUMNS, PROBABILITY_COLUMNS

# ── Probability column → ActionType mapping ────────────────────────────────────
# Authoritative mapping between latent outcome columns and action types.
ACTION_PROB_COLUMNS: dict[ActionType, str] = {
    ActionType.RETRY_NOW:    "p_retry_now",
    ActionType.RETRY_LATER:  "p_retry_later",
    ActionType.REMINDER:     "p_reminder",
    ActionType.INCENTIVE:    "p_incentive",
    ActionType.ESCALATE:     "p_escalate",
    ActionType.DO_NOTHING:   "p_do_nothing",
}

# Binarization threshold: same value used by BaselinePolicy
BINARIZATION_THRESHOLD: float = 0.5


def build_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """
    Extract the feature matrix (X) from a dataset DataFrame.

    Args:
        df: DataFrame produced by generate_dataset(rows, seed).

    Returns:
        numpy array of shape (n_rows, 13) — float64.
        Columns follow FEATURE_COLUMNS order exactly.

    Raises:
        ValueError: If any FEATURE_COLUMNS are missing from df.

    Note on duplicate columns:
        The synthetic dataset has duplicate column names (e.g. customer_success_rate
        appears in both the helper block and the feature block). We deduplicate by
        dropping duplicate column names while keeping the LAST occurrence, which
        corresponds to the properly encoded feature columns.
    """
    # Deduplicate columns — keep last occurrence (the encoded feature columns)
    df_dedup = df.loc[:, ~df.columns.duplicated(keep="last")]

    missing = [col for col in FEATURE_COLUMNS if col not in df_dedup.columns]
    if missing:
        raise ValueError(
            f"Dataset is missing feature columns: {missing}\n"
            f"Available columns: {list(df_dedup.columns)}"
        )
    return df_dedup[FEATURE_COLUMNS].to_numpy(dtype=np.float64)


def build_label_matrix(df: pd.DataFrame) -> dict[ActionType, np.ndarray]:
    """
    Build per-action binary labels (y) from the latent probability columns.

    Binarization: label = (p_action >= BINARIZATION_THRESHOLD).astype(int)
    This is deterministic — no randomness introduced.

    Args:
        df: DataFrame produced by generate_dataset(rows, seed).

    Returns:
        Dict mapping each ActionType to a binary label array of shape (n_rows,).
        Values are 0 (failed) or 1 (succeeded).

    Raises:
        ValueError: If any probability columns are missing from df.
    """
    missing = [col for col in PROBABILITY_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Dataset is missing probability columns: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )

    labels: dict[ActionType, np.ndarray] = {}
    for action, prob_col in ACTION_PROB_COLUMNS.items():
        raw_probs = df[prob_col].to_numpy(dtype=np.float64)
        labels[action] = (raw_probs >= BINARIZATION_THRESHOLD).astype(np.int32)

    return labels


def context_to_feature_vector(context) -> np.ndarray:
    """
    Convert a CaseContext to a feature vector for inference.

    Returns a numpy array of shape (1, 13) — compatible with
    XGBClassifier.predict_proba().

    The column order matches FEATURE_COLUMNS exactly.
    Uses the same encoding functions as ml/features.py.
    """
    from ml.features import encode_failure_code, encode_method
    import math

    row = [
        float(context.amount),
        float(encode_method(context.method)),
        float(encode_failure_code(context.failure_code)),
        float(context.attempt_number),
        float(context.customer_transaction_count),
        float(context.customer_success_count),
        float(context.customer_failure_count),
        float(context.customer_success_rate),
        float(context.customer_avg_amount),
        float(context.time_since_failure_hours),
        float(context.hour_of_day),
        float(context.day_of_week),
        float(context.previous_failure_count),
    ]
    return np.array([row], dtype=np.float64)
