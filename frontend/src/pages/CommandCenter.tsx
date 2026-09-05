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

import { useEffect, useRef, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { RecoveryFunnel } from '../components/charts/RecoveryFunnel';
import { ErrorBanner } from '../components/layout/ErrorBanner';
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
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = (silent = false) => {
    if (!silent) setLoading(true);
    api.getDashboardSummary()
      .then((data) => {
        setSummary(data);
        setLastRefreshed(new Date());
        if (!silent) setLoading(false);
      })
      .catch((err) => {
        setError(err.message ?? 'Failed to load dashboard');
        if (!silent) setLoading(false);
      });
  };

  useEffect(() => {
    load();
    timerRef.current = setInterval(() => load(true), 30_000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pending = summary?.pending_approval_count ?? 0;

  // Mini chart data: Baseline vs AI (from last experiment if available)
  const comparisonData = summary ? [
    { name: 'Baseline', value: parseFloat(summary.baseline_recovered) || 0, fill: 'hsl(210,50%,45%)' },
    { name: 'AI Recovered', value: parseFloat(summary.revenue_recovered) || 0, fill: 'hsl(35,85%,60%)' },
    { name: 'Net Increment', value: parseFloat(summary.net_incremental_recovery) || 0, fill: 'hsl(140,50%,45%)' },
  ] : [];

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Command Center"
        title="Revenue Recovery Overview"
        subtitle={
          lastRefreshed
            ? `Real-time financial impact · Last updated ${lastRefreshed.toLocaleTimeString()}`
            : 'Real-time financial impact of AI-powered payment recovery'
        }
        actions={
          pending > 0 ? (
            <a href="/recovery-queue" className="btn btn--primary" id="btn-pending-approvals">
              {pending} Pending Approval{pending !== 1 ? 's' : ''}
            </a>
          ) : undefined
        }
      />

      <div className={styles.content}>
        {error && (
          <div style={{ marginBottom: 16 }}>
            <ErrorBanner message={error} onRetry={() => load()} />
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

        {/* ── Recovery Trajectory & Funnel (design.md §20) ── */}
        <section className={styles.section} aria-label="Recovery analysis">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24 }}>
            <div>
              <p className={`label-mono ${styles.sectionLabel}`}>Recovery Comparison</p>
              {comparisonData.length > 0 ? (
                <div style={{ height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={comparisonData} margin={{ top: 4, right: 16, bottom: 4, left: 16 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(0,0%,14%)" vertical={false} />
                      <XAxis dataKey="name" tick={{ fill: '#888', fontSize: 12 }} axisLine={false} tickLine={false} />
                      <YAxis
                        tick={{ fill: '#666', fontSize: 11 }}
                        tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        formatter={(v: any) => [
                          new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(v) || 0),
                          ''
                        ]}
                        contentStyle={{ background: 'hsl(0,0%,10%)', border: '1px solid hsl(0,0%,18%)', borderRadius: 8, fontSize: 13 }}
                      />
                      <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                        {comparisonData.map((entry) => (
                          <Cell key={entry.name} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p style={{ color: 'hsl(0,0%,40%)', fontSize: 13, textAlign: 'center', padding: '32px 0' }}>
                  Run a simulator experiment to see the comparison chart.
                </p>
              )}
            </div>
            <div>
              <p className={`label-mono ${styles.sectionLabel}`}>Pipeline Recovery Funnel</p>
              <RecoveryFunnel
                totalFailed={summary?.total_cases || 5}
                eligible={Math.max((summary?.total_cases || 5) - (summary?.guardrail_stops || 0), 0)}
                actioned={Math.max((summary?.total_cases || 5) - (summary?.guardrail_stops || 0) - (summary?.do_nothing_count || 0), 0)}
                recovered={Math.round((summary?.total_cases || 5) * (summary?.recovery_rate || 0.65))}
              />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
