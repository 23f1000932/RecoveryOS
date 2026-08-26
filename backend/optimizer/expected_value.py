"""
RecoveryOS — Expected Value Optimizer

The authoritative decision maker.

Architecture rules (§12):
    - Accept action predictions (probabilities only).
    - Calculate expected financial value for each action.
    - Rank actions.
    - Return a deterministic result.

    The optimizer:
    - MUST include do_nothing.
    - MUST rank only supplied actions.
    - MUST NEVER execute anything.
    - MUST NEVER call Gemini.
    - MUST NEVER bypass guardrails.

Financial formulas (§8):
    expected_gross_recovery(action) = probability × recoverable_amount
    expected_net_revenue(action)    = gross - intervention_cost
                                           - incentive_cost
                                           - contact_cost

All financial values are Decimal. Never float.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from backend.domain.enums import ActionType
from backend.ml_models.protocol import ActionPrediction
from backend.optimizer.cost_model import ActionCost, calculate_action_cost

logger = logging.getLogger(__name__)

_TWO_PLACES = Decimal("0.01")


@dataclass
class CandidateEV:
    """
    Expected value breakdown for a single action candidate.

    Fields:
        action                  — the action
        probability             — P(success) from ML model
        confidence              — model confidence
        expected_gross_recovery — probability × recoverable_amount
        intervention_cost       — fixed backend cost
        incentive_cost          — customer incentive (0 unless INCENTIVE action)
        contact_cost            — outreach cost
        expected_net_revenue    — gross - all costs
        allowed                 — True unless guardrails blocked it
        blocked_reason          — non-None if allowed=False
        rank                    — 1 = best (0 = unranked / blocked)
    """

    action: ActionType
    probability: float
    confidence: float
    expected_gross_recovery: Decimal
    intervention_cost: Decimal
    incentive_cost: Decimal
    contact_cost: Decimal
    expected_net_revenue: Decimal
    allowed: bool
    blocked_reason: str | None
    rank: int


@dataclass
class OptimizationResult:
    """
    Authoritative output of the optimizer.

    selected_action            — the action with highest ENR among allowed candidates
    selected_expected_net_revenue — its ENR value
    candidates                 — full ranked list (all actions, allowed + blocked)
    model_name / model_version — for audit trail
    policy_version             — for audit trail
    """

    selected_action: ActionType
    selected_expected_net_revenue: Decimal
    candidates: list[CandidateEV]
    model_name: str
    model_version: str
    policy_version: str


def rank_actions(
    predictions: list[ActionPrediction],
    recoverable_amount: Decimal,
    max_incentive_per_customer: Decimal,
    policy_version: str,
    blocked_actions: dict[ActionType, str] | None = None,
) -> OptimizationResult:
    """
    Rank all candidate actions by expected net revenue.

    This is the authoritative financial decision. It does not:
    - consult Gemini;
    - write to the database;
    - mutate guardrail state;
    - skip do_nothing.

    Args:
        predictions:                 ActionPrediction list from any model.
        recoverable_amount:          The payment amount (what we can recover).
        max_incentive_per_customer:  Policy cap on incentive value.
        policy_version:              For audit trail.
        blocked_actions:             Dict of {action: reason} blocked by guardrails.
                                     Pass None or {} to rank all actions.

    Returns:
        OptimizationResult with the best allowed action selected.
        If all actions are blocked, do_nothing is always selected.
    """
    blocked = blocked_actions or {}

    # Build a fast lookup: action → prediction
    pred_map: dict[ActionType, ActionPrediction] = {p.action: p for p in predictions}

    candidates: list[CandidateEV] = []

    for action in ActionType:
        pred = pred_map.get(action)
        if pred is None:
            logger.debug("No prediction for action %s — skipping.", action)
            continue

        cost: ActionCost = calculate_action_cost(
            action=action,
            payment_amount=recoverable_amount,
            max_incentive_per_customer=max_incentive_per_customer,
        )

        gross = (Decimal(str(pred.probability)) * recoverable_amount).quantize(
            _TWO_PLACES, rounding=ROUND_HALF_UP
        )
        net = (gross - cost.total_cost).quantize(
            _TWO_PLACES, rounding=ROUND_HALF_UP
        )

        is_blocked = action in blocked
        candidates.append(
            CandidateEV(
                action=action,
                probability=pred.probability,
                confidence=pred.confidence,
                expected_gross_recovery=gross,
                intervention_cost=cost.intervention_cost,
                incentive_cost=cost.incentive_cost,
                contact_cost=cost.contact_cost,
                expected_net_revenue=net,
                allowed=not is_blocked,
                blocked_reason=blocked.get(action),
                rank=0,  # assigned below
            )
        )

    # Rank allowed candidates by ENR (descending)
    allowed_candidates = [c for c in candidates if c.allowed]
    blocked_candidates = [c for c in candidates if not c.allowed]

    # Always fall back to do_nothing if all are blocked
    if not allowed_candidates:
        logger.warning(
            "All actions blocked — forcing do_nothing. Blocked: %s",
            list(blocked.keys()),
        )
        # do_nothing must always be present; add it if somehow missing
        dn_pred = pred_map.get(ActionType.DO_NOTHING)
        if dn_pred:
            dn_cost = calculate_action_cost(
                action=ActionType.DO_NOTHING,
                payment_amount=recoverable_amount,
                max_incentive_per_customer=max_incentive_per_customer,
            )
            gross = (Decimal(str(dn_pred.probability)) * recoverable_amount).quantize(
                _TWO_PLACES, rounding=ROUND_HALF_UP
            )
            net = (gross - dn_cost.total_cost).quantize(
                _TWO_PLACES, rounding=ROUND_HALF_UP
            )
            fallback = CandidateEV(
                action=ActionType.DO_NOTHING,
                probability=dn_pred.probability,
                confidence=dn_pred.confidence,
                expected_gross_recovery=gross,
                intervention_cost=Decimal("0"),
                incentive_cost=Decimal("0"),
                contact_cost=Decimal("0"),
                expected_net_revenue=net,
                allowed=True,
                blocked_reason=None,
                rank=1,
            )
            all_candidates = [fallback] + blocked_candidates
            return OptimizationResult(
                selected_action=ActionType.DO_NOTHING,
                selected_expected_net_revenue=net,
                candidates=all_candidates,
                model_name=predictions[0].model_name if predictions else "unknown",
                model_version=predictions[0].model_version if predictions else "unknown",
                policy_version=policy_version,
            )

    # Sort allowed by ENR descending, then by action name for stability
    allowed_candidates.sort(
        key=lambda c: (c.expected_net_revenue, c.action.value),
        reverse=True,
    )

    # Assign ranks to allowed candidates
    for i, candidate in enumerate(allowed_candidates):
        candidate.rank = i + 1

    best = allowed_candidates[0]
    all_candidates = allowed_candidates + blocked_candidates

    return OptimizationResult(
        selected_action=best.action,
        selected_expected_net_revenue=best.expected_net_revenue,
        candidates=all_candidates,
        model_name=predictions[0].model_name if predictions else "unknown",
        model_version=predictions[0].model_version if predictions else "unknown",
        policy_version=policy_version,
    )
