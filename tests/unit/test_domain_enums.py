"""
RecoveryOS — Unit Tests: Domain Enums and State Machine

Tests the state machine transitions defined in enums.py.
These are safety-critical — invalid transitions must be caught at runtime.
"""

import pytest

from backend.domain.enums import (
    ALLOWED_TRANSITIONS,
    ActionType,
    ApprovalStatus,
    AuditEventType,
    CaseStatus,
    ExecutionMode,
    GuardrailOutcome,
    PipelineSource,
)


class TestCaseStatus:
    def test_all_statuses_defined(self):
        """Ensure all 13 statuses from the spec are present."""
        expected = {
            "CREATED", "ANALYZING", "DECISION_READY", "PENDING_APPROVAL",
            "APPROVED", "EXECUTING", "VERIFYING",
            "RECOVERED", "STOPPED", "ESCALATED", "FAILED", "EXPIRED", "UNKNOWN",
        }
        actual = {s.value for s in CaseStatus}
        assert expected == actual, f"Missing statuses: {expected - actual}"

    def test_terminal_states(self):
        terminal = {CaseStatus.RECOVERED, CaseStatus.STOPPED, CaseStatus.ESCALATED,
                    CaseStatus.FAILED, CaseStatus.EXPIRED}
        for s in terminal:
            assert s.is_terminal, f"{s.value} should be terminal"

    def test_non_terminal_states(self):
        non_terminal = {
            CaseStatus.CREATED, CaseStatus.ANALYZING, CaseStatus.DECISION_READY,
            CaseStatus.PENDING_APPROVAL, CaseStatus.APPROVED,
            CaseStatus.EXECUTING, CaseStatus.VERIFYING, CaseStatus.UNKNOWN,
        }
        for s in non_terminal:
            assert not s.is_terminal, f"{s.value} should not be terminal"

    def test_is_executable(self):
        assert CaseStatus.APPROVED.is_executable
        assert CaseStatus.DECISION_READY.is_executable
        assert not CaseStatus.CREATED.is_executable
        assert not CaseStatus.EXECUTING.is_executable
        assert not CaseStatus.RECOVERED.is_executable

    def test_transition_table_completeness(self):
        """Every CaseStatus must appear in ALLOWED_TRANSITIONS."""
        for status in CaseStatus:
            assert status in ALLOWED_TRANSITIONS, \
                f"CaseStatus.{status.value} missing from ALLOWED_TRANSITIONS"

    # --- Valid transitions ---
    @pytest.mark.parametrize("from_s,to_s", [
        (CaseStatus.CREATED, CaseStatus.ANALYZING),
        (CaseStatus.ANALYZING, CaseStatus.DECISION_READY),
        (CaseStatus.ANALYZING, CaseStatus.STOPPED),
        (CaseStatus.ANALYZING, CaseStatus.ESCALATED),
        (CaseStatus.ANALYZING, CaseStatus.FAILED),
        (CaseStatus.DECISION_READY, CaseStatus.PENDING_APPROVAL),
        (CaseStatus.DECISION_READY, CaseStatus.APPROVED),
        (CaseStatus.DECISION_READY, CaseStatus.STOPPED),
        (CaseStatus.PENDING_APPROVAL, CaseStatus.APPROVED),
        (CaseStatus.PENDING_APPROVAL, CaseStatus.STOPPED),
        (CaseStatus.APPROVED, CaseStatus.EXECUTING),
        (CaseStatus.EXECUTING, CaseStatus.VERIFYING),
        (CaseStatus.EXECUTING, CaseStatus.FAILED),
        (CaseStatus.VERIFYING, CaseStatus.RECOVERED),
        (CaseStatus.VERIFYING, CaseStatus.STOPPED),
        (CaseStatus.VERIFYING, CaseStatus.FAILED),
        (CaseStatus.VERIFYING, CaseStatus.UNKNOWN),
    ])
    def test_valid_transition(self, from_s: CaseStatus, to_s: CaseStatus):
        assert to_s in ALLOWED_TRANSITIONS[from_s], \
            f"Expected {from_s.value} → {to_s.value} to be valid"

    # --- Invalid transitions ---
    @pytest.mark.parametrize("from_s,to_s", [
        (CaseStatus.CREATED, CaseStatus.RECOVERED),
        (CaseStatus.CREATED, CaseStatus.EXECUTING),
        (CaseStatus.APPROVED, CaseStatus.DECISION_READY),    # backward
        (CaseStatus.RECOVERED, CaseStatus.ANALYZING),         # terminal → any
        (CaseStatus.STOPPED, CaseStatus.EXECUTING),           # terminal → any
        (CaseStatus.EXECUTING, CaseStatus.CREATED),           # backward
        (CaseStatus.ANALYZING, CaseStatus.RECOVERED),         # skip steps
    ])
    def test_invalid_transition(self, from_s: CaseStatus, to_s: CaseStatus):
        assert to_s not in ALLOWED_TRANSITIONS[from_s], \
            f"Expected {from_s.value} → {to_s.value} to be INVALID"

    def test_terminal_has_no_transitions(self):
        for s in CaseStatus:
            if s.is_terminal:
                assert len(ALLOWED_TRANSITIONS[s]) == 0, \
                    f"Terminal state {s.value} must have no outgoing transitions"


class TestActionType:
    def test_all_actions_defined(self):
        expected = {"retry_now", "retry_later", "reminder", "incentive", "escalate", "do_nothing"}
        actual = {a.value for a in ActionType}
        assert expected == actual

    def test_retry_actions(self):
        assert ActionType.RETRY_NOW.is_retry
        assert ActionType.RETRY_LATER.is_retry
        assert not ActionType.REMINDER.is_retry
        assert not ActionType.DO_NOTHING.is_retry

    def test_uses_incentive_budget(self):
        assert ActionType.INCENTIVE.uses_incentive_budget
        assert not ActionType.RETRY_NOW.uses_incentive_budget
        assert not ActionType.DO_NOTHING.uses_incentive_budget

    def test_uses_contact(self):
        assert ActionType.REMINDER.uses_contact
        assert ActionType.INCENTIVE.uses_contact
        assert not ActionType.RETRY_NOW.uses_contact


class TestApprovalStatus:
    def test_all_statuses(self):
        values = {s.value for s in ApprovalStatus}
        assert "not_required" in values
        assert "pending" in values
        assert "approved" in values
        assert "rejected" in values


class TestAuditEventTypes:
    def test_all_events_defined(self):
        """Ensure all 19 audit event types from the spec are present."""
        expected = {
            "payment_failed", "context_loaded", "predictions_generated",
            "optimization_completed", "guardrail_passed", "guardrail_blocked",
            "approval_requested", "approval_granted", "approval_rejected",
            "action_requested", "action_executed", "action_failed",
            "verification_started", "payment_recovered", "verification_failed",
            "case_stopped", "case_escalated", "case_expired",
            "agent_explanation", "agent_fallback", "case_unknown",
        }
        actual = {e.value for e in AuditEventType}
        missing = expected - actual
        assert not missing, f"Missing audit event types: {missing}"


class TestPipelineEnums:
    def test_pipeline_source_values(self):
        values = {s.value for s in PipelineSource}
        assert "simulator" in values
        assert "webhook" in values
        assert "dashboard" in values

    def test_execution_mode_values(self):
        values = {m.value for m in ExecutionMode}
        assert "simulation" in values
        assert "test_mode" in values
        assert "dry_run" in values
