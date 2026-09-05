/**
 * RecoveryOS — AI Recovery Queue (Phase 7 — Full Implementation)
 *
 * Features:
 *   - Status filter tabs (All | Pending | Decision Ready | Approved | Recovered | Failed)
 *   - Clickable rows → Case Detail
 *   - Approval required badge
 *   - Confidence column (from model_confidence)
 *   - Pagination (page_size = 20)
 *   - Auto-refresh every 15 seconds
 *   - EmptyState + ErrorBanner consistent components
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CaseStatusBadge, ActionBadge } from '../components/controls/StatusBadge';
import { EmptyState } from '../components/layout/EmptyState';
import { ErrorBanner } from '../components/layout/ErrorBanner';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatINR } from '../services/api';
import type { RecoveryCaseSummary } from '../types';
import styles from './RecoveryQueue.module.css';

// ── Filter Tabs ───────────────────────────────────────────────────────────────

const STATUS_TABS: { label: string; value: string }[] = [
  { label: 'All',            value: '' },
  { label: '⏳ Pending',     value: 'CREATED,ANALYZING' },
  { label: '🤖 Decision',    value: 'DECISION_READY' },
  { label: '🔒 Approval',    value: 'PENDING_APPROVAL' },
  { label: '✓ Approved',     value: 'APPROVED' },
  { label: '💰 Recovered',   value: 'RECOVERED' },
  { label: '⏹ Stopped',      value: 'STOPPED' },
  { label: '✗ Failed',       value: 'FAILED' },
];

const REFRESH_INTERVAL_MS = 15_000;
const PAGE_SIZE = 20;

// ── Row ───────────────────────────────────────────────────────────────────────

function CaseRow({
  c,
  onClick,
}: {
  c: RecoveryCaseSummary;
  onClick: () => void;
}) {
  return (
    <tr className={styles.row} onClick={onClick} tabIndex={0} role="button">
      <td className={styles.tdId}>
        <span className={styles.caseId}>{c.id.slice(0, 8)}…</span>
      </td>
      <td>
        <CaseStatusBadge status={c.status} />
      </td>
      <td className={styles.tdAmount}>
        {formatINR(c.revenue_at_risk)}
      </td>
      <td>
        {c.selected_action
          ? <ActionBadge action={c.selected_action} />
          : <span className={styles.dash}>—</span>}
      </td>
      <td className={styles.tdEnr}>
        {c.expected_net_revenue ? formatINR(c.expected_net_revenue) : <span className={styles.dash}>—</span>}
      </td>
      <td className={styles.tdConf}>
        {c.model_confidence != null
          ? `${(c.model_confidence * 100).toFixed(0)}%`
          : <span className={styles.dash}>—</span>}
      </td>
      <td>
        {c.requires_approval
          ? <span className={styles.approvalBadge}>Approval</span>
          : <span className={styles.dash}>—</span>}
      </td>
      <td className={styles.tdTime}>
        {new Date(c.created_at).toLocaleString('en-IN', {
          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
        })}
      </td>
    </tr>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export function RecoveryQueue() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<RecoveryCaseSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);

    try {
      // When filter has multiple statuses, fetch all and client-filter
      // (backend only supports single status filter)
      const params: { status?: string; page?: number; page_size?: number } = {
        page,
        page_size: PAGE_SIZE,
      };

      // Use the first status in the filter for API call; multiple handled below
      const statuses = statusFilter ? statusFilter.split(',') : [];
      if (statuses.length === 1) params.status = statuses[0];

      const res = await api.listCases(params);
      let filtered = res.cases;

      // Client-side multi-status filter (e.g. "CREATED,ANALYZING")
      if (statuses.length > 1) {
        filtered = res.cases.filter((c) => statuses.includes(c.status));
      }

      setCases(filtered);
      setTotal(statuses.length > 1 ? filtered.length : res.total);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  // Initial load + auto-refresh
  useEffect(() => {
    load();
    timerRef.current = setInterval(() => load(true), REFRESH_INTERVAL_MS);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [load]);

  // Reset page when filter changes
  const handleFilterChange = (v: string) => {
    setStatusFilter(v);
    setPage(1);
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Recovery Queue"
        title="AI Recovery Cases"
        subtitle={`${total.toLocaleString()} case${total !== 1 ? 's' : ''} · refreshes every 15s`}
      />

      {/* Filter tabs */}
      <div className={styles.filterTabs} role="tablist">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            role="tab"
            aria-selected={statusFilter === tab.value}
            className={`${styles.tab} ${statusFilter === tab.value ? styles.tabActive : ''}`}
            onClick={() => handleFilterChange(tab.value)}
          >
            {tab.label}
          </button>
        ))}

        {/* Manual refresh */}
        <button
          className={styles.refreshBtn}
          onClick={() => load()}
          disabled={loading}
          aria-label="Refresh"
          title="Refresh now"
        >
          ↻
        </button>
      </div>

      {error && (
        <div style={{ marginBottom: 12 }}>
          <ErrorBanner message={error} onRetry={() => load()} />
        </div>
      )}

      {loading && cases.length === 0 ? (
        <div className={styles.loadingState}>
          <div className={styles.spinner} />
        </div>
      ) : cases.length === 0 ? (
        <EmptyState
          icon="📭"
          title="No cases found"
          description={
            statusFilter
              ? `No cases with status "${statusFilter.replace(',', ' or ')}". Try a different filter.`
              : 'No recovery cases yet. Cases appear here when a payment fails.'
          }
          action={{ label: 'Clear filter', onClick: () => handleFilterChange('') }}
        />
      ) : (
        <>
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>Status</th>
                  <th>Amount</th>
                  <th>Best Action</th>
                  <th>Exp. Net Rev.</th>
                  <th>Confidence</th>
                  <th>Approval</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((c) => (
                  <CaseRow
                    key={c.id}
                    c={c}
                    onClick={() => navigate(`/cases/${c.id}`)}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className={styles.pagination}>
              <button
                className="btn btn--ghost"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                ← Prev
              </button>
              <span className={styles.pageInfo}>
                Page {page} of {totalPages}
              </span>
              <button
                className="btn btn--ghost"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
