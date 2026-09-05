"""
RecoveryOS — Case Service

Handles business logic for persisting optimizer decisions and execution outcomes.
Enforces architecture §22, §23, §33 and techstack §11.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from backend.db.connection import db_available
from backend.db.repositories.recovery_cases import RecoveryCaseRepository
from backend.domain.enums import ApprovalStatus, CaseStatus, GuardrailOutcome
from backend.orchestrator.context import DecisionProposal

logger = logging.getLogger(__name__)


class CaseService:
    def __init__(self, repo: RecoveryCaseRepository | None = None) -> None:
        self.repo = repo or RecoveryCaseRepository()

    async def persist_decision(
        self,
        case_id: str,
        proposal: DecisionProposal,
    ) -> CaseStatus:
        """
        Persist the output of the 10-stage optimization pipeline onto the recovery case
        and save action candidates.
        """
        if not db_available():
            logger.warning("CaseService: DB unavailable, skipping persist_decision for %s", case_id)
            return CaseStatus.DECISION_READY

        # Determine next status based on guardrail & approval rules
        if proposal.guardrail_result.verdict == GuardrailOutcome.ESCALATE.value:
            next_status = CaseStatus.ESCALATED
            approval_status = ApprovalStatus.NOT_REQUIRED
        elif proposal.requires_approval:
            next_status = CaseStatus.PENDING_APPROVAL
            approval_status = ApprovalStatus.PENDING
        else:
            next_status = CaseStatus.DECISION_READY
            approval_status = ApprovalStatus.NOT_REQUIRED

        # 1. Update recovery case decision fields
        opt_res = proposal.optimization_result
        selected_cand = next(
            (c for c in opt_res.candidates if c.action == proposal.recommended_action),
            None,
        )
        gross_rec = selected_cand.expected_gross_recovery if selected_cand else Decimal("0")
        net_rec = opt_res.selected_expected_net_revenue

        await self.repo.update_decision(
            case_id=case_id,
            selected_action=proposal.recommended_action,
            expected_gross_recovery=gross_rec,
            expected_net_revenue=net_rec,
            requires_approval=proposal.requires_approval,
            approval_status=approval_status,
            model_name=proposal.model_name or "unknown",
            model_version=proposal.model_version or "unknown",
            policy_version=proposal.policy_version or "unknown",
            status=next_status,
        )

        # 2. Persist candidate action rankings
        if opt_res.candidates:
            candidate_dicts = [
                {
                    "action": c.action.value if hasattr(c.action, "value") else str(c.action),
                    "probability": float(c.probability),
                    "confidence": float(getattr(c, "model_confidence", 0.8) or 0.8),
                    "recoverable_amount": getattr(c, "recoverable_amount", c.expected_gross_recovery),
                    "intervention_cost": getattr(c, "cost", Decimal("0")),
                    "incentive_cost": getattr(c, "incentive_cost", Decimal("0")),
                    "contact_cost": getattr(c, "contact_cost", Decimal("0")),
                    "expected_gross_recovery": c.expected_gross_recovery,
                    "expected_net_revenue": c.expected_net_revenue,
                    "allowed": c.allowed,
                    "blocked_reason": getattr(c, "blocked_reason", None),
                    "rank": c.rank,
                }
                for c in opt_res.candidates
            ]
            await self.repo.save_action_candidates(
                case_id=case_id,
                candidates=candidate_dicts,
            )

        logger.info(
            "CaseService: Decision persisted for case %s -> status=%s action=%s",
            case_id, next_status.value, proposal.recommended_action.value,
        )
        return next_status

    async def persist_execution(
        self,
        case_id: str,
        actual_recovered: Decimal,
        cost: Decimal,
    ) -> CaseStatus:
        """
        Update the recovery case with actual recovery results and mark terminal state.
        """
        if not db_available():
            logger.warning("CaseService: DB unavailable, skipping persist_execution for %s", case_id)
            return CaseStatus.RECOVERED if actual_recovered > 0 else CaseStatus.FAILED

        final_status = CaseStatus.RECOVERED if actual_recovered > 0 else CaseStatus.FAILED
        net_recovered = actual_recovered - cost

        await self.repo.update_result(
            case_id=case_id,
            status=final_status,
            actual_recovered=actual_recovered,
            intervention_cost=cost,
            incremental_recovery=actual_recovered,
            net_incremental_recovery=net_recovered,
        )

        logger.info(
            "CaseService: Execution persisted for case %s -> status=%s recovered=%.2f cost=%.2f",
            case_id, final_status.value, actual_recovered, cost,
        )
        return final_status
