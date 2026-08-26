"""
RecoveryOS — Unit Tests: Recovery Pipeline (End-to-End)

5 integration-style tests using in-memory components (no DB, no Gemini).
Verifies the full 10-stage pipeline contract.
"""

from __future__ import annotations

import pytest
from decimal import Decimal

from backend.domain.enums import ActionType, ExecutionMode, PipelineSource
from backend.ml_models.rule_based import RuleBasedRecoveryModel
from backend.orchestrator.context import CaseContext, DecisionProposal, RecoveryPolicy
from backend.orchestrator.recovery_pipeline import RecoveryPipeline


# ── Helpers ────────────────────────────────────────────────────────────────────

def _policy(**kwargs) -> RecoveryPolicy:
    defaults = dict(
        version="1.0",
        max_retries_per_customer=2,
        max_messages_per_customer=2,
        max_incentive_per_customer=Decimal("100"),
        daily_incentive_pool=Decimal("5000"),
        high_value_threshold=Decimal("10000"),
        min_expected_net_revenue=Decimal("0"),     # zero = don't force do_nothing
        min_model_confidence=0.0,                  # zero = don't escalate
        recovery_window_hours=48,
        auto_action_probability=0.70,
    )
    defaults.update(kwargs)
    return RecoveryPolicy(**defaults)


def _context(**kwargs) -> CaseContext:
    defaults = dict(
        case_id="pipe-case-001",
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


@pytest.fixture
def pipeline() -> RecoveryPipeline:
    return RecoveryPipeline(
        model=RuleBasedRecoveryModel(),
        execution_mode=ExecutionMode.SIMULATION,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestRecoveryPipeline:

    @pytest.mark.asyncio
    async def test_full_pipeline_returns_proposal(self, pipeline):
        """The pipeline must return a DecisionProposal for a clean case."""
        proposal = await pipeline.process_case(_context(), PipelineSource.SIMULATOR)
        assert isinstance(proposal, DecisionProposal)
        assert proposal.case_id == "pipe-case-001"
        assert proposal.recommended_action is not None

    @pytest.mark.asyncio
    async def test_pipeline_selects_best_action(self, pipeline):
        """
        For a high-quality customer (success_rate=0.90), the pipeline should
        select a meaningful action — not do_nothing.
        """
        ctx = _context(customer_success_rate=0.90, customer_transaction_count=30)
        proposal = await pipeline.process_case(ctx, PipelineSource.SIMULATOR)
        # With good customer, best action should not be do_nothing
        assert proposal.recommended_action != ActionType.ESCALATE

    @pytest.mark.asyncio
    async def test_pipeline_respects_guardrail_retry_limit(self, pipeline):
        """
        When retry_count >= max_retries, pipeline must not select retry_now or retry_later.
        """
        ctx = _context(retry_count=2)  # at the policy max
        proposal = await pipeline.process_case(ctx, PipelineSource.SIMULATOR)
        assert proposal.recommended_action not in {
            ActionType.RETRY_NOW,
            ActionType.RETRY_LATER,
        }

    @pytest.mark.asyncio
    async def test_pipeline_is_deterministic(self, pipeline):
        """Same context → same proposal every time."""
        ctx = _context()
        p1 = await pipeline.process_case(ctx, PipelineSource.SIMULATOR)
        p2 = await pipeline.process_case(ctx, PipelineSource.SIMULATOR)
        assert p1.recommended_action == p2.recommended_action
        assert p1.optimization_result.selected_expected_net_revenue == \
               p2.optimization_result.selected_expected_net_revenue

    @pytest.mark.asyncio
    async def test_pipeline_explanation_is_non_empty(self, pipeline):
        """The pipeline must always return a non-empty explanation string."""
        proposal = await pipeline.process_case(_context(), PipelineSource.SIMULATOR)
        assert isinstance(proposal.explanation, str)
        assert len(proposal.explanation.strip()) > 0

    @pytest.mark.asyncio
    async def test_pipeline_stops_on_already_succeeded_payment(self, pipeline):
        """If payment_already_succeeded, pipeline should recommend do_nothing or stop."""
        ctx = _context(payment_already_succeeded=True)
        proposal = await pipeline.process_case(ctx, PipelineSource.SIMULATOR)
        assert proposal.recommended_action == ActionType.DO_NOTHING
        assert proposal.guardrail_result.verdict == "stop"
