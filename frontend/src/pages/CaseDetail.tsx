/**
 * RecoveryOS — Case Detail Page (Phase 7 — Full Implementation)
 *
 * Sections:
 *   1. Payment + customer context
 *   2. AI Decision (recommended action, Gemini explanation)
 *   3. Candidate actions table + ENR chart
 *   4. Guardrail results
 *   5. State-gated action buttons (Analyze / Approve / Reject / Execute / Stop)
 *   6. Audit timeline
 *
 * UI Safety Rules (architecture §30):
 *   Execute: only if APPROVED, or (DECISION_READY && !requires_approval)
 *   Approve/Reject: only if PENDING_APPROVAL
 *   Stop: only if not terminal
 *   Analyze: only if not terminal
 */

import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ActionBarChart } from '../components/charts/ActionBarChart';
import { CaseStatusBadge, ActionBadge, ApprovalBadge } from '../components/controls/StatusBadge';
import { EmptyState } from '../components/layout/EmptyState';
import { ErrorBanner } from '../components/layout/ErrorBanner';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatAction, formatINR } from '../services/api';
import type { AuditLogEntry, RecoveryCaseDetail as CaseDetailType } from '../types';
import styles from './CaseDetail.module.css';

// ── Terminal states (no further actions available) ────────────────────────────
const TERMINAL: string[] = ['RECOVERED', 'STOPPED', 'ESCALATED', 'FAILED', 'EXPIRED'];

// ── Audit event colour coding ─────────────────────────────────────────────────
function auditEventColor(type: string): string {
  if (type.includes('recovered') || type.includes('granted')) return 'hsl(140,50%,50%)';
  if (type.includes('failed') || type.includes('blocked') || type.includes('rejected')) return 'hsl(0,60%,55%)';
  if (type.includes('approval_requested') || type.includes('escalat')) return 'hsl(38,90%,58%)';
  if (type.includes('executed') || type.includes('started')) return 'hsl(210,65%,60%)';
  return 'hsl(0,0%,55%)';
}

function auditLabel(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// ── Mini JsonViewer ───────────────────────────────────────────────────────────
function JsonSnapshot({ data }: { data: Record<string, unknown> | null }) {
  if (!data || !Object.keys(data).length) return <span style={{ color: '#555' }}>—</span>;
  return (
    <pre style={{
      fontSize: 11, color: '#aaa', background: 'hsl(0,0%,7%)',
      borderRadius: 6, padding: '8px 10px', overflowX: 'auto',
      maxHeight: 160, margin: 0,
    }}>
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

// ── Audit Timeline ─────────────────────────────────────────────────────────────
function AuditTimeline({ entries }: { entries: AuditLogEntry[] }) {
  if (!entries.length) {
    return <EmptyState icon="📋" title="No audit events yet" description="Events appear as the pipeline processes this case." />;
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
                <p className={styles.snapshotLabel}>Input</p>
                <JsonSnapshot data={e.input_snapshot} />
              </div>
              <div>
                <p className={styles.snapshotLabel}>Output</p>
                <JsonSnapshot data={e.output_snapshot} />
              </div>
            </div>
          </div>
        </details>
      ))}
    </div>
  );
}

