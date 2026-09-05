/**
 * RecoveryOS — Recovery Queue
 * Operational pipeline of failed payments requiring analysis, intervention, or approval.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RotateCcw,
  Search,
  ShieldAlert,
  ArrowRight,
} from 'lucide-react';
import { CaseStatusBadge, ActionBadge } from '../components/controls/StatusBadge';
import { EmptyState } from '../components/layout/EmptyState';
import { ErrorBanner } from '../components/layout/ErrorBanner';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatINR } from '../services/api';
import type { RecoveryCaseSummary } from '../types';
import styles from './RecoveryQueue.module.css';

const STATUS_TABS: { label: string; value: string }[] = [
  { label: 'All',              value: '' },
  { label: 'Analyzing',        value: 'CREATED,ANALYZING' },
  { label: 'Decision Ready',   value: 'DECISION_READY' },
  { label: 'Pending Approval', value: 'PENDING_APPROVAL' },
  { label: 'Approved',         value: 'APPROVED' },
  { label: 'Recovered',        value: 'RECOVERED' },
  { label: 'Stopped',          value: 'STOPPED' },
  { label: 'Failed',           value: 'FAILED' },
];

const REFRESH_INTERVAL_MS = 15_000;
const PAGE_SIZE = 20;

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
        <span className={styles.caseId}>CASE-{c.id.slice(0, 8).toUpperCase()}</span>
      </td>
      <td>
        <CaseStatusBadge status={c.status} />
      </td>
      <td className={styles.tdAmount}>
        {formatINR(c.revenue_at_risk)}
      </td>
      <td>
        {c.selected_action ? (
          <ActionBadge action={c.selected_action} />
        ) : (
          <span className={styles.dash}>—</span>
        )}
      </td>
      <td className={styles.tdEnr}>
        {c.expected_net_revenue ? (
          formatINR(c.expected_net_revenue)
        ) : (
          <span className={styles.dash}>—</span>
        )}
      </td>
      <td className={styles.tdConf}>
        {c.model_confidence != null ? (
          <div className={styles.confBar}>
            <span
              className={styles.confDot}
              style={{
                background:
                  c.model_confidence >= 0.75
                    ? 'var(--success-text)'
                    : c.model_confidence >= 0.55
                    ? '#F59E0B'
                    : '#EF4444',
              }}
            />
            <span>{(c.model_confidence * 100).toFixed(0)}%</span>
          </div>
        ) : (
          <span className={styles.dash}>—</span>
        )}
      </td>
      <td>
        {c.requires_approval ? (
          <span className={styles.approvalBadge}>
            <ShieldAlert size={12} />
            Approval Required
          </span>
        ) : (
          <span className={styles.dash}>Automatic</span>
        )}
      </td>
      <td className={styles.tdTime}>
        {new Date(c.created_at).toLocaleString('en-IN', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })}
      </td>
      <td style={{ textAlign: 'right' }}>
        <span className={styles.inspectLink}>
          Inspect <ArrowRight size={13} />
        </span>
      </td>
    </tr>
  );
}

export function RecoveryQueue() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<RecoveryCaseSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);

    try {
      const params: { status?: string; page?: number; page_size?: number } = {
        page,
        page_size: PAGE_SIZE,
      };

      const statuses = statusFilter ? statusFilter.split(',') : [];
      if (statuses.length === 1) params.status = statuses[0];

      const res = await api.listCases(params);
      let filtered = res.cases;

      if (statuses.length > 1) {
        filtered = res.cases.filter((c) => statuses.includes(c.status));
      }

      setCases(filtered);
      setTotal(statuses.length > 1 ? filtered.length : res.total);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    load();
    timerRef.current = setInterval(() => load(true), REFRESH_INTERVAL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [load]);

  const handleFilterChange = (v: string) => {
    setStatusFilter(v);
    setPage(1);
  };

  const handleInspect = (caseId: string) => {
    navigate(`/recovery-queue/${caseId}`);
  };

  // Client-side search filter by ID or amount
  const displayedCases = cases.filter((c) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.id.toLowerCase().includes(q) ||
      c.revenue_at_risk.toString().includes(q) ||
      (c.selected_action && c.selected_action.toLowerCase().includes(q))
    );
  });

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Recovery Operations"
        title="Recovery Queue"
        subtitle={`${total.toLocaleString()} failed payment case${total !== 1 ? 's' : ''} in pipeline · auto-refreshing every 15s`}
      />

      <div className={styles.toolbar}>
        <div className={styles.topControls}>
          {/* Status Filter Tabs */}
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
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Search Box */}
            <div className={styles.searchBox}>
              <Search size={14} color="var(--muted-foreground)" />
              <input
                className={styles.searchInput}
                type="text"
                placeholder="Search case ID or amount…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Manual Sync Button */}
            <button
              className={styles.refreshBtn}
              onClick={() => load()}
              disabled={loading || refreshing}
              title="Sync recovery cases"
            >
              <RotateCcw size={12} className={refreshing ? 'animate-spin' : ''} />
              <span>{refreshing ? 'SYNCING…' : 'SYNC'}</span>
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div style={{ marginBottom: 16 }}>
          <ErrorBanner message={error} onRetry={() => load()} />
        </div>
      )}

      {loading && cases.length === 0 ? (
        <div className={styles.loadingState}>
          <div className={styles.spinner} />
          <span className="label-mono">
            LOADING RECOVERY CASES…
          </span>
        </div>
      ) : displayedCases.length === 0 ? (
        <EmptyState
          icon="📋"
          title="No Recovery Cases Found"
          description={
            searchQuery
              ? `No cases match your search "${searchQuery}".`
              : statusFilter
              ? `No cases currently in state "${statusFilter.replace(',', ' or ')}".`
              : 'No recovery cases require attention. Cases appear here when a payment fails.'
          }
          action={
            searchQuery || statusFilter
              ? {
                  label: 'Clear Filters',
                  onClick: () => {
                    setStatusFilter('');
                    setSearchQuery('');
                  },
                }
              : undefined
          }
        />
      ) : (
        <>
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>Status</th>
                  <th>Revenue at Risk</th>
                  <th>Recommended Action</th>
                  <th>Expected Net Revenue</th>
                  <th>Confidence</th>
                  <th>Governance</th>
                  <th>Created At</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {displayedCases.map((c) => (
                  <CaseRow
                    key={c.id}
                    c={c}
                    onClick={() => handleInspect(c.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className={styles.pagination}>
              <button
                className={styles.pageBtn}
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                ← Previous
              </button>
              <span className={styles.pageInfo}>
                Page {page} of {totalPages} ({total} total cases)
              </span>
              <button
                className={styles.pageBtn}
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

export default RecoveryQueue;
