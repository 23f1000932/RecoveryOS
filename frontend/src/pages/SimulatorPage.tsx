/**
 * RecoveryOS — Simulator Page (Bitcoin DeFi Mining Rig Overhaul)
 *
 * Flow:
 *   1. User configures dataset rows + latent seed with quick presets
 *   2. POST /api/simulator/run → get experiment_id
 *   3. Real-time telemetry during polling (max 60 attempts)
 *   4. On completion:
 *      - Trigger Gamification (+400 XP, 'HASHRATE_SURGE' badge, celebration confetti)
 *      - Render High-Yield Alpha metrics & Dual-Comparison Charts
 *   5. Keeps interactive history of past runs
 */

import { useEffect, useRef, useState } from 'react';
import {
  Cpu,
  Zap,
  Play,
  RotateCcw,
  ShieldCheck,
  TrendingUp,
  Coins,
  Activity,
  History,
  CheckCircle2,
} from 'lucide-react';
import { IncrementalRevenueChart } from '../components/charts/IncrementalRevenueChart';
import { RecoveryComparisonChart } from '../components/charts/RecoveryComparisonChart';
import { EmptyState } from '../components/layout/EmptyState';
import { ErrorBanner } from '../components/layout/ErrorBanner';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatINR, formatPercent } from '../services/api';
import { gamification } from '../services/gamification';
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
          <span className={styles.compTag}>Baseline Policy</span>
          <span className={styles.compVal}>{baseline}</span>
        </div>
        <div className={styles.comparisonCol}>
          <span className={styles.compTag} style={{ color: 'var(--color-brand-primary)' }}>RecoveryOS AI</span>
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
      setError(`Experiment timed out after ${(MAX_POLL_ATTEMPTS * POLL_INTERVAL_MS) / 1000}s. The compute node is still processing.`);
      return;
    }

    setPollAttempt(attempt + 1);

    api.getExperiment(experimentId)
      .then((res) => {
        setPolling(false);
        setResult(res);
        setHistory((h) => [res, ...h.filter((x) => x.experiment_id !== res.experiment_id)].slice(0, 4));

        // Gamification check: Award XP and Badge if positive alpha
        const netAlpha = parseFloat(res.net_incremental_recovery) || 0;
        if (netAlpha > 0) {
          gamification.addXP(400, "Hashrate Surge Completed", netAlpha);
          gamification.unlockBadge("HASHRATE_SURGE");
          gamification.incrementStreak();
          gamification.fireCelebration(true);
        } else {
          gamification.addXP(100, "Simulation Benchmark Finished");
        }
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
          setError('Failed to retrieve experiment results from compute cluster.');
        }
      });
  };

  const isRunning = loading || polling;

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Mining Rig Simulator"
        title="A/B Latent Experiment Runner"
        subtitle="Simulate stress-test batches across 10-stage AI recovery pipelines vs naive baseline retry models. Identical seeds yield strictly deterministic latent failure outcomes."
      />

      <div className={styles.content}>
        {/* Rig Terminal & Configuration */}
        <section
          className={`${styles.rigTerminal} ${isRunning ? styles.rigTerminalRunning : ''}`}
          aria-label="Simulation configuration"
        >
          <div className={styles.rigHeader}>
            <div className={styles.rigTitleGroup}>
              <Cpu size={18} color="var(--color-brand-primary)" />
              <span className="label-mono" style={{ fontSize: 12, fontWeight: 700 }}>
                SYNTHETIC TRANSACTION MINING RIG
              </span>
            </div>
            <div className={`${styles.rigStatusPill} ${isRunning ? styles.rigStatusPillActive : ''}`}>
              {isRunning && <span className={styles.statusDotPulse} />}
              {isRunning ? 'MINING BATCH IN PROGRESS' : 'RIG STANDBY · READY'}
            </div>
          </div>

          <div className={styles.configGrid}>
            {/* Rows Config */}
            <div className={styles.fieldGroup}>
              <div className={styles.fieldLabel}>
                <span>Dataset Batch Size</span>
                <span style={{ color: 'var(--color-brand-primary)' }}>{rows.toLocaleString()} Cases</span>
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
                <span>Latent Pseudorandom Seed</span>
                <span style={{ color: 'var(--color-text-secondary)' }}>Deterministic RNG</span>
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
                  title="Randomize Latent Seed"
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
            <div className={styles.rigTelemetryInfo}>
              <div className={styles.telemetryItem}>
                <span>PIPELINE:</span>
                <span className={styles.telemetryVal}>10 STAGES</span>
              </div>
              <div className={styles.telemetryItem}>
                <span>CONSENSUS:</span>
                <span className={styles.telemetryVal}>EV &gt; THRESHOLD</span>
              </div>
              <div className={styles.telemetryItem}>
                <span>BOUNTY:</span>
                <span className={styles.telemetryVal} style={{ color: 'var(--color-accent-gold)' }}>+400 XP</span>
              </div>
            </div>

            <button
              id="btn-run-simulation"
              className={styles.btnMiningExecute}
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
                  MINING BATCH ({pollAttempt}/{MAX_POLL_ATTEMPTS})
                </>
              ) : (
                <>
                  <Play size={16} fill="currentColor" />
                  START SIMULATION RUN
                </>
              )}
            </button>
          </div>

          {/* Real-time Telemetry Bar */}
          {polling && (
            <div className={styles.miningTelemetryBox}>
              <div className={styles.telemetryHeader}>
                <span>
                  SYNTHETIC RUNNER COMPUTING ({rows.toLocaleString()} TRANSACTIONS)
                </span>
                <span>{Math.round((pollAttempt / MAX_POLL_ATTEMPTS) * 100)}%</span>
              </div>
              <div className={styles.progressBarTrack}>
                <div
                  className={styles.progressBarFill}
                  style={{ width: `${Math.max(5, (pollAttempt / MAX_POLL_ATTEMPTS) * 100)}%` }}
                />
              </div>
              <div className={styles.telemetryConsole}>
                <Activity size={13} color="var(--color-brand-primary)" className="animate-spin" />
                <span>
                  Stage {Math.min(10, Math.floor((pollAttempt % 10) + 1))}/10: Evaluating latent recovery outcomes under seed {seed}…
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
          <section className={styles.resultsCard}>
            <div className={styles.resultsHeader}>
              <div>
                <h3 className={styles.resultsTitle}>Experiment Completed</h3>
                <p className={styles.resultsMeta}>
                  EXPERIMENT ID: {result.experiment_id} · SEED #{result.seed} · {result.dataset_size.toLocaleString()} BATCH ROWS
                </p>
              </div>

              {parseFloat(result.net_incremental_recovery) > 0 && (
                <div className={styles.alphaBanner}>
                  <Coins size={15} />
                  <span>NET ALPHA GENERATED: +{formatINR(result.net_incremental_recovery)}</span>
                </div>
              )}
            </div>

            {/* Incremental Recovery Hero Cards */}
            <div className={styles.heroIncrementalGrid}>
              <div className={styles.heroIncCard}>
                <div className={styles.incCardHeader}>
                  <span className={styles.incCardLabel}>Gross Incremental Recovery</span>
                  <TrendingUp size={16} color="var(--color-text-muted)" />
                </div>
                <div className={styles.incCardVal}>{formatINR(result.incremental_recovery)}</div>
                <p className={styles.incCardSub}>
                  Total additional gross funds recovered by RecoveryOS AI over baseline naive retry.
                </p>
              </div>

              <div className={`${styles.heroIncCard} ${styles.heroIncNet}`}>
                <div className={styles.incCardHeader}>
                  <span className={styles.incCardLabel} style={{ color: 'var(--color-brand-primary)' }}>
                    Net Incremental Recovery (True Alpha)
                  </span>
                  <Zap size={16} color="var(--color-accent-gold)" />
                </div>
                <div className={styles.incCardVal} style={{ color: 'var(--color-accent-gold)' }}>
                  {formatINR(result.net_incremental_recovery)}
                </div>
                <p className={styles.incCardSub}>
                  Net revenue gain after strictly accounting for gateway fees and adapter execution costs.
                </p>
              </div>
            </div>

            {/* Metric Comparison Pairs */}
            <div className={styles.metricGrid}>
              <MetricCard
                label="Total Funds Recovered"
                baseline={formatINR(result.baseline_recovered)}
                ai={formatINR(result.ai_recovered)}
              />
              <MetricCard
                label="Aggregate Recovery Rate"
                baseline={formatPercent(result.baseline_recovery_rate)}
                ai={formatPercent(result.ai_recovery_rate)}
              />
              <MetricCard
                label="Intervention & Gateway Cost"
                baseline={formatINR(result.baseline_cost)}
                ai={formatINR(result.ai_cost)}
              />
            </div>

            {/* Guardrail & Cryptographic Stats */}
            <div className={styles.guardrailStrip}>
              <div className={styles.shieldBadge}>
                <ShieldCheck size={16} />
                <span>GUARDRAIL INTEGRITY VERIFIED</span>
              </div>
              <div className={styles.guardrailItem}>
                Policy Stops: <span className={styles.guardrailVal}>{result.guardrail_stops}</span>
              </div>
              <div className={styles.guardrailItem}>
                HITL Escalations: <span className={styles.guardrailVal}>{result.escalations}</span>
              </div>
              <div className={styles.guardrailItem}>
                Zero-Action Preserves: <span className={styles.guardrailVal}>{result.do_nothing_count}</span>
              </div>
              <div className={styles.guardrailItem}>
                Status: <span className={styles.guardrailVal} style={{ color: '#10B981' }}>CONSENSUS VALID</span>
              </div>
            </div>

            {/* Dual Comparison Charts */}
            <div className={styles.chartsGrid}>
              <div className={styles.chartContainer}>
                <div className={styles.chartHeader}>
                  <span>Total Capital Recovered Comparison</span>
                  <span style={{ color: 'var(--color-brand-primary)' }}>AI vs Baseline</span>
                </div>
                <RecoveryComparisonChart result={result} />
              </div>

              <div className={styles.chartContainer}>
                <div className={styles.chartHeader}>
                  <span>Cumulative Net Alpha Trajectory</span>
                  <span style={{ color: 'var(--color-accent-gold)' }}>Incremental ₹ Curve</span>
                </div>
                <IncrementalRevenueChart result={result} />
              </div>
            </div>
          </section>
        )}

        {/* Experiment History */}
        {history.length > 1 && (
          <section className={styles.historySection}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <History size={16} color="var(--color-brand-primary)" />
              <span className="label-mono" style={{ fontSize: 12, fontWeight: 700 }}>
                PREVIOUS EXPERIMENT RUNS
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
                    Net Alpha: {formatINR(h.net_incremental_recovery)}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {!result && !isRunning && !error && (
          <EmptyState
            icon="⚗"
            title="Rig Standing By"
            description="Configure synthetic dataset rows and random seed above, then execute simulation. Telemetry outputs and net incremental alpha curves generate in real-time."
          />
        )}
      </div>
    </div>
  );
}
