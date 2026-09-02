"""
RecoveryOS — Integration Tests: Gemini Agent (real API)

2 tests that call the real Gemini API.

IMPORTANT: These tests are automatically skipped when GEMINI_API_KEY is not set.
They require a valid GEMINI_API_KEY in your .env file.

Run with:
    .venv\\Scripts\\python -m pytest tests/integration/test_agent_integration.py -v --tb=short
"""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal

import pytest

# ── Skip entire module if GEMINI_API_KEY is not configured ─────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
pytestmark = pytest.mark.skipif(
    not GEMINI_API_KEY,
    reason="GEMINI_API_KEY not set — skipping Gemini integration tests",
)


# ── Shared helpers ─────────────────────────────────────────────────────────────

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
        case_id="integ-agent-001",
        payment_id="pay-001",
        customer_id="cust-001",
        merchant_id="merch-001",
        amount=Decimal("5000"),
        currency="INR",
        method="card",
        failure_code="insufficient_funds",
        attempt_number=1,
        customer_success_rate=0.75,
        customer_transaction_count=25,
        customer_success_count=18,
        customer_failure_count=7,
        customer_avg_amount=Decimal("4500"),
        time_since_failure_hours=3.0,
        hour_of_day=14,
        day_of_week=2,
        previous_failure_count=1,
        policy=_make_policy(),
    )


def _make_proposal():
    from backend.ml_models.rule_based import RuleBasedRecoveryModel
    from backend.optimizer.expected_value import rank_actions
    from backend.guardrails.engine import GuardrailEngine
    from backend.orchestrator.context import DecisionProposal
    from backend.domain.enums import ActionType

    ctx = _make_context()
    model = RuleBasedRecoveryModel()
    preds = model.predict_action_outcomes(ctx, list(ActionType))
    opt_result = rank_actions(
        predictions=preds,
        recoverable_amount=ctx.amount,
        max_incentive_per_customer=ctx.policy.max_incentive_per_customer,
        policy_version=ctx.policy.version,
    )
    guardrail_result = GuardrailEngine().check(ctx, opt_result)

    return ctx, DecisionProposal(
        case_id="integ-agent-001",
        recommended_action=opt_result.selected_action,
        optimization_result=opt_result,
        guardrail_result=guardrail_result,
        requires_approval=False,
        explanation="Template fallback explanation.",
        model_name="rule_based",
        model_version="v1",
        policy_version="1.0",
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestGeminiAgentIntegration:

    def test_real_gemini_returns_non_empty_explanation(self):
        """
        Real Gemini API call must return a non-empty AgentExplanation.

        This validates the full API → parse → validate pipeline with a live key.
        """
        from backend.agents.agent import GeminiAgent

        agent = GeminiAgent(api_key=GEMINI_API_KEY, model="gemini-2.5-flash", timeout=30.0)
        ctx, proposal = _make_proposal()

        result = asyncio.run(
            agent.explain(proposal, ctx)
        )

        assert result is not None, (
            "Gemini returned None — check API key and model availability."
        )
        assert result.is_valid(), f"Explanation is not valid: {result!r}"
        assert len(result.explanation) > 20, f"Explanation too short: {result.explanation!r}"
        assert len(result.key_factors) >= 1, "Expected at least 1 key factor"

    def test_real_gemini_does_not_change_financial_decision(self):
        """
        The pipeline's financial decision must be identical before and after agent call.

        Gemini only writes explanation — it NEVER changes recommended_action,
        expected_net_revenue, or any financial value.
        """
        from backend.ml_models.rule_based import RuleBasedRecoveryModel
        from backend.orchestrator.recovery_pipeline import RecoveryPipeline
        from backend.agents.agent import GeminiAgent
        from backend.domain.enums import ExecutionMode

        # Pipeline without agent (deterministic baseline)
        baseline_pipeline = RecoveryPipeline(
            model=RuleBasedRecoveryModel(),
            execution_mode=ExecutionMode.SIMULATION,
            agent=None,
        )

        # Pipeline with real Gemini agent
        agent = GeminiAgent(api_key=GEMINI_API_KEY, model="gemini-2.5-flash", timeout=30.0)
        agent_pipeline = RecoveryPipeline(
            model=RuleBasedRecoveryModel(),
            execution_mode=ExecutionMode.SIMULATION,
            agent=agent,
        )

        ctx = _make_context()

        # Run both pipelines
        baseline = asyncio.run(baseline_pipeline.process_case(ctx))
        with_agent = asyncio.run(agent_pipeline.process_case(ctx))

        # Financial values must be identical
        assert baseline.recommended_action == with_agent.recommended_action, (
            f"Action changed: {baseline.recommended_action.value} → "
            f"{with_agent.recommended_action.value}"
        )
        assert (
            baseline.optimization_result.selected_expected_net_revenue
            == with_agent.optimization_result.selected_expected_net_revenue
        ), "Expected net revenue changed after agent call — this violates Rule 1."

        # Only explanation may differ
        # (Gemini explanation may or may not differ from template — both are valid)
        assert with_agent.explanation, "Explanation must not be empty even with agent."
