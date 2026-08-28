"""
RecoveryOS — Unit Tests: XGBoost Recovery Model

6 tests covering the Protocol contract, error handling, and inference shape.
These tests do NOT train a real model — they use mocked/minimal artifacts.
"""

from __future__ import annotations

import os
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from backend.domain.enums import ActionType
from backend.ml_models.xgboost_model import (
    ModelNotTrainedError,
    XGBoostRecoveryModel,
    MODEL_NAME,
    MODEL_VERSION,
)
from backend.orchestrator.context import CaseContext, RecoveryPolicy


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_policy() -> RecoveryPolicy:
    return RecoveryPolicy(
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


def _make_context() -> CaseContext:
    return CaseContext(
        case_id="xgb-test-001",
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
        policy=_make_policy(),
    )


def _make_mock_clf(prob: float = 0.75) -> MagicMock:
    """Create a mock classifier that returns a fixed probability."""
    clf = MagicMock()
    clf.predict_proba.return_value = np.array([[1 - prob, prob]])
    return clf


def _mock_artifacts(tmp_dir: Path) -> dict[ActionType, MagicMock]:
    """Create mock .joblib files in tmp_dir and return the mock classifiers."""
    import joblib
    mocks: dict[ActionType, MagicMock] = {}
    probs = {
        ActionType.RETRY_NOW: 0.61,
        ActionType.RETRY_LATER: 0.79,
        ActionType.REMINDER: 0.52,
        ActionType.INCENTIVE: 0.87,
        ActionType.ESCALATE: 0.40,
        ActionType.DO_NOTHING: 0.08,
    }
    for action in ActionType:
        clf = _make_mock_clf(probs[action])
        mocks[action] = clf
        joblib.dump(clf, tmp_dir / f"{action.value}.joblib")
    return mocks


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestXGBoostModel:

    def test_raises_when_artifacts_missing(self):
        """ModelNotTrainedError must be raised when artifact dir is empty."""
        with tempfile.TemporaryDirectory() as tmp:
            with pytest.raises(ModelNotTrainedError, match="not found"):
                XGBoostRecoveryModel(artifact_dir=Path(tmp))

    def test_loads_from_valid_artifact_dir(self):
        """Should load successfully when all 6 .joblib files exist."""
        with tempfile.TemporaryDirectory() as tmp:
            _mock_artifacts(Path(tmp))
            model = XGBoostRecoveryModel(artifact_dir=Path(tmp))
            assert model is not None

    def test_returns_all_6_action_predictions(self):
        """predict_action_outcomes must return exactly one prediction per ActionType."""
        with tempfile.TemporaryDirectory() as tmp:
            _mock_artifacts(Path(tmp))
            model = XGBoostRecoveryModel(artifact_dir=Path(tmp))
            ctx = _make_context()
            preds = model.predict_action_outcomes(ctx, list(ActionType))
            assert len(preds) == 6
            returned_actions = {p.action for p in preds}
            assert returned_actions == set(ActionType)

    def test_probabilities_in_unit_interval(self):
        """All predicted probabilities must be in (0, 1)."""
        with tempfile.TemporaryDirectory() as tmp:
            _mock_artifacts(Path(tmp))
            model = XGBoostRecoveryModel(artifact_dir=Path(tmp))
            ctx = _make_context()
            preds = model.predict_action_outcomes(ctx, list(ActionType))
            for p in preds:
                assert 0.0 < p.probability < 1.0, (
                    f"{p.action.value}: probability={p.probability} out of (0, 1)"
                )

    def test_model_name_and_version_in_predictions(self):
        """All predictions must report xgboost_recovery / xgb_v1."""
        with tempfile.TemporaryDirectory() as tmp:
            _mock_artifacts(Path(tmp))
            model = XGBoostRecoveryModel(artifact_dir=Path(tmp))
            ctx = _make_context()
            preds = model.predict_action_outcomes(ctx, list(ActionType))
            for p in preds:
                assert p.model_name == MODEL_NAME
                assert p.model_version == MODEL_VERSION

    def test_context_to_feature_vector_shape(self):
        """context_to_feature_vector must return shape (1, 13)."""
        from ml.training import context_to_feature_vector
        ctx = _make_context()
        X = context_to_feature_vector(ctx)
        assert X.shape == (1, 13), f"Expected (1, 13), got {X.shape}"
        assert X.dtype == np.float64
