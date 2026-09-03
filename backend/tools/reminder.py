"""
RecoveryOS — Reminder Action Adapter

Sends a payment reminder to the customer.

In SIMULATION mode:
  - No external API call.
  - Returns synthetic success.

In TEST_MODE:
  - Creates a Razorpay Payment Link and returns the link ID.
  - The link is sent to the customer out-of-band (SMS/email configured in Razorpay dashboard).

Rule 4 (Safe failure): falls back to simulation if Razorpay unavailable.
Rule 5 (Idempotency): idempotency_key prevents duplicate reminders.
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

# Cost of sending a reminder (contact cost, in INR)
REMINDER_CONTACT_COST = Decimal("5.00")


class ReminderAdapter:
    """
    Sends a payment reminder via Razorpay Payment Link.

    Stateless. Thread-safe.
    """

    async def execute(
        self,
        case_id: str,
        context: CaseContext,
        attempt_number: int = 1,
    ) -> ActionResult:
        """Execute the reminder action."""
        idempotency_key = make_idempotency_key(case_id, "reminder", attempt_number)
        execution_mode = getattr(context, "execution_mode", ExecutionMode.SIMULATION)

        try:
            if execution_mode == ExecutionMode.TEST_MODE:
                return await self._execute_razorpay(case_id, context, idempotency_key)
            else:
                return self._execute_simulation(case_id, context, idempotency_key)
        except Exception as exc:
            logger.error("ReminderAdapter: error case=%s: %s", case_id, exc)
            return ActionResult(
                success=False,
                idempotency_key=idempotency_key,
                execution_mode=execution_mode,
                error_code="REMINDER_ADAPTER_ERROR",
                error_message=str(exc),
            )

    def _execute_simulation(
        self,
        case_id: str,
        context: CaseContext,
        idempotency_key: str,
    ) -> ActionResult:
        logger.info("ReminderAdapter [SIM]: case=%s amount=%.2f", case_id, context.amount)
        return ActionResult(
            success=True,
            idempotency_key=idempotency_key,
            provider_reference=f"sim-reminder-{case_id[:8]}",
            execution_mode=ExecutionMode.SIMULATION,
            cost=REMINDER_CONTACT_COST,
        )

    async def _execute_razorpay(
        self,
        case_id: str,
        context: CaseContext,
        idempotency_key: str,
    ) -> ActionResult:
        """Create a Razorpay Payment Link for the customer."""
        try:
            import razorpay
            from backend.config import get_settings
            settings = get_settings()

            if not settings.razorpay_available:
                logger.warning("ReminderAdapter: Razorpay not configured — using simulation.")
                return self._execute_simulation(case_id, context, idempotency_key)

            client = razorpay.Client(
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
            )
            amount_paise = int(context.amount * 100)

            link = client.payment_link.create({
                "amount": amount_paise,
                "currency": context.currency,
                "description": f"Complete your payment (Recovery case: {case_id[:8]})",
                "reference_id": idempotency_key[:40],
                "reminder_enable": True,
                "notes": {
                    "case_id": case_id,
                    "action": "reminder",
                },
            })

            logger.info(
                "ReminderAdapter [TEST]: case=%s link_id=%s", case_id, link["id"]
            )
            return ActionResult(
                success=True,
                idempotency_key=idempotency_key,
                provider_reference=link["id"],
                execution_mode=ExecutionMode.TEST_MODE,
                cost=REMINDER_CONTACT_COST,
            )

        except Exception as exc:
            logger.error("ReminderAdapter [TEST]: Razorpay error case=%s: %s", case_id, exc)
            return ActionResult(
                success=False,
                idempotency_key=idempotency_key,
                execution_mode=ExecutionMode.TEST_MODE,
                error_code="RAZORPAY_LINK_FAILED",
                error_message=str(exc),
            )
