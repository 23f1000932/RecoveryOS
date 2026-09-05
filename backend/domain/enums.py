"""
RecoveryOS — Domain Enumerations

These are the authoritative enums for the entire system.
Do not invent arbitrary status strings anywhere in the codebase.
Use these enums for DB values, API schemas, and internal logic.
"""

from enum import Enum


class CaseStatus(str, Enum):
    """
    Finite state machine for RecoveryCase.

    Allowed transitions:
        CREATED → ANALYZING
        ANALYZING → DECISION_READY | STOPPED | ESCALATED | FAILED
        DECISION_READY → PENDING_APPROVAL | APPROVED | STOPPED | ESCALATED
        PENDING_APPROVAL → APPROVED | STOPPED | ESCALATED
        APPROVED → EXECUTING
        EXECUTING → VERIFYING | FAILED
        VERIFYING → RECOVERED | STOPPED | FAILED | UNKNOWN

    Terminal states: RECOVERED, STOPPED, ESCALATED, FAILED, EXPIRED
    """

    CREATED = "CREATED"
    ANALYZING = "ANALYZING"
    DECISION_READY = "DECISION_READY"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    RECOVERED = "RECOVERED"
    STOPPED = "STOPPED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"

    @property
    def is_terminal(self) -> bool:
        return self in {
            CaseStatus.RECOVERED,
            CaseStatus.STOPPED,
            CaseStatus.ESCALATED,
            CaseStatus.FAILED,
            CaseStatus.EXPIRED,
        }

    @property
    def is_executable(self) -> bool:
        """Case can proceed to execution."""
        return self in {CaseStatus.APPROVED, CaseStatus.DECISION_READY}


# Valid state transitions (from → set of allowed destinations)
ALLOWED_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.CREATED: {CaseStatus.ANALYZING},
    CaseStatus.ANALYZING: {
        CaseStatus.DECISION_READY,
        CaseStatus.STOPPED,
        CaseStatus.ESCALATED,
        CaseStatus.FAILED,
    },
    CaseStatus.DECISION_READY: {
        CaseStatus.PENDING_APPROVAL,
        CaseStatus.APPROVED,
        CaseStatus.EXECUTING,
        CaseStatus.STOPPED,
        CaseStatus.ESCALATED,
    },
    CaseStatus.PENDING_APPROVAL: {
        CaseStatus.APPROVED,
        CaseStatus.STOPPED,
        CaseStatus.ESCALATED,
    },
    CaseStatus.APPROVED: {CaseStatus.EXECUTING, CaseStatus.STOPPED},
    CaseStatus.EXECUTING: {
        CaseStatus.VERIFYING,
        CaseStatus.RECOVERED,
        CaseStatus.FAILED,
        CaseStatus.STOPPED,
    },
    CaseStatus.VERIFYING: {
        CaseStatus.RECOVERED,
        CaseStatus.STOPPED,
        CaseStatus.FAILED,
        CaseStatus.UNKNOWN,
    },
    # Terminal states have no outgoing transitions
    CaseStatus.RECOVERED: set(),
    CaseStatus.STOPPED: set(),
    CaseStatus.ESCALATED: set(),
    CaseStatus.FAILED: set(),
    CaseStatus.EXPIRED: set(),
    CaseStatus.UNKNOWN: set(),
}


def can_transition(from_status: CaseStatus, to_status: CaseStatus) -> bool:
    """
    Check if a state transition is valid according to ALLOWED_TRANSITIONS.
    Enforces Rule 6 (state machine integrity).
    """
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())


class ActionType(str, Enum):
    """
    Fixed MVP candidate action set.
    Do not add new actions without documenting prediction, cost, guardrail, simulator, test, and UI behavior.
    """

    RETRY_NOW = "retry_now"
    RETRY_LATER = "retry_later"
    REMINDER = "reminder"
    INCENTIVE = "incentive"
    ESCALATE = "escalate"
    DO_NOTHING = "do_nothing"

    @property
    def is_retry(self) -> bool:
        return self in {ActionType.RETRY_NOW, ActionType.RETRY_LATER}

    @property
    def uses_contact(self) -> bool:
        return self in {ActionType.REMINDER, ActionType.INCENTIVE}

    @property
    def uses_incentive_budget(self) -> bool:
        return self == ActionType.INCENTIVE


ALL_ACTIONS: list[ActionType] = list(ActionType)


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ActionExecutionStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PaymentStatus(str, Enum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


class PipelineSource(str, Enum):
    SIMULATOR = "simulator"
    WEBHOOK = "webhook"
    DASHBOARD = "dashboard"


class ExecutionMode(str, Enum):
    SIMULATION = "simulation"
    TEST_MODE = "test_mode"
    DRY_RUN = "dry_run"


class GuardrailOutcome(str, Enum):
    PASS = "pass"
    BLOCK = "block"
    STOP = "stop"
    ESCALATE = "escalate"
    PENDING_APPROVAL = "pending_approval"
    EXPIRED = "expired"


class WebhookProcessingStatus(str, Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class AuditEventType(str, Enum):
    PAYMENT_FAILED = "payment_failed"
    CONTEXT_LOADED = "context_loaded"
    PREDICTIONS_GENERATED = "predictions_generated"
    OPTIMIZATION_COMPLETED = "optimization_completed"
    GUARDRAIL_PASSED = "guardrail_passed"
    GUARDRAIL_BLOCKED = "guardrail_blocked"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    ACTION_REQUESTED = "action_requested"
    ACTION_EXECUTED = "action_executed"
    ACTION_FAILED = "action_failed"
    VERIFICATION_STARTED = "verification_started"
    PAYMENT_RECOVERED = "payment_recovered"
    VERIFICATION_FAILED = "verification_failed"
    CASE_STOPPED = "case_stopped"
    CASE_ESCALATED = "case_escalated"
    CASE_EXPIRED = "case_expired"
    CASE_UNKNOWN = "case_unknown"
    AGENT_EXPLANATION = "agent_explanation"
    AGENT_FALLBACK = "agent_fallback"
