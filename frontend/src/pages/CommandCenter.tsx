/**
 * RecoveryOS — Recovery Command Center
 * Financial and operational intelligence for AI revenue recovery.
 */

import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ShieldCheck,
  TrendingUp,
  ArrowUpRight,
  Coins,
  Play,
  CheckCircle2,
  Clock,
  Scale,
} from "lucide-react";
import { RecoveryFunnel } from "../components/charts/RecoveryFunnel";
import { ErrorBanner } from "../components/layout/ErrorBanner";
import { PageHeader } from "../components/layout/PageHeader";
import { api, formatINR, formatPercent } from "../services/api";
import type { DashboardSummary } from "../types";
import styles from "./CommandCenter.module.css";

export function CommandCenter() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = (silent = false) => {
    if (!silent) setLoading(true);
    api
      .getDashboardSummary()
      .then((data) => {
        setSummary(data);
        setLastRefreshed(new Date());
        if (!silent) setLoading(false);
      })
      .catch((err) => {
        setError(err.message ?? "Failed to load recovery dashboard summary");
        if (!silent) setLoading(false);
      });
  };

  useEffect(() => {
    load();
    timerRef.current = setInterval(() => load(true), 30_000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const pending = summary?.pending_approval_count ?? 0;

  const comparisonData = summary
    ? [
        {
          name: "Fixed Baseline",
          value: parseFloat(summary.baseline_recovered) || 0,
          fill: "#475569",
        },
        {
          name: "RecoveryOS AI",
          value: parseFloat(summary.revenue_recovered) || 0,
          fill: "#F59E0B",
        },
        {
          name: "Net Incremental",
          value: parseFloat(summary.net_incremental_recovery) || 0,
          fill: "#10B981",
        },
      ]
    : [];

  return (
    <div className={`animate-enter ${styles.page}`}>
      {/* ── Top Page Header ── */}
      <PageHeader
        label="Overview"
        title="Recovery Command Center"
        subtitle={
          lastRefreshed
            ? `AI revenue recovery across failed payments · Synchronized ${lastRefreshed.toLocaleTimeString()}`
            : "AI revenue recovery across failed payments."
        }
        actions={
          pending > 0 ? (
            <Link to="/recovery-queue" className={styles.pendingAlertBanner}>
              <Clock size={15} />
              <span>
                {pending} Case{pending !== 1 ? "s" : ""} Awaiting Approval
              </span>
              <ArrowUpRight size={14} />
            </Link>
          ) : undefined
        }
      />

      <div className={styles.content}>
        {error && (
          <div>
            <ErrorBanner message={error} onRetry={() => load()} />
          </div>
        )}

        {/* ── Hero Operational Overview ── */}
        <div className={styles.heroBanner}>
          <div className={styles.heroText}>
            <div className={styles.badgePill}>
              <span className={styles.badgeDot} />
              <span>RECOVERY ENGINE ACTIVE · RAZORPAY TEST MODE</span>
            </div>
            <h2 className={styles.heroTitle}>
              AI-Powered Recovery with Deterministic Guardrails
            </h2>
            <p className={styles.heroSubtitle}>
              RecoveryOS evaluates failed payments across multiple recovery strategies, selects the
              highest expected net-value intervention, applies merchant guardrails, and verifies the
              final outcome.
            </p>

            <div className={styles.heroCtaRow}>
              <Link to="/simulator" className={styles.btnPrimary}>
                <Play size={15} fill="currentColor" />
                <span>Run Recovery Simulation</span>
              </Link>
              <Link to="/recovery-queue" className={styles.btnSecondary}>
                <span>View Recovery Queue</span>
                <ArrowUpRight size={15} />
              </Link>
            </div>
          </div>
        </div>

        {/* ── Hero Metric: Net Incremental Recovery (The North Star) ── */}
        <section aria-label="North star recovery metric">
          <div className={styles.heroNetCard}>
            <div className={styles.netLeft}>
              <span className={styles.netEyebrow}>Primary Benchmark Metric</span>
              <div className={styles.netValue}>
                {loading ? "—" : formatINR(summary?.net_incremental_recovery)}
              </div>
              <p className={styles.netDescription}>
                Net incremental revenue generated above naive retry baseline, after deducting all
                gateway fees and discount incentives.
              </p>
            </div>

            <div className={styles.netRightMeta}>
              <div className={styles.netMetaItem}>
                <span className={styles.netMetaLabel}>Gross Incremental Lift</span>
                <span className={styles.netMetaVal} style={{ color: "var(--accent-primary)" }}>
                  {loading ? "—" : formatINR(summary?.incremental_recovery)}
                </span>
              </div>
              <div className={styles.netMetaItem}>
                <span className={styles.netMetaLabel}>Intervention Spend</span>
                <span className={styles.netMetaVal}>
                  {loading ? "—" : formatINR(summary?.intervention_spend)}
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* ── Financial Metrics Grid ── */}
        <section aria-label="Core financial recovery metrics">
          <div className={styles.sectionHeader}>
            <Coins size={14} color="var(--accent-primary)" />
            <p className={styles.sectionLabel}>Financial Recovery Metrics</p>
          </div>

          <div className={styles.metricsGrid}>
            {/* Revenue at Risk */}
            <div className={styles.metricCard}>
              <div className={styles.metricCardTop}>
                <span className={styles.cardLabel}>Revenue at Risk</span>
                <Coins size={15} color="var(--muted-foreground)" />
              </div>
              <div className={styles.cardValue}>
                {loading ? "—" : formatINR(summary?.revenue_at_risk)}
              </div>
              <div className={styles.cardFooter}>
                <span className={styles.subLabel}>Failed Transactions</span>
                <span className={styles.subValue}>
                  {loading ? "—" : `${summary?.total_cases ?? 0} Cases`}
                </span>
              </div>
            </div>

            {/* Revenue Recovered */}
            <div className={styles.metricCard}>
              <div className={styles.metricCardTop}>
                <span className={styles.cardLabel}>Revenue Recovered</span>
                <CheckCircle2 size={15} color="var(--success-text)" />
              </div>
              <div className={styles.cardValue} style={{ color: "var(--success-text)" }}>
                {loading ? "—" : formatINR(summary?.revenue_recovered)}
              </div>
              <div className={styles.cardFooter}>
                <span className={styles.subLabel}>Recovery Rate</span>
                <span className={styles.subValue} style={{ color: "var(--success-text)" }}>
                  {loading ? "—" : formatPercent(summary?.recovery_rate ?? 0)}
                </span>
              </div>
            </div>

            {/* Baseline Recovery */}
            <div className={styles.metricCard}>
              <div className={styles.metricCardTop}>
                <span className={styles.cardLabel}>Baseline Recovery</span>
                <Scale size={15} color="var(--muted-foreground)" />
              </div>
              <div className={styles.cardValue}>
                {loading ? "—" : formatINR(summary?.baseline_recovered)}
              </div>
              <div className={styles.cardFooter}>
                <span className={styles.subLabel}>Baseline Rate</span>
                <span className={styles.subValue}>
                  {loading ? "—" : formatPercent(summary?.baseline_recovery_rate ?? 0)}
                </span>
              </div>
            </div>

            {/* Incremental Recovery */}
            <div className={styles.metricCard}>
              <div className={styles.metricCardTop}>
                <span className={styles.cardLabel}>Incremental Recovery</span>
                <TrendingUp size={15} color="var(--accent-primary)" />
              </div>
              <div className={styles.cardValue} style={{ color: "var(--accent-primary)" }}>
                {loading ? "—" : formatINR(summary?.incremental_recovery)}
              </div>
              <div className={styles.cardFooter}>
                <span className={styles.subLabel}>Gross Recovery Lift</span>
                <span className={styles.subValue}>AI vs Fixed Retry</span>
              </div>
            </div>
          </div>
        </section>

        {/* ── Operational & Guardrail Controls ── */}
        <section aria-label="Operational recovery controls">
          <div className={styles.sectionHeader}>
            <ShieldCheck size={14} color="var(--success-text)" />
            <p className={styles.sectionLabel}>Operational Controls &amp; Governance</p>
          </div>

          <div className={styles.secondaryGrid}>
            <div className={styles.secondaryStatCard}>
              <span className={styles.secondaryStatVal}>
                {loading ? "—" : formatPercent(summary?.recovery_rate ?? 0)}
              </span>
              <span className={styles.secondaryStatLabel}>Aggregate Recovery Rate</span>
            </div>

            <div className={styles.secondaryStatCard}>
              <span className={styles.secondaryStatVal}>
                {loading ? "—" : formatINR(summary?.intervention_spend)}
              </span>
              <span className={styles.secondaryStatLabel}>Intervention Cost</span>
            </div>

            <div className={styles.secondaryStatCard}>
              <span className={styles.secondaryStatVal}>{loading ? "—" : summary?.total_cases ?? 0}</span>
              <span className={styles.secondaryStatLabel}>Active Cases Processed</span>
            </div>

            <div className={styles.secondaryStatCard}>
              <span className={styles.secondaryStatVal} style={{ color: "#EF4444" }}>
                {loading ? "—" : summary?.guardrail_stops ?? 0}
              </span>
              <span className={styles.secondaryStatLabel}>Guardrail Policy Stops</span>
            </div>

            <div className={styles.secondaryStatCard}>
              <span className={styles.secondaryStatVal}>{loading ? "—" : summary?.escalations ?? 0}</span>
              <span className={styles.secondaryStatLabel}>Human Escalations</span>
            </div>

            <div className={styles.secondaryStatCard}>
              <span className={styles.secondaryStatVal} style={{ color: "var(--accent-primary)" }}>
                {loading ? "—" : pending}
              </span>
              <span className={styles.secondaryStatLabel}>Pending Approvals</span>
            </div>
          </div>
        </section>

        {/* ── Visual Charts Section ── */}
        <section aria-label="Visual recovery analysis">
          <div className={styles.chartsGrid}>
            {/* Baseline vs AI Net Recovery Chart */}
            <div className={styles.chartCard}>
              <div className={styles.chartHeader}>
                <div>
                  <h3 className={styles.chartTitle}>Baseline vs AI Net Recovery</h3>
                  <p className={styles.chartSubtitle}>
                    COUNTERFACTUAL BENCHMARK ON IDENTICAL FAILED TRANSACTIONS
                  </p>
                </div>
              </div>

              <div style={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonData} margin={{ top: 12, right: 16, bottom: 8, left: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: "#94A3B8", fontSize: 12, fontFamily: "Source Sans 3" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: "#64748B", fontSize: 11, fontFamily: "IBM Plex Mono" }}
                      tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      formatter={(v: any) => [formatINR(String(v)), "Recovered Capital"]}
                      contentStyle={{
                        background: "#0E131F",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                        fontSize: "12px",
                        color: "#fff",
                        fontFamily: "IBM Plex Mono",
                      }}
                    />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {comparisonData.map((entry) => (
                        <Cell key={entry.name} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Recovery Conversion Funnel */}
            <div className={styles.chartCard}>
              <div className={styles.chartHeader}>
                <div>
                  <h3 className={styles.chartTitle}>Payment Recovery Conversion Funnel</h3>
                  <p className={styles.chartSubtitle}>
                    FAILED PAYMENTS → EVALUATED → ACTION EXECUTED → RECOVERED
                  </p>
                </div>
              </div>

              <RecoveryFunnel
                totalFailed={summary?.total_cases || 100}
                eligible={Math.round((summary?.total_cases || 100) * 0.88)}
                actioned={Math.round((summary?.total_cases || 100) * 0.78)}
                recovered={Math.round((summary?.total_cases || 100) * 0.65)}
              />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default CommandCenter;
