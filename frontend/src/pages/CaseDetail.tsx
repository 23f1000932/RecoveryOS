/**
 * RecoveryOS — Case Detail Page
 * Comprehensive forensic view answering what failed, why, recommended action, and guardrails.
 */

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  ShieldCheck,
  ShieldAlert,
  Play,
  Zap,
  CheckCircle2,
  XCircle,
  Coins,
  UserCheck,
  CreditCard,
  Layers,
  ChevronDown,
  ChevronUp,
  AlertCircle,
} from 'lucide-react';
import { ActionBarChart } from '../components/charts/ActionBarChart';
import { CaseStatusBadge, ActionBadge, ApprovalBadge } from '../components/controls/StatusBadge';
import { EmptyState } from '../components/layout/EmptyState';
import { ErrorBanner } from '../components/layout/ErrorBanner';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatAction, formatINR } from '../services/api';
import type { AuditLogEntry, RecoveryCaseDetail as CaseDetailType } from '../types';
import styles from './CaseDetail.module.css';

const TERMINAL: string[] = ['RECOVERED', 'STOPPED', 'ESCALATED', 'FAILED', 'EXPIRED'];

function auditEventColor(type: string): string {
  if (type.includes('recovered') || type.includes('granted') || type.includes('approved')) return 'var(--success-text)';
  if (type.includes('failed') || type.includes('blocked') || type.includes('rejected')) return '#EF4444';
  if (type.includes('approval_requested') || type.includes('escalat')) return '#F59E0B';
  if (type.includes('executed') || type.includes('started')) return 'var(--accent-primary)';
  return 'var(--muted-foreground)';
}

