"""
RecoveryOS — Unit Tests: Optimizer (Expected Value)

7 test cases verifying financial correctness, ranking logic, and fallbacks.
"""

from __future__ import annotations

import pytest
from decimal import Decimal

from backend.domain.enums import ActionType
from backend.ml_models.protocol import ActionPrediction
from backend.optimizer.expected_value import rank_actions, CandidateEV, OptimizationResult


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_pred(
    action: ActionType,
    probability: float = 0.60,
    confidence: float = 0.70,
) -> ActionPrediction:
    return ActionPrediction(
        action=action,
        probability=probability,
        confidence=confidence,
        model_name="test_model",
        model_version="v0",
    )


def _all_preds(probability: float = 0.60) -> list[ActionPrediction]:
    return [_make_pred(a, probability=probability) for a in ActionType]


_AMOUNT = Decimal("5000")
_MAX_INCENTIVE = Decimal("100")
_POLICY_VERSION = "1.0"


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestOptimizer:

    def test_selects_highest_net_revenue_action(self):
        """
        With equal probabilities, incentive has the highest incentive cost so
        its ENR is lower. retry_now/retry_later (zero cost) should win for a
        high-probability customer.
        """
        preds = _all_preds(probability=0.80)
        result = rank_actions(preds, _AMOUNT, _MAX_INCENTIVE, _POLICY_VERSION)

        # retry_now and retry_later both have 0 cost, so gross == net
        # they should rank above incentive (which has cost ~250 → but capped at 100)
        assert result.selected_action in {
            ActionType.RETRY_NOW, ActionType.RETRY_LATER
        }, f"Expected retry action, got {result.selected_action}"

    def test_do_nothing_always_included_in_candidates(self):
        """do_nothing must always appear in the candidates list."""
        result = rank_actions(_all_preds(), _AMOUNT, _MAX_INCENTIVE, _POLICY_VERSION)
        actions = {c.action for c in result.candidates}
        assert ActionType.DO_NOTHING in actions

    def test_incentive_cost_deducted_from_enr(self):
        """The incentive action's ENR must be lower than its gross recovery."""
        result = rank_actions(_all_preds(), _AMOUNT, _MAX_INCENTIVE, _POLICY_VERSION)
        incentive_cand = next(c for c in result.candidates if c.action == ActionType.INCENTIVE)
        assert incentive_cand.expected_net_revenue < incentive_cand.expected_gross_recovery

    def test_all_blocked_falls_back_to_do_nothing(self):
        """When all actions are blocked, do_nothing must be selected."""
        blocked = {a: "test_block" for a in ActionType if a != ActionType.DO_NOTHING}
        result = rank_actions(_all_preds(), _AMOUNT, _MAX_INCENTIVE, _POLICY_VERSION,
                              blocked_actions=blocked)
        assert result.selected_action == ActionType.DO_NOTHING

    def test_candidate_ranking_is_deterministic(self):
        """Same inputs → same rank order every time."""
        preds = _all_preds(probability=0.75)
        r1 = rank_actions(preds, _AMOUNT, _MAX_INCENTIVE, _POLICY_VERSION)
        r2 = rank_actions(preds, _AMOUNT, _MAX_INCENTIVE, _POLICY_VERSION)
        assert [c.action for c in r1.candidates] == [c.action for c in r2.candidates]

    def test_expected_gross_uses_probability(self):
        """expected_gross_recovery must equal probability × amount."""
        prob = 0.75
        preds = [_make_pred(ActionType.RETRY_NOW, probability=prob)]
        result = rank_actions(preds, _AMOUNT, _MAX_INCENTIVE, _POLICY_VERSION)
        retry_cand = next(c for c in result.candidates if c.action == ActionType.RETRY_NOW)
        expected_gross = (Decimal(str(prob)) * _AMOUNT).quantize(Decimal("0.01"))
        assert retry_cand.expected_gross_recovery == expected_gross

    def test_financial_values_are_decimal_not_float(self):
        """All ENR values must be Decimal instances, never float."""
        result = rank_actions(_all_preds(), _AMOUNT, _MAX_INCENTIVE, _POLICY_VERSION)
        assert isinstance(result.selected_expected_net_revenue, Decimal)
        for c in result.candidates:
            assert isinstance(c.expected_net_revenue, Decimal)
            assert isinstance(c.expected_gross_recovery, Decimal)
