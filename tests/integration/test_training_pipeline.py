"""
RecoveryOS — Integration Tests: Training Pipeline

4 end-to-end tests that exercise the full train → save → load → predict round-trip.

These tests train real XGBoost models on 2,000 rows to keep runtime under 15 seconds.
They verify that the training pipeline produces valid artifacts and that the
XGBoostRecoveryModel produces better predictions than random chance.

Run with:
    .venv\\Scripts\\python -m pytest tests/integration/ -v --tb=short
"""

from __future__ import annotations

import json
import tempfile
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest

from backend.domain.enums import ActionType
from backend.ml_models.xgboost_model import XGBoostRecoveryModel
from backend.orchestrator.context import CaseContext, RecoveryPolicy
from ml.train import MODELS_DIR, run_training
from ml.training import build_feature_matrix, build_label_matrix
from ml.generate_data import generate_dataset


# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def trained_model_dir(tmp_path_factory):
    """
    Train a real XGBoost model on 2,000 rows and return the artifact directory.
    Scoped to module so training happens only once per test session.
    """
    artifact_dir = tmp_path_factory.mktemp("models")
    # Monkey-patch MODELS_DIR for this training run
    import ml.train as train_module
    original_dir = train_module.MODELS_DIR
    train_module.MODELS_DIR = artifact_dir
    try:
        run_training(rows=2_000, seed=42)
    finally:
        train_module.MODELS_DIR = original_dir
    return artifact_dir


@pytest.fixture(scope="module")
def xgb_model(trained_model_dir):
    return XGBoostRecoveryModel(artifact_dir=trained_model_dir)


def _make_context() -> CaseContext:
    policy = RecoveryPolicy(
        version="1.0",
        max_retries_per_customer=2,
        max_messages_per_customer=2,
        max_incentive_per_customer=Decimal("100"),
        daily_incentive_pool=Decimal("5000"),
        high_value_threshold=Decimal("10000"),
        min_expected_net_revenue=Decimal("100"),
        min_model_confidence=0.65,
        recovery_window_hours=48,
        auto_action_probability=0.70,
    )
    return CaseContext(
        case_id="integ-test-001",
        payment_id="pay-001",
        customer_id="cust-001",
        merchant_id="merch-001",
        amount=Decimal("3000"),
        currency="INR",
        method="card",
        failure_code="insufficient_funds",
        attempt_number=1,
        customer_success_rate=0.80,
        customer_transaction_count=20,
        customer_success_count=16,
        customer_failure_count=4,
        customer_avg_amount=Decimal("3000"),
        time_since_failure_hours=2.0,
        hour_of_day=10,
        day_of_week=1,
        previous_failure_count=2,
        policy=policy,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestTrainingPipeline:

    def test_train_saves_all_6_artifacts(self, trained_model_dir):
        """Training must produce one .joblib file per ActionType."""
        for action in ActionType:
            artifact = trained_model_dir / f"{action.value}.joblib"
            assert artifact.exists(), f"Missing artifact: {artifact}"

    def test_evaluation_report_written(self, trained_model_dir):
        """Training must produce a valid evaluation_report.json."""
        report_path = trained_model_dir / "evaluation_report.json"
        assert report_path.exists(), "evaluation_report.json not found"

        report = json.loads(report_path.read_text())
        # Should have one entry per action
        for action in ActionType:
            assert action.value in report, f"Missing {action.value} in report"
            metrics = report[action.value]
            assert "f1" in metrics
            assert "pr_auc" in metrics
            assert 0.0 <= metrics["f1"] <= 1.0
            assert 0.0 <= metrics["pr_auc"] <= 1.0

    def test_round_trip_train_load_predict(self, xgb_model):
        """Trained model → load → predict must return valid ActionPredictions."""
        ctx = _make_context()
        preds = xgb_model.predict_action_outcomes(ctx, list(ActionType))

        assert len(preds) == 6
        for p in preds:
            assert 0.0 < p.probability < 1.0
            assert p.model_name == "xgboost_recovery"
            assert p.model_version == "xgb_v1"

    def test_xgboost_better_than_chance_on_test_set(self, trained_model_dir):
        """
        XGBoost PR-AUC must exceed per-action minimum thresholds.

        do_nothing is heavily imbalanced (positive_rate ~0.7%) so its PR-AUC
        baseline is much lower. All other actions have balanced enough labels
        to exceed 0.55 (better than random chance).

        Note: these are synthetic-data metrics only — see spec §9.
        """
        report_path = trained_model_dir / "evaluation_report.json"
        report = json.loads(report_path.read_text())

        # Per-action minimum PR-AUC thresholds
        # Note: tested on 2,000-row training (fast integration test).
        # do_nothing has ~14 positive samples at 2k rows — essentially no signal.
        # The threshold just confirms training produced a valid report entry.
        min_pr_auc = {
            ActionType.RETRY_NOW:    0.55,
            ActionType.RETRY_LATER:  0.55,
            ActionType.REMINDER:     0.55,
            ActionType.INCENTIVE:    0.55,
            ActionType.ESCALATE:     0.55,
            ActionType.DO_NOTHING:   0.01,   # ~14 positives in 2k rows — low signal
        }

        for action in ActionType:
            pr_auc = report[action.value]["pr_auc"]
            threshold = min_pr_auc[action]
            assert pr_auc > threshold, (
                f"{action.value}: PR-AUC={pr_auc:.3f} <= {threshold:.2f}"
            )
