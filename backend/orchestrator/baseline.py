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
outcome (p_retry_now from the synthetic dataset) together with the case's
shared uniform draw to determine success. RecoveryOS is evaluated against
that same draw — guaranteeing counterfactual validity (one shared potential
outcome environment). See backend/domain/simulation.py.
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
        uniform_draw: float,
    ) -> BaselineResult:
        """
        Evaluate the baseline policy for a single case.

        Args:
            payment_amount: The failed payment amount (INR).
            p_retry_now:    The latent potential outcome for retry_now.
                            Pre-baked probability from the synthetic dataset.
            uniform_draw:   The case's shared uniform draw u ∈ [0, 1), from
                            backend.domain.simulation.derive_uniform_draw().
                            RecoveryOS is evaluated against this same u, so both
                            arms resolve in one shared world (§10.3).

        Returns:
            BaselineResult with always-retry_now action, success/fail,
            recovered amount, and zero cost.

        Note:
            The baseline does NOT draw its own random number. It receives the
            case's shared draw and compares it against p_retry_now:

                success = (u < p_retry_now)

            This is the common-random-numbers construction — see
            backend/domain/simulation.py for why a per-arm draw (different
            worlds) and a fixed 0.5 threshold (biased rates) are both wrong.
        """
        # Potential outcome Y(retry_now) under the case's shared draw.
        success = uniform_draw < p_retry_now

        recovered = payment_amount if success else Decimal("0")

        return BaselineResult(
            action=ActionType.RETRY_NOW,
            success=success,
            recovered_amount=recovered,
            cost=Decimal("0"),
        )
