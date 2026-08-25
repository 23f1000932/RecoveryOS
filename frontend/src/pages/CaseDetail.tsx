/**
 * RecoveryOS — Case Detail Page
 * Full case view. Approve/reject/execute/stop controls.
 * Agent explanation, audit log, action candidates.
 * Fully implemented in Phase 10 (after Phases 7 + 9 create real data).
 */

import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CaseStatusBadge, ActionBadge, ApprovalBadge } from '../components/controls/StatusBadge';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatINR, formatPercent } from '../services/api';
import type { RecoveryCaseDetail as CaseDetail } from '../types';
import styles from './CaseDetail.module.css';

export function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);

  const load = () => {
    if (!caseId) return;
    setLoading(true);
    api.getCase(caseId)
      .then((d) => { setCaseData(d); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  };

  useEffect(load, [caseId]);

  const handleApprove = async () => {
    if (!caseId || actionPending) return;
    setActionPending(true);
    try {
      await api.approveCase(caseId);
      load();
    } finally {
      setActionPending(false);
    }
  };

  const handleReject = async () => {
    if (!caseId || actionPending) return;
    setActionPending(true);
    try {
      await api.rejectCase(caseId);
      load();
    } finally {
      setActionPending(false);
    }
  };

  const handleStop = async () => {
    if (!caseId || actionPending) return;
    setActionPending(true);
    try {
      await api.stopCase(caseId);
      load();
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
        <div className={styles.content}>
          <div className={`card ${styles.errorCard}`} role="alert">
            {error ?? 'Case not found'}
            <button className="btn btn--secondary" onClick={() => navigate(-1)}>← Back</button>
          </div>
        </div>
      </div>
    );
  }

  const isPendingApproval = caseData.status === 'PENDING_APPROVAL';
  const canStop = !['RECOVERED', 'STOPPED', 'ESCALATED', 'FAILED', 'EXPIRED'].includes(caseData.status);

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Recovery Case"
        title={`₹${parseFloat(caseData.revenue_at_risk || '0').toLocaleString('en-IN')}`}
        subtitle={`${caseData.payment_method} · ${caseData.payment_failure_code} · Attempt ${caseData.payment_attempt_number}`}
        actions={
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {isPendingApproval && (
              <>
                <button
                  id="btn-approve-case"
                  className="btn btn--primary"
                  onClick={handleApprove}
                  disabled={actionPending}
                >
                  Approve
                </button>
                <button
                  id="btn-reject-case"
                  className="btn btn--secondary"
                  onClick={handleReject}
                  disabled={actionPending}
                >
                  Reject
                </button>
              </>
            )}
            {canStop && (
              <button
                id="btn-stop-case"
                className="btn btn--ghost"
                onClick={handleStop}
                disabled={actionPending}
              >
                Stop
              </button>
            )}
          </div>
        }
      />

      <div className={styles.content}>
        {/* Status row */}
        <div className={styles.statusRow}>
          <CaseStatusBadge status={caseData.status} />
          <ApprovalBadge status={caseData.approval_status} />
          <span className="label-mono">{caseData.model_name ?? '—'} {caseData.model_version ?? ''}</span>
        </div>

        <div className={styles.twoCol}>
          {/* Left: Decision */}
          <section className={`card ${styles.section}`} aria-label="Decision">
            <p className={`label-mono ${styles.sectionTitle}`}>Recommended Action</p>
            <div className={styles.decisionDisplay}>
              <ActionBadge action={caseData.selected_action} />
              {caseData.expected_net_revenue && (
                <p className={styles.decisionMetric}>
                  Expected Net Revenue: <strong>{formatINR(caseData.expected_net_revenue)}</strong>
                </p>
              )}
              {caseData.actual_recovered && (
                <p className={styles.decisionMetric}>
                  Actual Recovered: <strong>{formatINR(caseData.actual_recovered)}</strong>
                </p>
              )}
            </div>
          </section>

          {/* Right: Payment context */}
          <section className={`card ${styles.section}`} aria-label="Payment context">
            <p className={`label-mono ${styles.sectionTitle}`}>Payment Details</p>
            <dl className={styles.detailList}>
              <dt>Amount</dt><dd>{formatINR(caseData.payment_amount)}</dd>
              <dt>Method</dt><dd>{caseData.payment_method}</dd>
              <dt>Failure</dt><dd><code>{caseData.payment_failure_code}</code></dd>
              <dt>External ID</dt><dd><code className={styles.externalId}>{caseData.external_payment_id}</code></dd>
              <dt>Attempts</dt><dd>{caseData.payment_attempt_number}</dd>
            </dl>
          </section>
        </div>

        {/* Customer context */}
        <section className={`card ${styles.section}`} aria-label="Customer context">
          <p className={`label-mono ${styles.sectionTitle}`}>Customer Profile</p>
          <dl className={styles.detailList}>
            <dt>Transactions</dt><dd>{caseData.customer_transaction_count}</dd>
            <dt>Success Rate</dt><dd>{formatPercent(caseData.customer_success_rate)}</dd>
            <dt>Avg Amount</dt><dd>{formatINR(caseData.customer_avg_amount)}</dd>
            <dt>Preferred Method</dt><dd>{caseData.customer_preferred_method}</dd>
          </dl>
        </section>

        {/* Agent explanation */}
        {caseData.agent_explanation && (
          <section className={`card ${styles.section}`} aria-label="Agent explanation">
            <p className={`label-mono ${styles.sectionTitle}`}>AI Reasoning</p>
            <p className={styles.agentText}>{caseData.agent_explanation}</p>
          </section>
        )}

        {/* Action candidates */}
        {caseData.candidates.length > 0 && (
          <section aria-label="Action candidates">
            <p className={`label-mono ${styles.sectionTitle}`} style={{ marginBottom: '1rem' }}>
              All Candidates
            </p>
            <div className={styles.candidateList}>
              {caseData.candidates.map((c) => (
                <div
                  key={c.action}
                  className={`card ${styles.candidateCard} ${c.action === caseData.selected_action ? styles.candidateSelected : ''}`}
                >
                  <div className={styles.candidateTop}>
                    <ActionBadge action={c.action} />
                    <span className={`label-mono ${styles.candidateRank}`}>#{c.rank + 1}</span>
                  </div>
                  <dl className={styles.candidateMeta}>
                    <dt>P(success)</dt><dd>{(c.probability * 100).toFixed(1)}%</dd>
                    <dt>Expected Net</dt><dd>{formatINR(c.expected_net_revenue)}</dd>
                    <dt>Allowed</dt><dd>{c.allowed ? 'Yes' : `No — ${c.blocked_reason ?? '—'}`}</dd>
                  </dl>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Guardrail results placeholder */}
        <div className={`card ${styles.section} ${styles.phaseNotice}`}>
          <p className="label-mono">Audit Log</p>
          <p>Full audit timeline and guardrail check details available in Phase 10.</p>
        </div>
      </div>
    </div>
  );
}
