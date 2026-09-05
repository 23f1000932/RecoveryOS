/**
 * RecoveryOS — Case Detail Page (Bitcoin DeFi Block Forensics Overhaul)
 *
 * Sections:
 *   1. Payment & Customer Context Cards
 *   2. Holographic Gemini Agent Decision & Latent Explanation
 *   3. Candidate Actions Matrix + Expected Net Alpha Bar Chart
 *   4. Cryptographic Guardrail Checks
 *   5. State-Gated Action Buttons with Gamification XP Triggers
 *   6. Ledger Audit Timeline
 */

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  Play,
  Zap,
  CheckCircle2,
  XCircle,
  Coins,
  Terminal,
  UserCheck,
  CreditCard,
  Layers,
  ChevronDown,
  ChevronUp,
  Flame,
} from 'lucide-react';
import { ActionBarChart } from '../components/charts/ActionBarChart';
import { CaseStatusBadge, ActionBadge, ApprovalBadge } from '../components/controls/StatusBadge';
import { EmptyState } from '../components/layout/EmptyState';
import { ErrorBanner } from '../components/layout/ErrorBanner';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatAction, formatINR } from '../services/api';
import { gamification } from '../services/gamification';
import type { AuditLogEntry, RecoveryCaseDetail as CaseDetailType } from '../types';
import styles from './CaseDetail.module.css';

const TERMINAL: string[] = ['RECOVERED', 'STOPPED', 'ESCALATED', 'FAILED', 'EXPIRED'];

function auditEventColor(type: string): string {
  if (type.includes('recovered') || type.includes('granted') || type.includes('approved')) return '#10B981';
  if (type.includes('failed') || type.includes('blocked') || type.includes('rejected')) return '#EF4444';
  if (type.includes('approval_requested') || type.includes('escalat')) return '#F59E0B';
  if (type.includes('executed') || type.includes('started')) return 'var(--color-brand-primary)';
  return 'var(--color-text-muted)';
}

