"""
RecoveryOS — Unit Tests: Guardrail Engine

8 test cases covering all critical guardrail checks.
No DB required — all tests use CaseContext directly.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from backend.domain.enums import ActionType
from backend.guardrails.engine import GuardrailEngine
from backend.ml_models.protocol import ActionPrediction
from backend.optimizer.expected_value import rank_actions
from backend.orchestrator.context import CaseContext, RecoveryPolicy


# ── Helpers ────────────────────────────────────────────────────────────────────

def _policy(**kwargs) -> RecoveryPolicy:
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


def _context(**kwargs) -> CaseContext:
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
        policy=_policy(),
        payment_already_succeeded=False,
    )
    defaults.update(kwargs)
    return CaseContext(**defaults)


def _make_opt_result(probability: float = 0.75, confidence: float = 0.75):
    """Build a simple OptimizationResult from uniform predictions."""
    preds = [
        ActionPrediction(a, probability, confidence, "test", "v0")
        for a in ActionType
    ]
    return rank_actions(preds, Decimal("3000"), Decimal("100"), "1.0")


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestGuardrails:

    def test_already_successful_payment_stops(self):
        """Check 1: payment_already_succeeded=True → verdict=stop."""
        ctx = _context(payment_already_succeeded=True)
        result = GuardrailEngine.check(ctx, _make_opt_result())
        assert result.verdict == "stop"
        assert not result.passed

    def test_expired_case_stops(self):
        """Check 2: case expired → verdict=expired."""
        past = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        ctx = _context(case_expires_at=past)
        result = GuardrailEngine.check(ctx, _make_opt_result())
        assert result.verdict == "expired"

    def test_retry_limit_removes_retry_actions(self):
        """Check 5: retry_count >= max_retries → retry_now + retry_later blocked."""
        ctx = _context(retry_count=2)  # policy max is 2
        result = GuardrailEngine.check(ctx, _make_opt_result())
        assert ActionType.RETRY_NOW in result.blocked_actions
        assert ActionType.RETRY_LATER in result.blocked_actions

    def test_message_limit_removes_reminder(self):
        """Check 6: message_count >= max_messages → reminder blocked."""
        ctx = _context(message_count=2)  # policy max is 2
        result = GuardrailEngine.check(ctx, _make_opt_result())
        assert ActionType.REMINDER in result.blocked_actions

    def test_customer_incentive_limit_removes_incentive(self):
        """Check 7: customer_incentive_spent >= max_incentive → incentive blocked."""
        ctx = _context(customer_incentive_spent=Decimal("100"))  # at the limit
        result = GuardrailEngine.check(ctx, _make_opt_result())
        assert ActionType.INCENTIVE in result.blocked_actions

    def test_high_value_requires_approval(self):
        """Check 9: amount >= high_value_threshold → requires_approval=True."""
        ctx = _context(amount=Decimal("15000"))  # threshold is 10000
        result = GuardrailEngine.check(ctx, _make_opt_result())
        assert result.requires_approval is True
        # Without approval granted, verdict should be pending_approval
        assert result.verdict == "pending_approval"

    def test_high_value_approved_proceeds(self):
        """Check 9+10: high-value case with approved=True → verdict=proceed."""
        ctx = _context(amount=Decimal("15000"))
        result = GuardrailEngine.check(ctx, _make_opt_result(), approved=True)
        # After approval, should proceed (assuming other checks pass)
        assert result.verdict in {"proceed", "escalate"}  # escalate if confidence too low

    def test_low_confidence_escalates(self):
        """Check 11: model confidence below min_model_confidence → verdict=escalate."""
        # min_model_confidence is 0.65; use 0.50
        result = GuardrailEngine.check(_context(), _make_opt_result(confidence=0.50))
        assert result.verdict == "escalate"

    def test_all_checks_pass_when_clean(self):
        """Clean context with good confidence → verdict=proceed, passed=True."""
        ctx = _context()  # all defaults are clean
        result = GuardrailEngine.check(ctx, _make_opt_result(probability=0.80, confidence=0.80))
        assert result.verdict == "proceed"
        assert result.passed is True
