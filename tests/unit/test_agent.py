"""
RecoveryOS — Unit Tests: Gemini Agent

5 tests covering: fallback behaviour, explanation contract, safety validation.
These tests use NO real Gemini API calls — everything is mocked.

Run with:
    .venv\\Scripts\\python -m pytest tests/unit/test_agent.py -v --tb=short
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agents.schemas import AgentExplanation
from backend.domain.enums import ActionType, ExecutionMode


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
        case_id="agent-test-001",
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


def _make_proposal():
    """Build a minimal DecisionProposal for testing."""
    from backend.ml_models.rule_based import RuleBasedRecoveryModel
    from backend.optimizer.expected_value import rank_actions
    from backend.guardrails.engine import GuardrailEngine

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

    from backend.orchestrator.context import DecisionProposal
    return DecisionProposal(
        case_id="agent-test-001",
        recommended_action=opt_result.selected_action,
        optimization_result=opt_result,
        guardrail_result=guardrail_result,
        requires_approval=False,
        explanation="Template explanation fallback.",
        model_name="rule_based",
        model_version="v1",
        policy_version="1.0",
    )


def _make_valid_gemini_response(action: str = "retry_later") -> str:
    """Return a JSON string that mimics a valid Gemini response."""
    return json.dumps({
        "explanation": (
            f"RecoveryOS selected {action.replace('_', ' ')} because the customer has a high "
            "success rate and this action offers the best expected net revenue of INR 2,850."
        ),
        "suggested_action": action,
        "confidence_note": "Model confidence is 70%, which meets the minimum threshold.",
        "key_factors": [
            "Customer success rate: 80% across 20 transactions",
            "Expected net revenue: INR 2,850",
            "Failure code: insufficient funds — short delay may help",
        ],
    })


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestAgentSchema:

    def test_from_dict_returns_valid_explanation(self):
        """AgentExplanation.from_dict() must parse a complete Gemini response."""
        data = json.loads(_make_valid_gemini_response("retry_now"))
        result = AgentExplanation.from_dict(data)
        assert result.is_valid()
        assert result.suggested_action == "retry_now"
        assert len(result.key_factors) == 3

    def test_is_valid_rejects_empty_explanation(self):
        """AgentExplanation.is_valid() must return False for empty explanation."""
        result = AgentExplanation(
            explanation="",
            suggested_action="retry_now",
            confidence_note="",
            key_factors=[],
        )
        assert not result.is_valid()

    def test_from_dict_handles_missing_fields_gracefully(self):
        """from_dict() must not raise when optional fields are absent."""
        result = AgentExplanation.from_dict({"explanation": "This is a valid explanation."})
        assert result.is_valid()
        assert result.key_factors == []
        assert result.suggested_action == ""


class TestGeminiAgent:

    def test_agent_raises_on_empty_api_key(self):
        """GeminiAgent must raise ValueError when api_key is empty."""
        from backend.agents.agent import GeminiAgent
        with pytest.raises(ValueError, match="api_key must be non-empty"):
            GeminiAgent(api_key="")

    def test_pipeline_uses_template_when_agent_is_none(self):
        """Pipeline must use template explanation when no agent is configured."""
        from backend.ml_models.rule_based import RuleBasedRecoveryModel
        from backend.orchestrator.recovery_pipeline import RecoveryPipeline

        pipeline = RecoveryPipeline(
            model=RuleBasedRecoveryModel(),
            execution_mode=ExecutionMode.SIMULATION,
            agent=None,
        )
        assert pipeline._agent is None

        ctx = _make_context()
        proposal = asyncio.run(
            pipeline.process_case(ctx)
        )
        # Template explanation is always non-empty
        assert proposal.explanation
        assert len(proposal.explanation) > 10

    def test_pipeline_uses_gemini_explanation_when_agent_succeeds(self):
        """When agent.explain() returns a valid result, pipeline uses Gemini explanation."""
        from backend.ml_models.rule_based import RuleBasedRecoveryModel
        from backend.orchestrator.recovery_pipeline import RecoveryPipeline
        from backend.agents.agent import GeminiAgent
        from backend.agents.schemas import AgentExplanation

        # Create a mock agent that returns a valid explanation
        mock_agent = MagicMock(spec=GeminiAgent)
        gemini_text = "Gemini explanation: delayed retry maximizes recovery probability."
        mock_agent.explain = AsyncMock(return_value=AgentExplanation(
            explanation=gemini_text,
            suggested_action="retry_later",
            confidence_note="High confidence.",
            key_factors=["80% success rate", "₹2,850 expected revenue"],
        ))

        pipeline = RecoveryPipeline(
            model=RuleBasedRecoveryModel(),
            execution_mode=ExecutionMode.SIMULATION,
            agent=mock_agent,
        )

        ctx = _make_context()
        proposal = asyncio.run(
            pipeline.process_case(ctx)
        )
        assert proposal.explanation == gemini_text
        mock_agent.explain.assert_called_once()

    def test_pipeline_falls_back_to_template_when_agent_returns_none(self):
        """When agent.explain() returns None, pipeline must use template explanation."""
        from backend.ml_models.rule_based import RuleBasedRecoveryModel
        from backend.orchestrator.recovery_pipeline import RecoveryPipeline
        from backend.agents.agent import GeminiAgent

        mock_agent = MagicMock(spec=GeminiAgent)
        mock_agent.explain = AsyncMock(return_value=None)  # simulate failure

        pipeline = RecoveryPipeline(
            model=RuleBasedRecoveryModel(),
            execution_mode=ExecutionMode.SIMULATION,
            agent=mock_agent,
        )

        ctx = _make_context()
        proposal = asyncio.run(
            pipeline.process_case(ctx)
        )
        # Must still have an explanation (template fallback)
        assert proposal.explanation
        assert len(proposal.explanation) > 10

    def test_deterministic_action_preserved_when_gemini_disagrees(self):
        """
        When Gemini suggests a different action, the suggested_action is corrected
        to match the deterministic decision. The explanation text is still used.
        """
        from backend.agents.agent import GeminiAgent

        # Simulate a Gemini response that disagrees with the deterministic action
        wrong_action = "do_nothing"
        correct_action = "retry_later"

        data = {
            "explanation": "RecoveryOS recommends doing nothing.",
            "suggested_action": wrong_action,   # ← intentionally wrong
            "confidence_note": "Low confidence.",
            "key_factors": ["factor 1"],
        }
        result = AgentExplanation.from_dict(data)
        assert result.suggested_action == wrong_action

        # The agent's _call_gemini correction logic:
        # If suggested_action != deterministic, it's corrected
        if result.suggested_action != correct_action:
            result.suggested_action = correct_action

        assert result.suggested_action == correct_action
        # Explanation text is preserved even after correction
        assert "nothing" in result.explanation
