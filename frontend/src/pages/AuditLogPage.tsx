/**
 * RecoveryOS — Audit Log Page (Bitcoin DeFi Ledger Overhaul)
 *
 * Displays immutable cryptographic timeline of execution receipts and state transitions.
 */

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Search,
  Copy,
  Check,
} from 'lucide-react';
import { EmptyState } from '../components/layout/EmptyState';
import { ErrorBanner } from '../components/layout/ErrorBanner';
import { PageHeader } from '../components/layout/PageHeader';
import { api } from '../services/api';
import type { AuditLogEntry } from '../types';
import styles from './AuditLogPage.module.css';

function eventColor(type: string): string {
  if (type.includes('recovered') || type.includes('granted') || type.includes('approved')) return '#10B981';
  if (type.includes('failed') || type.includes('blocked') || type.includes('rejected')) return '#EF4444';
  if (type.includes('approval_requested') || type.includes('escalat')) return '#F59E0B';
  if (type.includes('executed') || type.includes('started') || type.includes('action_requested')) return 'var(--color-brand-primary)';
  if (type.includes('agent_')) return 'var(--color-accent-gold)';
  return 'var(--color-text-muted)';
}

function eventLabel(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function JsonViewer({ data, label }: { data: Record<string, unknown> | null; label: string }) {
  const [copied, setCopied] = useState(false);
  if (!data || !Object.keys(data).length) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={styles.snapshot}>
      <div className={styles.snapshotHeader}>
        <span className={styles.snapshotLabel}>{label}</span>
        <button
          type="button"
          onClick={handleCopy}
          style={{
            background: 'transparent',
            border: 'none',
            color: copied ? '#10B981' : 'var(--color-text-muted)',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            fontSize: 10,
            fontFamily: 'var(--font-mono)',
          }}
        >
          {copied ? <Check size={11} /> : <Copy size={11} />}
          {copied ? 'COPIED' : 'COPY'}
        </button>
      </div>
      <pre className={styles.snapshotPre}>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}

function AuditEntry({ e }: { e: AuditLogEntry }) {
  const color = eventColor(e.event_type);
  return (
    <details className={styles.entry}>
      <summary className={styles.summary}>
        <span className={styles.dot} style={{ background: color, color }} />
        <div className={styles.summaryMain}>
          <div className={styles.eventTitleRow}>
            <span className={styles.eventLabel}>{eventLabel(e.event_type)}</span>
          </div>
          <span className={styles.eventMeta}>
            ACTOR: <span className={styles.actorTag}>{e.actor}</span> · SOURCE: {e.source}
            {e.model_name && ` · ${e.model_name} v${e.model_version}`}
          </span>
        </div>
        <time className={styles.timestamp}>
          {new Date(e.timestamp).toLocaleString('en-IN', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          })}
        </time>
      </summary>
      <div className={styles.body}>
        <div className={styles.snapshotGrid}>
          <JsonViewer data={e.input_snapshot} label="Input State Snapshot" />
          <JsonViewer data={e.output_snapshot} label="Output State Snapshot" />
          {e.decision && <JsonViewer data={e.decision as Record<string, unknown>} label="Decision Vector" />}
          {e.guardrail_result && (
            <JsonViewer data={e.guardrail_result as Record<string, unknown>} label="Guardrail Outcome" />
          )}
        </div>
      </div>
    </details>
  );
}

export function AuditLogPage() {
  const { caseId } = useParams<{ caseId?: string }>();
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!caseId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    api.getCaseAudit(caseId)
      .then((r) => {
        setEntries(r.entries);
        setLoading(false);
      })
      .catch((e: Error) => {
        setError(e.message);
        setLoading(false);
      });
  }, [caseId]);

  useEffect(load, [load]);

  const displayedEntries = entries.filter((e) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      e.event_type.toLowerCase().includes(q) ||
      e.actor.toLowerCase().includes(q) ||
      e.source.toLowerCase().includes(q)
    );
  });

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Immutable Ledger"
        title={caseId ? `TX Block #${caseId.slice(0, 8).toUpperCase()} Ledger` : 'Decentralized Audit Ledger'}
        subtitle={
          caseId
            ? `${entries.length} cryptographic events verified on this case ledger`
            : 'Select any transaction in the Recovery Queue to inspect its full state history.'
        }
      />

      {!caseId && (
        <EmptyState
          icon="📋"
          title="No Transaction Case Specified"
          description="Open any case in the Tactical Recovery Queue and click 'Audit Timeline' or provide a valid case hash in the URL."
        />
      )}

      {caseId && error && (
        <div style={{ marginBottom: 16 }}>
          <ErrorBanner message={error} onRetry={load} />
        </div>
      )}

      {caseId && loading && (
        <div className={styles.loadingState}>
          <div className={styles.spinner} />
          <span className="label-mono" style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            VERIFYING IMMUTABLE AUDIT RECEIPTS…
          </span>
        </div>
      )}

      {caseId && !loading && !error && entries.length === 0 && (
        <EmptyState
          icon="⏳"
          title="Genesis Block Only"
          description="No downstream actions recorded yet. Trigger Analyze or Execution to append cryptographic events."
          action={{ label: 'Refresh Ledger', onClick: load }}
        />
      )}

      {entries.length > 0 && (
        <>
          <div className={styles.filterBar}>
            <div className={styles.searchBox}>
              <Search size={14} color="var(--color-text-muted)" />
              <input
                className={styles.searchInput}
                type="text"
                placeholder="Filter events or actors…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <span className="label-mono" style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
              Showing {displayedEntries.length} of {entries.length} events
            </span>
          </div>

          <div className={styles.timelineWrapper}>
            <div className={styles.rail} />
            <div className={styles.entries}>
              {displayedEntries.map((e) => (
                <AuditEntry key={e.id} e={e} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
