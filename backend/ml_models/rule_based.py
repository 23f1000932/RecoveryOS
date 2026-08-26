"""
RecoveryOS — Rule-Based Recovery Model

Deterministic rule-based model used as the Phase 3 development model.
Requires zero training. The entire pipeline can run and be tested with this.

Design (from architecture_v2.md §9):
    "Implement RuleBasedRecoveryModel first so the entire application
     can run without training infrastructure."

When XGBoostRecoveryModel is ready (Phase 4), it replaces this model
in RecoveryPipeline with zero code changes to the pipeline.

Model logic:
    base_signal  = customer_quality_signal + payment_context_signal
    p(action)    = clamp(base_signal × action_multiplier, 0.01, 0.95)

Confidence is a fixed conservative estimate of 0.70.
This is intentional and documented — the rule-based model is not
a calibrated probabilistic model.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.domain.enums import ActionType
from backend.ml_models.protocol import ActionPrediction

if TYPE_CHECKING:
    from backend.orchestrator.context import CaseContext

logger = logging.getLogger(__name__)

MODEL_NAME = "rule_based_recovery"
MODEL_VERSION = "v1"
FIXED_CONFIDENCE = 0.70  # conservative, documented

# ── Failure Code Recoverability ────────────────────────────────────────────────
# Higher = more likely to recover with any retry/reminder action.
_FAILURE_RECOVERABILITY: dict[str, float] = {
    "insufficient_funds":  0.70,   # timing issue — often recoverable
    "card_declined":       0.45,   # bank decision — harder
    "bank_error":          0.65,   # transient — usually resolves
    "network_timeout":     0.80,   # very transient — highly recoverable
    "do_not_honour":       0.25,   # strong bank block — hard
    "expired_card":        0.15,   # needs card update — unlikely
    "cvv_mismatch":        0.60,   # user error — fixable
    "unknown":             0.40,   # uncertain baseline
}

# ── Action Multipliers ─────────────────────────────────────────────────────────
# Applied to base_signal to derive per-action probability.
# Calibrated so AI (best action) outperforms baseline (retry_now).
_ACTION_MULTIPLIERS: dict[ActionType, float] = {
    ActionType.RETRY_NOW:    1.00,  # reference
    ActionType.RETRY_LATER:  1.15,  # timing premium
    ActionType.REMINDER:     0.80,  # weaker than retry
    ActionType.INCENTIVE:    1.25,  # financial motivation
    ActionType.ESCALATE:     0.55,  # human review — uncertain
    ActionType.DO_NOTHING:   0.12,  # no action — very low recovery
}


def _customer_quality(context: CaseContext) -> float:
    """
    Compute a 0–1 customer quality signal.

    High success rate and more transaction history → higher quality.
    Capped at 0.95 to avoid overconfidence.
    """
    rate = float(context.customer_success_rate)

    # Log-normalize transaction count: 1 tx → 0.5, 30 tx → ~0.72
    import math
    count_bonus = min(math.log1p(context.customer_transaction_count) / 10.0, 0.15)

    quality = min(rate * 0.85 + count_bonus, 0.95)
    return quality


def _payment_context_signal(context: CaseContext) -> float:
    """
    Compute a 0–1 payment context signal.

    Incorporates failure code recoverability and attempt penalty.
    """
    recoverability = _FAILURE_RECOVERABILITY.get(context.failure_code, 0.40)

    # Each extra attempt lowers the probability (customer less willing)
    attempt_penalty = max(0.0, 1.0 - (context.attempt_number - 1) * 0.15)

    return recoverability * attempt_penalty


def _base_signal(context: CaseContext) -> float:
    """
    Combine customer quality and payment context into a base signal.

    Weighted: 60% customer quality, 40% payment context.
    Range: (0, 1).
    """
    quality = _customer_quality(context)
    context_signal = _payment_context_signal(context)
    return quality * 0.60 + context_signal * 0.40


class RuleBasedRecoveryModel:
    """
    Deterministic rule-based recovery outcome model.

    Satisfies RecoveryOutcomeModel Protocol via duck typing.
    Zero training required. Used as Phase 3 dev model and Phase 8
    simulation fallback.

    Thread-safe: stateless, no mutable instance state.
    """

    def predict_action_outcomes(
        self,
        context: CaseContext,
        actions: list[ActionType],
    ) -> list[ActionPrediction]:
        """
        Predict success probability for each requested action.

        Returns one ActionPrediction per action, in input order.
        All probabilities are in (0.01, 0.95).
        """
        base = _base_signal(context)

        predictions: list[ActionPrediction] = []
        for action in actions:
            multiplier = _ACTION_MULTIPLIERS.get(action, 0.40)
            raw_p = base * multiplier
            probability = float(max(0.01, min(0.95, raw_p)))

            predictions.append(
                ActionPrediction(
                    action=action,
                    probability=probability,
                    confidence=FIXED_CONFIDENCE,
                    model_name=MODEL_NAME,
                    model_version=MODEL_VERSION,
                )
            )

        return predictions
