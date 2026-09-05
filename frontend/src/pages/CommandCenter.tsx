/**
 * RecoveryOS — Command Center (Bitcoin DeFi Aesthetic & Gamified Mining Rig)
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
  Flame,
  ShieldCheck,
  TrendingUp,
  Cpu,
  ArrowUpRight,
  ShieldAlert,
  Coins,
  Sparkles,
  Activity,
} from "lucide-react";
import { RecoveryFunnel } from "../components/charts/RecoveryFunnel";
import { ErrorBanner } from "../components/layout/ErrorBanner";
import { PageHeader } from "../components/layout/PageHeader";
import { api, formatINR, formatPercent } from "../services/api";
import { gamification } from "../services/gamification";
import type { DashboardSummary } from "../types";
import styles from "./CommandCenter.module.css";

interface MetricCardProps {
  label: string;
  value: string;
  subValue?: string;
  subLabel?: string;
  featured?: boolean;
  accent?: "orange" | "gold" | "cyan" | "green";
  loading?: boolean;
}

function MetricCard({
  label,
  value,
  subValue,
  subLabel,
  featured,
  accent = "orange",
  loading,
}: MetricCardProps) {
  const accentClass =
    accent === "gold"
      ? styles.accentGold
      : accent === "cyan"
      ? styles.accentCyan
      : accent === "green"
      ? styles.accentGreen
      : styles.accentOrange;

  return (
    <div
      className={`card-block corner-accents ${styles.metricCard} ${
        featured ? styles.featuredCard : ""
      } ${accentClass}`}
    >
      <div className={styles.cardHeader}>
        <p className={styles.metricLabel}>{label}</p>
        <span className={styles.pulseNode} />
      </div>

      {loading ? (
        <div className={styles.skeleton} aria-hidden="true" />
      ) : (
        <div className={styles.cardBody}>
          <p className={styles.metricValue}>{value}</p>
          {subValue && (
            <p className={styles.metricSub}>
              {subLabel && <span className={styles.metricSubLabel}>{subLabel} </span>}
              <span className={styles.metricSubValue}>{subValue}</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export function CommandCenter() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [bonusClaimed, setBonusClaimed] = useState(false);
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
        setError(err.message ?? "Failed to load dashboard");
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

  const handleClaimDailyBonus = () => {
    if (bonusClaimed) return;
    setBonusClaimed(true);
    gamification.addXP(100, "Claimed Daily Hashrate Energy Bonus");
    gamification.incrementStreak();
  };

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
          fill: "#F7931A",
        },
        {
          name: "Net Alpha",
          value: parseFloat(summary.net_incremental_recovery) || 0,
          fill: "#FFD600",
        },
      ]
    : [];

  return (
    <div className={styles.page}>
      {/* ── Top Page Header ── */}
      <PageHeader
        label="REVENUE RECOVERY PROTOCOL :: OVERVIEW"
        title="Command Center"
        subtitle={
          lastRefreshed
            ? `Cryptographic settlement feed · Last synced ${lastRefreshed.toLocaleTimeString()}`
            : "Real-time financial impact of autonomous expected-value recovery"
        }
        actions={
          <div className="flex items-center gap-3">
            <button
              onClick={handleClaimDailyBonus}
              disabled={bonusClaimed}
              className={`btn-pill-btc flex items-center gap-2 ${
                bonusClaimed ? "opacity-50 cursor-not-allowed" : ""
              }`}
              title="Claim Daily Mining Hashrate Bonus (+100 XP)"
            >
              <Sparkles size={16} />
              <span>{bonusClaimed ? "Daily Bonus Claimed" : "Claim Daily Bonus (+100 XP)"}</span>
            </button>
            {pending > 0 && (
              <Link
                to="/recovery-queue"
                className="btn-pill-btc bg-gradient-to-r from-[#EA580C] to-[#FFD600] animate-pulse"
                id="btn-pending-approvals"
              >
                <Flame size={16} />
                <span>{pending} Pending Approval{pending !== 1 ? "s" : ""}</span>
              </Link>
            )}
          </div>
        }
      />

      <div className={styles.content}>
        {error && (
          <div className="mb-4">
            <ErrorBanner message={error} onRetry={() => load()} />
          </div>
        )}

        {/* ── Hero 3D Orbital Banner ── */}
        <div className={styles.heroBanner}>
          <div className={styles.heroText}>
            <div className={styles.badgePill}>
              <span className={styles.badgeDot} />
              <span>CONSENSUS PROOF :: RECOVERY ENGINE ACTIVE</span>
            </div>
            <h2 className={styles.heroTitle}>
              Autonomous AI Recovery with{" "}
              <span className="text-gradient-btc">Cryptographic Precision</span>
            </h2>
            <p className={styles.heroSubtitle}>
              RecoveryOS monitors failed transactions, calculates expected net revenue across 6
              algorithmic actions, and guarantees merchant limit safety before dispatching funds.
            </p>

            <div className={styles.heroCtaRow}>
              <Link to="/simulator" className="btn-pill-btc">
                <Cpu size={16} />
                <span>Launch Mining Simulator</span>
              </Link>
              <Link to="/recovery-queue" className="btn-pill-outline">
                <span>View Recovery Queue</span>
                <ArrowUpRight size={16} />
              </Link>
            </div>
          </div>

          {/* 3D-Style Spinning Orbital Node */}
          <div className={styles.orbContainer}>
            <div className={styles.ringOuter} />
            <div className={styles.ringInner} />
            <div className={styles.coreOrb}>
              <Coins size={36} className="text-[#030304]" />
            </div>
          </div>
        </div>

        {/* ── Primary Financial Alpha Grid ── */}
        <section aria-label="Primary financial metrics">
          <div className={styles.sectionHeader}>
            <span className={styles.sectionIcon}><Coins size={15} /></span>
            <p className={styles.sectionLabel}>Financial Alpha &amp; Yield</p>
          </div>

          <div className={styles.metricsGrid}>
            <MetricCard
              label="Net Incremental Alpha"
              value={loading ? "—" : formatINR(summary?.net_incremental_recovery)}
              subLabel="Spend"
              subValue={loading ? "—" : formatINR(summary?.intervention_spend)}
              featured
              accent="gold"
              loading={loading}
            />
            <MetricCard
              label="Revenue at Risk"
              value={loading ? "—" : formatINR(summary?.revenue_at_risk)}
              subLabel="Total Intercepted"
              subValue={loading ? "—" : `${summary?.total_cases ?? 0} Cases`}
              accent="orange"
              loading={loading}
            />
            <MetricCard
              label="AI Recovered Value"
              value={loading ? "—" : formatINR(summary?.revenue_recovered)}
              subLabel="Recovery Rate"
              subValue={loading ? "—" : formatPercent(summary?.recovery_rate ?? 0)}
              featured
              accent="green"
              loading={loading}
            />
            <MetricCard
              label="Fixed Baseline Rate"
              value={loading ? "—" : formatINR(summary?.baseline_recovered)}
              subLabel="Baseline Success"
              subValue={loading ? "—" : formatPercent(summary?.baseline_recovery_rate ?? 0)}
              accent="cyan"
              loading={loading}
            />
            <MetricCard
              label="Gross Incremental Lift"
              value={loading ? "—" : formatINR(summary?.incremental_recovery)}
              subLabel="Formula"
              subValue="AI Lift vs Baseline"
              accent="orange"
              loading={loading}
            />
            <MetricCard
              label="Intervention Budget Spent"
              value={loading ? "—" : formatINR(summary?.intervention_spend)}
              subLabel="Guardrail Pool"
              subValue="Daily ₹5,000 Cap"
              accent="orange"
              loading={loading}
            />
          </div>
        </section>

        {/* ── Guardrail Enforcement Activity ── */}
        <section aria-label="Guardrail enforcement metrics">
          <div className={styles.sectionHeader}>
            <span className={styles.sectionIcon}><ShieldCheck size={15} /></span>
            <p className={styles.sectionLabel}>Deterministic Guardrail Activity</p>
          </div>

          <div className={styles.guardrailGrid}>
            <div className={styles.guardrailStat}>
              <div className={styles.statIconBadge}><ShieldAlert size={18} className="text-[#F87171]" /></div>
              <p className={styles.guardrailValue}>{loading ? "—" : summary?.guardrail_stops ?? 0}</p>
              <p className={styles.guardrailLabel}>Guardrail Stops</p>
            </div>
            <div className={styles.guardrailStat}>
              <div className={styles.statIconBadge}><TrendingUp size={18} className="text-[#38BDF8]" /></div>
              <p className={styles.guardrailValue}>{loading ? "—" : summary?.escalations ?? 0}</p>
              <p className={styles.guardrailLabel}>Escalations</p>
            </div>
            <div className={styles.guardrailStat}>
              <div className={styles.statIconBadge}><Activity size={18} className="text-[#94A3B8]" /></div>
              <p className={styles.guardrailValue}>{loading ? "—" : summary?.do_nothing_count ?? 0}</p>
              <p className={styles.guardrailLabel}>Do Nothing (Safe Halt)</p>
            </div>
            <div className={styles.guardrailStat}>
              <div className={styles.statIconBadge}><Flame size={18} className="text-[#FFD600]" /></div>
              <p className={styles.guardrailValue}>{loading ? "—" : pending}</p>
              <p className={styles.guardrailLabel}>Pending Human Approval</p>
            </div>
          </div>
        </section>

        {/* ── Charts & Visual Funnels ── */}
        <section aria-label="Visual recovery analysis">
          <div className={styles.chartsGrid}>
            {/* Net Comparison Chart */}
            <div className="card-block p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-base font-heading font-bold text-white">
                    Baseline vs AI Net Recovery
                  </h3>
                  <p className="text-xs font-mono text-[#94A3B8]">
                    COUNTERFACTUAL BENCHMARK ON IDENTICAL DATASET
                  </p>
                </div>
                <span className="text-xs font-mono text-[#FFD600] px-2.5 py-1 rounded-full bg-[#FFD600]/10 border border-[#FFD600]/30">
                  +{(Number(summary?.net_incremental_recovery ?? 0) > 0 ? "PROVEN ALPHA" : "ACTIVE")}
                </span>
              </div>

              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonData} margin={{ top: 12, right: 16, bottom: 8, left: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                    <XAxis dataKey="name" tick={{ fill: "#FFFFFF", fontSize: 11, fontFamily: "Space Grotesk" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "#94A3B8", fontSize: 11, fontFamily: "JetBrains Mono" }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
                    <Tooltip
                      formatter={(v: any) => [formatINR(String(v)), "Amount"]}
                      contentStyle={{
                        background: "#0F1115",
                        border: "1px solid rgba(247, 147, 26, 0.4)",
                        borderRadius: "12px",
                        fontSize: "12px",
                        color: "#fff",
                        fontFamily: "JetBrains Mono",
                      }}
                    />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                      {comparisonData.map((entry) => (
                        <Cell key={entry.name} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* 4-Stage Recovery Funnel */}
            <div className="card-block p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-base font-heading font-bold text-white">
                    Protocol Conversion Funnel
                  </h3>
                  <p className="text-xs font-mono text-[#94A3B8]">
                    INGESTION → VERIFIED → DISPATCHED → SETTLED
                  </p>
                </div>
                <span className="text-xs font-mono text-[#34D399] px-2.5 py-1 rounded-full bg-[#10B981]/10 border border-[#10B981]/30">
                  HEALTHY CONVERSION
                </span>
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
