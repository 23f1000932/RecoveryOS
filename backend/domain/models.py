"""
RecoveryOS — Domain Models

Internal business objects used across backend modules.
These are NOT API schemas (those live in schemas.py).
These are the typed domain objects passed between orchestrator, optimizer, guardrails, agents, and tools.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from backend.domain.enums import (
    ActionExecutionStatus,
    ActionType,
    ApprovalStatus,
    AuditEventType,
    CaseStatus,
    ExecutionMode,
    GuardrailOutcome,
    PaymentStatus,
    PipelineSource,
)


# ── Core Data Models ───────────────────────────────────────────────────────────

@dataclass
class MerchantPolicy:
    """Loaded from policies/recovery_policy.yaml. Authoritative guardrail config."""
    version: str
    max_retries_per_customer: int
    max_messages_per_customer: int
    max_incentive_per_customer: Decimal
    daily_incentive_pool: Decimal
    high_value_threshold: Decimal
    recovery_window_hours: int
    min_expected_net_revenue: Decimal
    min_model_confidence: float
    auto_action_probability: float
    action_costs: dict[str, ActionCostModel]


@dataclass
class ActionCostModel:
    intervention_cost: Decimal
    contact_cost: Decimal
    incentive_cost: Decimal

    @property
    def total_cost(self) -> Decimal:
        return self.intervention_cost + self.contact_cost + self.incentive_cost


@dataclass
class CustomerContext:
    id: str
    merchant_id: str
    transaction_count: int
    success_count: int
    failure_count: int
    avg_amount: Decimal
    preferred_method: str
    retry_count_this_case: int = 0
    message_count_this_case: int = 0
    incentive_amount_this_case: Decimal = Decimal("0")

    @property
    def success_rate(self) -> float:
        if self.transaction_count == 0:
            return 0.0
        return self.success_count / self.transaction_count


@dataclass
class PaymentContext:
    id: str
    merchant_id: str
    customer_id: str
    external_payment_id: str
    amount: Decimal
    currency: str
    method: str
    status: PaymentStatus
    failure_code: str
    attempt_number: int
    created_at: datetime
    updated_at: datetime


@dataclass
class CaseContext:
    """
    Full context loaded by the Contextualize stage.
    This is the input to the ML model and optimizer.
    Must NOT include any post-action information.
    """
    case_id: str
    merchant_id: str
    payment: PaymentContext
    customer: CustomerContext
    policy: MerchantPolicy
    time_since_failure_hours: float
    previous_actions: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


# ── ML / Prediction Models ─────────────────────────────────────────────────────

@dataclass
class ActionPrediction:
    """Output of RecoveryOutcomeModel for a single action."""
    action: ActionType
    probability: float          # P(success | context, action) in [0, 1]
    confidence: float           # model confidence in [0, 1]
    model_name: str
    model_version: str


# ── Optimization Models ────────────────────────────────────────────────────────

@dataclass
class ActionCandidate:
    """
    One evaluated action candidate.
    All financial values are deterministically computed by the optimizer.
    Never set by LLM.
    """
    action: ActionType
    probability: float
    confidence: float
    model_name: str
    model_version: str
    recoverable_amount: Decimal
    intervention_cost: Decimal
    incentive_cost: Decimal
    contact_cost: Decimal
    expected_gross_recovery: Decimal   # probability × recoverable_amount
    expected_net_revenue: Decimal      # gross - intervention - incentive - contact
    allowed: bool = True
    blocked_reason: str | None = None
    rank: int = 0


@dataclass
class OptimizationResult:
    """
    Output of the Expected-Value Optimizer.
    selected_action is the deterministically chosen best action.
    Optimizer never executes. Never calls Gemini.
    """
    selected_action: ActionType
    candidates: list[ActionCandidate]
    selected_expected_net_revenue: Decimal
    model_name: str
    model_version: str


# ── Guardrail Models ───────────────────────────────────────────────────────────

@dataclass
class GuardrailCheck:
    """Result of a single guardrail check."""
    check_name: str
    passed: bool
    outcome: GuardrailOutcome
    blocked_actions: list[ActionType]
    reason: str | None = None


@dataclass
class GuardrailResult:
    """
    Aggregated result of the guardrail engine.
    requires_approval is set by the engine, not by LLM or frontend.
    """
    overall_outcome: GuardrailOutcome
    checks: list[GuardrailCheck]
    requires_approval: bool
    approval_reason: str | None
    final_optimization: OptimizationResult | None  # re-ranked after blocks


# ── Decision Proposal ──────────────────────────────────────────────────────────

@dataclass
class DecisionProposal:
    """
    The complete decision object assembled by the RecoveryPipeline.
    Passed to GeminiAgent for explanation.
    Backend owns all authoritative values here.
    """
    case_id: str
    recommended_action: ActionType
    candidate_actions: list[ActionCandidate]
    selected_expected_net_revenue: Decimal
    guardrail_result: GuardrailResult
    requires_approval: bool
    approval_status: ApprovalStatus
    model_name: str
    model_version: str
    policy_version: str
    agent_explanation: str | None = None


# ── Agent Output ───────────────────────────────────────────────────────────────

@dataclass
class AgentOutput:
    """
    Output from GeminiAgent. Explanation only.
    recommended_action from agent is informational — the optimizer's decision is authoritative.
    """
    explanation: str
    agent_recommended_action: ActionType | None
    agent_confidence: float | None
    is_fallback: bool = False


# ── Action Execution ───────────────────────────────────────────────────────────

@dataclass
class ActionRequest:
    """Validated action execution request. Never created by LLM directly."""
    case_id: str
    action: ActionType
    idempotency_key: str
    recoverable_amount: Decimal
    execution_mode: ExecutionMode
    source: PipelineSource
    latent_outcome: float | None = None   # used in simulation mode only


@dataclass
class ActionResult:
    """Result from an action adapter. Verification is separate."""
    success: bool
    provider_reference: str | None
    cost: Decimal
    error_code: str | None = None
    error_message: str | None = None


# ── Verification ───────────────────────────────────────────────────────────────

@dataclass
class VerificationResult:
    """
    Result of post-action payment verification.
    actual_recovered is ONLY set if payment status is confirmed SUCCESS.
    """
    payment_id: str
    verified_status: PaymentStatus
    actual_recovered: Decimal      # 0 unless verified success
    verified_at: datetime
    provider_reference: str | None = None


# ── Recovery Pipeline Result ───────────────────────────────────────────────────

@dataclass
class RecoveryResult:
    """Final result returned by RecoveryPipeline.process_case()."""
    case_id: str
    final_status: CaseStatus
    selected_action: ActionType | None
    actual_recovered: Decimal
    intervention_cost: Decimal
    incremental_recovery: Decimal        # vs baseline (0 for live, computed for sim)
    net_incremental_recovery: Decimal
    decision: DecisionProposal | None
    verification: VerificationResult | None
    error: str | None = None


# ── Audit ──────────────────────────────────────────────────────────────────────

@dataclass
class AuditEntry:
    """One audit log entry. Written for every meaningful pipeline event."""
    case_id: str
    event_type: AuditEventType
    actor: str                          # "system" | "merchant" | "webhook"
    source: PipelineSource
    input_snapshot: dict[str, Any]
    output_snapshot: dict[str, Any]
    model_name: str | None = None
    model_version: str | None = None
    policy_version: str | None = None
    decision: dict[str, Any] | None = None
    guardrail_result: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


# ── Experiment / Simulator ─────────────────────────────────────────────────────

@dataclass
class ExperimentCase:
    """Per-case outcome in a simulator experiment."""
    case_id: str
    baseline_action: ActionType
    baseline_success: bool
    baseline_recovered: Decimal
    ai_action: ActionType
    ai_success: bool
    ai_recovered: Decimal
    ai_cost: Decimal


@dataclass
class ExperimentMetrics:
    """Aggregate metrics for a simulator experiment run."""
    experiment_id: str
    seed: int
    dataset_size: int
    baseline_policy: str
    ai_policy: str
    baseline_recovered: Decimal
    ai_recovered: Decimal
    baseline_cost: Decimal
    ai_cost: Decimal
    incremental_recovery: Decimal        # ai_recovered - baseline_recovered
    net_incremental_recovery: Decimal    # incremental - (ai_cost - baseline_cost)
    baseline_recovery_rate: float
    ai_recovery_rate: float
    guardrail_stops: int
    escalations: int
    do_nothing_count: int
    created_at: datetime = field(default_factory=datetime.utcnow)
