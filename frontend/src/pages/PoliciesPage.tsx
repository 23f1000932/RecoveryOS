/**
 * RecoveryOS — Policies Page (Bitcoin DeFi Smart Contract Governance Overhaul)
 *
 * Visualizes authoritative merchant recovery policy configurations, deterministic guardrails,
 * and includes an interactive Real-Time Governance Simulator.
 */

import { useEffect, useState } from 'react';
import {
  ShieldCheck,
  Lock,
  Scale,
  Coins,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  Zap,
  Activity,
} from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatINR } from '../services/api';
import type { PolicyView } from '../types';
import styles from './PoliciesPage.module.css';

export function PoliciesPage() {
  const [policy, setPolicy] = useState<PolicyView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Interactive tester state
  const [testAmount, setTestAmount] = useState<number>(12500);
  const [testConfidence, setTestConfidence] = useState<number>(0.85);

  useEffect(() => {
    api.getPolicy()
      .then((p) => {
        setPolicy(p);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  const isHighValue = policy ? testAmount >= (parseFloat(policy.high_value_threshold) || 0) : false;
  const isAutoActionAllowed = policy
    ? testConfidence >= policy.auto_action_probability && !isHighValue
    : false;

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Smart Contract Policies"
        title="Deterministic Guardrail Governance"
        subtitle="Cryptographically binding merchant recovery policies. Enforced by 12 deterministic guardrail checks — mathematically non-negotiable by AI models."
      />

      <div className={styles.content}>
        {loading && (
          <div style={{ textAlign: 'center', padding: 48, fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>
            READING SMART CONTRACT POLICIES…
          </div>
        )}

        {error && (
          <div className="card" style={{ borderColor: '#EF4444', color: '#EF4444' }} role="alert">
            {error}
          </div>
        )}

        {policy && (
          <>
            {/* Version & Immutability Bar */}
            <div className={styles.versionBar}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className="label-mono" style={{ fontSize: 11 }}>POLICY SPEC:</span>
                <span className={styles.versionBadge}>
                  <FileCode size={13} />
                  {policy.version}
                </span>
              </div>
              <div className={styles.immutablePill}>
                <Lock size={13} />
                <span>STATE: IMMUTABLE CODE ENFORCED</span>
              </div>
            </div>

            {/* Financial & Multi-Sig Thresholds */}
            <section className={styles.sectionCard}>
              <div className={styles.sectionHeader}>
                <Coins size={16} color="var(--color-brand-primary)" />
                <span className={styles.sectionTitle}>Capital Bounds &amp; Multi-Sig Guardrails</span>
              </div>
              <div className={styles.grid}>
                <div className={styles.policyTile}>
                  <div className={styles.tileHeader}>
                    <span className={styles.tileLabel}>High-Value Threshold</span>
                    <Lock size={14} color="var(--color-accent-gold)" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary} style={{ color: 'var(--color-accent-gold)' }}>
                      {formatINR(policy.high_value_threshold)}
                    </span>
                  </div>
                  <p className={styles.tileDescription}>
                    Transactions at or above this threshold strictly require manual multi-sig merchant consensus.
                  </p>
                </div>

                <div className={styles.policyTile}>
                  <div className={styles.tileHeader}>
                    <span className={styles.tileLabel}>Max Incentive / Customer</span>
                    <Scale size={14} color="var(--color-brand-primary)" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary}>
                      {formatINR(policy.max_incentive_per_customer)}
                    </span>
                  </div>
                  <p className={styles.tileDescription}>
                    Hard ceiling for promotional discount or cash incentive offered to a single user.
                  </p>
                </div>

                <div className={styles.policyTile}>
                  <div className={styles.tileHeader}>
                    <span className={styles.tileLabel}>Daily Incentive Pool</span>
                    <Activity size={14} color="var(--color-brand-primary)" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary}>
                      {formatINR(policy.daily_incentive_pool)}
                    </span>
                    <span className={styles.valueUnit}>/ 24h</span>
                  </div>
                  <p className={styles.tileDescription}>
                    Global daily budget allocated across all automated recovery discount incentives.
                  </p>
                </div>

                <div className={styles.policyTile}>
                  <div className={styles.tileHeader}>
                    <span className={styles.tileLabel}>Min Expected Net Alpha</span>
                    <Zap size={14} color="var(--color-brand-primary)" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary}>
                      {formatINR(policy.min_expected_net_revenue)}
                    </span>
                    <span className={styles.valueUnit}>to trigger</span>
                  </div>
                  <p className={styles.tileDescription}>
                    Interventions with expected net return lower than this floor are halted to avoid fee burn.
                  </p>
                </div>
              </div>
            </section>

            {/* AI Autonomy & Confidence Bounds */}
            <section className={styles.sectionCard}>
              <div className={styles.sectionHeader}>
                <ShieldCheck size={16} color="#10B981" />
                <span className={styles.sectionTitle}>AI Confidence &amp; Anti-Spam Bounds</span>
              </div>
              <div className={styles.grid}>
                <div className={styles.policyTile}>
                  <div className={styles.tileHeader}>
                    <span className={styles.tileLabel}>Auto-Action Threshold</span>
                    <Zap size={14} color="#10B981" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary} style={{ color: '#10B981' }}>
                      {(policy.auto_action_probability * 100).toFixed(0)}%
                    </span>
                    <span className={styles.valueUnit}>P(Success)</span>
                  </div>
                  <p className={styles.tileDescription}>
                    Minimum predicted probability required for autonomous zero-touch adapter execution.
                  </p>
                </div>

                <div className={styles.policyTile}>
                  <div className={styles.tileHeader}>
                    <span className={styles.tileLabel}>Min Model Confidence</span>
                    <CheckCircle2 size={14} color="var(--color-brand-primary)" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary}>
                      {(policy.min_model_confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className={styles.tileDescription}>
                    Ensemble model agreement floor; lower certainty triggers mandatory human-in-the-loop review.
                  </p>
                </div>

                <div className={styles.policyTile}>
                  <div className={styles.tileHeader}>
                    <span className={styles.tileLabel}>Max Retries / Customer</span>
                    <Activity size={14} color="var(--color-text-muted)" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary}>
                      {policy.max_retries_per_customer}
                    </span>
                    <span className={styles.valueUnit}>max attempts</span>
                  </div>
                  <p className={styles.tileDescription}>
                    Customer retry ceiling within a 24-hour cycle to prevent issuer rate-limiting or lockouts.
                  </p>
                </div>

                <div className={styles.policyTile}>
                  <div className={styles.tileHeader}>
                    <span className={styles.tileLabel}>Recovery Time Window</span>
                    <Activity size={14} color="var(--color-text-muted)" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary}>
                      {policy.recovery_window_hours}
                    </span>
                    <span className={styles.valueUnit}>hours max</span>
                  </div>
                  <p className={styles.tileDescription}>
                    Maximum permissible case lifetime before unrecovered transactions are gracefully expired.
                  </p>
                </div>
              </div>
            </section>

            {/* Interactive Smart Contract Threshold Tester */}
            <section className={styles.testerCard}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Zap size={18} color="var(--color-brand-primary)" />
                <span className="label-mono" style={{ fontSize: 13, fontWeight: 700 }}>
                  INTERACTIVE GOVERNANCE SIMULATOR
                </span>
              </div>
              <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 4 }}>
                Simulate how hypothetical payment amounts and AI confidence scores trigger smart contract guardrails.
              </p>

              <div className={styles.testerRow}>
                <div className={styles.testerInputWrapper}>
                  <span className="label-mono" style={{ fontSize: 11 }}>Hypothetical Amount (₹)</span>
                  <input
                    className={styles.testerInput}
                    type="number"
                    step={500}
                    value={testAmount}
                    onChange={(e) => setTestAmount(parseFloat(e.target.value) || 0)}
                  />
                </div>

                <div className={styles.testerInputWrapper}>
                  <span className="label-mono" style={{ fontSize: 11 }}>Model Confidence (%)</span>
                  <input
                    className={styles.testerInput}
                    type="number"
                    min={0}
                    max={100}
                    value={Math.round(testConfidence * 100)}
                    onChange={(e) => setTestConfidence((parseFloat(e.target.value) || 0) / 100)}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <span className="label-mono" style={{ fontSize: 11 }}>Contract Evaluation</span>
                  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                    {isHighValue ? (
                      <span
                        className={styles.testerOutcomeBadge}
                        style={{
                          background: 'rgba(245, 158, 11, 0.15)',
                          border: '1px solid rgba(245, 158, 11, 0.4)',
                          color: '#F59E0B',
                        }}
                      >
                        <AlertTriangle size={14} />
                        MULTI-SIG CONSENSUS MANDATED (&gt;= {formatINR(policy.high_value_threshold)})
                      </span>
                    ) : (
                      <span
                        className={styles.testerOutcomeBadge}
                        style={{
                          background: 'rgba(16, 185, 129, 0.15)',
                          border: '1px solid rgba(16, 185, 129, 0.4)',
                          color: '#10B981',
                        }}
                      >
                        <CheckCircle2 size={14} />
                        BELOW HIGH-VALUE CEILING
                      </span>
                    )}

                    {isAutoActionAllowed ? (
                      <span
                        className={styles.testerOutcomeBadge}
                        style={{
                          background: 'rgba(16, 185, 129, 0.15)',
                          border: '1px solid rgba(16, 185, 129, 0.4)',
                          color: '#10B981',
                        }}
                      >
                        <Zap size={14} />
                        ZERO-TOUCH AUTONOMOUS EXECUTION
                      </span>
                    ) : (
                      <span
                        className={styles.testerOutcomeBadge}
                        style={{
                          background: 'rgba(255, 255, 255, 0.05)',
                          border: '1px solid var(--color-border)',
                          color: 'var(--color-text-secondary)',
                        }}
                      >
                        HUMAN-IN-THE-LOOP REQUIRED
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </section>

            {/* Immutability Notice Card */}
            <div className={styles.noticeCard}>
              <FileCode size={20} color="var(--color-brand-primary)" style={{ flexShrink: 0, marginTop: 2 }} />
              <div className={styles.noticeText}>
                <strong>Immutable Policy Configuration:</strong> Recovery rules are defined in{' '}
                <code>policies/recovery_policy.yaml</code>. Changes are versioned through code commits and audited in the immutable ledger.
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