// ── Candidate Table ────────────────────────────────────────────────────────────
function CandidateTable({ candidates, recommendedAction }: {
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
            <th>Action</th>
            <th>P(success)</th>
            <th>Exp. Net Revenue</th>
            <th>Cost</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => (
            <tr
              key={c.action}
              className={c.action === recommendedAction ? styles.rowSelected : ''}
              data-blocked={!c.allowed}
            >
              <td className={styles.rankCell}>#{c.rank}</td>
              <td>
                <ActionBadge action={c.action} />
                {c.action === recommendedAction && (
                  <span className={styles.selectedTag}>Selected</span>
                )}
              </td>
              <td>{(c.probability * 100).toFixed(1)}%</td>
              <td>{formatINR(c.expected_net_revenue)}</td>
              <td>{formatINR(c.intervention_cost)}</td>
              <td>
                {c.allowed
                  ? <span className={styles.allowedTag}>✓ Allowed</span>
                  : <span className={styles.blockedTag} title={c.blocked_reason ?? ''}>✗ Blocked</span>
                }
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();

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
      .then((d) => { setCaseData(d); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, [caseId]);

  useEffect(load, [load]);

  const loadAudit = () => {
    if (!caseId) return;
    setAuditLoading(true);
    api.getCaseAudit(caseId)
      .then((r) => { setAudit(r.entries); setAuditLoading(false); })
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
        <div className={styles.loadingFill} aria-label="Loading case…">
          <div className={styles.spinner} />
        </div>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className={styles.page}>
        <PageHeader title="Case Not Found" />
        <ErrorBanner message={error ?? 'Case data unavailable.'} onRetry={load} />
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
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <PageHeader
        label="Recovery Case"
        title={`Case ${caseData.id.slice(0, 8)}…`}
        subtitle={`Payment ${caseData.external_payment_id || caseData.payment_id.slice(0, 8)}…`}
      />

      {/* ── Status bar ─────────────────────────────────────────────────────── */}
      <div className={styles.statusBar}>
        <CaseStatusBadge status={caseData.status} />
        {caseData.selected_action && <ActionBadge action={caseData.selected_action} />}
        <ApprovalBadge status={caseData.approval_status} />
        {caseData.requires_approval && (
          <span className={styles.approvalWarning}>⚠ Approval Required</span>
        )}
      </div>

      {actionMessage && (
        <div style={{ marginBottom: 12 }}>
          <ErrorBanner message={actionMessage} />
        </div>
      )}

      {/* ── 2-col grid ─────────────────────────────────────────────────────── */}
      <div className={styles.grid}>

        {/* ── LEFT column ─────────────────────────────────────────────────── */}
        <div className={styles.leftCol}>

          {/* Payment context */}
          <section className="card">
            <p className="label-mono" style={{ marginBottom: 16 }}>Payment Context</p>
            <div className={styles.contextGrid}>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Amount</span>
                <span className={styles.ctxValue}>{formatINR(caseData.payment_amount)}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Method</span>
                <span className={styles.ctxValue}>{caseData.payment_method?.toUpperCase() ?? '—'}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Failure Code</span>
                <span className={styles.ctxValue}>{caseData.payment_failure_code ?? '—'}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Attempt #</span>
                <span className={styles.ctxValue}>{caseData.payment_attempt_number ?? 1}</span>
              </div>
            </div>
          </section>

          {/* Customer context */}
          <section className="card" style={{ marginTop: 12 }}>
            <p className="label-mono" style={{ marginBottom: 16 }}>Customer History</p>
            <div className={styles.contextGrid}>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Success Rate</span>
                <span className={styles.ctxValue}>
                  {caseData.customer_success_rate != null
                    ? `${(caseData.customer_success_rate * 100).toFixed(0)}%`
                    : '—'}
                </span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Transactions</span>
                <span className={styles.ctxValue}>{caseData.customer_transaction_count ?? '—'}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Failures</span>
                <span className={styles.ctxValue}>{caseData.customer_failure_count ?? '—'}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Avg Amount</span>
                <span className={styles.ctxValue}>{formatINR(caseData.customer_avg_amount)}</span>
              </div>
            </div>
          </section>

          {/* Financial summary */}
          <section className="card" style={{ marginTop: 12 }}>
            <p className="label-mono" style={{ marginBottom: 16 }}>Financial Summary</p>
            <div className={styles.contextGrid}>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Revenue at Risk</span>
                <span className={styles.ctxValue}>{formatINR(caseData.revenue_at_risk)}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Exp. Net Revenue</span>
                <span className={styles.ctxValue}>{formatINR(caseData.expected_net_revenue)}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Actual Recovered</span>
                <span className={styles.ctxValue} style={{ color: 'hsl(140,50%,60%)' }}>
                  {caseData.actual_recovered ? formatINR(caseData.actual_recovered) : '—'}
                </span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Net Incremental</span>
                <span className={styles.ctxValue}>
                  {caseData.net_incremental_recovery ? formatINR(caseData.net_incremental_recovery) : '—'}
                </span>
              </div>
            </div>
          </section>

          {/* Actions */}
          <section className="card" style={{ marginTop: 12 }}>
            <p className="label-mono" style={{ marginBottom: 16 }}>Actions</p>
            <div className={styles.actionButtons}>
              <button
                id="btn-analyze"
                className="btn btn--secondary"
                disabled={!canAnalyze || actionPending}
                title={!canAnalyze ? 'Case is in a terminal state.' : 'Re-run pipeline analysis'}
                onClick={() => doAction(
                  () => api.analyzeCase(caseId!),
                  'Analysis complete.',
                )}
              >
                {actionPending ? '…' : '⚡ Analyze'}
              </button>

              {canApprove && (
                <button
                  id="btn-approve"
                  className="btn btn--primary"
                  disabled={actionPending}
                  onClick={() => doAction(
                    () => api.approveCase(caseId!),
                    'Case approved.',
                  )}
                >
                  ✓ Approve
                </button>
              )}

              {canReject && (
                <button
                  id="btn-reject"
                  className="btn btn--secondary"
                  disabled={actionPending}
                  onClick={() => doAction(
                    () => api.rejectCase(caseId!),
                    'Case rejected.',
                  )}
                >
                  ✗ Reject
                </button>
              )}

              {canExecute && (
                <button
                  id="btn-execute"
                  className="btn btn--primary"
                  disabled={actionPending}
                  title="Execute the selected recovery action"
                  onClick={() => doAction(
                    () => api.executeCase(caseId!),
                    'Execution complete.',
                  )}
                >
                  ▶ Execute
                </button>
              )}

              {canStop && (
                <button
                  id="btn-stop"
                  className="btn btn--ghost"
                  disabled={actionPending}
                  onClick={() => doAction(
                    () => api.stopCase(caseId!),
                    'Recovery stopped.',
                  )}
                >
                  ⏹ Stop
                </button>
              )}
            </div>

            {/* State gate explanation */}
            {!canExecute && !canApprove && !isTerminal && (
              <p className={styles.gateHint}>
                {caseData.status === 'CREATED' && 'Run Analyze to generate a decision.'}
                {caseData.status === 'ANALYZING' && 'Pipeline is running…'}
                {caseData.status === 'PENDING_APPROVAL' && 'Awaiting merchant approval before execution.'}
              </p>
            )}
            {isTerminal && (
              <p className={styles.gateHint}>
                Case is {caseData.status.toLowerCase()} — no further actions available.
              </p>
            )}
          </section>
        </div>

        {/* ── RIGHT column ────────────────────────────────────────────────── */}
        <div className={styles.rightCol}>

          {/* AI Decision */}
          <section className="card">
            <p className="label-mono" style={{ marginBottom: 16 }}>AI Recommendation</p>
            {caseData.selected_action ? (
              <div className={styles.decisionBlock}>
                <div className={styles.decisionAction}>
                  <ActionBadge action={caseData.selected_action} />
                  <span className={styles.decisionLabel}>
                    {formatAction(caseData.selected_action)}
                  </span>
                </div>
                {caseData.model_name && (
                  <p className={styles.modelMeta}>
                    Model: {caseData.model_name} v{caseData.model_version} · Policy: {caseData.policy_version}
                  </p>
                )}
              </div>
            ) : (
              <EmptyState
                icon="🤖"
                title="No decision yet"
                description="Click Analyze to run the pipeline and generate an AI decision."
              />
            )}
          </section>

          {/* Gemini Explanation */}
          {caseData.agent_explanation && (
            <section className="card" style={{ marginTop: 12 }}>
              <p className="label-mono" style={{ marginBottom: 12 }}>Gemini Explanation</p>
              <div className={styles.explanationBlock}>
                {caseData.agent_explanation}
              </div>
            </section>
          )}

          {/* Guardrail summary */}
          {caseData.guardrail_result && (
            <section className="card" style={{ marginTop: 12 }}>
              <p className="label-mono" style={{ marginBottom: 12 }}>Guardrail Result</p>
              <div className={styles.guardrailRow}>
                <span className={styles.verdictTag} data-verdict={caseData.guardrail_result.overall_outcome}>
                  {caseData.guardrail_result.overall_outcome.replace('_', ' ').toUpperCase()}
                </span>
                {caseData.guardrail_result.approval_reason && (
                  <span className={styles.guardrailReason}>
                    {caseData.guardrail_result.approval_reason}
                  </span>
                )}
              </div>
              <div className={styles.guardrailChecks}>
                {caseData.guardrail_result.checks.map((c) => (
                  <div key={c.check_name} className={styles.guardrailCheck}>
                    <span style={{ color: c.passed ? 'hsl(140,50%,55%)' : 'hsl(0,60%,55%)' }}>
                      {c.passed ? '✓' : '✗'}
                    </span>
                    <span style={{ color: '#aaa', fontSize: 12 }}>
                      {c.check_name.replace(/_/g, ' ')}
                    </span>
                    {c.reason && <span style={{ color: '#666', fontSize: 11 }}>{c.reason}</span>}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Candidate table + chart */}
          {caseData.candidates.length > 0 && (
            <section className="card" style={{ marginTop: 12 }}>
              <p className="label-mono" style={{ marginBottom: 16 }}>Action Candidates</p>
              <CandidateTable
                candidates={caseData.candidates}
                recommendedAction={caseData.selected_action}
              />
              <div style={{ marginTop: 24 }}>
                <p className="label-mono" style={{ marginBottom: 8, fontSize: 11 }}>
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

      {/* ── Audit Timeline ──────────────────────────────────────────────────── */}
      <section className="card" style={{ marginTop: 20 }}>
        <div className={styles.auditHeader} onClick={toggleAudit} role="button" tabIndex={0}>
          <p className="label-mono" style={{ margin: 0 }}>Audit Timeline</p>
          <span className={styles.auditToggle}>{showAudit ? '▲ Hide' : '▼ Show'}</span>
        </div>
        {showAudit && (
          auditLoading
            ? <div className={styles.loadingFill} style={{ height: 80 }}><div className={styles.spinner} /></div>
            : <AuditTimeline entries={audit} />
        )}
      </section>
    </div>
  );
}
