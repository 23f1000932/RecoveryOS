/**
 * RecoveryOS — Recovery Queue Page
 * Lists all active recovery cases. Filter by status.
 * Fully implemented in Phase 10.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CaseStatusBadge, ActionBadge } from '../components/controls/StatusBadge';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatINR } from '../services/api';
import type { CaseStatus, RecoveryCaseSummary } from '../types';
import styles from './RecoveryQueue.module.css';

const STATUS_FILTERS: { label: string; value: CaseStatus | '' }[] = [
  { label: 'All', value: '' },
  { label: 'Pending Approval', value: 'PENDING_APPROVAL' },
  { label: 'Decision Ready', value: 'DECISION_READY' },
  { label: 'Executing', value: 'EXECUTING' },
  { label: 'Recovered', value: 'RECOVERED' },
  { label: 'Failed', value: 'FAILED' },
];

export function RecoveryQueue() {
  const [cases, setCases] = useState<RecoveryCaseSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<CaseStatus | ''>('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.listCases({ status: statusFilter || undefined })
      .then((data) => {
        if (!cancelled) {
          setCases(data.cases);
          setTotal(data.total);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [statusFilter]);

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Recovery Queue"
        title="Active Recovery Cases"
        subtitle={`${total} total cases`}
      />

      <div className={styles.content}>
        {/* Status filter tabs */}
        <div className={styles.filters} role="tablist" aria-label="Filter cases by status">
          {STATUS_FILTERS.map(({ label, value }) => (
            <button
              key={value || 'all'}
              id={`filter-${value || 'all'}`}
              role="tab"
              aria-selected={statusFilter === value}
              className={`btn btn--ghost ${styles.filterTab} ${statusFilter === value ? styles.filterTabActive : ''}`}
              onClick={() => setStatusFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>

        {error && (
          <div className={`card ${styles.errorCard}`} role="alert">{error}</div>
        )}

        {loading ? (
          <div className={styles.loadingState} aria-label="Loading cases">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className={`card ${styles.skeletonRow}`} aria-hidden="true" />
            ))}
          </div>
        ) : cases.length === 0 ? (
          <div className={`card ${styles.emptyState}`}>
            <p className={styles.emptyStateText}>No recovery cases found.</p>
            <p className={styles.emptyStateHint}>
              Cases appear here when a failed payment triggers the RecoveryPipeline.
            </p>
          </div>
        ) : (
          <div className={styles.caseList} role="list">
            {cases.map((c) => (
              <Link
                key={c.id}
                to={`/recovery-queue/${c.id}`}
                className={`card ${styles.caseRow}`}
                role="listitem"
                id={`case-row-${c.id}`}
              >
                <div className={styles.caseRowMain}>
                  <div>
                    <p className={`label-mono ${styles.caseId}`}>{c.id.slice(0, 8)}…</p>
                    <p className={styles.caseAmount}>{formatINR(c.revenue_at_risk)}</p>
                  </div>
                  <CaseStatusBadge status={c.status} />
                </div>
                <div className={styles.caseRowMeta}>
                  <span>Action: <ActionBadge action={c.selected_action} /></span>
                  {c.expected_net_revenue && (
                    <span>Expected: {formatINR(c.expected_net_revenue)}</span>
                  )}
                  <span className={styles.caseDate}>
                    {new Date(c.created_at).toLocaleDateString('en-IN')}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
