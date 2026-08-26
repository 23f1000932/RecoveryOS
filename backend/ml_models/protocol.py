"""
RecoveryOS — ML Model Protocol

Defines the stable interface all recovery models must implement.

Architecture rule (§9):
    "The optimizer must not know which model generated predictions."

This Protocol enables duck-typing — RuleBasedRecoveryModel and
XGBoostRecoveryModel both satisfy it without inheriting from a base class.
Swapping models requires zero pipeline changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from backend.domain.enums import ActionType

if TYPE_CHECKING:
    from backend.orchestrator.context import CaseContext


@dataclass(frozen=True)
class ActionPrediction:
    """
    Model output for a single (case, action) pair.

    probability  — P(success | context, action). ML output only.
                   Never used directly as a financial value.
    confidence   — Model's self-reported confidence in this prediction.
                   Used by guardrails to decide if human approval is needed.
    model_name   — Identifies which model produced this prediction.
    model_version — Version string for audit trail.
    """

    action: ActionType
    probability: float       # in (0, 1)
    confidence: float        # in (0, 1)
    model_name: str
    model_version: str


@runtime_checkable
class RecoveryOutcomeModel(Protocol):
    """
    Protocol that all recovery models must satisfy.

    Implementations:
      Phase 3: RuleBasedRecoveryModel  (deterministic rules, zero training)
      Phase 4: XGBoostRecoveryModel    (trained on synthetic dataset)

    Contract:
      - Must return exactly one ActionPrediction per requested action.
      - Must not call Gemini.
      - Must not execute any action.
      - Must not write to the database.
      - Must be pure: same context + same actions → same predictions.
    """

    def predict_action_outcomes(
        self,
        context: "CaseContext",
        actions: list[ActionType],
    ) -> list[ActionPrediction]:
        """
        Generate success probability predictions for a list of actions.

        Args:
            context: Full case context including customer history,
                     payment details, policy, and timing.
            actions: The candidate actions to predict for.
                     Always includes ActionType.DO_NOTHING.

        Returns:
            One ActionPrediction per action, in the same order as `actions`.
        """
        ...
