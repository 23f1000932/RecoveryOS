/**
 * RecoveryOS — Policies Page
 * View current merchant recovery policy configuration.
 * Policy is read from YAML — not editable via UI (intentional).
 */

import { useEffect, useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatINR } from '../services/api';
import type { PolicyView } from '../types';
import styles from './PoliciesPage.module.css';

export function PoliciesPage() {
  const [policy, setPolicy] = useState<PolicyView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getPolicy()
      .then((p) => { setPolicy(p); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, []);

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Policies"
        title="Recovery Policy Configuration"
        subtitle="Authoritative guardrail rules. These values are enforced deterministically — not negotiable by AI."
      />

      <div className={styles.content}>
        {loading && <div className={styles.loadingText}>Loading policy…</div>}
        {error && <div className={`card ${styles.errorCard}`} role="alert">{error}</div>}

        {policy && (
          <>
            <div className={styles.versionRow}>
              <span className="label-mono">Policy Version</span>
              <code className={styles.version}>{policy.version}</code>
            </div>

            <div className={styles.grid}>
              <PolicyRow label="Max Retries / Customer" value={String(policy.max_retries_per_customer)} unit="retries" />
              <PolicyRow label="Max Messages / Customer" value={String(policy.max_messages_per_customer)} unit="messages" />
              <PolicyRow label="Max Incentive / Customer" value={formatINR(policy.max_incentive_per_customer)} />
              <PolicyRow label="Daily Incentive Pool" value={formatINR(policy.daily_incentive_pool)} unit="per day" />
              <PolicyRow label="High-Value Threshold" value={formatINR(policy.high_value_threshold)} unit="requires approval" />
              <PolicyRow label="Recovery Window" value={String(policy.recovery_window_hours)} unit="hours" />
              <PolicyRow label="Min Expected Net Revenue" value={formatINR(policy.min_expected_net_revenue)} unit="to act" />
              <PolicyRow label="Min Model Confidence" value={`${(policy.min_model_confidence * 100).toFixed(0)}%`} />
              <PolicyRow label="Auto-Action Threshold" value={`${(policy.auto_action_probability * 100).toFixed(0)}%`} unit="confidence" />
            </div>

            <div className={`card ${styles.notice}`}>
              <p className="label-mono">Read-Only</p>
              <p>
                To change policy values, edit <code>policies/recovery_policy.yaml</code> and restart the backend.
                All changes are logged in the audit trail.
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function PolicyRow({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className={`card ${styles.policyRow}`}>
      <p className={`label-mono ${styles.policyLabel}`}>{label}</p>
      <div className={styles.policyValueRow}>
        <p className={`metric-number ${styles.policyValue}`}>{value}</p>
        {unit && <span className={styles.policyUnit}>{unit}</span>}
      </div>
    </div>
  );
}
