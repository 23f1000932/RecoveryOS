"""
RecoveryOS — Deterministic Action Cost Model

All INR cost values for every recovery action originate here.

Architecture rule (§2): Financial numbers are deterministic.
Never let Gemini calculate or modify these values.

Cost model:
    Four components per action:
    1. intervention_cost — backend processing cost (fixed per action type)
    2. incentive_cost    — financial incentive given to customer (amount-dependent)
    3. contact_cost      — cost of contacting the customer (message, call)
    4. total_cost        — sum of all three

All values are in INR as Decimal for financial correctness.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from backend.domain.enums import ActionType

# ── Cost Constants (INR) ───────────────────────────────────────────────────────
# Change these values here only. Never hardcode elsewhere.

# Base intervention costs (backend processing)
_INTERVENTION_COST: dict[ActionType, Decimal] = {
    ActionType.RETRY_NOW:    Decimal("0"),
    ActionType.RETRY_LATER:  Decimal("0"),
    ActionType.REMINDER:     Decimal("5"),
    ActionType.INCENTIVE:    Decimal("5"),
    ActionType.ESCALATE:     Decimal("25"),
    ActionType.DO_NOTHING:   Decimal("0"),
}

# Contact costs (message / outreach cost per action)
_CONTACT_COST: dict[ActionType, Decimal] = {
    ActionType.RETRY_NOW:    Decimal("0"),
    ActionType.RETRY_LATER:  Decimal("0"),
    ActionType.REMINDER:     Decimal("5"),
    ActionType.INCENTIVE:    Decimal("5"),
    ActionType.ESCALATE:     Decimal("25"),
    ActionType.DO_NOTHING:   Decimal("0"),
}

# Incentive rate: fraction of payment amount offered as incentive
_INCENTIVE_RATE = Decimal("0.05")   # 5%


@dataclass(frozen=True)
class ActionCost:
    """
    Complete cost breakdown for a single action on a single case.

    All fields are Decimal (INR). Never float.
    """

    action: ActionType
    intervention_cost: Decimal
    incentive_cost: Decimal
    contact_cost: Decimal
    total_cost: Decimal


def calculate_action_cost(
    action: ActionType,
    payment_amount: Decimal,
    max_incentive_per_customer: Decimal,
) -> ActionCost:
    """
    Calculate the full cost of applying an action to a specific payment.

    Args:
        action:                   The action to cost.
        payment_amount:           The original failed payment amount (INR).
        max_incentive_per_customer: Policy cap on incentive per customer.

    Returns:
        ActionCost with all components and total.

    Rules:
        - incentive_cost is only non-zero for ActionType.INCENTIVE.
        - incentive is min(amount × 5%, max_incentive_per_customer).
        - All values rounded to 2 decimal places (ROUND_HALF_UP).
    """
    intervention = _INTERVENTION_COST.get(action, Decimal("0"))
    contact = _CONTACT_COST.get(action, Decimal("0"))

    # Incentive cost is only incurred for the incentive action
    if action == ActionType.INCENTIVE:
        raw_incentive = (payment_amount * _INCENTIVE_RATE).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        incentive = min(raw_incentive, max_incentive_per_customer)
    else:
        incentive = Decimal("0")

    total = (intervention + incentive + contact).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return ActionCost(
        action=action,
        intervention_cost=intervention,
        incentive_cost=incentive,
        contact_cost=contact,
        total_cost=total,
    )
