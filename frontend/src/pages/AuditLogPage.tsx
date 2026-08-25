/**
 * RecoveryOS — Audit Log Page
 * Browse full audit timeline across all cases (Phase 10) or per-case (accessible from CaseDetail).
 * Phase 1: Page skeleton with structure.
 */

import { PageHeader } from '../components/layout/PageHeader';
import styles from './AuditLogPage.module.css';

export function AuditLogPage() {
  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Audit Log"
        title="Decision Audit Trail"
        subtitle="Every pipeline event, guardrail check, and decision recorded immutably."
      />

      <div className={styles.content}>
        <div className={`card ${styles.notice}`}>
          <p className="label-mono">Audit Log Browser</p>
          <p className={styles.noticeText}>
            The per-case audit timeline is available on each{' '}
            <a href="/recovery-queue">Recovery Case detail page</a>.
            A full cross-case audit browser with filtering by event type, actor, and time range
            will be implemented in Phase 10.
          </p>
        </div>

        {/* Placeholder audit entries for structure */}
        <div className={styles.legend}>
          <p className={`label-mono ${styles.legendTitle}`}>Audit Event Types</p>
          <div className={styles.legendGrid}>
            {[
              { type: 'payment_failed', desc: 'Webhook received, case created' },
              { type: 'context_loaded', desc: 'Customer + payment context assembled' },
              { type: 'predictions_generated', desc: 'ML model scored all 6 actions' },
              { type: 'optimization_completed', desc: 'EV optimizer ranked candidates' },
              { type: 'guardrail_passed', desc: 'All guardrail checks passed' },
              { type: 'guardrail_blocked', desc: 'One or more actions blocked' },
              { type: 'approval_requested', desc: 'High-value case sent for review' },
              { type: 'approval_granted', desc: 'Merchant approved execution' },
              { type: 'action_executed', desc: 'Recovery action dispatched' },
              { type: 'payment_recovered', desc: 'Payment confirmed successful' },
              { type: 'agent_explanation', desc: 'Gemini generated reasoning' },
            ].map(({ type, desc }) => (
              <div key={type} className={`card ${styles.legendEntry}`}>
                <code className={styles.eventType}>{type}</code>
                <p className={styles.eventDesc}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
