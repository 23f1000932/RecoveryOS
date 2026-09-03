"""
RecoveryOS — Stop Action Adapter

Stops recovery attempts for a case. Terminal action.

No payment API call. Transitions case to STOPPED.
Used when guardrail verdict == "stop" or merchant explicitly stops a case.
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


class StopAdapter:
    """
    Stops recovery — transitions case to STOPPED.

    Pure state transition — no payment API calls.
    Stateless. Thread-safe.
    """

    async def execute(
        self,
        case_id: str,
        context: CaseContext,
        reason: str = "Recovery stopped by policy.",
        attempt_number: int = 1,
    ) -> ActionResult:
        """
        Execute stop (state transition only).

        Args:
            case_id:        Recovery case ID.
            context:        Full CaseContext.
            reason:         Human-readable stop reason for audit.
            attempt_number: For idempotency key.
        """
        idempotency_key = make_idempotency_key(case_id, "do_nothing", attempt_number)
        execution_mode = getattr(context, "execution_mode", ExecutionMode.SIMULATION)

        logger.info(
            "StopAdapter: case=%s reason=%r mode=%s",
            case_id, reason, execution_mode.value,
        )

        return ActionResult(
            success=True,
            idempotency_key=idempotency_key,
            provider_reference=f"stopped-{case_id[:8]}",
            execution_mode=execution_mode,
            cost=Decimal("0"),
        )
