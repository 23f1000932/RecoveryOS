/**
 * RecoveryOS — Status Badge Component
 * Maps CaseStatus and ActionType values to the semantic badge styles.
 */

import type { ActionType, ApprovalStatus, CaseStatus, GuardrailOutcome } from '../../types';
import styles from './StatusBadge.module.css';

type BadgeVariant = 'success' | 'warning' | 'danger' | 'neutral' | 'accent';

function caseStatusVariant(status: CaseStatus): BadgeVariant {
  switch (status) {
    case 'RECOVERED': return 'success';
    case 'EXECUTING': case 'VERIFYING': case 'ANALYZING': return 'accent';
    case 'PENDING_APPROVAL': case 'DECISION_READY': return 'warning';
    case 'APPROVED': return 'accent';
    case 'CREATED': return 'neutral';
    case 'FAILED': case 'STOPPED': case 'EXPIRED': return 'danger';
    case 'ESCALATED': return 'warning';
    case 'UNKNOWN': return 'neutral';
    default: return 'neutral';
  }
}

function actionVariant(action: ActionType): BadgeVariant {
  switch (action) {
    case 'retry_now': case 'retry_later': return 'accent';
    case 'reminder': return 'neutral';
    case 'incentive': return 'warning';
    case 'escalate': return 'warning';
    case 'do_nothing': return 'neutral';
    default: return 'neutral';
  }
}

function approvalVariant(status: ApprovalStatus): BadgeVariant {
  switch (status) {
    case 'approved': return 'success';
    case 'rejected': return 'danger';
    case 'pending': return 'warning';
    case 'not_required': return 'neutral';
    default: return 'neutral';
  }
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface CaseStatusBadgeProps { status: CaseStatus }
export function CaseStatusBadge({ status }: CaseStatusBadgeProps) {
  const variant = caseStatusVariant(status);
  return (
    <span className={`badge badge--${variant} ${styles.badge}`}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}

interface ActionBadgeProps { action: ActionType | null | undefined }
export function ActionBadge({ action }: ActionBadgeProps) {
  if (!action) return <span className="badge badge--neutral">—</span>;
  const variant = actionVariant(action);
  const label = action.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  return <span className={`badge badge--${variant} ${styles.badge}`}>{label}</span>;
}

interface ApprovalBadgeProps { status: ApprovalStatus }
export function ApprovalBadge({ status }: ApprovalBadgeProps) {
  const variant = approvalVariant(status);
  const label = status.replace(/_/g, ' ');
  return <span className={`badge badge--${variant} ${styles.badge}`}>{label}</span>;
}

interface GuardrailBadgeProps { outcome: GuardrailOutcome }
export function GuardrailBadge({ outcome }: GuardrailBadgeProps) {
  const variantMap: Record<GuardrailOutcome, BadgeVariant> = {
    pass: 'success',
    block: 'danger',
    stop: 'danger',
    escalate: 'warning',
    pending_approval: 'warning',
    expired: 'neutral',
  };
  return (
    <span className={`badge badge--${variantMap[outcome] ?? 'neutral'} ${styles.badge}`}>
      {outcome.replace(/_/g, ' ')}
    </span>
  );
}
