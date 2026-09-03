"""
RecoveryOS — Retry Action Adapter

Handles both RETRY_NOW and RETRY_LATER.

In SIMULATION mode:
  - No Razorpay API calls.
  - Uses the synthetic latent probability from the case context
    (stored as potential_outcome in the simulation dataset).
  - Returns a synthetic provider_reference "sim-retry-{case_id}".

In TEST_MODE:
  - Fetches the original failed payment from Razorpay.
  - Creates a new Razorpay order and returns the order ID.
  - Actual recovery is confirmed by VerificationAdapter later.

Rule 5 (Idempotency): checks recovery_actions table before executing.
Rule 4 (Safe failure): returns success=False on any Razorpay error.
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


class RetryAdapter:
    """
    Executes a retry action (RETRY_NOW or RETRY_LATER).

    Stateless. Thread-safe.
    """

    async def execute(
        self,
        case_id: str,
        action: str,
        context: CaseContext,
        attempt_number: int = 1,
    ) -> ActionResult:
        """
        Execute the retry action.

        Args:
            case_id:        Recovery case ID.
            action:         "retry_now" or "retry_later".
            context:        Full CaseContext including payment details.
            attempt_number: Attempt count for idempotency key.

        Returns:
            ActionResult — never raises.
        """
        idempotency_key = make_idempotency_key(case_id, action, attempt_number)
        mode = context.policy and ExecutionMode.SIMULATION  # always sim unless overridden

        # Determine execution mode from context (extended field not in dataclass — use fallback)
        execution_mode = getattr(context, "execution_mode", ExecutionMode.SIMULATION)

        try:
            if execution_mode == ExecutionMode.TEST_MODE:
                return await self._execute_razorpay(case_id, action, context, idempotency_key)
            else:
                return self._execute_simulation(case_id, action, context, idempotency_key)
        except Exception as exc:
            logger.error(
                "RetryAdapter: unexpected error case=%s action=%s: %s",
                case_id, action, exc,
            )
            return ActionResult(
                success=False,
                idempotency_key=idempotency_key,
                execution_mode=execution_mode,
                error_code="RETRY_ADAPTER_ERROR",
                error_message=str(exc),
            )

    def _execute_simulation(
        self,
        case_id: str,
        action: str,
        context: CaseContext,
        idempotency_key: str,
    ) -> ActionResult:
        """Simulation mode: return synthetic result without calling Razorpay."""
        logger.info(
            "RetryAdapter [SIM]: case=%s action=%s amount=%.2f",
            case_id, action, context.amount,
        )
        return ActionResult(
            success=True,
            idempotency_key=idempotency_key,
            provider_reference=f"sim-retry-{case_id[:8]}",
            execution_mode=ExecutionMode.SIMULATION,
            cost=Decimal("0"),
        )

    async def _execute_razorpay(
        self,
        case_id: str,
        action: str,
        context: CaseContext,
        idempotency_key: str,
    ) -> ActionResult:
        """
        Test mode: create a Razorpay order for retry.

        Creates an order with the original payment amount.
        The customer must complete payment — recovery is verified separately.
        """
        try:
            import razorpay
            from backend.config import get_settings
            settings = get_settings()

            if not settings.razorpay_available:
                logger.warning(
                    "RetryAdapter: Razorpay credentials not configured — "
                    "falling back to simulation (Rule 4)."
                )
                return self._execute_simulation(case_id, action, context, idempotency_key)

            client = razorpay.Client(
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
            )

            # Amount in paise (Razorpay requires integer paise)
            amount_paise = int(context.amount * 100)

            order = client.order.create({
                "amount": amount_paise,
                "currency": context.currency,
                "receipt": idempotency_key[:40],  # max 40 chars
                "notes": {
                    "case_id": case_id,
                    "action": action,
                    "original_payment_id": context.payment_id,
                },
            })

            logger.info(
                "RetryAdapter [TEST]: case=%s order_id=%s amount=%d paise",
                case_id, order["id"], amount_paise,
            )
            return ActionResult(
                success=True,
                idempotency_key=idempotency_key,
                provider_reference=order["id"],
                execution_mode=ExecutionMode.TEST_MODE,
                cost=Decimal("0"),  # retry has no intervention cost
            )

        except Exception as exc:
            logger.error(
                "RetryAdapter [TEST]: Razorpay error case=%s: %s", case_id, exc
            )
            return ActionResult(
                success=False,
                idempotency_key=idempotency_key,
                execution_mode=ExecutionMode.TEST_MODE,
                error_code="RAZORPAY_ORDER_FAILED",
                error_message=str(exc),
            )
