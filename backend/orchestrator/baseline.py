"""
RecoveryOS — Baseline Policy

Fixed deterministic comparator for A/B measurement.

Architecture spec (§11):
    "If payment failed:
        attempt immediate retry once
        if successful → recovered
        otherwise → stop"

    "The baseline must not use:
        - Gemini
        - ML optimization
        - dynamic incentives"

    "Its purpose is to provide a stable comparison."

The baseline always selects retry_now. It consults the latent potential
outcome (p_retry_now from the synthetic dataset) to determine success.
This is the same p_retry_now that RecoveryOS also has access to —
guaranteeing counterfactual validity (same potential outcome environment).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from backend.domain.enums import ActionType


@dataclass(frozen=True)
class BaselineResult:
    """
    Result of the baseline policy evaluation for a single case.

    action:           Always retry_now (the baseline never picks anything else).
    success:          True if the latent outcome says retry_now succeeds.
    recovered_amount: payment amount if success, else Decimal("0").
    cost:             Always Decimal("0") — baseline incurs no intervention cost.
    """

    action: ActionType
    success: bool
    recovered_amount: Decimal
    cost: Decimal


class BaselinePolicy:
    """
    Fixed naive retry policy used as the A/B baseline comparator.

    The baseline is intentionally simple:
        retry_now → if success: recovered; else: stopped.

    It does not use:
        - ML model predictions (uses latent p_retry_now directly)
        - Gemini
        - incentives
        - any optimizer

    Thread-safe: stateless, no mutable instance state.
    """

    def evaluate(
        self,
        payment_amount: Decimal,
        p_retry_now: float,
    ) -> BaselineResult:
        """
        Evaluate the baseline policy for a single case.

        Args:
            payment_amount: The failed payment amount (INR).
            p_retry_now:    The latent potential outcome for retry_now.
                            This is the pre-baked probability from the
                            synthetic dataset — deterministic given the seed.

        Returns:
            BaselineResult with always-retry_now action, success/fail,
            recovered amount, and zero cost.

        Note:
            The baseline does NOT sample a new random outcome.
            It uses p_retry_now as a deterministic threshold:
            success = (p_retry_now >= 0.5).

            This is the correct counterfactual approach — the same threshold
            is applied consistently, ensuring that baseline and AI are
            evaluated on the exact same potential outcome environment.
        """
        # Deterministic: success if latent probability exceeds 50% threshold.
        # We do NOT re-sample — that would break counterfactual validity.
        success = p_retry_now >= 0.5

        recovered = payment_amount if success else Decimal("0")

        return BaselineResult(
            action=ActionType.RETRY_NOW,
            success=success,
            recovered_amount=recovered,
            cost=Decimal("0"),
        )
