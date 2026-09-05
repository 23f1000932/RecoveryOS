/**
 * RecoveryOS — Recovery Simulation Lab (Section 24 & 25)
 *
 * Professional Fintech Simulation Architecture:
 *   - Evaluates identical synthetic payment failure batches across:
 *       1. Fixed Naive Baseline: immediate single retry
 *       2. RecoveryOS: intelligent 6-action evaluation + deterministic guardrails
 *   - Strictly communicates expected financial value, costs, and net incremental revenue.
 *   - Clean operational telemetry with reproducible random seed controls.
 */

import { useEffect, useRef, useState } from 'react';
import {
  Cpu,
  Zap,
  Play,
  RotateCcw,
  ShieldCheck,
  TrendingUp,
  Activity,
  History,
  CheckCircle2,
  ArrowRight,
  Sliders,
  DollarSign,
} from 'lucide-react';
import { IncrementalRevenueChart } from '../components/charts/IncrementalRevenueChart';
import { RecoveryComparisonChart } from '../components/charts/RecoveryComparisonChart';
import { EmptyState } from '../components/layout/EmptyState';
import { ErrorBanner } from '../components/layout/ErrorBanner';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatINR, formatPercent } from '../services/api';
import type { SimulatorResult } from '../types';
import styles from './SimulatorPage.module.css';

const MAX_POLL_ATTEMPTS = 60;
const POLL_INTERVAL_MS = 2000;

interface MetricCardProps {
  label: string;
  baseline: string;
  ai: string;
}

function MetricCard({ label, baseline, ai }: MetricCardProps) {
  return (
    <div className={styles.metricCard}>
      <p className={styles.metricLabel}>{label}</p>
      <div className={styles.comparisonRow}>
        <div className={styles.comparisonCol}>
          <span className={styles.compTag}>Baseline Retry</span>
          <span className={styles.compVal}>{baseline}</span>
        </div>
        <div className={styles.comparisonCol}>
          <span className={styles.compTag} style={{ color: 'var(--accent-primary)' }}>RecoveryOS AI</span>
          <span className={`${styles.compVal} ${styles.compValAI}`}>{ai}</span>
        </div>
      </div>
    </div>
  );
}

