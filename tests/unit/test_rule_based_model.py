"""
RecoveryOS — Unit Tests: Rule-Based Recovery Model

6 test cases covering probability correctness, model contract, and calibration.
"""

from __future__ import annotations

import pytest
from decimal import Decimal

from backend.domain.enums import ActionType
from backend.ml_models.rule_based import RuleBasedRecoveryModel
from backend.orchestrator.context import CaseContext, RecoveryPolicy


# ── Shared Fixtures ────────────────────────────────────────────────────────────

def _make_policy(**kwargs) -> RecoveryPolicy:
    defaults = dict(
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
    defaults.update(kwargs)
    return RecoveryPolicy(**defaults)


def _make_context(**kwargs) -> CaseContext:
    defaults = dict(
        case_id="case-001",
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
    defaults.update(kwargs)
    return CaseContext(**defaults)


@pytest.fixture
def model() -> RuleBasedRecoveryModel:
    return RuleBasedRecoveryModel()


@pytest.fixture
def good_context() -> CaseContext:
    return _make_context()


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestRuleBasedModel:

    def test_returns_all_6_actions(self, model, good_context):
        """Output must contain exactly one prediction per ActionType."""
        preds = model.predict_action_outcomes(good_context, list(ActionType))
        assert len(preds) == len(list(ActionType))
        returned_actions = {p.action for p in preds}
        assert returned_actions == set(ActionType)

    def test_probabilities_in_unit_interval(self, model, good_context):
        """All predicted probabilities must be in (0, 1)."""
        preds = model.predict_action_outcomes(good_context, list(ActionType))
        for p in preds:
            assert 0.0 < p.probability < 1.0, (
                f"{p.action.value}: probability={p.probability} out of (0,1)"
            )

    def test_incentive_probability_higher_than_do_nothing(self, model, good_context):
        """incentive probability must be higher than do_nothing."""
        preds = model.predict_action_outcomes(good_context, list(ActionType))
        pred_map = {p.action: p.probability for p in preds}
        assert pred_map[ActionType.INCENTIVE] > pred_map[ActionType.DO_NOTHING], (
            f"incentive={pred_map[ActionType.INCENTIVE]:.4f} "
            f"<= do_nothing={pred_map[ActionType.DO_NOTHING]:.4f}"
        )

    def test_high_success_rate_increases_probs(self, model):
        """A customer with 95% success rate should get higher probs than 30% success rate."""
        good_ctx = _make_context(customer_success_rate=0.95, customer_transaction_count=50)
        bad_ctx = _make_context(customer_success_rate=0.30, customer_transaction_count=5)

        good_preds = model.predict_action_outcomes(good_ctx, [ActionType.RETRY_NOW])
        bad_preds = model.predict_action_outcomes(bad_ctx, [ActionType.RETRY_NOW])

        assert good_preds[0].probability > bad_preds[0].probability, (
            "Higher success rate should produce higher retry_now probability"
        )

    def test_expired_card_lowers_retry_prob_vs_network_timeout(self, model):
        """expired_card should produce lower retry_now prob than network_timeout."""
        expired_ctx = _make_context(failure_code="expired_card")
        timeout_ctx = _make_context(failure_code="network_timeout")

        expired_preds = model.predict_action_outcomes(expired_ctx, [ActionType.RETRY_NOW])
        timeout_preds = model.predict_action_outcomes(timeout_ctx, [ActionType.RETRY_NOW])

        assert expired_preds[0].probability < timeout_preds[0].probability, (
            "expired_card should have lower retry probability than network_timeout"
        )

    def test_confidence_is_constant_070(self, model, good_context):
        """All predictions must report confidence=0.70 (documented conservative estimate)."""
        preds = model.predict_action_outcomes(good_context, list(ActionType))
        for p in preds:
            assert abs(p.confidence - 0.70) < 1e-9, (
                f"{p.action.value}: confidence={p.confidence}, expected 0.70"
            )
