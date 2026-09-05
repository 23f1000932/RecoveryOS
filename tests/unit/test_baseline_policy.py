"""
RecoveryOS — Unit Tests: Baseline Policy

Tests for the fixed retry_now comparator.

The baseline resolves the potential outcome Y(retry_now) = 1[u < p_retry_now]
using the case's shared uniform draw, so that RecoveryOS can be scored against
the same u (architecture §10.3). See backend/domain/simulation.py.
"""

from __future__ import annotations

import pytest
from decimal import Decimal

from backend.domain.enums import ActionType
from backend.orchestrator.baseline import BaselinePolicy, BaselineResult


@pytest.fixture
def policy() -> BaselinePolicy:
    return BaselinePolicy()


class TestBaselinePolicy:

    def test_always_selects_retry_now(self, policy):
        """Baseline always picks retry_now — no exceptions."""
        for p in [0.01, 0.49, 0.50, 0.90, 0.99]:
            result = policy.evaluate(
                payment_amount=Decimal("3000"),
                p_retry_now=p,
                uniform_draw=0.5,
            )
            assert result.action == ActionType.RETRY_NOW, (
                f"Expected retry_now for p={p}, got {result.action}"
            )

    def test_success_when_draw_below_probability(self, policy):
        """u < p_retry_now → recovered."""
        for p in [0.30, 0.50, 0.75, 0.99]:
            result = policy.evaluate(
                Decimal("5000"), p_retry_now=p, uniform_draw=0.25,
            )
            assert result.success is True, f"Expected success for p={p}, u=0.25"
            assert result.recovered_amount == Decimal("5000")

    def test_failure_when_draw_at_or_above_probability(self, policy):
        """u >= p_retry_now → not recovered, nothing recovered, no cost."""
        for p in [0.01, 0.30, 0.49, 0.75]:
            result = policy.evaluate(
                Decimal("5000"), p_retry_now=p, uniform_draw=0.75,
            )
            assert result.success is False, f"Expected failure for p={p}, u=0.75"
            assert result.recovered_amount == Decimal("0")
            assert result.cost == Decimal("0")

    def test_low_probability_case_can_still_recover(self, policy):
        """
        A p=0.3 case recovers when the draw is favourable.

        This is the property the old `p >= 0.5` threshold destroyed: it made
        every sub-0.5 case a guaranteed failure, so aggregate recovery rate
        measured "fraction of cases above 0.5" rather than expected recovery.
        """
        result = policy.evaluate(
            Decimal("5000"), p_retry_now=0.3, uniform_draw=0.1,
        )
        assert result.success is True
        assert result.recovered_amount == Decimal("5000")

    def test_high_probability_case_can_still_fail(self, policy):
        """Symmetrically, a p=0.9 case fails on an unfavourable draw."""
        result = policy.evaluate(
            Decimal("5000"), p_retry_now=0.9, uniform_draw=0.95,
        )
        assert result.success is False
        assert result.recovered_amount == Decimal("0")

    def test_deterministic_given_same_inputs(self, policy):
        """Same (amount, p, u) → same result, always."""
        args = dict(payment_amount=Decimal("2500"), p_retry_now=0.62, uniform_draw=0.41)
        first = policy.evaluate(**args)
        for _ in range(20):
            assert policy.evaluate(**args) == first

    def test_baseline_never_charges_cost(self, policy):
        """Baseline incurs no intervention cost regardless of outcome (§16)."""
        for u in [0.0, 0.25, 0.5, 0.75, 0.999]:
            result = policy.evaluate(
                Decimal("1000"), p_retry_now=0.5, uniform_draw=u,
            )
            assert result.cost == Decimal("0")
