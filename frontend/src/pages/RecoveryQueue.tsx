/**
 * RecoveryOS — AI Recovery Queue (Bitcoin DeFi Tactical Mempool Overhaul)
 *
 * Features:
 *   - Mempool status filter tabs (All, Pending, Decision Ready, Multi-Sig Approval, Approved, Recovered, Stopped, Failed)
 *   - Real-time client-side search by Case ID or Amount
 *   - Tactical row view with cryptographic hashes, expected net revenue, and model confidence
 *   - Auto-refresh ticker every 15 seconds with manual sync
 *   - Gamification hook on inspection
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RotateCcw,
  Search,
  SlidersHorizontal,
  ShieldAlert,
  ArrowRight,
  Zap,
  CheckCircle2,
  Clock,
  Layers,
} from 'lucide-react';
import { CaseStatusBadge, ActionBadge } from '../components/controls/StatusBadge';
import { EmptyState } from '../components/layout/EmptyState';
import { ErrorBanner } from '../components/layout/ErrorBanner';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatINR } from '../services/api';
import { gamification } from '../services/gamification';
import type { RecoveryCaseSummary } from '../types';
import styles from './RecoveryQueue.module.css';

const STATUS_TABS: { label: string; value: string }[] = [
  { label: 'All Mempool',        value: '' },
  { label: '⏳ Ingesting',       value: 'CREATED,ANALYZING' },
  { label: '⚡ Decision Ready',  value: 'DECISION_READY' },
  { label: '🔒 Multi-Sig Approval', value: 'PENDING_APPROVAL' },
  { label: '✓ Approved',        value: 'APPROVED' },
  { label: '💰 Recovered Alpha', value: 'RECOVERED' },
  { label: '⏹ Halted',          value: 'STOPPED' },
  { label: '✗ Failed',          value: 'FAILED' },
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
        <div className={styles.caseIdWrapper}>
          <span className={styles.caseId}>{c.id.slice(0, 8)}…</span>
        </div>
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
                  c.model_confidence >= 0.8
                    ? '#10B981'
                    : c.model_confidence >= 0.6
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
            <ShieldAlert size={11} />
            REQUIRES MULTI-SIG
          </span>
        ) : (
          <span className={styles.dash}>Autonomous</span>
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
      <td>
        <button className={styles.inspectBtn} onClick={onClick}>
          Inspect →
        </button>
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

  // Initial load + auto-refresh
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
    gamification.addXP(25, "Forensics Investigation Initiated");
    navigate(`/cases/${caseId}`);
  };

  // Filter cases by search query (ID or amount)
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
        label="Tactical Queue"
        title="Payment Mempool & Forensics"
        subtitle={`${total.toLocaleString()} active transaction${total !== 1 ? 's' : ''} in pipeline · decentralized auto-sync every 15s`}
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
              <Search size={14} color="var(--color-text-muted)" />
              <input
                className={styles.searchInput}
                type="text"
                placeholder="Search case hash or amount…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Manual Sync Button */}
            <button
              className={styles.refreshBtn}
              onClick={() => load()}
              disabled={loading || refreshing}
              title="Sync mempool transactions"
            >
              <RotateCcw size={13} className={refreshing ? 'animate-spin' : ''} />
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
          <span className="label-mono" style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            INGESTING MEMPOOL BLOCKS…
          </span>
        </div>
      ) : displayedCases.length === 0 ? (
        <EmptyState
          icon="📭"
          title="No Transactions Found"
          description={
            searchQuery
              ? `No transactions match your query "${searchQuery}".`
              : statusFilter
              ? `No cases currently in state "${statusFilter}". Try switching filters.`
              : 'Mempool is currently clear. Failed transactions will stream in as detected.'
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
                  <th>Case Hash</th>
                  <th>Consensus Status</th>
                  <th>Revenue at Risk</th>
                  <th>Optimal Action</th>
                  <th>Expected Net Alpha</th>
                  <th>Confidence</th>
                  <th>Governance</th>
                  <th>Block Timestamp</th>
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
                ← Prev Block
              </button>
              <span className={styles.pageInfo}>
                Page {page} of {totalPages} ({total} cases)
              </span>
              <button
                className={styles.pageBtn}
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next Block →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
