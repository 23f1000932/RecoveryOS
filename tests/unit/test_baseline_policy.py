"""
RecoveryOS — Unit Tests: Baseline Policy

3 test cases for the fixed retry_now comparator.
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
            )
            assert result.action == ActionType.RETRY_NOW, (
                f"Expected retry_now for p={p}, got {result.action}"
            )

    def test_success_when_p_retry_now_at_or_above_threshold(self, policy):
        """p_retry_now >= 0.5 → success=True."""
        for p in [0.50, 0.75, 0.99]:
            result = policy.evaluate(Decimal("5000"), p_retry_now=p)
            assert result.success is True, f"Expected success for p={p}"
            assert result.recovered_amount == Decimal("5000")

    def test_failure_when_p_retry_now_below_threshold(self, policy):
        """p_retry_now < 0.5 → success=False, recovered=0."""
        for p in [0.01, 0.30, 0.49]:
            result = policy.evaluate(Decimal("5000"), p_retry_now=p)
            assert result.success is False, f"Expected failure for p={p}"
            assert result.recovered_amount == Decimal("0")
            assert result.cost == Decimal("0")
