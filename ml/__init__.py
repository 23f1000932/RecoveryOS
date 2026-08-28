"""
RecoveryOS — ML Package

Public API:
    generate_dataset(rows, seed) → pd.DataFrame
    build_feature_matrix(df)    → np.ndarray
    build_label_matrix(df)      → dict[ActionType, np.ndarray]
    context_to_feature_vector(context) → np.ndarray
"""

from ml.generate_data import generate_dataset
from ml.training import build_feature_matrix, build_label_matrix, context_to_feature_vector

__all__ = [
    "generate_dataset",
    "build_feature_matrix",
    "build_label_matrix",
    "context_to_feature_vector",
]
