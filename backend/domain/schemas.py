"""
RecoveryOS — API Schemas (Pydantic)

These are the request/response models for the FastAPI REST API.
Frontend TypeScript types must correspond to these models.
When a schema changes: update here → update frontend types → update API client → update tests.

Financial values in API responses are always strings (to avoid float precision issues in JSON).
The frontend renders these as formatted currency strings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.domain.enums import (
    ActionExecutionStatus,
    ActionType,
    ApprovalStatus,
    AuditEventType,
    CaseStatus,
    GuardrailOutcome,
)


# ── Error Contract ─────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    revenue_at_risk: str                   # formatted INR
    revenue_recovered: str
    baseline_recovered: str
    incremental_recovery: str
    net_incremental_recovery: str
    intervention_spend: str
    recovery_rate: float                   # 0.0–1.0
    baseline_recovery_rate: float
    guardrail_stops: int
    escalations: int
    do_nothing_count: int
    total_cases: int
    pending_approval_count: int


# ── Action Candidate ───────────────────────────────────────────────────────────

class ActionCandidateSchema(BaseModel):
    action: ActionType
    probability: float
    confidence: float
    model_name: str
    model_version: str
    recoverable_amount: str
    intervention_cost: str
    incentive_cost: str
    contact_cost: str
    expected_gross_recovery: str
    expected_net_revenue: str
    allowed: bool
    blocked_reason: str | None = None
    rank: int


# ── Guardrail ─────────────────────────────────────────────────────────────────

class GuardrailCheckSchema(BaseModel):
    check_name: str
    passed: bool
    outcome: GuardrailOutcome
    blocked_actions: list[ActionType]
    reason: str | None = None


class GuardrailResultSchema(BaseModel):
    overall_outcome: GuardrailOutcome
    checks: list[GuardrailCheckSchema]
    requires_approval: bool
    approval_reason: str | None = None


# ── Recovery Case ─────────────────────────────────────────────────────────────

class RecoveryCaseSummary(BaseModel):
    """Lightweight case view for the Recovery Queue list."""
    id: str
    payment_id: str
    customer_id: str
    merchant_id: str
    status: CaseStatus
    revenue_at_risk: str
    selected_action: ActionType | None = None
    expected_net_revenue: str | None = None
    model_confidence: float | None = None
    requires_approval: bool
    approval_status: ApprovalStatus
    created_at: datetime
    updated_at: datetime


class RecoveryCaseDetail(BaseModel):
    """Full case view for the Case Detail page."""
    id: str
    payment_id: str
    customer_id: str
    merchant_id: str
    status: CaseStatus

    # Payment context
    payment_amount: str
    payment_currency: str
    payment_method: str
    payment_failure_code: str
    payment_attempt_number: int
    external_payment_id: str

    # Customer context
    customer_transaction_count: int
    customer_success_count: int
    customer_failure_count: int
    customer_success_rate: float
    customer_avg_amount: str
    customer_preferred_method: str

    # Decision
    revenue_at_risk: str
    selected_action: ActionType | None = None
    expected_gross_recovery: str | None = None
    expected_net_revenue: str | None = None
    actual_recovered: str | None = None
    intervention_cost: str | None = None
    incremental_recovery: str | None = None
    net_incremental_recovery: str | None = None

    # Decision metadata
    requires_approval: bool
    approval_status: ApprovalStatus
    model_name: str | None = None
    model_version: str | None = None
    policy_version: str | None = None

    # Candidates and guardrails
    candidates: list[ActionCandidateSchema] = Field(default_factory=list)
    guardrail_result: GuardrailResultSchema | None = None

    # Agent explanation
    agent_explanation: str | None = None

    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RecoveryCaseListResponse(BaseModel):
    cases: list[RecoveryCaseSummary]
    total: int
    page: int
    page_size: int


# ── Approval ──────────────────────────────────────────────────────────────────

class ApprovalRequest(BaseModel):
    actor: str = Field(default="merchant", description="Who is approving")
    reason: str | None = None


class ApprovalResponse(BaseModel):
    case_id: str
    approval_status: ApprovalStatus
    case_status: CaseStatus
    message: str


# ── Execute / Stop ────────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    actor: str = Field(default="merchant")


class ExecuteResponse(BaseModel):
    case_id: str
    case_status: CaseStatus
    action_executed: ActionType | None = None
    actual_recovered: str | None = None
    message: str


class StopResponse(BaseModel):
    case_id: str
    case_status: CaseStatus
    message: str


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditLogEntry(BaseModel):
    id: str
    case_id: str
    event_type: AuditEventType
    actor: str
    source: str
    model_name: str | None = None
    model_version: str | None = None
    policy_version: str | None = None
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_snapshot: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] | None = None
    guardrail_result: dict[str, Any] | None = None
    timestamp: datetime


class AuditLogResponse(BaseModel):
    case_id: str
    entries: list[AuditLogEntry]
    total: int


# ── Simulator ─────────────────────────────────────────────────────────────────

class SimulatorRunRequest(BaseModel):
    rows: int = Field(default=1000, ge=10, le=50000, description="Number of synthetic cases")
    seed: int = Field(default=42, description="Random seed for reproducibility")


class SimulatorRunResponse(BaseModel):
    experiment_id: str
    message: str


class SimulatorCaseResult(BaseModel):
    case_id: str
    baseline_action: ActionType
    baseline_success: bool
    baseline_recovered: str
    ai_action: ActionType
    ai_success: bool
    ai_recovered: str
    ai_cost: str


class SimulatorResult(BaseModel):
    experiment_id: str
    seed: int
    dataset_size: int
    baseline_policy: str
    ai_policy: str
    baseline_recovered: str
    ai_recovered: str
    baseline_cost: str
    ai_cost: str
    incremental_recovery: str
    net_incremental_recovery: str
    baseline_recovery_rate: float
    ai_recovery_rate: float
    guardrail_stops: int
    escalations: int
    do_nothing_count: int
    approvals_required: int = 0
    cases: list[SimulatorCaseResult] = Field(default_factory=list)
    created_at: datetime


# ── Policies ──────────────────────────────────────────────────────────────────

class PolicyView(BaseModel):
    version: str
    max_retries_per_customer: int
    max_messages_per_customer: int
    max_incentive_per_customer: str
    daily_incentive_pool: str
    high_value_threshold: str
    recovery_window_hours: int
    min_expected_net_revenue: str
    min_model_confidence: float
    auto_action_probability: float


# ── Webhook ───────────────────────────────────────────────────────────────────

class WebhookAckResponse(BaseModel):
    status: str
    message: str
    case_id: str | None = None
