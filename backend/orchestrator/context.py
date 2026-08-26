"""
RecoveryOS — Orchestrator Domain Objects

Shared dataclasses that form the contract between all pipeline components:
  CaseContext     — full enriched context passed into the pipeline
  DecisionProposal — authoritative output of the pipeline

Rules:
  - These are pure data containers. No business logic here.
  - All monetary fields are Decimal.
  - policy is the loaded RecoveryPolicy object (from YAML).
  - DecisionProposal.explanation is a template string in Phase 3;
    Gemini overwrites it in Phase 5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from backend.domain.enums import ActionType

if TYPE_CHECKING:
    from backend.guardrails.engine import GuardrailResult
    from backend.optimizer.expected_value import OptimizationResult


@dataclass
class RecoveryPolicy:
    """
    Loaded from policies/recovery_policy.yaml.
    Passed into CaseContext so the pipeline never reads from disk mid-run.
    """

    version: str
    max_retries_per_customer: int
    max_messages_per_customer: int
    max_incentive_per_customer: Decimal
    daily_incentive_pool: Decimal
    high_value_threshold: Decimal
    min_expected_net_revenue: Decimal
    min_model_confidence: float
    recovery_window_hours: int
    auto_action_probability: float


@dataclass
class CaseContext:
    """
    Complete enriched context for a single recovery case.

    Built by the pipeline caller (API endpoint or simulator) before
    calling RecoveryPipeline.process_case(). The pipeline is read-only
    with respect to this object.

    All monetary amounts are Decimal (INR).
    All rates/probabilities are float (0–1).
    """

    # ── Identifiers ──────────────────────────────────────────────────────────
    case_id: str
    payment_id: str
    customer_id: str
    merchant_id: str

    # ── Payment ───────────────────────────────────────────────────────────────
    amount: Decimal               # failed payment amount (what we can recover)
    currency: str                 # e.g. "INR"
    method: str                   # e.g. "card", "upi"
    failure_code: str             # e.g. "insufficient_funds"
    attempt_number: int           # 1-based retry count

    # ── Customer History ──────────────────────────────────────────────────────
    customer_success_rate: float
    customer_transaction_count: int
    customer_success_count: int
    customer_failure_count: int
    customer_avg_amount: Decimal
    time_since_failure_hours: float
    hour_of_day: int              # 0–23
    day_of_week: int              # 0 (Mon) – 6 (Sun)
    previous_failure_count: int

    # ── Policy + Budget ───────────────────────────────────────────────────────
    policy: RecoveryPolicy

    # ── Current Case State ────────────────────────────────────────────────────
    prior_actions: list[str] = field(default_factory=list)
    retry_count: int = 0
    message_count: int = 0
    customer_incentive_spent: Decimal = field(default_factory=lambda: Decimal("0"))
    daily_incentive_remaining: Decimal = field(default_factory=lambda: Decimal("5000"))
    payment_already_succeeded: bool = False
    case_expires_at: datetime | None = None


@dataclass
class DecisionProposal:
    """
    The authoritative output of RecoveryPipeline.process_case().

    This is the complete decision record — it contains everything needed
    to execute, approve, audit, and explain the decision.

    The pipeline does NOT write this to the database.
    The caller (API endpoint or simulator runner) is responsible for DB writes.

    explanation:
        In Phase 3 — a deterministic template string.
        In Phase 5 — overwritten by Gemini's structured output.
        The financial decision is NEVER changed by the explanation.
    """

    case_id: str
    recommended_action: ActionType
    optimization_result: OptimizationResult
    guardrail_result: GuardrailResult
    requires_approval: bool
    explanation: str
    model_name: str
    model_version: str
    policy_version: str
