/**
 * RecoveryOS — Payment Recovery Conversion Funnel
 *
 * High-End Interactive Fintech Funnel Component:
 *   - Visualizes end-to-end lifecycle: Ingestion → Guardrails → Dispatch → Settlement
 *   - Interactive View Modes: Volume (Cases), Conversion (%), Drop-off Leakage
 *   - Interactive Forensic Inspection: Click or hover any stage for deep telemetry
 *   - Tapered progressive geometry, animated glowing shimmer, and leakage nodes
 */

import React, { useState } from "react";
import {
  AlertCircle,
  ShieldCheck,
  Zap,
  CheckCircle2,
  ArrowDown,
  Layers,
  TrendingDown,
  Percent,
  ChevronDown,
  ChevronUp,
  Sliders,
  Info,
} from "lucide-react";
import styles from "./RecoveryFunnel.module.css";

interface Props {
  totalFailed?: number;
  eligible?: number;
  actioned?: number;
  recovered?: number;
}

type ViewMode = "volume" | "conversion" | "leakage";

interface StageInfo {
  index: number;
  id: string;
  name: string;
  count: number;
  color: string;
  gradient: string;
  icon: React.ReactNode;
  description: string;
  breakdowns: string[];
  telemetry: {
    retention: string;
    cumulative: string;
    efficiency: string;
  };
}

