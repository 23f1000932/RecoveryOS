"""
RecoveryOS — Audit Service

Provides centralized audit logging for all pipeline stages and case mutations.
Enforces architecture §25, §26 and Rule 4 (safe failure when DB is unavailable).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from backend.db.connection import db_available
from backend.db.repositories.audit import AuditRepository
from backend.domain.enums import (
    ActionType,
    ApprovalStatus,
    AuditEventType,
    PipelineSource,
)
from backend.domain.models import AuditEntry
from backend.orchestrator.context import CaseContext, DecisionProposal

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, repo: AuditRepository | None = None) -> None:
        self.repo = repo or AuditRepository()

    async def write_pipeline_events(
        self,
        case_id: str,
        proposal: DecisionProposal,
        context: CaseContext,
        source: PipelineSource,
        actor: str = "system",
    ) -> None:
        """
        Record the sequence of audit entries produced by running the 10-stage pipeline.
        Maps guardrail results, model predictions, optimization choices, and agent output.
        """
        if not db_available():
            logger.warning("AuditService: DB unavailable, skipping write_pipeline_events for %s", case_id)
            return

        now = datetime.now(timezone.utc)
        context_snapshot = {
            "case_id": case_id,
            "payment_id": context.payment_id,
            "customer_id": context.customer_id,
            "amount": str(context.amount),
            "currency": context.currency,
            "method": context.method,
            "failure_code": context.failure_code,
            "attempt_number": context.attempt_number,
            "customer_success_rate": context.customer_success_rate,
        }

        candidates_snapshot = [
            {
                "action": c.action.value,
                "probability": round(float(c.probability), 4),
                "expected_gross_recovery": str(c.expected_gross_recovery),
                "expected_net_revenue": str(c.expected_net_revenue),
                "allowed": c.allowed,
                "rank": c.rank,
            }
            for c in proposal.optimization_result.candidates
        ]

        selected_cand = next(
            (c for c in proposal.optimization_result.candidates if c.action == proposal.recommended_action),
            None,
        )
        conf = getattr(selected_cand, "confidence", None)

        decision_snapshot = {
            "recommended_action": proposal.recommended_action.value,
            "expected_net_revenue": str(proposal.optimization_result.selected_expected_net_revenue),
            "requires_approval": proposal.requires_approval,
            "model_confidence": round(float(conf), 4) if conf is not None else None,
        }

        guardrail_snapshot = {
            "verdict": (
                proposal.guardrail_result.verdict.value
                if hasattr(proposal.guardrail_result.verdict, "value")
                else str(proposal.guardrail_result.verdict)
            ),
            "passed": proposal.guardrail_result.passed,
            "blocked_actions": [
                a.value if hasattr(a, "value") else str(a)
                for a in proposal.guardrail_result.blocked_actions
            ],
            "block_reasons": {
                (k.value if hasattr(k, "value") else str(k)): str(v)
                for k, v in getattr(proposal.guardrail_result, "block_reasons", {}).items()
            },
            "audit_events": proposal.guardrail_result.audit_events,
        }

        # 1. Context Loaded
        await self.repo.write(
            AuditEntry(
                case_id=case_id,
                event_type=AuditEventType.CONTEXT_LOADED,
                actor=actor,
                source=source,
                input_snapshot={"case_id": case_id, "payment_id": context.payment_id},
                output_snapshot=context_snapshot,
                timestamp=now,
            )
        )

        # 2. Predictions Generated
        await self.repo.write(
            AuditEntry(
                case_id=case_id,
                event_type=AuditEventType.PREDICTIONS_GENERATED,
                actor=actor,
                source=source,
                input_snapshot=context_snapshot,
                output_snapshot={"candidates": candidates_snapshot},
                model_name=proposal.model_name,
                model_version=proposal.model_version,
                policy_version=proposal.policy_version,
                timestamp=now,
            )
        )

        # 3. Optimization Completed
        await self.repo.write(
            AuditEntry(
                case_id=case_id,
                event_type=AuditEventType.OPTIMIZATION_COMPLETED,
                actor=actor,
                source=source,
                input_snapshot={"candidates_count": len(candidates_snapshot)},
                output_snapshot=decision_snapshot,
                decision=decision_snapshot,
                model_name=proposal.model_name,
                model_version=proposal.model_version,
                policy_version=proposal.policy_version,
                timestamp=now,
            )
        )

        # 4. Guardrail Events
        guardrail_event_type = (
            AuditEventType.GUARDRAIL_PASSED
            if proposal.guardrail_result.passed
            else AuditEventType.GUARDRAIL_BLOCKED
        )
        await self.repo.write(
            AuditEntry(
                case_id=case_id,
                event_type=guardrail_event_type,
                actor=actor,
                source=source,
                input_snapshot=decision_snapshot,
                output_snapshot=guardrail_snapshot,
                guardrail_result=guardrail_snapshot,
                policy_version=proposal.policy_version,
                timestamp=now,
            )
        )

        # 5. Approval Requested (if applicable)
        if proposal.requires_approval:
            await self.repo.write(
                AuditEntry(
                    case_id=case_id,
                    event_type=AuditEventType.APPROVAL_REQUESTED,
                    actor=actor,
                    source=source,
                    input_snapshot=decision_snapshot,
                    output_snapshot={
                        "reason": "High-value transaction or model confidence below threshold",
                        "requires_approval": True,
                    },
                    timestamp=now,
                )
            )

        # 6. Explanation Generated (Agent or Template fallback)
        is_agent = "Gemini" in (proposal.explanation or "") or len(proposal.explanation or "") > 200
        await self.repo.write(
            AuditEntry(
                case_id=case_id,
                event_type=AuditEventType.AGENT_EXPLANATION if is_agent else AuditEventType.AGENT_FALLBACK,
                actor=actor,
                source=source,
                input_snapshot={"action": proposal.recommended_action.value},
                output_snapshot={"explanation": proposal.explanation},
                timestamp=now,
            )
        )

    async def record_approval(
        self,
        case_id: str,
        approval_status: ApprovalStatus,
        actor: str = "merchant",
        source: PipelineSource = PipelineSource.DASHBOARD,
    ) -> None:
        """Record human approval or rejection."""
        if not db_available():
            return
        event_type = (
            AuditEventType.APPROVAL_GRANTED
            if approval_status == ApprovalStatus.APPROVED
            else AuditEventType.APPROVAL_REJECTED
        )
        await self.repo.write(
            AuditEntry(
                case_id=case_id,
                event_type=event_type,
                actor=actor,
                source=source,
                input_snapshot={"approval_status": approval_status.value},
                output_snapshot={"status": approval_status.value},
            )
        )

    async def record_execution(
        self,
        case_id: str,
        action: ActionType,
        success: bool,
        recovered_amount: Decimal,
        cost: Decimal,
        provider_reference: str | None = None,
        actor: str = "system",
        source: PipelineSource = PipelineSource.DASHBOARD,
    ) -> None:
        """Record action execution and verification outcomes."""
        if not db_available():
            return

        now = datetime.now(timezone.utc)
        # 1. Action requested / executing
        await self.repo.write(
            AuditEntry(
                case_id=case_id,
                event_type=AuditEventType.ACTION_REQUESTED,
                actor=actor,
                source=source,
                input_snapshot={"action": action.value},
                output_snapshot={"status": "executing"},
                timestamp=now,
            )
        )

        # 2. Action executed or failed
        await self.repo.write(
            AuditEntry(
                case_id=case_id,
                event_type=AuditEventType.ACTION_EXECUTED if success else AuditEventType.ACTION_FAILED,
                actor=actor,
                source=source,
                input_snapshot={"action": action.value},
                output_snapshot={
                    "success": success,
                    "provider_reference": provider_reference,
                    "cost": str(cost),
                },
                timestamp=now,
            )
        )

        # 3. Verification & Payment outcome
        if recovered_amount > 0:
            await self.repo.write(
                AuditEntry(
                    case_id=case_id,
                    event_type=AuditEventType.PAYMENT_RECOVERED,
                    actor=actor,
                    source=source,
                    input_snapshot={"action": action.value, "provider_reference": provider_reference},
                    output_snapshot={
                        "recovered_amount": str(recovered_amount),
                        "cost": str(cost),
                        "net_recovered": str(recovered_amount - cost),
                    },
                    timestamp=now,
                )
            )
        else:
            await self.repo.write(
                AuditEntry(
                    case_id=case_id,
                    event_type=AuditEventType.VERIFICATION_FAILED,
                    actor=actor,
                    source=source,
                    input_snapshot={"action": action.value},
                    output_snapshot={"recovered_amount": "0.00", "cost": str(cost)},
                    timestamp=now,
                )
            )

    async def record_case_stopped(
        self,
        case_id: str,
        actor: str = "merchant",
        source: PipelineSource = PipelineSource.DASHBOARD,
        reason: str = "Manual stop requested",
    ) -> None:
        """Record case manually stopped."""
        if not db_available():
            return
        await self.repo.write(
            AuditEntry(
                case_id=case_id,
                event_type=AuditEventType.CASE_STOPPED,
                actor=actor,
                source=source,
                input_snapshot={"reason": reason},
                output_snapshot={"status": "stopped"},
            )
        )