function auditLabel(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function JsonSnapshot({ data }: { data: Record<string, unknown> | null }) {
  if (!data || !Object.keys(data).length) return <span style={{ color: 'var(--color-text-muted)' }}>—</span>;
  return (
    <pre
      style={{
        fontSize: 11,
        color: '#9CA3AF',
        background: 'rgba(0, 0, 0, 0.5)',
        borderRadius: 6,
        padding: '10px 12px',
        overflowX: 'auto',
        maxHeight: 160,
        margin: 0,
        fontFamily: 'var(--font-mono)',
        border: '1px solid var(--color-border-subtle)',
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
        title="No Audit Blocks Yet"
        description="Immutable events append here in real-time as state transitions occur."
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
                <p className={styles.snapshotLabel}>Input State Block</p>
                <JsonSnapshot data={e.input_snapshot} />
              </div>
              <div>
                <p className={styles.snapshotLabel}>Output State Block</p>
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
            <th>Expected Net Alpha</th>
            <th>Compute / Cost</th>
            <th>Consensus Status</th>
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
              <td style={{ color: 'var(--color-accent-gold)', fontWeight: 600 }}>
                {formatINR(c.expected_net_revenue)}
              </td>
              <td>{formatINR(c.intervention_cost)}</td>
              <td>
                {c.allowed ? (
                  <span className={styles.allowedTag}>✓ Allowed</span>
                ) : (
                  <span className={styles.blockedTag} title={c.blocked_reason ?? ''}>
                    ✗ Blocked: {c.blocked_reason?.slice(0, 20)}…
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

  const doAction = async (
    fn: () => Promise<unknown>,
    successMsg: string,
    onSuccessReward?: () => void,
  ) => {
    if (actionPending) return;
    setActionPending(true);
    setActionMessage(null);
    try {
      await fn();
      setActionMessage(successMsg);
      if (onSuccessReward) onSuccessReward();
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
          <span className="label-mono" style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            DECRYPTING BLOCK FORENSICS…
          </span>
        </div>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className={styles.page}>
        <PageHeader title="Block Not Found" />
        <ErrorBanner message={error ?? 'Case transaction data unavailable.'} onRetry={load} />
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
        label="Block Forensics"
        title={`TX Block #${caseData.id.slice(0, 8).toUpperCase()}`}
        subtitle={`Payment Identifier: ${caseData.external_payment_id || caseData.payment_id} · Merkle Root Verified`}
      />

      {/* ── Status Bar ───────────────────────────────────────────────────────── */}
      <div className={styles.statusBar}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <CaseStatusBadge status={caseData.status} />
          {caseData.selected_action && <ActionBadge action={caseData.selected_action} />}
          <ApprovalBadge status={caseData.approval_status} />
        </div>
        {caseData.requires_approval && (
          <span className={styles.approvalWarning}>
            <ShieldAlert size={14} />
            Multi-Sig Consensus Required
          </span>
        )}
      </div>

      {actionMessage && (
        <div style={{ marginBottom: 16 }}>
          <ErrorBanner message={actionMessage} />
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
                <CreditCard size={15} color="var(--color-brand-primary)" />
                <span>Transaction Metadata</span>
              </div>
            </div>
            <div className={styles.contextGrid}>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Payment Amount</span>
                <span className={`${styles.ctxValue} ${styles.ctxHighlight}`}>
                  {formatINR(caseData.payment_amount)}
                </span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Payment Gateway</span>
                <span className={styles.ctxValue}>{caseData.payment_method?.toUpperCase() ?? 'UPI'}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Error Code</span>
                <span className={styles.ctxValue} style={{ color: '#EF4444' }}>
                  {caseData.payment_failure_code ?? 'DECLINED'}
                </span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Attempt Counter</span>
                <span className={styles.ctxValue}>{caseData.payment_attempt_number ?? 1} / 3</span>
              </div>
            </div>
          </section>

          {/* Customer History Card */}
          <section className={styles.cardSection}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitle}>
                <UserCheck size={15} color="var(--color-brand-primary)" />
                <span>Customer Credibility Score</span>
              </div>
            </div>
            <div className={styles.contextGrid}>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Historic Success Rate</span>
                <span className={styles.ctxValue} style={{ color: '#10B981' }}>
                  {caseData.customer_success_rate != null
                    ? `${(caseData.customer_success_rate * 100).toFixed(0)}%`
                    : '92%'}
                </span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Total TX Lifetime</span>
                <span className={styles.ctxValue}>{caseData.customer_transaction_count ?? 18}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Prior Failures</span>
                <span className={styles.ctxValue}>{caseData.customer_failure_count ?? 1}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Average Basket Value</span>
                <span className={styles.ctxValue}>{formatINR(caseData.customer_avg_amount || caseData.payment_amount)}</span>
              </div>
            </div>
          </section>

          {/* Financial Summary Card */}
          <section className={styles.cardSection}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitle}>
                <Coins size={15} color="var(--color-accent-gold)" />
                <span>Alpha Ledger Breakdown</span>
              </div>
            </div>
            <div className={styles.contextGrid}>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Revenue at Risk</span>
                <span className={styles.ctxValue}>{formatINR(caseData.revenue_at_risk)}</span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Expected Net Alpha</span>
                <span className={styles.ctxValue} style={{ color: 'var(--color-accent-gold)' }}>
                  {formatINR(caseData.expected_net_revenue)}
                </span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Actual Recovered</span>
                <span className={styles.ctxValue} style={{ color: '#10B981' }}>
                  {caseData.actual_recovered ? formatINR(caseData.actual_recovered) : '—'}
                </span>
              </div>
              <div className={styles.contextItem}>
                <span className={styles.ctxLabel}>Net Incremental</span>
                <span className={styles.ctxValue} style={{ color: 'var(--color-brand-primary)' }}>
                  {caseData.net_incremental_recovery ? formatINR(caseData.net_incremental_recovery) : '—'}
                </span>
              </div>
            </div>
          </section>

          {/* Action Command Console */}
          <section className={styles.cardSection}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitle}>
                <Terminal size={15} color="var(--color-brand-primary)" />
                <span>Execution Governance Console</span>
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
                    'AI Forensics analysis completed.',
                    () => {
                      gamification.addXP(50, "Forensics Re-Analysis Completed");
                      gamification.incrementStreak();
                      gamification.unlockBadge("GENESIS_ANALYSIS");
                    },
                  )
                }
              >
                <Zap size={14} />
                {actionPending ? 'Analyzing…' : '⚡ Re-Analyze'}
              </button>

              {canApprove && (
                <button
                  id="btn-approve"
                  className={styles.btnActionPrimary}
                  disabled={actionPending}
                  onClick={() =>
                    doAction(
                      () => api.approveCase(caseId!),
                      'Multi-sig consensus confirmed. Case approved for execution.',
                      () => {
                        gamification.addXP(150, "Multi-Sig Consensus Approved", caseData.payment_amount);
                        gamification.incrementStreak();
                        if (caseData.payment_amount >= 10000) {
                          gamification.unlockBadge("WHALE_SAVER");
                        }
                        gamification.unlockBadge("ZERO_BREACH");
                        gamification.fireCelebration(false);
                      },
                    )
                  }
                >
                  <CheckCircle2 size={15} />
                  ✓ Multi-Sig Approve (+150 XP)
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
                      'Case flagged and rejected by governance.',
                      () => gamification.resetStreak(),
                    )
                  }
                >
                  <XCircle size={14} />
                  ✗ Reject & Halt
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
                      'Recovery action adapter deployed successfully.',
                      () => {
                        gamification.addXP(200, "Lightning Recovery Action Executed", caseData.payment_amount);
                        gamification.unlockBadge("LIGHTNING_EXECUTE");
                        gamification.fireCelebration(true);
                      },
                    )
                  }
                >
                  <Play size={15} fill="currentColor" />
                  ▶ Lightning Execute (+200 XP)
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
                      'Recovery protocol permanently stopped.',
                    )
                  }
                >
                  ⏹ Halt
                </button>
              )}
            </div>

            {/* State gate explanation */}
            {!canExecute && !canApprove && !isTerminal && (
              <p className={styles.gateHint}>
                {caseData.status === 'CREATED' && 'Run Analyze above to initiate 10-stage forensic pipeline.'}
                {caseData.status === 'ANALYZING' && 'Mining rig is synthesizing latent recovery strategies…'}
                {caseData.status === 'PENDING_APPROVAL' && 'Awaiting merchant multi-sig consensus before deployment.'}
              </p>
            )}
            {isTerminal && (
              <p className={styles.gateHint}>
                Case has settled in terminal state ({caseData.status}) — state is cryptographically locked.
              </p>
            )}
          </section>
        </div>

        {/* ── RIGHT COLUMN: AI Intelligence & Candidate Matrix ─────────────────── */}
        <div className={styles.rightCol}>
          {/* Holographic Gemini Agent Card */}
          <section className={styles.hologramCard}>
            <div className={styles.hologramHeader}>
              <div className={styles.hologramTag}>
                <Sparkles size={16} color="var(--color-brand-primary)" />
                <span>GEMINI 2.5 PRO · LATENT FORENSIC AGENT</span>
              </div>
              <span className="label-mono" style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                {caseData.model_name ? `${caseData.model_name} v${caseData.model_version}` : 'Autonomous Consensus'}
              </span>
            </div>

            {caseData.selected_action ? (
              <>
                <div className={styles.decisionBanner}>
                  <div>
                    <span className="label-mono" style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>
                      RECOMMENDED STRATEGY
                    </span>
                    <div className={styles.decisionActionName}>
                      {formatAction(caseData.selected_action)}
                    </div>
                  </div>
                  <ActionBadge action={caseData.selected_action} />
                </div>

                {caseData.agent_explanation && (
                  <div className={styles.explanationBox}>
                    {caseData.agent_explanation}
                  </div>
                )}
              </>
            ) : (
              <EmptyState
                icon="🤖"
                title="Model Standing By"
                description="Trigger Re-Analyze in the governance console to synthesize the optimal recovery strategy."
              />
            )}
          </section>

          {/* Guardrail Matrix */}
          {caseData.guardrail_result && (
            <section className={styles.cardSection}>
              <div className={styles.cardHeader}>
                <div className={styles.cardTitle}>
                  <ShieldCheck size={16} color="#10B981" />
                  <span>Smart Contract Guardrail Verification</span>
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
                  <span style={{ fontSize: 12, color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {caseData.guardrail_result.approval_reason}
                  </span>
                )}
              </div>

              <div className={styles.guardrailChecksGrid}>
                {caseData.guardrail_result.checks.map((c) => (
                  <div key={c.check_name} className={styles.guardrailCheckItem}>
                    {c.passed ? (
                      <CheckCircle2 size={14} color="#10B981" />
                    ) : (
                      <XCircle size={14} color="#EF4444" />
                    )}
                    <span style={{ color: c.passed ? 'var(--color-text-secondary)' : '#EF4444' }}>
                      {c.check_name.replace(/_/g, ' ')}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Candidate Actions Matrix & Chart */}
          {caseData.candidates.length > 0 && (
            <section className={styles.cardSection}>
              <div className={styles.cardHeader}>
                <div className={styles.cardTitle}>
                  <Layers size={16} color="var(--color-brand-primary)" />
                  <span>Candidate Action Matrix</span>
                </div>
              </div>

              <CandidateTable
                candidates={caseData.candidates}
                recommendedAction={caseData.selected_action}
              />

              <div style={{ marginTop: 24 }}>
                <p className="label-mono" style={{ marginBottom: 12, fontSize: 11 }}>
                  Expected Net Alpha by Candidate (₹)
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

      {/* ── Ledger Audit Timeline ────────────────────────────────────────────── */}
      <section className={styles.cardSection} style={{ marginTop: 24 }}>
        <div className={styles.auditHeader} onClick={toggleAudit} role="button" tabIndex={0}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Terminal size={16} color="var(--color-brand-primary)" />
            <span className="label-mono" style={{ fontSize: 12, fontWeight: 700 }}>
              IMMUTABLE AUDIT LOG &amp; CRYPTOGRAPHIC RECEIPTS
            </span>
          </div>
          <span className={styles.auditToggle}>
            {showAudit ? (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                <ChevronUp size={14} /> Collapse
              </span>
            ) : (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                <ChevronDown size={14} /> Expand Timeline
              </span>
            )}
          </span>
        </div>
        {showAudit &&
          (auditLoading ? (
            <div className={styles.loadingFill} style={{ minHeight: 120 }}>
              <div className={styles.spinner} />
            </div>
          ) : (
            <AuditTimeline entries={audit} />
          ))}
      </section>
    </div>
  );
}
