/**
 * RecoveryOS — TypeScript Domain Types
 *
 * These mirror the backend Pydantic schemas in backend/domain/schemas.py.
 * When a backend schema changes, update this file too.
 * Never use `any` unless absolutely necessary.
 */

// ── Enums ─────────────────────────────────────────────────────────────────────

export type CaseStatus =
  | 'CREATED'
  | 'ANALYZING'
  | 'DECISION_READY'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'EXECUTING'
  | 'VERIFYING'
  | 'RECOVERED'
  | 'STOPPED'
  | 'ESCALATED'
  | 'FAILED'
  | 'EXPIRED'
  | 'UNKNOWN';

export type ActionType =
  | 'retry_now'
  | 'retry_later'
  | 'reminder'
  | 'incentive'
  | 'escalate'
  | 'do_nothing';

export type ApprovalStatus =
  | 'not_required'
  | 'pending'
  | 'approved'
  | 'rejected';

export type GuardrailOutcome =
  | 'pass'
  | 'block'
  | 'stop'
  | 'escalate'
  | 'pending_approval'
  | 'expired';

export type AuditEventType =
  | 'payment_failed'
  | 'context_loaded'
  | 'predictions_generated'
  | 'optimization_completed'
  | 'guardrail_passed'
  | 'guardrail_blocked'
  | 'approval_requested'
  | 'approval_granted'
  | 'approval_rejected'
  | 'action_requested'
  | 'action_executed'
  | 'action_failed'
  | 'verification_started'
  | 'payment_recovered'
  | 'verification_failed'
  | 'case_stopped'
  | 'case_escalated'
  | 'case_expired'
  | 'agent_explanation'
  | 'agent_fallback'
  | 'case_unknown';

// ── API Error ──────────────────────────────────────────────────────────────────

export interface ApiError {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}

// ── Health ─────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export interface DashboardSummary {
  revenue_at_risk: string;
  revenue_recovered: string;
  baseline_recovered: string;
  incremental_recovery: string;
  net_incremental_recovery: string;
  intervention_spend: string;
  recovery_rate: number;
  baseline_recovery_rate: number;
  guardrail_stops: number;
  escalations: number;
  do_nothing_count: number;
  total_cases: number;
  pending_approval_count: number;
}

// ── Action Candidate ───────────────────────────────────────────────────────────

export interface ActionCandidate {
  action: ActionType;
  probability: number;
  confidence: number;
  model_name: string;
  model_version: string;
  recoverable_amount: string;
  intervention_cost: string;
  incentive_cost: string;
  contact_cost: string;
  expected_gross_recovery: string;
  expected_net_revenue: string;
  allowed: boolean;
  blocked_reason: string | null;
  rank: number;
}

// ── Guardrail ─────────────────────────────────────────────────────────────────

export interface GuardrailCheck {
  check_name: string;
  passed: boolean;
  outcome: GuardrailOutcome;
  blocked_actions: ActionType[];
  reason: string | null;
}

export interface GuardrailResult {
  overall_outcome: GuardrailOutcome;
  checks: GuardrailCheck[];
  requires_approval: boolean;
  approval_reason: string | null;
}

// ── Recovery Case ─────────────────────────────────────────────────────────────

export interface RecoveryCaseSummary {
  id: string;
  payment_id: string;
  customer_id: string;
  merchant_id: string;
  status: CaseStatus;
  revenue_at_risk: string;
  selected_action: ActionType | null;
  expected_net_revenue: string | null;
  model_confidence: number | null;
  requires_approval: boolean;
  approval_status: ApprovalStatus;
  created_at: string;
  updated_at: string;
}

export interface RecoveryCaseDetail {
  id: string;
  payment_id: string;
  customer_id: string;
  merchant_id: string;
  status: CaseStatus;
  // Payment context
  payment_amount: string;
  payment_currency: string;
  payment_method: string;
  payment_failure_code: string;
  payment_attempt_number: number;
  external_payment_id: string;
  // Customer context
  customer_transaction_count: number;
  customer_success_count: number;
  customer_failure_count: number;
  customer_success_rate: number;
  customer_avg_amount: string;
  customer_preferred_method: string;
  // Financial values
  revenue_at_risk: string;
  selected_action: ActionType | null;
  expected_gross_recovery: string | null;
  expected_net_revenue: string | null;
  actual_recovered: string | null;
  intervention_cost: string | null;
  incremental_recovery: string | null;
  net_incremental_recovery: string | null;
  // Decision metadata
  requires_approval: boolean;
  approval_status: ApprovalStatus;
  model_name: string | null;
  model_version: string | null;
  policy_version: string | null;
  // Candidates and guardrails
  candidates: ActionCandidate[];
  guardrail_result: GuardrailResult | null;
  agent_explanation: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecoveryCaseListResponse {
  cases: RecoveryCaseSummary[];
  total: number;
  page: number;
  page_size: number;
}

// ── Approval ──────────────────────────────────────────────────────────────────

export interface ApprovalResponse {
  case_id: string;
  approval_status: ApprovalStatus;
  case_status: CaseStatus;
  message: string;
}

export interface ExecuteResponse {
  case_id: string;
  case_status: CaseStatus;
  action_executed: ActionType | null;
  actual_recovered: string | null;
  message: string;
}

// ── Audit ─────────────────────────────────────────────────────────────────────

export interface AuditLogEntry {
  id: string;
  case_id: string;
  event_type: AuditEventType;
  actor: string;
  source: string;
  model_name: string | null;
  model_version: string | null;
  policy_version: string | null;
  input_snapshot: Record<string, unknown>;
  output_snapshot: Record<string, unknown>;
  decision: Record<string, unknown> | null;
  guardrail_result: Record<string, unknown> | null;
  timestamp: string;
}

export interface AuditLogResponse {
  case_id: string;
  entries: AuditLogEntry[];
  total: number;
}

// ── Simulator ─────────────────────────────────────────────────────────────────

export interface SimulatorRunRequest {
  rows: number;
  seed: number;
}

export interface SimulatorRunResponse {
  experiment_id: string;
  message: string;
}

export interface SimulatorCaseResult {
  case_id: string;
  baseline_action: ActionType;
  baseline_success: boolean;
  baseline_recovered: string;
  ai_action: ActionType;
  ai_success: boolean;
  ai_recovered: string;
  ai_cost: string;
}

export interface SimulatorResult {
  experiment_id: string;
  seed: number;
  dataset_size: number;
  baseline_policy: string;
  ai_policy: string;
  baseline_recovered: string;
  ai_recovered: string;
  baseline_cost: string;
  ai_cost: string;
  incremental_recovery: string;
  net_incremental_recovery: string;
  baseline_recovery_rate: number;
  ai_recovery_rate: number;
  guardrail_stops: number;
  escalations: number;
  do_nothing_count: number;
  cases: SimulatorCaseResult[];
  created_at: string;
}

// ── Policy ────────────────────────────────────────────────────────────────────

export interface PolicyView {
  version: string;
  max_retries_per_customer: number;
  max_messages_per_customer: number;
  max_incentive_per_customer: string;
  daily_incentive_pool: string;
  high_value_threshold: string;
  recovery_window_hours: number;
  min_expected_net_revenue: string;
  min_model_confidence: number;
  auto_action_probability: number;
}
