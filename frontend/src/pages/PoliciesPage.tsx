/**
 * RecoveryOS — Guardrails & Policies (Section 21 & 26)
 *
 * Visualizes authoritative merchant recovery policy configurations, deterministic financial controls,
 * and includes an interactive Policy Simulator.
 */

import { useEffect, useState } from 'react';
import {
  ShieldCheck,
  Lock,
  Scale,
  DollarSign,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  Zap,
  Activity,
  Sliders,
} from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatINR } from '../services/api';
import type { PolicyView } from '../types';
import styles from './PoliciesPage.module.css';

export function PoliciesPage() {
  const [policy, setPolicy] = useState<PolicyView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Interactive Policy Simulator state
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
        label="GOVERNANCE &amp; CONTROLS"
        title="Guardrails &amp; Policies"
        subtitle="Merchant-defined controls govern every recovery action before execution."
      />

      <div className={styles.content}>
        {loading && (
          <div style={{ textAlign: 'center', padding: 48, fontFamily: 'var(--font-mono)', color: 'var(--muted)' }}>
            LOADING MERCHANT RECOVERY POLICIES…
          </div>
        )}

        {error && (
          <div className="card" style={{ borderColor: 'var(--danger-border)', color: 'var(--danger-text)', padding: 20 }} role="alert">
            {error}
          </div>
        )}

        {policy && (
          <>
            {/* Version & Immutability Bar */}
            <div className={styles.versionBar}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--muted-foreground)', fontWeight: 600 }}>
                  POLICY SPECIFICATION:
                </span>
                <span className={styles.versionBadge}>
                  <FileCode size={13} />
                  {policy.version}
                </span>
              </div>
              <div className={styles.enforcedPill}>
                <Lock size={13} />
                <span>DETERMINISTIC ENFORCEMENT ACTIVE</span>
              </div>
            </div>

            {/* Financial & Approval Thresholds */}
            <section className={styles.sectionCard} aria-label="Financial Guardrails">
              <div className={styles.sectionHeader}>
                <DollarSign size={16} color="var(--accent-primary)" />
                <span className={styles.sectionTitle}>Financial Bounds &amp; Approval Thresholds</span>
              </div>
              <div className={styles.grid}>
                <div className={styles.policyTile}>
                  <div className={styles.tileHeader}>
                    <span className={styles.tileLabel}>High-Value Threshold</span>
                    <Lock size={14} color="var(--accent-primary)" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary} style={{ color: 'var(--accent-primary)' }}>
                      {formatINR(policy.high_value_threshold)}
                    </span>
                  </div>
                  <p className={styles.tileDescription}>
                    Payments at or above this threshold strictly require human merchant approval before execution.
                  </p>
                </div>

                <div className={styles.policyTile}>
                  <div className={styles.tileHeader}>
                    <span className={styles.tileLabel}>Max Incentive / Customer</span>
                    <Scale size={14} color="var(--accent-primary)" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary}>
                      {formatINR(policy.max_incentive_per_customer)}
                    </span>
                  </div>
                  <p className={styles.tileDescription}>
                    Maximum discount or fee subsidy permitted for a single customer within the recovery window.
                  </p>
                </div>

                <div className={styles.policyTile}>
                  <div className={styles.tileHeader}>
                    <span className={styles.tileLabel}>Daily Incentive Pool</span>
                    <Activity size={14} color="var(--accent-primary)" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary}>
                      {formatINR(policy.daily_incentive_pool)}
                    </span>
                    <span className={styles.valueUnit}>/ 24h</span>
                  </div>
                  <p className={styles.tileDescription}>
                    Global daily merchant budget allocated across all automated recovery discount incentives.
                  </p>
                </div>

                <div className={styles.policyTile}>
                  <div className={styles.tileHeader}>
                    <span className={styles.tileLabel}>Min Expected Net Revenue</span>
                    <Zap size={14} color="var(--accent-primary)" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary}>
                      {formatINR(policy.min_expected_net_revenue)}
                    </span>
                    <span className={styles.valueUnit}>floor</span>
                  </div>
                  <p className={styles.tileDescription}>
                    Interventions with expected net revenue below this floor are halted to prevent negative ROI.
                  </p>
                </div>
              </div>
            </section>

            {/* AI Confidence & Execution Bounds */}
            <section className={styles.sectionCard} aria-label="Operational Guardrails">
              <div className={styles.sectionHeader}>
                <ShieldCheck size={16} color="#10B981" />
                <span className={styles.sectionTitle}>Model Confidence &amp; Anti-Spam Bounds</span>
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
                    <CheckCircle2 size={14} color="var(--accent-primary)" />
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
                    <Activity size={14} color="var(--muted)" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary}>
                      {policy.max_retries_per_customer}
                    </span>
                    <span className={styles.valueUnit}>attempts</span>
                  </div>
                  <p className={styles.tileDescription}>
                    Customer retry ceiling within a 24-hour cycle to prevent customer friction or bank lockouts.
                  </p>
                </div>

                <div className={styles.policyTile}>
                  <div className={styles.tileHeader}>
                    <span className={styles.tileLabel}>Recovery Time Window</span>
                    <Activity size={14} color="var(--muted)" />
                  </div>
                  <div className={styles.valueRow}>
                    <span className={styles.valuePrimary}>
                      {policy.recovery_window_hours}
                    </span>
                    <span className={styles.valueUnit}>hours max</span>
                  </div>
                  <p className={styles.tileDescription}>
                    Maximum permissible case lifetime before unrecovered transactions are gracefully closed.
                  </p>
                </div>
              </div>
            </section>

            {/* Interactive Policy Simulator (Section 26) */}
            <section className={styles.testerCard} aria-label="Interactive Policy Simulator">
              <div className={styles.testerHeader}>
                <Sliders size={18} color="var(--accent-primary)" />
                <span className={styles.testerTitle}>
                  POLICY SIMULATOR
                </span>
              </div>
              <p className={styles.testerDesc}>
                See how payment amount, expected value and model confidence interact with RecoveryOS guardrails.
              </p>

              <div className={styles.testerRow}>
                <div className={styles.testerInputWrapper}>
                  <label htmlFor="test-amount" className={styles.testerInputLabel}>Payment Amount (₹)</label>
                  <input
                    id="test-amount"
                    className={styles.testerInput}
                    type="number"
                    step={500}
                    value={testAmount}
                    onChange={(e) => setTestAmount(parseFloat(e.target.value) || 0)}
                  />
                </div>

                <div className={styles.testerInputWrapper}>
                  <label htmlFor="test-confidence" className={styles.testerInputLabel}>Model Confidence (%)</label>
                  <input
                    id="test-confidence"
                    className={styles.testerInput}
                    type="number"
                    min={0}
                    max={100}
                    value={Math.round(testConfidence * 100)}
                    onChange={(e) => setTestConfidence((parseFloat(e.target.value) || 0) / 100)}
                  />
                </div>

                <div className={styles.testerOutcomeCol}>
                  <span className={styles.testerInputLabel}>Guardrail Evaluation</span>
                  <div className={styles.testerOutcomeBadges}>
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
                        APPROVAL REQUIRED (&gt;= {formatINR(policy.high_value_threshold)})
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
                        BELOW APPROVAL THRESHOLD
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
                        AUTONOMOUS EXECUTION ALLOWED
                      </span>
                    ) : (
                      <span
                        className={styles.testerOutcomeBadge}
                        style={{
                          background: 'rgba(255, 255, 255, 0.05)',
                          border: '1px solid var(--border)',
                          color: 'var(--muted)',
                        }}
                      >
                        MANUAL REVIEW REQUIRED
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </section>

            {/* Policy Configuration Notice */}
            <div className={styles.noticeCard}>
              <FileCode size={20} color="var(--accent-primary)" style={{ flexShrink: 0, marginTop: 2 }} />
              <div className={styles.noticeText}>
                <strong>Merchant Policy Specification:</strong> Recovery controls are defined in{' '}
                <code>policies/recovery_policy.yaml</code>. Every recovery evaluation is deterministic, non-negotiable by ML models, and fully documented in the Decision Audit.
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
