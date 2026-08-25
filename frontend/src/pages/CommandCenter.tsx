/**
 * RecoveryOS — Command Center (Dashboard) Page
 *
 * The primary financial overview page.
 * Shows: Revenue At Risk, Revenue Recovered, Incremental Recovery,
 * Net Incremental Recovery, Intervention Spend, Recovery Rate.
 *
 * Charts and full metrics are populated in Phase 10.
 * Phase 1 shows the layout skeleton with loading states.
 */

import { useEffect, useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatINR, formatPercent } from '../services/api';
import type { DashboardSummary } from '../types';
import styles from './CommandCenter.module.css';

interface MetricCardProps {
  label: string;
  value: string;
  subValue?: string;
  subLabel?: string;
  featured?: boolean;
  loading?: boolean;
}

function MetricCard({ label, value, subValue, subLabel, featured, loading }: MetricCardProps) {
  return (
    <div className={`card ${featured ? 'card--featured' : ''} ${styles.metricCard}`}>
      <p className={`label-mono ${styles.metricLabel}`}>{label}</p>
      {loading ? (
        <div className={styles.skeleton} aria-hidden="true" />
      ) : (
        <>
          <p className={`metric-number ${styles.metricValue}`}>{value}</p>
          {subValue && (
            <p className={styles.metricSub}>
              {subLabel && <span className={styles.metricSubLabel}>{subLabel} </span>}
              {subValue}
            </p>
          )}
        </>
      )}
    </div>
  );
}

export function CommandCenter() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    api.getDashboardSummary()
      .then((data) => {
        if (!cancelled) {
          setSummary(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message ?? 'Failed to load dashboard');
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, []);

  const pending = summary?.pending_approval_count ?? 0;

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Command Center"
        title="Revenue Recovery Overview"
        subtitle="Real-time financial impact of AI-powered payment recovery"
        actions={
          pending > 0 ? (
            <a href="/recovery-queue?status=PENDING_APPROVAL" className="btn btn--primary" id="btn-pending-approvals">
              {pending} Pending Approval{pending !== 1 ? 's' : ''}
            </a>
          ) : undefined
        }
      />

      <div className={styles.content}>
        {error && (
          <div className={`card ${styles.errorCard}`} role="alert">
            <p>{error}</p>
            <button className="btn btn--secondary" onClick={() => window.location.reload()}>
              Retry
            </button>
          </div>
        )}

        {/* ── Primary Metrics Row ── */}
        <section className={styles.section} aria-label="Primary financial metrics">
          <p className={`label-mono ${styles.sectionLabel}`}>Financial Impact</p>
          <div className={styles.metricsGrid}>
            <MetricCard
              label="Revenue at Risk"
              value={loading ? '—' : formatINR(summary?.revenue_at_risk)}
              subLabel="Total cases"
              subValue={loading ? '—' : String(summary?.total_cases ?? 0)}
              featured
              loading={loading}
            />
            <MetricCard
              label="AI Recovered"
              value={loading ? '—' : formatINR(summary?.revenue_recovered)}
              subLabel="Rate"
              subValue={loading ? '—' : formatPercent(summary?.recovery_rate ?? 0)}
              featured
              loading={loading}
            />
            <MetricCard
              label="Baseline Recovered"
              value={loading ? '—' : formatINR(summary?.baseline_recovered)}
              subLabel="Rate"
              subValue={loading ? '—' : formatPercent(summary?.baseline_recovery_rate ?? 0)}
              loading={loading}
            />
            <MetricCard
              label="Incremental Recovery"
              value={loading ? '—' : formatINR(summary?.incremental_recovery)}
              subLabel="vs Baseline"
              subValue={loading ? '—' : 'AI - Baseline'}
              loading={loading}
            />
            <MetricCard
              label="Net Incremental"
              value={loading ? '—' : formatINR(summary?.net_incremental_recovery)}
              subLabel="After costs"
              subValue={loading ? '—' : `Spend: ${formatINR(summary?.intervention_spend)}`}
              loading={loading}
            />
            <MetricCard
              label="Intervention Spend"
              value={loading ? '—' : formatINR(summary?.intervention_spend)}
              loading={loading}
            />
          </div>
        </section>

        <hr className="editorial-rule" />

        {/* ── Guardrail Stats ── */}
        <section className={styles.section} aria-label="Guardrail statistics">
          <p className={`label-mono ${styles.sectionLabel}`}>Guardrail Activity</p>
          <div className={styles.guardrailGrid}>
            <div className={styles.guardrailStat}>
              <p className={`metric-number ${styles.guardrailValue}`}>
                {loading ? '—' : summary?.guardrail_stops ?? 0}
              </p>
              <p className={styles.guardrailLabel}>Guardrail Stops</p>
            </div>
            <div className={styles.guardrailStat}>
              <p className={`metric-number ${styles.guardrailValue}`}>
                {loading ? '—' : summary?.escalations ?? 0}
              </p>
              <p className={styles.guardrailLabel}>Escalations</p>
            </div>
            <div className={styles.guardrailStat}>
              <p className={`metric-number ${styles.guardrailValue}`}>
                {loading ? '—' : summary?.do_nothing_count ?? 0}
              </p>
              <p className={styles.guardrailLabel}>Do Nothing</p>
            </div>
            <div className={styles.guardrailStat}>
              <p className={`metric-number ${styles.guardrailValue}`}>
                {loading ? '—' : pending}
              </p>
              <p className={styles.guardrailLabel}>Pending Approval</p>
            </div>
          </div>
        </section>

        <hr className="editorial-rule" />

        {/* Phase 10 placeholder for charts */}
        <section className={styles.section} aria-label="Recovery trend charts (Phase 10)">
          <p className={`label-mono ${styles.sectionLabel}`}>Recovery Trends</p>
          <div className={styles.chartPlaceholder}>
            <p className={styles.chartPlaceholderText}>
              Recovery trend charts — Recharts visualizations wired in Phase 10
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