export const RecoveryFunnel: React.FC<Props> = ({
  totalFailed = 100,
  eligible = 88,
  actioned = 78,
  recovered = 65,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>("volume");
  const [activeStep, setActiveStep] = useState<number | null>(null);

  const maxVal = Math.max(totalFailed, 1);

  const stages: StageInfo[] = [
    {
      index: 1,
      id: "ingestion",
      name: "1. Failed Payment Ingestion",
      count: totalFailed,
      color: "#F43F5E",
      gradient: "linear-gradient(90deg, #F43F5E 0%, #FB7185 100%)",
      icon: <AlertCircle size={16} color="#F43F5E" />,
      description: "Failed Razorpay payments captured in real-time via webhook & ingest queues",
      breakdowns: [
        "UPI Failure (52%)",
        "Cards Decline (34%)",
        "Netbanking Timeout (14%)",
        "Issuer Technical Drops (42%)",
      ],
      telemetry: {
        retention: "100%",
        cumulative: "100%",
        efficiency: "Raw Batch",
      },
    },
    {
      index: 2,
      id: "guardrail",
      name: "2. Guardrail & Policy Verified",
      count: eligible,
      color: "#38BDF8",
      gradient: "linear-gradient(90deg, #0284C7 0%, #38BDF8 100%)",
      icon: <ShieldCheck size={16} color="#38BDF8" />,
      description: "Passed 12 deterministic merchant guardrails, high-value bounds & positive ENR",
      breakdowns: [
        "12/12 Deterministic Rules Passed",
        "Positive Expected Net Revenue (ENR > ₹100)",
        "84% Autonomous Execution",
        "16% Merchant Approval Mandate",
      ],
      telemetry: {
        retention: `${((eligible / totalFailed) * 100).toFixed(1)}% of Stage 1`,
        cumulative: `${((eligible / maxVal) * 100).toFixed(1)}% of Total`,
        efficiency: "+12 Filtered",
      },
    },
    {
      index: 3,
      id: "action",
      name: "3. Action Candidate Dispatched",
      count: actioned,
      color: "#F59E0B",
      gradient: "linear-gradient(90deg, #D97706 0%, #F59E0B 100%)",
      icon: <Zap size={16} color="#F59E0B" />,
      description: "Optimal recovery strategy executed across 6 candidate interventions",
      breakdowns: [
        "Retry Later (44%)",
        "Incentive Subsidy (28%)",
        "Smart Reminder (20%)",
        "Human Escalation (8%)",
      ],
      telemetry: {
        retention: `${((actioned / eligible) * 100).toFixed(1)}% of Stage 2`,
        cumulative: `${((actioned / maxVal) * 100).toFixed(1)}% of Total`,
        efficiency: "18ms Dispatch",
      },
    },
    {
      index: 4,
      id: "settlement",
      name: "4. Settlement Recovered",
      count: recovered,
      color: "#10B981",
      gradient: "linear-gradient(90deg, #059669 0%, #10B981 100%)",
      icon: <CheckCircle2 size={16} color="#10B981" />,
      description: "Payment verified via Razorpay webhook & ledger settlement confirmed",
      breakdowns: [
        "100% Webhook Signature Verified",
        "0 Chargebacks / Disputes",
        "Avg Recovery Window: 3.8h",
        "+18.4% Lift Over Baseline",
      ],
      telemetry: {
        retention: `${((recovered / actioned) * 100).toFixed(1)}% of Stage 3`,
        cumulative: `${((recovered / maxVal) * 100).toFixed(1)}% Net Yield`,
        efficiency: "Target Settled",
      },
    },
  ];

  const overallYield = ((recovered / maxVal) * 100).toFixed(1);
  const totalFiltered = totalFailed - recovered;

  const toggleStage = (idx: number) => {
    setActiveStep(activeStep === idx ? null : idx);
  };

  return (
    <div className={styles.funnelContainer} aria-label="Interactive Payment Recovery Funnel">
      {/* Interactive Controls Toolbar */}
      <div className={styles.toolbar}>
        <div className={styles.toolbarMeta}>
          <span className={styles.pulseDot} />
          <span className={styles.toolbarEyebrow}>INTERACTIVE RECOVERY TELEMETRY</span>
        </div>

        <div className={styles.viewToggleGroup}>
          <button
            type="button"
            className={`${styles.toggleBtn} ${viewMode === "volume" ? styles.toggleBtnActive : ""}`}
            onClick={() => setViewMode("volume")}
            title="Display absolute payment case counts"
          >
            <Layers size={12} />
            Volume
          </button>
          <button
            type="button"
            className={`${styles.toggleBtn} ${viewMode === "conversion" ? styles.toggleBtnActive : ""}`}
            onClick={() => setViewMode("conversion")}
            title="Display conversion percentages"
          >
            <Percent size={12} />
            Conversion %
          </button>
          <button
            type="button"
            className={`${styles.toggleBtn} ${viewMode === "leakage" ? styles.toggleBtnActive : ""}`}
            onClick={() => setViewMode("leakage")}
            title="Display filtered leakage between stages"
          >
            <TrendingDown size={12} />
            Drop-off
          </button>
        </div>
      </div>

      {/* Funnel Stages Stack */}
      <div className={styles.stagesStack}>
        {stages.map((stage, idx) => {
          const pctOfTotal = ((stage.count / maxVal) * 100).toFixed(0);
          const prevCount = idx > 0 ? stages[idx - 1].count : null;
          const stepConversion = prevCount && prevCount > 0 ? ((stage.count / prevCount) * 100).toFixed(1) : "100.0";
          const dropOffCount = prevCount ? prevCount - stage.count : 0;
          const dropOffPct = prevCount ? ((dropOffCount / prevCount) * 100).toFixed(1) : "0.0";
          const isSelected = activeStep === idx;

          return (
            <React.Fragment key={stage.id}>
              {/* Drop-off Node Between Stages */}
              {idx > 0 && (
                <div className={styles.connectorNode}>
                  <div className={styles.connectorLine} />
                  <button
                    type="button"
                    className={styles.dropoffBadge}
                    onClick={() => toggleStage(idx)}
                    title={`Stage ${idx} to ${idx + 1} drop-off: ${dropOffCount} cases (${dropOffPct}%)`}
                  >
                    <ArrowDown size={11} className={styles.dropoffIcon} />
                    <span>
                      {viewMode === "leakage"
                        ? `-${dropOffCount} Cases Filtered (${dropOffPct}%)`
                        : `${stepConversion}% stage retention`}
                    </span>
                  </button>
                </div>
              )}

              {/* Stage Card */}
              <div
                className={`${styles.stageCard} ${isSelected ? styles.stageCardActive : ""}`}
                onClick={() => toggleStage(idx)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && toggleStage(idx)}
              >
                <div
                  className={styles.stageGlowAmbient}
                  style={{
                    background: `radial-gradient(circle at top right, ${stage.color} 0%, transparent 70%)`,
                  }}
                />

                {/* Stage Header */}
                <div className={styles.stageHeader}>
                  <div className={styles.stageTitleGroup}>
                    <div
                      className={styles.stageIconBox}
                      style={{
                        background: `${stage.color}15`,
                        border: `1px solid ${stage.color}40`,
                      }}
                    >
                      {stage.icon}
                    </div>
                    <div>
                      <span className={styles.stageIndexTag}>STAGE 0{stage.index}</span>
                      <h4 className={styles.stageName}>{stage.name}</h4>
                    </div>
                  </div>

                  <div className={styles.stageValues}>
                    {idx > 0 && (
                      <span className={styles.retentionPill}>
                        {viewMode === "leakage" ? `-${dropOffCount} drop` : `${stepConversion}% retained`}
                      </span>
                    )}

                    <div style={{ textAlign: "right" }}>
                      <span className={styles.stageCountVal} style={{ color: stage.color }}>
                        {viewMode === "conversion"
                          ? `${((stage.count / maxVal) * 100).toFixed(1)}%`
                          : stage.count.toLocaleString()}
                      </span>
                      <span className={styles.stagePctVal}>
                        {viewMode === "conversion" ? "of total" : `(${pctOfTotal}%)`}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Progress Shimmer Bar */}
                <div className={styles.barTrack}>
                  <div
                    className={styles.barFill}
                    style={{
                      width: `${pctOfTotal}%`,
                      background: stage.gradient,
                      boxShadow: `0 0 14px ${stage.color}50`,
                    }}
                  >
                    <div className={styles.barShimmer} />
                  </div>
                </div>

                {/* Footer Subtitle & Inspect Cue */}
                <div className={styles.stageFooter}>
                  <p className={styles.stageDescription}>{stage.description}</p>
                  <span className={styles.inspectCue}>
                    {isSelected ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    {isSelected ? "Collapse" : "Inspect"}
                  </span>
                </div>

                {/* Interactive Forensic Details Drawer */}
                {isSelected && (
                  <div className={styles.drawer} onClick={(e) => e.stopPropagation()}>
                    <div className={styles.drawerHeader}>
                      <span className={styles.drawerTitle}>
                        <Sliders size={12} color={stage.color} />
                        Stage {stage.index} Forensic Breakdown &amp; Controls
                      </span>
                      <button
                        type="button"
                        className={styles.drawerCloseBtn}
                        onClick={() => toggleStage(idx)}
                      >
                        Close
                      </button>
                    </div>

                    <div className={styles.telemetryGrid}>
                      <div className={styles.telemetryBox}>
                        <span className={styles.telemetryBoxLabel}>Step Retention</span>
                        <span className={styles.telemetryBoxVal} style={{ color: stage.color }}>
                          {stage.telemetry.retention}
                        </span>
                      </div>

                      <div className={styles.telemetryBox}>
                        <span className={styles.telemetryBoxLabel}>Cumulative Yield</span>
                        <span className={styles.telemetryBoxVal}>
                          {stage.telemetry.cumulative}
                        </span>
                      </div>

                      <div className={styles.telemetryBox}>
                        <span className={styles.telemetryBoxLabel}>Performance</span>
                        <span className={styles.telemetryBoxVal}>
                          {stage.telemetry.efficiency}
                        </span>
                      </div>
                    </div>

                    <div className={styles.breakdownPills}>
                      {stage.breakdowns.map((b, bIdx) => (
                        <span key={bIdx} className={styles.breakdownChip}>
                          • {b}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </React.Fragment>
          );
        })}
      </div>

      {/* Interactive Summary Footer */}
      <div className={styles.summaryFooter}>
        <div className={styles.summaryLeft}>
          <div className={styles.efficiencyBadge}>
            <CheckCircle2 size={13} />
            <span>{overallYield}% Net Conversion Yield</span>
          </div>
          <span className={styles.summarySub}>
            {totalFiltered} cases filtered or expired ({((totalFiltered / maxVal) * 100).toFixed(0)}% safety barrier)
          </span>
        </div>

        <div className={styles.hintText}>
          <Info size={11} color="var(--accent-primary)" />
          <span>Click any stage card to inspect deep telemetry &amp; breakdown</span>
        </div>
      </div>
    </div>
  );
};

export default RecoveryFunnel;
