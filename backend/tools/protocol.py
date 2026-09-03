"""
RecoveryOS — Action Adapter Protocol and Result Types

All action adapters return ActionResult.
VerificationAdapter returns VerificationResult.

Architecture rules:
  - Adapters never choose policy — they only execute a pre-validated action.
  - Adapters are idempotency-safe via idempotency_key.
  - Adapters return structured results; the pipeline decides next state.
  - In SIMULATION mode: no external API calls; synthetic outcome is used.
  - In TEST_MODE: real Razorpay test-mode API calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from backend.domain.enums import ExecutionMode


@dataclass
class ActionResult:
    """
    Structured result returned by every action adapter.

    Fields:
        success:            Whether the action was dispatched successfully.
                            Does NOT mean the payment was recovered.
        idempotency_key:    The key used to prevent duplicate execution.
        provider_reference: Razorpay payment/order/link ID, or "sim-..." in simulation.
        execution_mode:     Which mode was used for audit.
        cost:               Actual cost incurred (INR). 0 for simulation.
        error_code:         Short machine-readable error code on failure.
        error_message:      Human-readable error detail on failure.
    """

    success: bool
    idempotency_key: str
    provider_reference: str = ""
    execution_mode: ExecutionMode = ExecutionMode.SIMULATION
    cost: Decimal = Decimal("0")
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class VerificationResult:
    """
    Result of VerificationAdapter.verify().

    The pipeline sets actual_recovered based on payment_recovered.
    Never trust action result alone — always verify payment status.

    Fields:
        payment_recovered:  True if Razorpay confirms payment captured.
        actual_recovered:   Payment amount if recovered; 0 otherwise.
        payment_status:     Raw payment status string from Razorpay or "simulated".
        provider_reference: Razorpay payment ID that was verified.
        verified_at:        ISO timestamp of verification.
    """

    payment_recovered: bool
    actual_recovered: Decimal
    payment_status: str
    provider_reference: str = ""
    verified_at: str = ""


def make_idempotency_key(case_id: str, action: str, attempt_number: int) -> str:
    """
    Canonical idempotency key format: {case_id}:{action}:{attempt_number}

    Must match the UNIQUE constraint on recovery_actions.idempotency_key.
    """
    return f"{case_id}:{action}:{attempt_number}"
