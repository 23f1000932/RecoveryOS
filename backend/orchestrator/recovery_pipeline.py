"""
RecoveryOS — Recovery Pipeline

The single 10-stage pipeline shared by Simulator, Dashboard, and Webhook.

Architecture rule (§3):
    "The simulator, dashboard, and Razorpay webhook must use the same
     core RecoveryPipeline."

    "Only the event source and execution adapter may differ."

Pipeline stages:
    1.  Detect         — validate case_id, confirm context is provided
    2.  Contextualize  — validate context completeness
    3.  Predict        — call model.predict_action_outcomes()
    4.  Optimize       — rank_actions() → OptimizationResult
    5.  Guard          — GuardrailEngine.check()
    6.  Re-optimize    — if guardrails blocked actions, re-rank remaining
    7.  Approval       — set requires_approval on DecisionProposal
    8.  Explain        — template explanation (Gemini overwrites in Phase 5)
    9.  Measure        — financial values already computed in optimizer
    10. Audit          — return audit event list (caller writes to DB)

Deliberate design decisions:
    - The pipeline does NOT write to the database. It returns a DecisionProposal.
      The caller (API endpoint or simulator runner) does DB writes.
      This makes the pipeline fully testable without a DB mock.
    - The pipeline is async to match FastAPI's execution model, even though
      Phase 3 components are all synchronous. Phase 5+ (Gemini) will be async.
    - Guardrail failures return a DecisionProposal (not an exception) so the
      caller can always serialize and store the decision record.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from backend.domain.enums import ActionType, ExecutionMode, PipelineSource
from backend.guardrails.engine import GuardrailEngine
from backend.ml_models.protocol import RecoveryOutcomeModel
from backend.optimizer.expected_value import rank_actions
from backend.orchestrator.context import CaseContext, DecisionProposal

logger = logging.getLogger(__name__)

_ALL_ACTIONS = list(ActionType)


def _build_explanation(proposal_action: ActionType, enr: Decimal, verdict: str) -> str:
    """
    Template explanation for Phase 3.
    Gemini will overwrite this in Phase 5.
    """
    if verdict == "stop":
        return "Recovery was stopped because the payment has already been collected."
    if verdict == "expired":
        return "This case has passed its recovery window and can no longer be actioned."
    if verdict == "pending_approval":
        return (
            "This case requires merchant approval before any action can be taken. "
            "Please review and approve or reject from the case detail page."
        )
    if verdict == "escalate":
        return (
            "Model confidence is below the required threshold. "
            "This case has been escalated for human review."
        )
    if proposal_action == ActionType.DO_NOTHING:
        return (
            "RecoveryOS determined that no intervention is economically justified "
            "for this case. Expected net revenue is below the minimum threshold."
        )
    return (
        f"RecoveryOS selected {proposal_action.value.replace('_', ' ')} "
        f"because it has the highest expected net revenue "
        f"(₹{enr:,.2f}) among currently allowed actions."
    )


class RecoveryPipeline:
    """
    10-stage recovery decision pipeline.

    Shared by: Simulator (Phase 8), Dashboard case analysis (Phase 5+),
               Razorpay webhook (Phase 6).

    Args:
        model:          Any RecoveryOutcomeModel implementation.
        execution_mode: SIMULATION, TEST_MODE, or DRY_RUN.

    Usage:
        pipeline = RecoveryPipeline(model=RuleBasedRecoveryModel(),
                                    execution_mode=ExecutionMode.SIMULATION)
        proposal = await pipeline.process_case(context, source=PipelineSource.SIMULATOR)
    """

    def __init__(
        self,
        model: RecoveryOutcomeModel,
        execution_mode: ExecutionMode = ExecutionMode.SIMULATION,
    ) -> None:
        self._model = model
        self._execution_mode = execution_mode
        logger.info(
            "RecoveryPipeline initialized: model=%s mode=%s",
            type(model).__name__, execution_mode.value,
        )

    async def process_case(
        self,
        context: CaseContext,
        source: PipelineSource = PipelineSource.SIMULATOR,
        approved: bool = False,
    ) -> DecisionProposal:
        """
        Run the full 10-stage pipeline for a single recovery case.

        Args:
            context:  Complete CaseContext. The pipeline reads this but never mutates it.
            source:   Where this case came from (simulator/webhook/dashboard).
            approved: True if the merchant has already approved this case.

        Returns:
            DecisionProposal — the complete decision record.
            The caller is responsible for writing this to the database.

        This method NEVER:
            - writes to the database;
            - calls Razorpay;
            - executes a payment action;
            - let Gemini pick the action.
        """
        case_id = context.case_id
        policy = context.policy

        logger.info(
            "[Pipeline] Starting. case=%s source=%s mode=%s",
            case_id, source.value, self._execution_mode.value,
        )

        # ── Stage 1: Detect ───────────────────────────────────────────────────
        if not case_id:
            raise ValueError("CaseContext.case_id must not be empty.")
        logger.debug("[Stage 1: Detect] case=%s", case_id)

        # ── Stage 2: Contextualize ────────────────────────────────────────────
        # Validate mandatory fields are populated
        if not context.payment_id or not context.customer_id:
            raise ValueError(
                f"Incomplete CaseContext for case={case_id}: "
                "payment_id and customer_id are required."
            )
        logger.debug("[Stage 2: Contextualize] case=%s amount=%.2f", case_id, context.amount)

        # ── Stage 3: Predict ──────────────────────────────────────────────────
        predictions = self._model.predict_action_outcomes(context, _ALL_ACTIONS)
        logger.debug(
            "[Stage 3: Predict] case=%s model=%s predictions=%d",
            case_id,
            predictions[0].model_name if predictions else "none",
            len(predictions),
        )

        # ── Stage 4: Optimize ─────────────────────────────────────────────────
        optimization_result = rank_actions(
            predictions=predictions,
            recoverable_amount=context.amount,
            max_incentive_per_customer=policy.max_incentive_per_customer,
            policy_version=policy.version,
        )
        logger.debug(
            "[Stage 4: Optimize] case=%s selected=%s enr=%.2f",
            case_id,
            optimization_result.selected_action.value,
            optimization_result.selected_expected_net_revenue,
        )

        # ── Stage 5: Guard ────────────────────────────────────────────────────
        guardrail_result = GuardrailEngine.check(
            context=context,
            optimization_result=optimization_result,
            approved=approved,
        )
        logger.debug(
            "[Stage 5: Guard] case=%s verdict=%s blocked=%s",
            case_id,
            guardrail_result.verdict,
            [a.value for a in guardrail_result.blocked_actions],
        )

        # ── Stage 6: Re-optimize (if guardrails blocked some actions) ─────────
        final_result = optimization_result
        if guardrail_result.blocked_actions and guardrail_result.verdict == "proceed":
            blocked_map = {
                a: guardrail_result.block_reasons.get(a, "blocked")
                for a in guardrail_result.blocked_actions
            }
            final_result = rank_actions(
                predictions=predictions,
                recoverable_amount=context.amount,
                max_incentive_per_customer=policy.max_incentive_per_customer,
                policy_version=policy.version,
                blocked_actions=blocked_map,
            )
            logger.debug(
                "[Stage 6: Re-optimize] case=%s new_selected=%s",
                case_id, final_result.selected_action.value,
            )

        # ── Stage 7: Approval ─────────────────────────────────────────────────
        requires_approval = guardrail_result.requires_approval
        logger.debug(
            "[Stage 7: Approval] case=%s requires_approval=%s approved=%s",
            case_id, requires_approval, approved,
        )

        # Determine final recommended action
        if guardrail_result.verdict == "stop":
            recommended_action = ActionType.DO_NOTHING
        elif guardrail_result.verdict in ("expired", "escalate"):
            recommended_action = ActionType.ESCALATE
        elif guardrail_result.verdict == "pending_approval":
            # Keep the intended action, but mark it as needing approval
            recommended_action = final_result.selected_action
        else:
            recommended_action = final_result.selected_action

        # ── Stage 8: Explain ──────────────────────────────────────────────────
        explanation = _build_explanation(
            proposal_action=recommended_action,
            enr=final_result.selected_expected_net_revenue,
            verdict=guardrail_result.verdict,
        )
        logger.debug("[Stage 8: Explain] case=%s explanation=%r", case_id, explanation[:60])

        # ── Stage 9: Measure ──────────────────────────────────────────────────
        # Financial values are already in OptimizationResult — nothing to do here.
        logger.debug(
            "[Stage 9: Measure] case=%s gross=%.2f net=%.2f",
            case_id,
            next(
                (c.expected_gross_recovery for c in final_result.candidates
                 if c.action == final_result.selected_action),
                Decimal("0"),
            ),
            final_result.selected_expected_net_revenue,
        )

        # ── Stage 10: Audit ───────────────────────────────────────────────────
        # Return audit events — the CALLER writes them to audit_logs table.
        logger.info(
            "[Pipeline] Complete. case=%s action=%s verdict=%s enr=%.2f events=%s",
            case_id,
            recommended_action.value,
            guardrail_result.verdict,
            final_result.selected_expected_net_revenue,
            guardrail_result.audit_events,
        )

        return DecisionProposal(
            case_id=case_id,
            recommended_action=recommended_action,
            optimization_result=final_result,
            guardrail_result=guardrail_result,
            requires_approval=requires_approval,
            explanation=explanation,
            model_name=final_result.model_name,
            model_version=final_result.model_version,
            policy_version=policy.version,
        )
