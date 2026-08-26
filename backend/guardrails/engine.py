"""
RecoveryOS — Guardrail Engine

Deterministic policy enforcement. 12 hard checks in strict order.

Architecture rule (§13):
    "Deterministic only."
    "Every guardrail decision must be logged."
    "After removing blocked actions, re-run optimization."

The engine is stateless — it receives all context it needs in GuardrailContext.
It NEVER mutates the database or calls external services.

Check order (from architecture_v2.md §13):
    1.  Payment already successful             → STOP
    2.  Case expired                           → EXPIRED
    3.  Duplicate action / idempotency         → STOP
    4.  Action not in allowed set              → BLOCK
    5.  Retry limit reached                    → remove retry_now + retry_later
    6.  Message limit reached                  → remove reminder
    7.  Customer incentive limit reached       → remove incentive
    8.  Daily incentive pool exhausted         → remove incentive
    9.  High-value threshold                   → requires_approval = True
    10. Required approval missing              → PENDING_APPROVAL
    11. Model confidence too low               → ESCALATE or approval
    12. Expected net revenue below minimum     → force do_nothing
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timezone
from typing import Literal

from backend.domain.enums import ActionType
from backend.orchestrator.context import CaseContext
from backend.optimizer.expected_value import CandidateEV, OptimizationResult

logger = logging.getLogger(__name__)

GuardrailVerdict = Literal["proceed", "stop", "expired", "pending_approval", "escalate"]


@dataclass
class GuardrailResult:
    """
    Result of running the guardrail engine against a case.

    passed:          True if all checks passed (verdict == "proceed").
    blocked_actions: Actions removed by guardrail checks.
    block_reasons:   Per-action reason string.
    requires_approval: True if the decision needs human approval.
    verdict:         Final routing decision.
    audit_events:    List of event names to write to audit_logs table.
    policy_version:  The policy version that produced this result.
    """

    passed: bool
    blocked_actions: list[ActionType]
    block_reasons: dict[ActionType, str]
    requires_approval: bool
    verdict: GuardrailVerdict
    audit_events: list[str]
    policy_version: str


class GuardrailEngine:
    """
    Deterministic guardrail engine.

    Usage:
        result = GuardrailEngine.check(context, optimization_result)

    The engine is a stateless class — instantiation is optional but
    supported for dependency injection / testing.
    """

    @staticmethod
    def check(
        context: CaseContext,
        optimization_result: OptimizationResult,
        approved: bool = False,
    ) -> GuardrailResult:
        """
        Run all 12 guardrail checks against the case context.

        Args:
            context:            Full CaseContext including policy.
            optimization_result: Current optimizer output (before guardrail filtering).
            approved:           True if a human approval has been granted.

        Returns:
            GuardrailResult with verdict and list of blocked actions.
        """
        policy = context.policy
        blocked: dict[ActionType, str] = {}
        audit_events: list[str] = []
        requires_approval: bool = False

        # ── Check 1: Payment already successful ───────────────────────────────
        if context.payment_already_succeeded:
            logger.info("[Guardrail 1] Payment already succeeded — STOP. case=%s", context.case_id)
            audit_events.append("guardrail_blocked:payment_already_succeeded")
            return GuardrailResult(
                passed=False,
                blocked_actions=list(ActionType),
                block_reasons={a: "payment_already_succeeded" for a in ActionType},
                requires_approval=False,
                verdict="stop",
                audit_events=audit_events,
                policy_version=policy.version,
            )

        # ── Check 2: Case expired ──────────────────────────────────────────────
        if context.case_expires_at is not None:
            now = datetime.now(tz=timezone.utc)
            if now > context.case_expires_at:
                logger.info("[Guardrail 2] Case expired. case=%s", context.case_id)
                audit_events.append("guardrail_blocked:case_expired")
                return GuardrailResult(
                    passed=False,
                    blocked_actions=list(ActionType),
                    block_reasons={a: "case_expired" for a in ActionType},
                    requires_approval=False,
                    verdict="expired",
                    audit_events=audit_events,
                    policy_version=policy.version,
                )

        # ── Check 3: Duplicate action / idempotency ───────────────────────────
        # Selected action was already executed for this case
        selected_action = optimization_result.selected_action
        if selected_action.value in context.prior_actions:
            logger.info(
                "[Guardrail 3] Duplicate action %s already attempted. case=%s",
                selected_action, context.case_id,
            )
            audit_events.append(f"guardrail_blocked:duplicate_action:{selected_action.value}")
            blocked[selected_action] = "duplicate_action_idempotency"

        # ── Check 4: Retry limit ───────────────────────────────────────────────
        if context.retry_count >= policy.max_retries_per_customer:
            logger.info(
                "[Guardrail 5] Retry limit reached (%d). case=%s",
                context.retry_count, context.case_id,
            )
            audit_events.append("guardrail_blocked:retry_limit_reached")
            blocked[ActionType.RETRY_NOW] = "retry_limit_reached"
            blocked[ActionType.RETRY_LATER] = "retry_limit_reached"

        # ── Check 5: Message limit ─────────────────────────────────────────────
        if context.message_count >= policy.max_messages_per_customer:
            logger.info(
                "[Guardrail 6] Message limit reached (%d). case=%s",
                context.message_count, context.case_id,
            )
            audit_events.append("guardrail_blocked:message_limit_reached")
            blocked[ActionType.REMINDER] = "message_limit_reached"

        # ── Check 6: Customer incentive limit ─────────────────────────────────
        if context.customer_incentive_spent >= policy.max_incentive_per_customer:
            logger.info(
                "[Guardrail 7] Customer incentive limit reached. case=%s", context.case_id,
            )
            audit_events.append("guardrail_blocked:customer_incentive_limit")
            blocked[ActionType.INCENTIVE] = "customer_incentive_limit_reached"

        # ── Check 7: Daily incentive pool ─────────────────────────────────────
        # Find incentive cost from candidates
        incentive_cost = Decimal("0")
        for candidate in optimization_result.candidates:
            if candidate.action == ActionType.INCENTIVE:
                incentive_cost = candidate.incentive_cost
                break

        if ActionType.INCENTIVE not in blocked and incentive_cost > context.daily_incentive_remaining:
            logger.info(
                "[Guardrail 8] Daily incentive pool exhausted. case=%s", context.case_id,
            )
            audit_events.append("guardrail_blocked:daily_incentive_pool_exhausted")
            blocked[ActionType.INCENTIVE] = "daily_incentive_pool_exhausted"

        # ── Check 8: High-value threshold → approval required ─────────────────
        if context.amount >= policy.high_value_threshold:
            logger.info(
                "[Guardrail 9] High-value case (%.2f >= %.2f) requires approval. case=%s",
                context.amount, policy.high_value_threshold, context.case_id,
            )
            audit_events.append("guardrail_flagged:high_value_approval_required")
            requires_approval = True

        # ── Check 9: Required approval not yet granted ─────────────────────────
        if requires_approval and not approved:
            logger.info("[Guardrail 10] Approval required but not granted. case=%s", context.case_id)
            audit_events.append("guardrail_blocked:pending_approval")
            return GuardrailResult(
                passed=False,
                blocked_actions=list(blocked.keys()),
                block_reasons=blocked,
                requires_approval=True,
                verdict="pending_approval",
                audit_events=audit_events,
                policy_version=policy.version,
            )

        # ── Check 10: Model confidence too low ────────────────────────────────
        # Find the confidence for the selected action
        selected_confidence = 0.0
        for candidate in optimization_result.candidates:
            if candidate.action == optimization_result.selected_action:
                selected_confidence = candidate.confidence
                break

        if selected_confidence < policy.min_model_confidence:
            logger.info(
                "[Guardrail 11] Model confidence %.3f < %.3f — ESCALATE. case=%s",
                selected_confidence, policy.min_model_confidence, context.case_id,
            )
            audit_events.append(
                f"guardrail_blocked:low_model_confidence:{selected_confidence:.3f}"
            )
            return GuardrailResult(
                passed=False,
                blocked_actions=list(blocked.keys()),
                block_reasons=blocked,
                requires_approval=False,
                verdict="escalate",
                audit_events=audit_events,
                policy_version=policy.version,
            )

        # ── Check 11: Expected net revenue below minimum ──────────────────────
        best_enr = optimization_result.selected_expected_net_revenue
        if best_enr < policy.min_expected_net_revenue:
            logger.info(
                "[Guardrail 12] Best ENR %.2f < min %.2f — DO NOTHING. case=%s",
                best_enr, policy.min_expected_net_revenue, context.case_id,
            )
            audit_events.append(f"guardrail_forced:do_nothing:enr_below_minimum:{best_enr:.2f}")
            # Block all actions except do_nothing
            for action in ActionType:
                if action != ActionType.DO_NOTHING and action not in blocked:
                    blocked[action] = "expected_net_revenue_below_minimum"

        # ── All checks passed (or only some actions blocked) ──────────────────
        passed = len(blocked) == 0
        if passed:
            audit_events.append("guardrail_passed")
        else:
            audit_events.append(f"guardrail_partial:blocked={len(blocked)}")

        return GuardrailResult(
            passed=passed,
            blocked_actions=list(blocked.keys()),
            block_reasons=blocked,
            requires_approval=requires_approval,
            verdict="proceed",
            audit_events=audit_events,
            policy_version=policy.version,
        )
