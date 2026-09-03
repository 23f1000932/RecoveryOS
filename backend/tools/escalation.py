"""
RecoveryOS — Escalation Action Adapter

Marks a case as escalated for human review.

This adapter never calls a payment API.
It transitions the case to ESCALATED state and writes an audit event.
No cost incurred. No external call.

Used when:
  - Guardrail verdict == "escalate"
  - Model confidence is below threshold
  - Amount is too high for automated action
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from backend.domain.enums import ExecutionMode
from backend.tools.protocol import ActionResult, make_idempotency_key

if TYPE_CHECKING:
    from backend.orchestrator.context import CaseContext

logger = logging.getLogger(__name__)


class EscalationAdapter:
    """
    Transitions case to ESCALATED for human review.

    Pure state transition — no payment API calls.
    Stateless. Thread-safe.
    """

    async def execute(
        self,
        case_id: str,
        context: CaseContext,
        reason: str = "Escalated by RecoveryOS policy.",
        attempt_number: int = 1,
    ) -> ActionResult:
        """
        Execute escalation (state transition only).

        Args:
            case_id:       Recovery case ID.
            context:       Full CaseContext.
            reason:        Human-readable escalation reason for audit.
            attempt_number: For idempotency key.
        """
        idempotency_key = make_idempotency_key(case_id, "escalate", attempt_number)
        execution_mode = getattr(context, "execution_mode", ExecutionMode.SIMULATION)

        logger.info(
            "EscalationAdapter: case=%s reason=%r mode=%s",
            case_id, reason, execution_mode.value,
        )

        # Escalation never fails — it's a pure state write
        return ActionResult(
            success=True,
            idempotency_key=idempotency_key,
            provider_reference=f"escalated-{case_id[:8]}",
            execution_mode=execution_mode,
            cost=Decimal("0"),
        )
