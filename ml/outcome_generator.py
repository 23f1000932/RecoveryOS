"""
RecoveryOS — Latent Potential Outcome Generator

This is the core of counterfactual validity.

Architecture principle (architecture_v2.md §10):
    "Do not independently sample a fresh random outcome every time
     baseline and AI are evaluated."

Solution:
    For each case, generate one latent probability per action,
    deterministically from (global_seed + row_index).
    Both Baseline and RecoveryOS read these pre-baked probabilities.
    Same seed → identical outcomes → fair A/B comparison.

Model design (logit-space additive):
    base_logit = customer_quality_signal + payment_context_signal + noise
    p(action)  = sigmoid(base_logit + action_lift[action])

This module is pure computation — no I/O, no DB, no state.
"""

from __future__ import annotations

import numpy as np

# ── Action Lift Table ─────────────────────────────────────────────────────────
# Additive lifts in logit space for each action.
# Calibrated so AI (best action) outperforms naive retry by ~8–15% recovery rate.
# Do NOT change these without updating the phase 4 training curriculum.
ACTION_LIFTS: dict[str, float] = {
    "retry_now": 0.3,      # modest — immediate retry, some improvement
    "retry_later": 0.8,    # best timing — customer has cooled down
    "reminder": 0.4,       # moderate — customer reminded of obligation
    "incentive": 1.2,      # strongest — financial motivation
    "escalate": -0.1,      # marginal — human review, mixed results
    "do_nothing": -2.5,    # very low — no intervention
}


def _sigmoid(x: float) -> float:
    """Standard sigmoid: maps real → (0, 1)."""
    return 1.0 / (1.0 + np.exp(-float(x)))


def _customer_quality_signal(
    success_rate: float,
    transaction_count: int,
    avg_amount: float,
) -> float:
    """
    Compute a customer quality score in logit space.

    Higher success_rate and more transactions → higher base recovery probability.
    Large avg_amount adds a small positive signal (high-value customers pay).

    Returns a value roughly in [-1.5, +1.5].
    """
    # Success rate: maps [0,1] → [-1.5, +1.5] centered at 0.75
    rate_signal = (success_rate - 0.75) * 4.0

    # Transaction count: diminishing returns via log1p
    # 10 tx → 0, 30 tx → +0.35, 100 tx → +0.69
    count_signal = np.log1p(max(0, transaction_count - 10)) * 0.15

    # Amount: large amounts slightly increase recovery motivation
    # ₹5000 → 0.0, ₹20000 → +0.28
    amount_signal = np.log1p(max(0, avg_amount - 5000)) * 0.05

    return float(np.clip(rate_signal + count_signal + amount_signal, -2.0, 2.0))


def _payment_context_signal(
    failure_code_encoded: int,
    attempt_number: int,
    amount: float,
) -> float:
    """
    Compute a payment context adjustment in logit space.

    Some failure codes are more recoverable than others.
    More attempts → lower chance of success (customer is less willing).
    Higher amount → moderate positive signal (customer motivation to resolve).

    Returns a value roughly in [-1.0, +0.5].
    """
    # Failure code recoverability
    # insufficient_funds(0)=easy, card_declined(1)=medium, bank_error(2)=medium,
    # network_timeout(3)=easy, do_not_honour(4)=hard, expired_card(5)=hard,
    # cvv_mismatch(6)=easy, unknown(7)=medium
    failure_recoverability: dict[int, float] = {
        0: +0.5,   # insufficient_funds — often just timing
        1: -0.1,   # card_declined — bank decision, harder
        2: +0.3,   # bank_error — transient, recoverable
        3: +0.6,   # network_timeout — very recoverable
        4: -0.5,   # do_not_honour — strong bank block
        5: -0.8,   # expired_card — needs card update, unlikely
        6: +0.2,   # cvv_mismatch — user error, fixable
        7: -0.1,   # unknown — uncertain
    }
    code_signal = failure_recoverability.get(failure_code_encoded, -0.1)

    # Attempt number penalty: each extra attempt reduces success chance
    # attempt 1 → 0.0, attempt 2 → -0.3, attempt 3 → -0.6, attempt 4 → -0.9
    attempt_penalty = (attempt_number - 1) * -0.3

    # Amount signal: larger amounts give slight motivation boost
    # ₹500 → -0.1, ₹3000 → 0, ₹10000 → +0.12, ₹50000 → +0.24
    amount_signal = np.log1p(max(0, amount - 3000)) * 0.04

    return float(np.clip(code_signal + attempt_penalty + amount_signal, -2.0, 1.0))


def generate_case_outcomes(
    row_index: int,
    global_seed: int,
    success_rate: float,
    transaction_count: int,
    avg_amount: float,
    failure_code_encoded: int,
    attempt_number: int,
    amount: float,
) -> dict[str, float]:
    """
    Generate latent outcome probabilities for all 6 actions for a single case.

    This is deterministic given (row_index, global_seed) — calling this function
    twice with the same arguments produces the same result.

    Args:
        row_index:             Position of this case in the dataset (0-based).
        global_seed:           The global random seed for the experiment.
        success_rate:          Customer historical success rate [0, 1].
        transaction_count:     Customer lifetime transaction count.
        avg_amount:            Customer average transaction amount (INR).
        failure_code_encoded:  Integer-encoded failure reason.
        attempt_number:        Retry attempt number (1–4).
        amount:                This payment's amount (INR).

    Returns:
        Dict mapping action name → probability ∈ (0, 1).
    """
    # Per-row RNG — deterministic, independent per case
    rng = np.random.default_rng(seed=global_seed + row_index * 31337)

    # Base logit from customer quality + payment context
    quality = _customer_quality_signal(success_rate, transaction_count, avg_amount)
    context = _payment_context_signal(failure_code_encoded, attempt_number, amount)

    # Small per-case noise — clamped so it cannot dominate the signal
    noise = float(rng.normal(loc=0.0, scale=0.4))
    noise = float(np.clip(noise, -0.5, 0.5))

    base_logit = quality + context + noise

    # Compute probability for each action
    outcomes: dict[str, float] = {}
    for action, lift in ACTION_LIFTS.items():
        raw_p = _sigmoid(base_logit + lift)
        # Clamp to (0.01, 0.99) so we never produce exact 0 or 1
        outcomes[action] = float(np.clip(raw_p, 0.01, 0.99))

    return outcomes
