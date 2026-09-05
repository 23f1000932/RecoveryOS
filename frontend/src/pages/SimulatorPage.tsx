/**
 * RecoveryOS — Simulator Page (Phase 7 — Full Implementation)
 *
 * Flow:
 *   1. User configures rows + seed
 *   2. POST /api/simulator/run → get experiment_id
 *   3. Poll GET /api/simulator/{id} every 2s (max 60 attempts)
 *   4. On success → show metric cards + RecoveryComparisonChart
 *   5. Keep last 3 experiment results in history
 */

import { useEffect, useRef, useState } from 'react';
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

interface MetricPairProps {
  label: string;
  baseline: string;
  ai: string;
  highlight?: boolean;
}

function MetricPair({ label, baseline, ai, highlight }: MetricPairProps) {
  return (
    <div className={`${styles.metricPair} ${highlight ? styles.metricPairHighlight : ''}`}>
      <p className={styles.pairLabel}>{label}</p>
      <div className={styles.pairRow}>
        <div className={styles.pairCol}>
          <p className={styles.pairTag}>Baseline</p>
          <p className={styles.pairValue}>{baseline}</p>
        </div>
        <div className={styles.pairCol}>
          <p className={styles.pairTag} style={{ color: 'hsl(35,85%,60%)' }}>RecoveryOS AI</p>
          <p className={styles.pairValue} style={{ color: 'hsl(35,85%,68%)' }}>{ai}</p>
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
      setError(`Experiment timed out after ${MAX_POLL_ATTEMPTS * POLL_INTERVAL_MS / 1000}s. The backend may still be running — try fetching manually.`);
      return;
    }

    setPollAttempt(attempt + 1);

    api.getExperiment(experimentId)
      .then((res) => {
        setPolling(false);
        setResult(res);
        setHistory((h) => [res, ...h].slice(0, 3));
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
          setError('Failed to retrieve experiment results.');
        }
      });
  };

  const isRunning = loading || polling;

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Simulator"
        title="A/B Experiment Runner"
        subtitle="Compare Baseline (fixed retry) vs RecoveryOS AI on identical synthetic datasets. Same seed = same latent outcomes."
      />

      <div className={styles.content}>
        {/* Configuration */}
        <section className={`card ${styles.configCard}`} aria-label="Simulation configuration">
          <p className={`label-mono ${styles.configLabel}`}>Experiment Configuration</p>
          <div className={styles.configRow}>
            <label className={styles.fieldGroup} htmlFor="sim-rows">
              <span className="label-mono">Dataset Rows</span>
              <input
                id="sim-rows"
                className={`input ${styles.numberInput}`}
                type="number"
                min={10}
                max={50000}
                value={rows}
                disabled={isRunning}
                onChange={(e) => setRows(parseInt(e.target.value, 10) || 1000)}
              />
            </label>
            <label className={styles.fieldGroup} htmlFor="sim-seed">
              <span className="label-mono">Random Seed</span>
              <input
                id="sim-seed"
                className={`input ${styles.numberInput}`}
                type="number"
                value={seed}
                disabled={isRunning}
                onChange={(e) => setSeed(parseInt(e.target.value, 10) || 42)}
              />
            </label>
            <div className={styles.fieldGroup} style={{ justifyContent: 'flex-end' }}>
              <button
                id="btn-run-simulation"
                className="btn btn--primary"
                onClick={runSim}
                disabled={isRunning}
              >
                {loading ? 'Starting…' : polling ? `Waiting… (${pollAttempt}/${MAX_POLL_ATTEMPTS})` : '▶ Run Experiment'}
              </button>
            </div>
          </div>

          {/* Progress bar */}
          {polling && (
            <div className={styles.progressBar}>
              <div
                className={styles.progressFill}
                style={{ width: `${(pollAttempt / MAX_POLL_ATTEMPTS) * 100}%` }}
              />
            </div>
          )}

          {polling && (
            <p className={styles.pollingHint}>
              ⏳ Experiment running on backend ({rows.toLocaleString()} cases)…
              Results appear in {Math.max(0, 5 - pollAttempt * 2)}–{Math.max(5, 30 - pollAttempt * 2)}s.
            </p>
          )}
        </section>

        {error && (
          <ErrorBanner message={error} onRetry={() => setError(null)} />
        )}

        {/* Results */}
        {result && (
          <section className="card" style={{ marginTop: 16 }}>
            <div className={styles.resultsHeader}>
              <p className="label-mono">Results — Seed {result.seed} · {result.dataset_size.toLocaleString()} cases</p>
              <p className={styles.policyLine}>{result.baseline_policy} vs {result.ai_policy}</p>
            </div>

            {/* Metric pairs */}
            <div className={styles.metricGrid}>
              <MetricPair
                label="Total Recovered"
                baseline={formatINR(result.baseline_recovered)}
                ai={formatINR(result.ai_recovered)}
              />
              <MetricPair
                label="Recovery Rate"
                baseline={formatPercent(result.baseline_recovery_rate)}
                ai={formatPercent(result.ai_recovery_rate)}
              />
              <MetricPair
                label="Intervention Cost"
                baseline={formatINR(result.baseline_cost)}
                ai={formatINR(result.ai_cost)}
              />
            </div>

            {/* Incremental highlight */}
            <div className={styles.incrementalRow}>
              <div className={styles.incrementalCard}>
                <p className={styles.incLabel}>Incremental Recovery</p>
                <p className={styles.incValue}>{formatINR(result.incremental_recovery)}</p>
              </div>
              <div className={`${styles.incrementalCard} ${styles.incrementalNet}`}>
                <p className={styles.incLabel}>Net Incremental Recovery</p>
                <p className={styles.incValue} style={{ color: 'hsl(140,55%,60%)' }}>
                  {formatINR(result.net_incremental_recovery)}
                </p>
              </div>
            </div>

            {/* Guardrail stats */}
            <div className={styles.guardrailStats}>
              <span className="label-mono" style={{ fontSize: 11 }}>
                Guardrail Stops: <b>{result.guardrail_stops}</b>
              </span>
              <span className="label-mono" style={{ fontSize: 11 }}>
                Escalations: <b>{result.escalations}</b>
              </span>
              <span className="label-mono" style={{ fontSize: 11 }}>
                Do Nothing: <b>{result.do_nothing_count}</b>
              </span>
            </div>

            {/* Charts */}
            <div style={{ marginTop: 24, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
              <div>
                <p className="label-mono" style={{ marginBottom: 8, fontSize: 11 }}>
                  Recovery Comparison (₹)
                </p>
                <RecoveryComparisonChart result={result} />
              </div>
              <div>
                <p className="label-mono" style={{ marginBottom: 8, fontSize: 11 }}>
                  Cumulative Net Incremental Trajectory (₹)
                </p>
                <IncrementalRevenueChart result={result} />
              </div>
            </div>
          </section>
        )}

        {/* History */}
        {history.length > 1 && (
          <section className="card" style={{ marginTop: 16 }}>
            <p className="label-mono" style={{ marginBottom: 12 }}>Recent Experiments</p>
            <div className={styles.historyList}>
              {history.map((h) => (
                <div
                  key={h.experiment_id}
                  className={styles.historyRow}
                  onClick={() => setResult(h)}
                  role="button"
                  tabIndex={0}
                >
                  <span className={styles.historyId}>{h.experiment_id.slice(0, 8)}</span>
                  <span className={styles.historyMeta}>Seed {h.seed} · {h.dataset_size} rows</span>
                  <span className={styles.historyNet}>Net: {formatINR(h.net_incremental_recovery)}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {!result && !isRunning && !error && (
          <EmptyState
            icon="⚗"
            title="No experiment yet"
            description="Configure rows and seed, then click Run Experiment. Results appear within 5–30 seconds depending on dataset size."
          />
        )}
      </div>
    </div>
  );
}
