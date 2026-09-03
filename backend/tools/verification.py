"""
RecoveryOS — Verification Adapter

Mandatory post-execution step. Checks actual payment status.

Architecture rule (§24):
  "Never infer recovery solely from an action API response."

In SIMULATION mode:
  - Uses a synthetic Bernoulli draw based on the case's latent probability.
  - For pipelines that don't store latent probs: assumes success=True for
    actions that reported success (conservative simulator behaviour).

In TEST_MODE:
  - Calls razorpay.payments.fetch(payment_id) and checks status == "captured".
  - actual_recovered is set only if payment status is "captured".

Rule 4 (Safe failure):
  - If Razorpay fetch fails → VerificationResult(payment_recovered=False).
  - Case transitions to FAILED (never RECOVERED without verified payment).
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from backend.domain.enums import ExecutionMode
from backend.tools.protocol import VerificationResult

if TYPE_CHECKING:
    from backend.orchestrator.context import CaseContext

logger = logging.getLogger(__name__)


class VerificationAdapter:
    """
    Verifies actual payment recovery after action execution.

    Stateless. Thread-safe.
    """

    async def verify(
        self,
        case_id: str,
        context: CaseContext,
        action_result_reference: str,
        latent_probability: float | None = None,
    ) -> VerificationResult:
        """
        Verify actual payment status after action execution.

        Args:
            case_id:                   Recovery case ID (for logging).
            context:                   Full CaseContext (has payment_id, amount).
            action_result_reference:   Provider reference from ActionResult
                                       (Razorpay order/link ID or "sim-...").
            latent_probability:        From synthetic data — used in simulation
                                       to decide if payment was recovered.
                                       If None, uses customer_success_rate.

        Returns:
            VerificationResult — never raises.
        """
        execution_mode = getattr(context, "execution_mode", ExecutionMode.SIMULATION)
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            if execution_mode == ExecutionMode.TEST_MODE:
                return await self._verify_razorpay(case_id, context, action_result_reference, now_iso)
            else:
                return self._verify_simulation(case_id, context, latent_probability, now_iso)
        except Exception as exc:
            logger.error("VerificationAdapter: unexpected error case=%s: %s", case_id, exc)
            return VerificationResult(
                payment_recovered=False,
                actual_recovered=Decimal("0"),
                payment_status="verification_error",
                provider_reference=action_result_reference,
                verified_at=now_iso,
            )

    def _verify_simulation(
        self,
        case_id: str,
        context: CaseContext,
        latent_probability: float | None,
        now_iso: str,
    ) -> VerificationResult:
        """
        Simulation: Bernoulli draw on the latent probability.

        Uses latent_probability if provided (from synthetic dataset),
        otherwise falls back to customer_success_rate.
        """
        prob = latent_probability if latent_probability is not None else context.customer_success_rate
        recovered = random.random() < prob
        actual = context.amount if recovered else Decimal("0")

        logger.debug(
            "VerificationAdapter [SIM]: case=%s prob=%.2f recovered=%s",
            case_id, prob, recovered,
        )
        return VerificationResult(
            payment_recovered=recovered,
            actual_recovered=actual,
            payment_status="captured" if recovered else "failed",
            provider_reference=f"sim-verify-{case_id[:8]}",
            verified_at=now_iso,
        )

    async def _verify_razorpay(
        self,
        case_id: str,
        context: CaseContext,
        provider_reference: str,
        now_iso: str,
    ) -> VerificationResult:
        """
        Test mode: fetch payment status from Razorpay.

        Checks status == "captured" as the only definition of recovery.
        """
        try:
            import razorpay
            from backend.config import get_settings
            settings = get_settings()

            if not settings.razorpay_available:
                logger.warning(
                    "VerificationAdapter: Razorpay not configured — marking not recovered."
                )
                return VerificationResult(
                    payment_recovered=False,
                    actual_recovered=Decimal("0"),
                    payment_status="razorpay_unavailable",
                    provider_reference=provider_reference,
                    verified_at=now_iso,
                )

            client = razorpay.Client(
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
            )

            # Use original payment_id to verify
            payment_id = context.payment_id
            if payment_id.startswith("pay_"):
                payment = client.payment.fetch(payment_id)
            else:
                # provider_reference may be an order_id — fetch order payments
                payment = {"status": "unknown", "amount": 0}

            status = payment.get("status", "unknown")
            recovered = status == "captured"
            actual = (
                Decimal(str(payment.get("amount", 0))) / 100  # paise → INR
                if recovered
                else Decimal("0")
            )

            logger.info(
                "VerificationAdapter [TEST]: case=%s payment_id=%s status=%s recovered=%s",
                case_id, payment_id, status, recovered,
            )
            return VerificationResult(
                payment_recovered=recovered,
                actual_recovered=actual,
                payment_status=status,
                provider_reference=payment_id,
                verified_at=now_iso,
            )

        except Exception as exc:
            logger.error(
                "VerificationAdapter [TEST]: Razorpay fetch error case=%s: %s", case_id, exc
            )
            return VerificationResult(
                payment_recovered=False,
                actual_recovered=Decimal("0"),
                payment_status="verification_failed",
                provider_reference=provider_reference,
                verified_at=now_iso,
            )
