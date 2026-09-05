/**
 * RecoveryOS — Decision Audit Page (Section 27)
 *
 * Displays chronological, tamper-evident audit trail of AI recovery decisions,
 * guardrail checks, execution receipts, and payment verification outcomes.
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
  if (type.includes('executed') || type.includes('started') || type.includes('action_requested')) return 'var(--accent-primary)';
  if (type.includes('agent_') || type.includes('prediction') || type.includes('decision')) return 'var(--accent-secondary)';
  return 'var(--muted)';
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
            color: copied ? '#10B981' : 'var(--muted)',
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
        label="GOVERNANCE &amp; AUDIT"
        title={caseId ? `Case CASE-${caseId.slice(0, 8).toUpperCase()} Decision Trail` : 'Decision Audit'}
        subtitle={
          caseId
            ? `${entries.length} audited recovery events recorded for this payment case.`
            : 'Select any recovery case in the Recovery Queue to inspect its complete decision history.'
        }
      />

      {!caseId && (
        <EmptyState
          icon="📋"
          title="No Recovery Case Selected"
          description="Open any case in the Recovery Queue and click 'Decision Trail' or provide a valid case ID in the URL to inspect its complete audit timeline."
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
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--muted)' }}>
            LOADING DECISION AUDIT TRAIL…
          </span>
        </div>
      )}

      {caseId && !loading && !error && entries.length === 0 && (
        <EmptyState
          icon="⏳"
          title="Initial Case Created"
          description="No recovery events recorded yet. Run analysis or execute an intervention to append decision audit entries."
          action={{ label: 'Refresh Audit', onClick: load }}
        />
      )}

      {entries.length > 0 && (
        <>
          <div className={styles.filterBar}>
            <div className={styles.searchBox}>
              <Search size={14} color="var(--muted)" />
              <input
                className={styles.searchInput}
                type="text"
                placeholder="Filter events, models, or actors…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <span className={styles.eventCounter}>
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
