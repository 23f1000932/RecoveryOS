"""
RecoveryOS — Unit Tests: Action Adapters (Tools)

8 tests covering:
  - ActionResult and VerificationResult contracts
  - idempotency_key format
  - each adapter returns ActionResult in simulation mode
  - pipeline execute=True calls _execute_action + VerificationAdapter

No external API calls — all mocked or in simulation mode.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from backend.tools.protocol import ActionResult, VerificationResult, make_idempotency_key
from backend.domain.enums import ActionType, ExecutionMode


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_policy():
    from backend.orchestrator.context import RecoveryPolicy
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


def _make_context():
    from backend.orchestrator.context import CaseContext
    return CaseContext(
        case_id="tools-test-001",
        payment_id="pay-001",
        customer_id="cust-001",
        merchant_id="merch-001",
        amount=Decimal("3000"),
        currency="INR",
        method="card",
        failure_code="insufficient_funds",
        attempt_number=1,
        customer_success_rate=0.75,
        customer_transaction_count=20,
        customer_success_count=15,
        customer_failure_count=5,
        customer_avg_amount=Decimal("3000"),
        time_since_failure_hours=2.0,
        hour_of_day=10,
        day_of_week=1,
        previous_failure_count=0,
        policy=_make_policy(),
    )


# ── Protocol Tests ─────────────────────────────────────────────────────────────

class TestProtocol:

    def test_make_idempotency_key_format(self):
        """Idempotency key must follow {case_id}:{action}:{attempt}."""
        key = make_idempotency_key("case-123", "retry_now", 1)
        assert key == "case-123:retry_now:1"

    def test_make_idempotency_key_different_attempts_differ(self):
        """Different attempt numbers must produce different keys."""
        k1 = make_idempotency_key("case-123", "retry_now", 1)
        k2 = make_idempotency_key("case-123", "retry_now", 2)
        assert k1 != k2

    def test_action_result_defaults(self):
        """ActionResult defaults must be safe."""
        result = ActionResult(
            success=True,
            idempotency_key="test-key",
        )
        assert result.provider_reference == ""
        assert result.cost == Decimal("0")
        assert result.error_code is None
        assert result.execution_mode == ExecutionMode.SIMULATION

    def test_verification_result_not_recovered(self):
        """VerificationResult with payment_recovered=False has actual_recovered=0."""
        result = VerificationResult(
            payment_recovered=False,
            actual_recovered=Decimal("0"),
            payment_status="failed",
        )
        assert not result.payment_recovered
        assert result.actual_recovered == Decimal("0")


# ── Adapter Simulation Tests ───────────────────────────────────────────────────

class TestAdaptersSimulation:

    def test_retry_adapter_simulation(self):
        """RetryAdapter in SIMULATION mode returns ActionResult.success=True."""
        from backend.tools.retry import RetryAdapter
        ctx = _make_context()
        result = asyncio.run(
            RetryAdapter().execute("case-001", "retry_now", ctx, attempt_number=1)
        )
        assert isinstance(result, ActionResult)
        assert result.success is True
        assert result.idempotency_key == "case-001:retry_now:1"
        assert result.provider_reference.startswith("sim-")

    def test_reminder_adapter_simulation(self):
        """ReminderAdapter in SIMULATION mode charges contact cost."""
        from backend.tools.reminder import ReminderAdapter, REMINDER_CONTACT_COST
        ctx = _make_context()
        result = asyncio.run(
            ReminderAdapter().execute("case-001", ctx, attempt_number=1)
        )
        assert result.success is True
        assert result.cost == REMINDER_CONTACT_COST

    def test_incentive_adapter_simulation(self):
        """IncentiveAdapter in SIMULATION mode charges contact + incentive cost."""
        from backend.tools.incentive import IncentiveAdapter, INCENTIVE_CONTACT_COST
        ctx = _make_context()
        incentive_amount = Decimal("100")
        result = asyncio.run(
            IncentiveAdapter().execute("case-001", ctx, incentive_amount=incentive_amount)
        )
        assert result.success is True
        assert result.cost == INCENTIVE_CONTACT_COST + incentive_amount

    def test_escalation_adapter_simulation(self):
        """EscalationAdapter always succeeds — pure state transition."""
        from backend.tools.escalation import EscalationAdapter
        ctx = _make_context()
        result = asyncio.run(
            EscalationAdapter().execute("case-001", ctx)
        )
        assert result.success is True
        assert result.cost == Decimal("0")

    def test_stop_adapter_simulation(self):
        """StopAdapter always succeeds — pure state transition."""
        from backend.tools.stop import StopAdapter
        ctx = _make_context()
        result = asyncio.run(
            StopAdapter().execute("case-001", ctx)
        )
        assert result.success is True
        assert result.cost == Decimal("0")


# ── Pipeline Execute Tests ─────────────────────────────────────────────────────

class TestPipelineExecute:

    def test_pipeline_execute_false_does_not_call_adapters(self):
        """
        pipeline.process_case(execute=False) must return a proposal
        with executed=False and no action_result.
        """
        from backend.ml_models.rule_based import RuleBasedRecoveryModel
        from backend.orchestrator.recovery_pipeline import RecoveryPipeline
        from backend.domain.enums import ExecutionMode

        pipeline = RecoveryPipeline(
            model=RuleBasedRecoveryModel(),
            execution_mode=ExecutionMode.SIMULATION,
        )
        ctx = _make_context()
        proposal = asyncio.run(pipeline.process_case(ctx, execute=False))

        assert not proposal.executed
        assert proposal.action_result is None
        assert proposal.actual_recovered == Decimal("0")

    def test_pipeline_execute_true_runs_adapter_and_verifies(self):
        """
        pipeline.process_case(execute=True) must populate executed=True
        and set action_result + verification_result.
        """
        from backend.ml_models.rule_based import RuleBasedRecoveryModel
        from backend.orchestrator.recovery_pipeline import RecoveryPipeline
        from backend.domain.enums import ExecutionMode

        pipeline = RecoveryPipeline(
            model=RuleBasedRecoveryModel(),
            execution_mode=ExecutionMode.SIMULATION,
        )
        ctx = _make_context()
        proposal = asyncio.run(pipeline.process_case(ctx, execute=True))

        assert proposal.executed is True
        assert proposal.action_result is not None
        assert proposal.verification_result is not None
        # Actual recovered is either 0 or the full amount (Bernoulli draw)
        assert proposal.actual_recovered >= Decimal("0")