export function SimulatorPage() {
  const [rows, setRows] = useState(1000);
  const [seed, setSeed] = useState(42);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [pollAttempt, setPollAttempt] = useState(0);
  const [result, setResult] = useState<SimulatorResult | null>(null);
  const [history, setHistory] = useState<SimulatorResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clean up polling on unmount
  useEffect(() => () => { if (pollRef.current) clearTimeout(pollRef.current); }, []);

  const randomizeSeed = () => {
    setSeed(Math.floor(Math.random() * 9000) + 1000);
  };

  const runSim = async () => {
    if (loading || polling) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const { experiment_id } = await api.runSimulation({ rows, seed });
      setLoading(false);
      setPolling(true);
      setPollAttempt(0);
      pollForResult(experiment_id, 0);
    } catch (e: unknown) {
      setError((e as Error).message);
      setLoading(false);
    }
  };

  const pollForResult = (experimentId: string, attempt: number) => {
    if (attempt >= MAX_POLL_ATTEMPTS) {
      setPolling(false);
      setError(`Simulation timed out after ${(MAX_POLL_ATTEMPTS * POLL_INTERVAL_MS) / 1000}s. The compute worker is still processing.`);
      return;
    }

    setPollAttempt(attempt + 1);

    api.getExperiment(experimentId)
      .then((res) => {
        setPolling(false);
        setResult(res);
        setHistory((h) => [res, ...h.filter((x) => x.experiment_id !== res.experiment_id)].slice(0, 4));
      })
      .catch((e: { status?: number }) => {
        if (e.status === 404) {
          // Not ready yet — poll again
          pollRef.current = setTimeout(
            () => pollForResult(experimentId, attempt + 1),
            POLL_INTERVAL_MS,
          );
        } else {
          setPolling(false);
          setError('Failed to retrieve simulation results from the calculation service.');
        }
      });
  };

  const isRunning = loading || polling;

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="RECOVERY INTELLIGENCE"
        title="Recovery Simulation Lab"
        subtitle="Compare RecoveryOS against a fixed retry baseline using reproducible synthetic payment failures."
      />

      <div className={styles.content}>
        {/* Section 25: Visual Story of Baseline vs RecoveryOS */}
        <section className={styles.storyCard} aria-label="Simulation Workflow">
          <div className={styles.storyHeader}>
            <Sliders size={16} color="var(--accent-primary)" />
            <span className={styles.storyEyebrow}>EVALUATION METHODOLOGY</span>
          </div>
          <div className={styles.storyPipeline}>
            <div className={styles.storyNode}>
              <span className={styles.nodeTitle}>1. IDENTICAL DATASET</span>
              <p className={styles.nodeDesc}>
                Controlled batch of failed Razorpay payment transactions with exact seed reproducibility.
              </p>
            </div>

            <div className={styles.storyArrow}>
              <ArrowRight size={18} />
            </div>

            <div className={styles.storyNode}>
              <span className={styles.nodeTitle}>2. FIXED BASELINE</span>
              <p className={styles.nodeDesc}>
                Naive standard retry once immediately without customer context or expected net value filtering.
              </p>
            </div>

            <div className={styles.storyArrow}>
              <span style={{ fontSize: '11px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--accent-primary)' }}>VS</span>
            </div>

            <div className={`${styles.storyNode} ${styles.storyNodeHighlight}`}>
              <span className={styles.nodeTitle} style={{ color: 'var(--accent-primary)' }}>3. RECOVERYOS AI</span>
              <p className={styles.nodeDesc}>
                Intelligent action evaluation (6 candidates), EV optimization, and deterministic policy guardrails.
              </p>
            </div>

            <div className={styles.storyArrow}>
              <ArrowRight size={18} />
            </div>

            <div className={styles.storyNode}>
              <span className={styles.nodeTitle}>4. BUSINESS OUTCOME</span>
              <p className={styles.nodeDesc}>
                Rigorous measurement of gross recovery, intervention cost, and Net Incremental Revenue.
              </p>
            </div>
          </div>
        </section>

        {/* Configuration Card */}
        <section className={styles.configCard} aria-label="Simulation Configuration">
          <div className={styles.configHeader}>
            <div className={styles.configTitleGroup}>
              <Cpu size={18} color="var(--accent-primary)" />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, letterSpacing: '0.04em' }}>
                SIMULATION PARAMETERS
              </span>
            </div>
            <div className={`${styles.configStatusPill} ${isRunning ? styles.configStatusActive : ''}`}>
              {isRunning && <span className={styles.statusDotPulse} />}
              {isRunning ? 'SIMULATION IN PROGRESS' : 'SIMULATOR READY'}
            </div>
          </div>

          <div className={styles.configGrid}>
            {/* Rows Config */}
            <div className={styles.fieldGroup}>
              <div className={styles.fieldLabel}>
                <span>Dataset Size</span>
                <span style={{ color: 'var(--accent-primary)' }}>{rows.toLocaleString()} Cases</span>
              </div>
              <div className={styles.inputGroup}>
                <input
                  id="sim-rows"
                  className={styles.numberInput}
                  type="number"
                  min={100}
                  max={50000}
                  step={500}
                  value={rows}
                  disabled={isRunning}
                  onChange={(e) => setRows(parseInt(e.target.value, 10) || 1000)}
                />
              </div>
              <div className={styles.presetChips}>
                {[1000, 2500, 5000, 10000].map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    className={`${styles.chip} ${rows === preset ? styles.chipActive : ''}`}
                    onClick={() => setRows(preset)}
                    disabled={isRunning}
                  >
                    {preset.toLocaleString()}
                  </button>
                ))}
              </div>
            </div>

            {/* Seed Config */}
            <div className={styles.fieldGroup}>
              <div className={styles.fieldLabel}>
                <span>Random Seed</span>
                <span style={{ color: 'var(--muted)' }}>Reproducible Evaluation</span>
              </div>
              <div className={styles.inputGroup}>
                <input
                  id="sim-seed"
                  className={styles.numberInput}
                  type="number"
                  value={seed}
                  disabled={isRunning}
                  onChange={(e) => setSeed(parseInt(e.target.value, 10) || 42)}
                />
                <button
                  type="button"
                  className={styles.randomBtn}
                  onClick={randomizeSeed}
                  disabled={isRunning}
                  title="Randomize Random Seed"
                >
                  <RotateCcw size={15} />
                </button>
              </div>
              <div className={styles.presetChips}>
                {[42, 1337, 2024, 7777].map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    className={`${styles.chip} ${seed === preset ? styles.chipActive : ''}`}
                    onClick={() => setSeed(preset)}
                    disabled={isRunning}
                  >
                    #{preset}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Action Row */}
          <div className={styles.actionRow}>
            <div className={styles.telemetrySummary}>
              <div>
                <span style={{ color: 'var(--muted-foreground)' }}>PIPELINE: </span>
                <span style={{ color: 'var(--foreground)', fontWeight: 600 }}>10 STAGES</span>
              </div>
              <div>
                <span style={{ color: 'var(--muted-foreground)' }}>OPTIMIZER: </span>
                <span style={{ color: 'var(--foreground)', fontWeight: 600 }}>MAX EXPECTED NET</span>
              </div>
              <div>
                <span style={{ color: 'var(--muted-foreground)' }}>GUARDRAILS: </span>
                <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>12 DETERMINISTIC RULES</span>
              </div>
            </div>

            <button
              id="btn-run-simulation"
              className={styles.btnRunSim}
              onClick={runSim}
              disabled={isRunning}
            >
              {loading ? (
                <>
                  <Activity size={16} className="animate-spin" />
                  INITIALIZING RUNNER…
                </>
              ) : polling ? (
                <>
                  <Zap size={16} className="animate-pulse" />
                  RUNNING SIMULATION ({pollAttempt}/{MAX_POLL_ATTEMPTS})
                </>
              ) : (
                <>
                  <Play size={16} fill="currentColor" />
                  RUN RECOVERY SIMULATION
                </>
              )}
            </button>
          </div>

          {/* Real-time Progress Bar */}
          {polling && (
            <div className={styles.simProgressBox}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: 11, marginBottom: 8, color: 'var(--foreground)' }}>
                <span>EVALUATING PAYMENT BATCH ({rows.toLocaleString()} TRANSACTIONS)</span>
                <span>{Math.round((pollAttempt / MAX_POLL_ATTEMPTS) * 100)}%</span>
              </div>
              <div className={styles.progressBarTrack}>
                <div
                  className={styles.progressBarFill}
                  style={{ width: `${Math.max(5, (pollAttempt / MAX_POLL_ATTEMPTS) * 100)}%` }}
                />
              </div>
              <div className={styles.progressHint}>
                <Activity size={13} color="var(--accent-primary)" className="animate-spin" />
                <span>
                  Stage {Math.min(10, Math.floor((pollAttempt % 10) + 1))}/10: Testing recovery policies against seed #{seed}…
                </span>
              </div>
            </div>
          )}
        </section>

        {error && (
          <ErrorBanner message={error} onRetry={() => setError(null)} />
        )}

        {/* Experiment Results Container */}
        {result && (
          <section className={styles.resultsCard} aria-label="Simulation Results">
            <div className={styles.resultsHeader}>
              <div>
                <h3 className={styles.resultsTitle}>Simulation Results</h3>
                <p className={styles.resultsMeta}>
                  EXPERIMENT: {result.experiment_id} · SEED #{result.seed} · {result.dataset_size.toLocaleString()} FAILED PAYMENTS
                </p>
              </div>

              {parseFloat(result.net_incremental_recovery) > 0 && (
                <div className={styles.netAlphaHighlightBanner}>
                  <DollarSign size={15} />
                  <span>NET INCREMENTAL RECOVERY: +{formatINR(result.net_incremental_recovery)}</span>
                </div>
              )}
            </div>

            {/* Incremental Recovery Hero Cards */}
            <div className={styles.heroIncGrid}>
              <div className={styles.heroIncCard}>
                <div className={styles.incCardHeader}>
                  <span className={styles.incCardLabel}>Gross Incremental Recovery</span>
                  <TrendingUp size={16} color="var(--muted-foreground)" />
                </div>
                <div className={styles.incCardVal}>{formatINR(result.incremental_recovery)}</div>
                <p className={styles.incCardSub}>
                  Additional gross revenue recovered by RecoveryOS intelligent decisioning over baseline retry.
                </p>
              </div>

              <div className={`${styles.heroIncCard} ${styles.heroIncNet}`}>
                <div className={styles.incCardHeader}>
                  <span className={styles.incCardLabel} style={{ color: 'var(--accent-primary)' }}>
                    Net Incremental Recovery (North-Star)
                  </span>
                  <Zap size={16} color="var(--accent-primary)" />
                </div>
                <div className={styles.incCardVal} style={{ color: 'var(--accent-primary)' }}>
                  {formatINR(result.net_incremental_recovery)}
                </div>
                <p className={styles.incCardSub}>
                  True bottom-line gain after strictly subtracting all intervention expenses and gateway fees.
                </p>
              </div>
            </div>

            {/* Metric Comparison Pairs */}
            <div className={styles.metricGrid}>
              <MetricCard
                label="Total Revenue Recovered"
                baseline={formatINR(result.baseline_recovered)}
                ai={formatINR(result.ai_recovered)}
              />
              <MetricCard
                label="Recovery Rate"
                baseline={formatPercent(result.baseline_recovery_rate)}
                ai={formatPercent(result.ai_recovery_rate)}
              />
              <MetricCard
                label="Intervention & Gateway Cost"
                baseline={formatINR(result.baseline_cost)}
                ai={formatINR(result.ai_cost)}
              />
            </div>

            {/* Guardrail & Policy Statistics */}
            <div className={styles.guardrailStrip}>
              <div className={styles.shieldBadge}>
                <ShieldCheck size={16} />
                <span>GUARDRAIL ENFORCEMENT</span>
              </div>
              <div className={styles.guardrailItem}>
                Policy Stops: <span className={styles.guardrailVal}>{result.guardrail_stops}</span>
              </div>
              <div className={styles.guardrailItem}>
                Manual Approvals: <span className={styles.guardrailVal}>{result.escalations}</span>
              </div>
              <div className={styles.guardrailItem}>
                Economically Blocked ("Do Nothing"): <span className={styles.guardrailVal}>{result.do_nothing_count}</span>
              </div>
              <div className={styles.guardrailItem}>
                Verification: <span className={styles.guardrailVal} style={{ color: '#10B981' }}>COMPLETED</span>
              </div>
            </div>

            {/* Dual Comparison Charts */}
            <div className={styles.chartsGrid}>
              <div className={styles.chartContainer}>
                <div className={styles.chartHeader}>
                  <span>Total Revenue Recovered Comparison</span>
                  <span style={{ color: 'var(--accent-primary)' }}>RecoveryOS vs Baseline</span>
                </div>
                <RecoveryComparisonChart result={result} />
              </div>

              <div className={styles.chartContainer}>
                <div className={styles.chartHeader}>
                  <span>Cumulative Net Incremental Trajectory</span>
                  <span style={{ color: 'var(--accent-primary)' }}>Net ₹ Curve</span>
                </div>
                <IncrementalRevenueChart result={result} />
              </div>
            </div>
          </section>
        )}

        {/* Simulation History */}
        {history.length > 1 && (
          <section className={styles.historySection}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <History size={16} color="var(--accent-primary)" />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                PREVIOUS SIMULATION RUNS
              </span>
            </div>
            <div className={styles.historyList}>
              {history.map((h) => (
                <div
                  key={h.experiment_id}
                  className={styles.historyRow}
                  onClick={() => setResult(h)}
                  role="button"
                  tabIndex={0}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <CheckCircle2 size={15} color="#10B981" />
                    <span className={styles.historyId}>{h.experiment_id.slice(0, 8)}</span>
                    <span className={styles.historyMeta}>
                      Seed #{h.seed} · {h.dataset_size.toLocaleString()} cases
                    </span>
                  </div>
                  <span className={styles.historyNet}>
                    Net Incremental: {formatINR(h.net_incremental_recovery)}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {!result && !isRunning && !error && (
          <EmptyState
            icon="⚗"
            title="Recovery Simulation Ready"
            description="Configure synthetic dataset rows and random seed above, then run the simulation. Comparative financial metrics, cost analysis, and net incremental curves will generate automatically."
          />
        )}
      </div>
    </div>
  );
}