function auditLabel(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function JsonSnapshot({ data }: { data: Record<string, unknown> | null }) {
  if (!data || !Object.keys(data).length) return <span style={{ color: 'var(--muted-foreground)' }}>—</span>;
  return (
    <pre
      style={{
        fontSize: 11,
        color: '#CBD5E1',
        background: 'rgba(0, 0, 0, 0.4)',
        borderRadius: 4,
        padding: '8px 12px',
        overflowX: 'auto',
        maxHeight: 160,
        margin: 0,
        fontFamily: 'var(--font-mono)',
        border: '1px solid var(--border-subtle)',
      }}
    >
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function AuditTimeline({ entries }: { entries: AuditLogEntry[] }) {
  if (!entries.length) {
    return (
      <EmptyState
        icon="📋"
        title="No Recovery Events Recorded Yet"
        description="Events appear here as the recovery pipeline evaluates and executes actions."
      />
    );
  }
  return (
    <div className={styles.auditTimeline}>
      {entries.map((e) => (
        <details key={e.id} className={styles.auditEntry}>
          <summary className={styles.auditSummary}>
            <span
              className={styles.auditDot}
              style={{ background: auditEventColor(e.event_type) }}
            />
            <span className={styles.auditLabel}>{auditLabel(e.event_type)}</span>
            <span className={styles.auditMeta}>
              {e.actor} · {e.source} · {new Date(e.timestamp).toLocaleTimeString()}
            </span>
          </summary>
          <div className={styles.auditBody}>
            <div className={styles.auditSnapshots}>
              <div>
                <p className={styles.snapshotLabel}>Input State</p>
                <JsonSnapshot data={e.input_snapshot} />
              </div>
              <div>
                <p className={styles.snapshotLabel}>Output State</p>
                <JsonSnapshot data={e.output_snapshot} />
              </div>
            </div>
          </div>
        </details>
      ))}
    </div>
  );
}

function CandidateTable({
  candidates,
  recommendedAction,
}: {
  candidates: CaseDetailType['candidates'];
  recommendedAction: string | null;
}) {
  if (!candidates.length) return null;
  const sorted = [...candidates].sort((a, b) => a.rank - b.rank);
  return (
    <div className={styles.tableWrapper}>
      <table className={styles.candidateTable}>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Candidate Action</th>
            <th>P(Success)</th>
            <th>Expected Net Revenue</th>
            <th>Cost</th>
            <th>Guardrail Status</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => (
            <tr
              key={c.action}
              className={c.action === recommendedAction ? styles.rowSelected : ''}
              data-blocked={!c.allowed}
            >
              <td>#{c.rank}</td>
              <td>
                <div style={{ display: 'inline-flex', alignItems: 'center' }}>
                  <ActionBadge action={c.action} />
                  {c.action === recommendedAction && (
                    <span className={styles.selectedTag}>Selected</span>
                  )}
                </div>
              </td>
              <td>{(c.probability * 100).toFixed(1)}%</td>
              <td style={{ color: 'var(--accent-gold)', fontWeight: 600 }}>
                {formatINR(c.expected_net_revenue)}
              </td>
              <td>{formatINR(c.intervention_cost)}</td>
              <td>
                {c.allowed ? (
                  <span className={styles.allowedTag}>✓ Allowed</span>
                ) : (
                  <span className={styles.blockedTag} title={c.blocked_reason ?? ''}>
                    ✗ Blocked: {c.blocked_reason?.slice(0, 24)}…
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();

  const [caseData, setCaseData] = useState<CaseDetailType | null>(null);
  const [audit, setAudit] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [auditLoading, setAuditLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [showAudit, setShowAudit] = useState(false);

  const load = useCallback(() => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    api.getCase(caseId)
      .then((d) => {
        setCaseData(d);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, [caseId]);

  useEffect(load, [load]);

  const loadAudit = () => {
    if (!caseId) return;
    setAuditLoading(true);
    api.getCaseAudit(caseId)
      .then((r) => {
        setAudit(r.entries);
        setAuditLoading(false);
      })
      .catch(() => setAuditLoading(false));
  };

  const toggleAudit = () => {
    if (!showAudit && !audit.length) loadAudit();
    setShowAudit((v) => !v);
  };

  const doAction = async (fn: () => Promise<unknown>, successMsg: string) => {
    if (actionPending) return;
    setActionPending(true);
    setActionMessage(null);
    try {
      await fn();
      setActionMessage(successMsg);
      load();
      loadAudit();
    } catch (e: unknown) {
      setActionMessage(`Error: ${(e as Error).message}`);
    } finally {
      setActionPending(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingFill} aria-label="Loading recovery case…">
          <div className={styles.spinner} />
          <span className="label-mono">
            LOADING PAYMENT CASE CONTEXT…
          </span>
        </div>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className={styles.page}>
        <PageHeader title="Case Not Found" />
        <ErrorBanner message={error ?? 'Payment recovery case data is unavailable.'} onRetry={load} />
      </div>
    );
  }

  const isTerminal = TERMINAL.includes(caseData.status);
  const canAnalyze = !isTerminal;
  const canApprove = caseData.status === 'PENDING_APPROVAL';
  const canReject = caseData.status === 'PENDING_APPROVAL';
  const canExecute =
    caseData.status === 'APPROVED' ||
    (caseData.status === 'DECISION_READY' && !caseData.requires_approval);
  const canStop = !isTerminal;

  return (
    <div className={`animate-enter ${styles.page}`}>
      {/* ── Page Header ───────────────────────────────────────────────────────── */}
      <PageHeader
        label="Case Detail"
        title={`Recovery Case: CASE-${caseData.id.slice(0, 8).toUpperCase()}`}
        subtitle={`Razorpay Payment ID: ${caseData.external_payment_id || caseData.payment_id}`}
      />

      {/* ── Status Bar ───────────────────────────────────────────────────────── */}
      <div className={styles.statusBar}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <CaseStatusBadge status={caseData.status} />
          {caseData.selected_action && <ActionBadge action={caseData.selected_action} />}
          <ApprovalBadge status={caseData.approval_status} />
        </div>
        {caseData.requires_approval && (
          <span className={styles.approvalWarning}>
            <ShieldAlert size={13} />
            Approval Required
          </span>
        )}
      </div>

      {actionMessage && (
        <div style={{ marginBottom: 16 }}>
          <ErrorBanner message={actionMessage} />
        </div>
      )}

      {/* ── Dedicated Approval Required Callout (Section 23) ────────────────── */}
      {caseData.requires_approval && caseData.status === 'PENDING_APPROVAL' && (
        <div className={styles.approvalPanel}>
          <div className={styles.approvalPanelHeader}>
            <ShieldAlert size={16} />
            <span>Merchant Approval Required Prior to Execution</span>
          </div>

          <div className={styles.approvalDetails}>
            <div className={styles.approvalItem}>
              <span className={styles.approvalLabel}>Amount at Risk</span>
              <span className={styles.approvalValue}>{formatINR(caseData.payment_amount)}</span>
            </div>
            <div className={styles.approvalItem}>
              <span className={styles.approvalLabel}>Recommended Action</span>
              <span className={styles.approvalValue}>
                {caseData.selected_action ? formatAction(caseData.selected_action) : '—'}
              </span>
            </div>
            <div className={styles.approvalItem}>
              <span className={styles.approvalLabel}>Expected Net Revenue</span>
              <span className={styles.approvalValue} style={{ color: 'var(--accent-gold)' }}>
                {formatINR(caseData.expected_net_revenue)}
              </span>
            </div>
            <div className={styles.approvalItem}>
              <span className={styles.approvalLabel}>Model Confidence</span>
              <span className={styles.approvalValue}>
                {(() => {
                  const sel = caseData.candidates?.find((c) => c.action === caseData.selected_action);
                  const conf = sel?.confidence ?? sel?.probability;
                  return conf ? `${(conf * 100).toFixed(0)}%` : '—';
                })()}
              </span>
            </div>
          </div>

          <p className={styles.approvalReasonText}>
            <strong>Why approval is required:</strong>{' '}
            {caseData.guardrail_result?.approval_reason ||
              'Payment amount exceeds the automatic execution threshold under current merchant policy.'}
          </p>
        </div>
      )}

      {/* ── 2-Column Responsive Layout ────────────────────────────────────────── */}
      <div className={styles.grid}>
        {/* ── LEFT COLUMN: Context & Controls ─────────────────────────────────── */}
        <div className={styles.leftCol}>
          {/* Payment Context Card */}
          <section className={styles.cardSection}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitle}>
                <CreditCard size={14} color="var(--accent-primary)" />
                <span>Payment Context</span>
              </div>
            </div>
            <div className={styles.contextGrid}>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Amount</span>
                <span className={`${styles.ctxValue} ${styles.ctxHighlight}`}>
                  {formatINR(caseData.payment_amount)}
                </span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Payment Method</span>
                <span className={styles.ctxValue}>{caseData.payment_method?.toUpperCase() ?? 'UPI'}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Failure Code</span>
                <span className={styles.ctxValue} style={{ color: '#EF4444' }}>
                  {caseData.payment_failure_code ?? 'DECLINED'}
                </span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Attempt Number</span>
                <span className={styles.ctxValue}>{caseData.payment_attempt_number ?? 1}</span>
              </div>
            </div>
          </section>

          {/* Customer Context Card */}
          <section className={styles.cardSection}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitle}>
                <UserCheck size={14} color="var(--accent-primary)" />
                <span>Customer History</span>
              </div>
            </div>
            <div className={styles.contextGrid}>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Historic Success Rate</span>
                <span className={styles.ctxValue} style={{ color: 'var(--success-text)' }}>
                  {caseData.customer_success_rate != null
                    ? `${(caseData.customer_success_rate * 100).toFixed(0)}%`
                    : '—'}
                </span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Total Transactions</span>
                <span className={styles.ctxValue}>{caseData.customer_transaction_count ?? '—'}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Prior Failures</span>
                <span className={styles.ctxValue}>{caseData.customer_failure_count ?? '—'}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Average Transaction</span>
                <span className={styles.ctxValue}>
                  {formatINR(caseData.customer_avg_amount || caseData.payment_amount)}
                </span>
              </div>
            </div>
          </section>

          {/* Financial Summary Card */}
          <section className={styles.cardSection}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitle}>
                <Coins size={14} color="var(--accent-gold)" />
                <span>Financial Recovery Summary</span>
              </div>
            </div>
            <div className={styles.contextGrid}>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Revenue at Risk</span>
                <span className={styles.ctxValue}>{formatINR(caseData.revenue_at_risk)}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Expected Net Revenue</span>
                <span className={styles.ctxValue} style={{ color: 'var(--accent-gold)' }}>
                  {formatINR(caseData.expected_net_revenue)}
                </span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Actual Recovered</span>
                <span className={styles.ctxValue} style={{ color: 'var(--success-text)' }}>
                  {caseData.actual_recovered ? formatINR(caseData.actual_recovered) : '—'}
                </span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Net Incremental Recovery</span>
                <span className={styles.ctxValue}>
                  {caseData.net_incremental_recovery ? formatINR(caseData.net_incremental_recovery) : '—'}
                </span>
              </div>
            </div>
          </section>

          {/* Governance Execution Console */}
          <section className={styles.cardSection}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitle}>
                <Zap size={14} color="var(--accent-primary)" />
                <span>Recovery Governance Actions</span>
              </div>
            </div>
            <div className={styles.actionButtons}>
              <button
                id="btn-analyze"
                className={styles.btnActionSecondary}
                disabled={!canAnalyze || actionPending}
                onClick={() =>
                  doAction(
                    () => api.analyzeCase(caseId!),
                    'Payment analysis completed.',
                  )
                }
              >
                <Zap size={14} />
                {actionPending ? 'Analyzing…' : 'Analyze Payment'}
              </button>

              {canApprove && (
                <button
                  id="btn-approve"
                  className={styles.btnActionPrimary}
                  disabled={actionPending}
                  onClick={() =>
                    doAction(
                      () => api.approveCase(caseId!),
                      'Case approved for execution.',
                    )
                  }
                >
                  <CheckCircle2 size={14} />
                  Approve Recovery
                </button>
              )}

              {canReject && (
                <button
                  id="btn-reject"
                  className={styles.btnActionDanger}
                  disabled={actionPending}
                  onClick={() =>
                    doAction(
                      () => api.rejectCase(caseId!),
                      'Case rejected by merchant policy.',
                    )
                  }
                >
                  <XCircle size={14} />
                  Reject
                </button>
              )}

              {canExecute && (
                <button
                  id="btn-execute"
                  className={styles.btnActionPrimary}
                  disabled={actionPending}
                  onClick={() =>
                    doAction(
                      () => api.executeCase(caseId!),
                      'Recovery action executed successfully.',
                    )
                  }
                >
                  <Play size={14} fill="currentColor" />
                  Execute Action
                </button>
              )}

              {canStop && (
                <button
                  id="btn-stop"
                  className={styles.btnActionSecondary}
                  disabled={actionPending}
                  onClick={() =>
                    doAction(
                      () => api.stopCase(caseId!),
                      'Recovery process stopped.',
                    )
                  }
                >
                  Stop Recovery
                </button>
              )}
            </div>

            {/* State gate explanation */}
            {!canExecute && !canApprove && !isTerminal && (
              <p className={styles.gateHint}>
                {caseData.status === 'CREATED' && 'Click Analyze to generate an AI recovery decision.'}
                {caseData.status === 'ANALYZING' && 'Evaluating recovery models and guardrails…'}
                {caseData.status === 'PENDING_APPROVAL' && 'Awaiting merchant approval before execution.'}
              </p>
            )}
            {isTerminal && (
              <p className={styles.gateHint}>
                Case settled in terminal state ({caseData.status.toLowerCase()}) — no further actions available.
              </p>
            )}
          </section>
        </div>

        {/* ── RIGHT COLUMN: AI Intelligence & Candidate Comparison ─────────────── */}
        <div className={styles.rightCol}>
          {/* AI Recommendation Card */}
          <section className={styles.aiDecisionCard}>
            <div className={styles.decisionHeader}>
              <span className={styles.decisionLabel}>AI Recommendation</span>
              <span className={styles.modelMeta}>
                {caseData.model_name ? `${caseData.model_name} v${caseData.model_version}` : 'RecoveryOS AI'}
                {caseData.policy_version && ` · Policy: ${caseData.policy_version}`}
              </span>
            </div>

            {caseData.selected_action ? (
              <>
                <div className={styles.decisionBanner}>
                  <div>
                    <span className="label-mono" style={{ fontSize: 10, color: 'var(--muted-foreground)' }}>
                      OPTIMAL INTERVENTION
                    </span>
                    <div className={styles.decisionActionName}>
                      {formatAction(caseData.selected_action)}
                    </div>
                  </div>
                  <ActionBadge action={caseData.selected_action} />
                </div>

                {/* Explicit "Do Nothing" Communication (Section 20) */}
                {caseData.selected_action === 'do_nothing' && (
                  <div className={styles.doNothingAlert}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, marginBottom: 4 }}>
                      <AlertCircle size={15} color="var(--accent-primary)" />
                      <span>Positive Decision: Do Nothing</span>
                    </div>
                    Recovery is not economically justified under current merchant policy. The expected intervention cost exceeds the expected recovery probability.
                  </div>
                )}

                {caseData.agent_explanation && (
                  <div className={styles.explanationBox}>
                    {caseData.agent_explanation}
                  </div>
                )}
              </>
            ) : (
              <EmptyState
                icon="🤖"
                title="No Decision Yet"
                description="Click 'Analyze Payment' to evaluate candidate actions and generate an AI decision."
              />
            )}
          </section>

          {/* Guardrail Verification Summary */}
          {caseData.guardrail_result && (
            <section className={styles.cardSection}>
              <div className={styles.cardHeader}>
                <div className={styles.cardTitle}>
                  <ShieldCheck size={14} color="var(--success-text)" />
                  <span>Deterministic Guardrail Verification</span>
                </div>
              </div>

              <div className={styles.guardrailSummaryRow}>
                <span
                  className={styles.verdictPill}
                  data-verdict={caseData.guardrail_result.overall_outcome}
                >
                  VERDICT: {caseData.guardrail_result.overall_outcome.replace('_', ' ').toUpperCase()}
                </span>
                {caseData.guardrail_result.approval_reason && (
                  <span style={{ fontSize: 12, color: 'var(--muted)', fontFamily: 'var(--font-mono)' }}>
                    {caseData.guardrail_result.approval_reason}
                  </span>
                )}
              </div>

              <div className={styles.guardrailChecksGrid}>
                {caseData.guardrail_result.checks.map((c) => (
                  <div key={c.check_name} className={styles.guardrailCheckItem}>
                    {c.passed ? (
                      <CheckCircle2 size={13} color="var(--success-text)" />
                    ) : (
                      <XCircle size={13} color="#EF4444" />
                    )}
                    <span style={{ color: c.passed ? 'var(--foreground)' : '#EF4444' }}>
                      {c.check_name.replace(/_/g, ' ')}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Candidate Actions Comparison (Section 19) */}
          {caseData.candidates.length > 0 && (
            <section className={styles.cardSection}>
              <div className={styles.cardHeader}>
                <div className={styles.cardTitle}>
                  <Layers size={14} color="var(--accent-primary)" />
                  <span>Action Candidates Comparison</span>
                </div>
              </div>

              <CandidateTable
                candidates={caseData.candidates}
                recommendedAction={caseData.selected_action}
              />

              <div style={{ marginTop: 20 }}>
                <p className="label-mono" style={{ marginBottom: 10 }}>
                  Expected Net Revenue by Action
                </p>
                <ActionBarChart
                  candidates={caseData.candidates}
                  recommendedAction={caseData.selected_action}
                />
              </div>
            </section>
          )}
        </div>
      </div>

      {/* ── Decision Audit Trail (Section 27) ─────────────────────────────────── */}
      <section className={styles.cardSection} style={{ marginTop: 24 }}>
        <div className={styles.auditHeader} onClick={toggleAudit} role="button" tabIndex={0}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="label-mono" style={{ fontSize: 12, fontWeight: 700, color: 'var(--foreground)' }}>
              DECISION AUDIT TRAIL
            </span>
          </div>
          <span className={styles.auditToggle}>
            {showAudit ? (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                <ChevronUp size={14} /> Collapse
              </span>
            ) : (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                <ChevronDown size={14} /> View Audit Events
              </span>
            )}
          </span>
        </div>
        {showAudit &&
          (auditLoading ? (
            <div className={styles.loadingFill} style={{ minHeight: 100 }}>
              <div className={styles.spinner} />
            </div>
          ) : (
            <AuditTimeline entries={audit} />
          ))}
      </section>
    </div>
  );
}

export default CaseDetailPage;
