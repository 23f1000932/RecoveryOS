"""
RecoveryOS — XGBoost Training CLI

Entry point for training the XGBoost recovery outcome models.

Usage:
    .venv\\Scripts\\python -m ml.train --rows 50000 --seed 42

This script:
  1. Generates the synthetic dataset via generate_dataset().
  2. Builds feature matrix (X) and per-action label arrays (y).
  3. Splits into 80/20 train/test.
  4. Trains one XGBClassifier per action (6 total).
  5. Evaluates each model on the test split.
  6. Saves model artifacts to ml/models/<action>.joblib.
  7. Saves evaluation report to ml/models/evaluation_report.json.

Architecture notes:
  - Training is a CLI operation, NOT an API endpoint.
  - Artifacts are git-ignored. Run this script to regenerate them.
  - Use a fixed seed for reproducibility.
  - XGBoost defaults defined here; no hyperparameter tuning in Phase 4.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from backend.domain.enums import ActionType
from ml.evaluate import evaluate_all, save_evaluation_report
from ml.generate_data import generate_dataset
from ml.training import build_feature_matrix, build_label_matrix

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Artifact directory ─────────────────────────────────────────────────────────
MODELS_DIR = Path("ml/models")

# ── XGBoost hyperparameters (Phase 4 defaults — no tuning) ────────────────────
XGBOOST_DEFAULTS: dict = {
    "n_estimators": 200,
    "max_depth": 4,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "eval_metric": "logloss",
    "random_state": 42,
    "verbosity": 0,
}


def artifact_path(action: ActionType) -> Path:
    """Return the .joblib path for a specific action model."""
    return MODELS_DIR / f"{action.value}.joblib"


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    action: ActionType,
) -> XGBClassifier:
    """
    Train a single XGBClassifier for a specific action.

    Args:
        X_train: Training feature matrix.
        y_train: Binary labels for this action on the training split.
        action:  Which action this classifier is being trained for.

    Returns:
        Fitted XGBClassifier.
    """
    clf = XGBClassifier(**XGBOOST_DEFAULTS)
    clf.fit(X_train, y_train)
    return clf


def run_training(rows: int, seed: int) -> None:
    """
    Full training pipeline: generate → split → train → evaluate → save.

    Args:
        rows: Number of synthetic cases to generate.
        seed: Random seed for reproducibility.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate dataset
    logger.info("Generating %d synthetic cases (seed=%d)...", rows, seed)
    t0 = time.time()
    df = generate_dataset(rows=rows, seed=seed)
    logger.info("  Dataset generated in %.1fs", time.time() - t0)

    # Step 2: Build feature + label matrices
    logger.info("Building feature and label matrices...")
    X = build_feature_matrix(df)
    y_all = build_label_matrix(df)
    logger.info("  X shape: %s  Feature columns: 13", X.shape)
    for action, y in y_all.items():
        logger.info(
            "  %s: positive_rate=%.3f  n=%d",
            action.value.ljust(12), y.mean(), len(y),
        )

    # Step 3: Train/test split (stratified by first action's labels for consistency)
    logger.info("Splitting 80/20 train/test (random_state=%d)...", seed)
    first_action = ActionType.RETRY_NOW
    X_train, X_test, *_ = train_test_split(
        X, y_all[first_action],
        test_size=0.20,
        random_state=seed,
        stratify=y_all[first_action],
    )
    # Get the same indices for all actions
    all_idx = np.arange(len(X))
    train_idx, test_idx = train_test_split(
        all_idx,
        test_size=0.20,
        random_state=seed,
        stratify=y_all[first_action],
    )
    X_train, X_test = X[train_idx], X[test_idx]

    # Step 4: Train one classifier per action
    logger.info("Training 6 XGBoost classifiers...")
    models: dict[ActionType, XGBClassifier] = {}
    y_test: dict[ActionType, np.ndarray] = {}

    for action in ActionType:
        y = y_all[action]
        y_tr, y_te = y[train_idx], y[test_idx]
        y_test[action] = y_te

        t1 = time.time()
        clf = train_model(X_train, y_tr, action)
        elapsed = time.time() - t1
        models[action] = clf
        logger.info("  Trained %s in %.1fs", action.value, elapsed)

    # Step 5: Evaluate
    logger.info("Evaluating on held-out test set (%d samples)...", len(X_test))
    metrics = evaluate_all(models, X_test, y_test)

    # Step 6: Save artifacts
    logger.info("Saving model artifacts to %s...", MODELS_DIR)
    for action, clf in models.items():
        path = artifact_path(action)
        joblib.dump(clf, path)
        logger.info("  Saved %s", path)

    # Step 7: Save evaluation report
    report_path = MODELS_DIR / "evaluation_report.json"
    save_evaluation_report(metrics, report_path)

    total_time = time.time() - t0
    logger.info(
        "Training complete in %.1fs. Artifacts: %s",
        total_time, MODELS_DIR,
    )

    # Print summary table
    print("\n─── Evaluation Summary ───────────────────────────────────")
    print(f"{'Action':<14} {'F1':>6} {'PR-AUC':>8} {'Recall':>8} {'Precision':>10}")
    print("─" * 52)
    for action in ActionType:
        m = metrics[action]
        print(
            f"{action.value:<14} {m.f1:>6.3f} {m.pr_auc:>8.3f} "
            f"{m.recall:>8.3f} {m.precision:>10.3f}"
        )
    print("─" * 52)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train XGBoost recovery outcome models on synthetic data."
    )
    parser.add_argument(
        "--rows", type=int, default=50_000,
        help="Number of synthetic cases to generate (default: 50000)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    args = parser.parse_args()

    if args.rows < 100:
        print("ERROR: --rows must be >= 100 for meaningful training.", file=sys.stderr)
        sys.exit(1)

    run_training(rows=args.rows, seed=args.seed)


if __name__ == "__main__":
    main()
