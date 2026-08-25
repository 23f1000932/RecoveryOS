/**
 * RecoveryOS — Simulator Page
 * Run A/B experiments and view results.
 * Fully wired in Phase 8.
 */

import { useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { api, formatINR, formatPercent } from '../services/api';
import type { SimulatorResult } from '../types';
import styles from './SimulatorPage.module.css';

export function SimulatorPage() {
  const [rows, setRows] = useState(1000);
  const [seed, setSeed] = useState(42);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulatorResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runSim = async () => {
    setLoading(true);
    setError(null);
    try {
      const { experiment_id } = await api.runSimulation({ rows, seed });
      // Phase 1 stub — in Phase 8 we poll for completion
      // For now, try to fetch immediately (will 404 until Phase 8 stores results)
      try {
        const res = await api.getExperiment(experiment_id);
        setResult(res);
      } catch {
        setResult(null);
        setError(`Experiment ${experiment_id.slice(0, 8)} started. Results will appear after Phase 8 is implemented.`);
      }
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`animate-enter ${styles.page}`}>
      <PageHeader
        label="Simulator"
        title="A/B Experiment Runner"
        subtitle="Compare Baseline vs RecoveryOS on identical synthetic datasets. Same seed = same latent outcomes."
      />

      <div className={styles.content}>
        {/* Configuration panel */}
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
                onChange={(e) => setSeed(parseInt(e.target.value, 10) || 42)}
              />
            </label>
            <div className={styles.fieldGroup} style={{ justifyContent: 'flex-end' }}>
              <button
                id="btn-run-simulation"
                className="btn btn--primary"
                onClick={runSim}
                disabled={loading}
              >
                {loading ? 'Running…' : 'Run Experiment'}
              </button>
            </div>
          </div>
          <p className={styles.configNote}>
            Same seed guarantees counterfactual validity: Baseline and RecoveryOS use identical latent payment outcomes.
          </p>
        </section>

        {error && (
          <div className={`card ${styles.notice}`} role="status">{error}</div>
        )}

        {/* Results */}
        {result ? (
          <section className={styles.results} aria-label="Experiment results">
            <p className={`label-mono ${styles.resultsLabel}`}>
              Experiment {result.experiment_id.slice(0, 8)} · {result.dataset_size} cases · Seed {result.seed}
            </p>
            <div className={styles.compareGrid}>
              <div className={`card ${styles.compareCard}`}>
                <p className={`label-mono ${styles.compareTitle}`}>Baseline</p>
                <p className={`metric-number ${styles.compareValue}`}>{formatINR(result.baseline_recovered)}</p>
                <p className={styles.compareRate}>{formatPercent(result.baseline_recovery_rate)} recovery rate</p>
              </div>
              <div className={`card card--featured ${styles.compareCard}`}>
                <p className={`label-mono ${styles.compareTitle}`}>RecoveryOS</p>
                <p className={`metric-number ${styles.compareValue}`}>{formatINR(result.ai_recovered)}</p>
                <p className={styles.compareRate}>{formatPercent(result.ai_recovery_rate)} recovery rate</p>
              </div>
              <div className={`card ${styles.compareCard}`}>
                <p className={`label-mono ${styles.compareTitle}`}>Incremental</p>
                <p className={`metric-number ${styles.compareValue}`}>{formatINR(result.incremental_recovery)}</p>
                <p className={styles.compareRate}>Net: {formatINR(result.net_incremental_recovery)}</p>
              </div>
            </div>
            <div className={styles.guardrailStats}>
              <span className="label-mono">Guardrail Stops: {result.guardrail_stops}</span>
              <span className="label-mono">Escalations: {result.escalations}</span>
              <span className="label-mono">Do Nothing: {result.do_nothing_count}</span>
            </div>
          </section>
        ) : !error && (
          <div className={`card ${styles.placeholder}`}>
            <p className={styles.placeholderText}>
              Configure an experiment above and click Run Experiment.
            </p>
            <p className={styles.placeholderHint}>
              Phase 8 wires the full experiment runner. Results will populate here.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
