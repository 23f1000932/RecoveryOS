/**
 * RecoveryOS — Audit Log Page (Phase 7 — Full Implementation)
 *
 * Shows the full audit timeline for a specific case (from URL param)
 * OR a recent global list when no case is selected.
 *
 * Each entry: event_type, actor, source, timestamp,
 * expandable input/output snapshots.
 */

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { EmptyState } from '../components/layout/EmptyState';
import { ErrorBanner } from '../components/layout/ErrorBanner';
import { PageHeader } from '../components/layout/PageHeader';
import { api } from '../services/api';
import type { AuditLogEntry } from '../types';
import styles from './AuditLogPage.module.css';

// ── Event type → colour ───────────────────────────────────────────────────────

function eventColor(type: string): string {
  if (type.includes('recovered') || type.includes('granted')) return 'hsl(140,50%,50%)';
  if (type.includes('failed') || type.includes('blocked') || type.includes('rejected')) return 'hsl(0,60%,55%)';
  if (type.includes('approval_requested') || type.includes('escalat')) return 'hsl(38,90%,58%)';
  if (type.includes('executed') || type.includes('started') || type.includes('action_requested')) return 'hsl(210,65%,60%)';
  if (type.includes('agent_')) return 'hsl(280,50%,60%)';
  return 'hsl(0,0%,50%)';
}

function eventLabel(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── JSON Snapshot viewer ──────────────────────────────────────────────────────

function JsonViewer({ data, label }: { data: Record<string, unknown> | null; label: string }) {
  if (!data || !Object.keys(data).length) return null;
  return (
    <div className={styles.snapshot}>
      <p className={styles.snapshotLabel}>{label}</p>
      <pre className={styles.snapshotPre}>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}

// ── Single Audit Entry ────────────────────────────────────────────────────────

function AuditEntry({ e }: { e: AuditLogEntry }) {
  return (
    <details className={styles.entry}>
      <summary className={styles.summary}>
        <span
          className={styles.dot}
          style={{ background: eventColor(e.event_type) }}
        />
        <div className={styles.summaryMain}>
          <span className={styles.eventLabel}>{eventLabel(e.event_type)}</span>
          <span className={styles.eventMeta}>
            {e.actor} · {e.source}
            {e.model_name && ` · ${e.model_name} v${e.model_version}`}
          </span>
        </div>
        <time className={styles.timestamp}>
          {new Date(e.timestamp).toLocaleString('en-IN', {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit',
          })}
        </time>
      </summary>
      <div className={styles.body}>
        <div className={styles.snapshotRow}>
          <JsonViewer data={e.input_snapshot} label="Input Snapshot" />
          <JsonViewer data={e.output_snapshot} label="Output Snapshot" />
          {e.decision && <JsonViewer data={e.decision as Record<string, unknown>} label="Decision" />}
          {e.guardrail_result && <JsonViewer data={e.guardrail_result as Record<string, unknown>} label="Guardrail" />}
        </div>
      </div>
    </details>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function AuditLogPage() {
  const { caseId } = useParams<{ caseId?: string }>();
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
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
      .then((r) => { setEntries(r.entries); setLoading(false); })
      .catch((e: Error) => { setError(e.message); setLoading(false); });
  }, [caseId]);

  useEffect(load, [load]);

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Audit Log"
        title={caseId ? `Case ${caseId.slice(0, 8)}… Timeline` : 'Audit Log'}
        subtitle={
          caseId
            ? `${entries.length} event${entries.length !== 1 ? 's' : ''} in chronological order`
            : 'Navigate to a case and click "Show Audit" to view its timeline.'
        }
      />

      {!caseId && (
        <EmptyState
          icon="📋"
          title="No case selected"
          description="Open a case from the Recovery Queue and expand the Audit Timeline section, or navigate directly to /audit/:caseId."
        />
      )}

      {caseId && error && (
        <ErrorBanner message={error} onRetry={load} />
      )}

      {caseId && loading && (
        <div className={styles.loadingState}>
          <div className={styles.spinner} />
        </div>
      )}

      {caseId && !loading && !error && entries.length === 0 && (
        <EmptyState
          icon="⏳"
          title="No audit events yet"
          description="Events are recorded as the pipeline processes the case. Run Analyze to trigger the first events."
          action={{ label: 'Refresh', onClick: load }}
        />
      )}

      {entries.length > 0 && (
        <div className={styles.timeline}>
          <div className={styles.rail} />
          <div className={styles.entries}>
            {entries.map((e) => (
              <AuditEntry key={e.id} e={e} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
