"""
RecoveryOS — Incentive Action Adapter

Creates a discounted payment link (incentive) to encourage recovery.

In SIMULATION mode:
  - Returns synthetic success. Incentive cost charged from budget.

In TEST_MODE:
  - Creates a Razorpay Payment Link with a reduced amount (discount applied).
  - The discount amount is deducted from the daily incentive pool (policy-enforced upstream).

Cost model (from optimizer):
  incentive_cost = min(discount_amount, max_incentive_per_customer)
  contact_cost   = 5.00 INR (same as reminder)

Rule 2: Incentive amount is calculated by optimizer — never by this adapter.
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

INCENTIVE_CONTACT_COST = Decimal("5.00")
DEFAULT_INCENTIVE_DISCOUNT_RATE = Decimal("0.05")   # 5% discount default


class IncentiveAdapter:
    """
    Sends a payment link with an incentive discount.

    The discount amount is passed in, not chosen by this adapter.
    Stateless. Thread-safe.
    """

    async def execute(
        self,
        case_id: str,
        context: CaseContext,
        incentive_amount: Decimal | None = None,
        attempt_number: int = 1,
    ) -> ActionResult:
        """
        Execute the incentive action.

        Args:
            case_id:          Recovery case ID.
            context:          Full CaseContext.
            incentive_amount: Discount in INR (computed by optimizer). If None, uses 5%.
            attempt_number:   For idempotency key.
        """
        idempotency_key = make_idempotency_key(case_id, "incentive", attempt_number)
        execution_mode = getattr(context, "execution_mode", ExecutionMode.SIMULATION)

        if incentive_amount is None:
            incentive_amount = (context.amount * DEFAULT_INCENTIVE_DISCOUNT_RATE).quantize(
                Decimal("0.01")
            )

        discounted_amount = max(context.amount - incentive_amount, Decimal("1"))
        total_cost = INCENTIVE_CONTACT_COST + incentive_amount

        try:
            if execution_mode == ExecutionMode.TEST_MODE:
                return await self._execute_razorpay(
                    case_id, context, discounted_amount, total_cost, idempotency_key
                )
            else:
                return self._execute_simulation(case_id, total_cost, idempotency_key)
        except Exception as exc:
            logger.error("IncentiveAdapter: error case=%s: %s", case_id, exc)
            return ActionResult(
                success=False,
                idempotency_key=idempotency_key,
                execution_mode=execution_mode,
                error_code="INCENTIVE_ADAPTER_ERROR",
                error_message=str(exc),
            )

    def _execute_simulation(
        self,
        case_id: str,
        total_cost: Decimal,
        idempotency_key: str,
    ) -> ActionResult:
        logger.info("IncentiveAdapter [SIM]: case=%s cost=%.2f", case_id, total_cost)
        return ActionResult(
            success=True,
            idempotency_key=idempotency_key,
            provider_reference=f"sim-incentive-{case_id[:8]}",
            execution_mode=ExecutionMode.SIMULATION,
            cost=total_cost,
        )

    async def _execute_razorpay(
        self,
        case_id: str,
        context: CaseContext,
        discounted_amount: Decimal,
        total_cost: Decimal,
        idempotency_key: str,
    ) -> ActionResult:
        """Create a Razorpay Payment Link at discounted amount."""
        try:
            import razorpay
            from backend.config import get_settings
            settings = get_settings()

            if not settings.razorpay_available:
                logger.warning("IncentiveAdapter: Razorpay not configured — using simulation.")
                return self._execute_simulation(case_id, total_cost, idempotency_key)

            client = razorpay.Client(
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
            )
            amount_paise = int(discounted_amount * 100)

            link = client.payment_link.create({
                "amount": amount_paise,
                "currency": context.currency,
                "description": (
                    f"Special recovery offer — pay now and save! "
                    f"(Case: {case_id[:8]})"
                ),
                "reference_id": idempotency_key[:40],
                "reminder_enable": True,
                "notes": {
                    "case_id": case_id,
                    "action": "incentive",
                    "original_amount": str(context.amount),
                    "discounted_amount": str(discounted_amount),
                },
            })

            logger.info(
                "IncentiveAdapter [TEST]: case=%s link_id=%s amount=%d paise",
                case_id, link["id"], amount_paise,
            )
            return ActionResult(
                success=True,
                idempotency_key=idempotency_key,
                provider_reference=link["id"],
                execution_mode=ExecutionMode.TEST_MODE,
                cost=total_cost,
            )

        except Exception as exc:
            logger.error("IncentiveAdapter [TEST]: Razorpay error case=%s: %s", case_id, exc)
            return ActionResult(
                success=False,
                idempotency_key=idempotency_key,
                execution_mode=ExecutionMode.TEST_MODE,
                error_code="RAZORPAY_INCENTIVE_LINK_FAILED",
                error_message=str(exc),
            )
