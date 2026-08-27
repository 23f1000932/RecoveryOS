"""
RecoveryOS — Per-Action Evaluation Metrics

Computes classification metrics for each trained XGBoost action model.

Reports per-action:
  - precision
  - recall
  - F1
  - PR-AUC (average precision)
  - positive_rate (% of cases where label=1)

Architecture note (§9):
  "Do not claim real-world predictive performance from synthetic data."
  The evaluation report exists for development comparison only.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_fscore_support

from backend.domain.enums import ActionType

logger = logging.getLogger(__name__)


@dataclass
class ActionMetrics:
    """Per-action classification metrics on the held-out test set."""

    action: str
    precision: float
    recall: float
    f1: float
    pr_auc: float
    positive_rate: float     # fraction of test labels that are 1
    n_test_samples: int


def evaluate_action(
    clf,
    X_test: np.ndarray,
    y_test: np.ndarray,
    action: ActionType,
) -> ActionMetrics:
    """
    Evaluate one trained classifier on the test split.

    Args:
        clf:     A fitted XGBClassifier (or any sklearn-compatible binary classifier).
        X_test:  Feature matrix for the test split.
        y_test:  Binary labels for this action on the test split.
        action:  Which action this classifier was trained for.

    Returns:
        ActionMetrics with all computed scores.
    """
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="binary", zero_division=0
    )
    pr_auc = float(average_precision_score(y_test, y_prob))
    positive_rate = float(y_test.mean())

    return ActionMetrics(
        action=action.value,
        precision=round(float(precision), 4),
        recall=round(float(recall), 4),
        f1=round(float(f1), 4),
        pr_auc=round(pr_auc, 4),
        positive_rate=round(positive_rate, 4),
        n_test_samples=len(y_test),
    )


def evaluate_all(
    models: dict[ActionType, object],
    X_test: np.ndarray,
    y_test: dict[ActionType, np.ndarray],
) -> dict[ActionType, ActionMetrics]:
    """
    Evaluate all 6 action classifiers on the test split.

    Args:
        models:  Dict mapping ActionType → fitted classifier.
        X_test:  Feature matrix (same for all actions — features don't change by action).
        y_test:  Dict mapping ActionType → binary label array.

    Returns:
        Dict mapping ActionType → ActionMetrics.
    """
    results: dict[ActionType, ActionMetrics] = {}
    for action, clf in models.items():
        metrics = evaluate_action(clf, X_test, y_test[action], action)
        results[action] = metrics
        logger.info(
            "  %s: precision=%.3f recall=%.3f F1=%.3f PR-AUC=%.3f positive_rate=%.3f",
            action.value.ljust(12),
            metrics.precision,
            metrics.recall,
            metrics.f1,
            metrics.pr_auc,
            metrics.positive_rate,
        )
    return results


def save_evaluation_report(
    metrics: dict[ActionType, ActionMetrics],
    output_path: Path,
) -> None:
    """
    Write the evaluation report as JSON to output_path.

    Args:
        metrics:     Dict from evaluate_all().
        output_path: File path to write to (parent dir must exist).
    """
    report = {
        action.value: asdict(m)
        for action, m in metrics.items()
    }
    output_path.write_text(json.dumps(report, indent=2))
    logger.info("Evaluation report saved: %s", output_path)
