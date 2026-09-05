/**
 * RecoveryOS — Recovery Funnel Component (Bitcoin DeFi Theme)
 */

import React from "react";

interface FunnelStep {
  label: string;
  count: number;
  color: string;
  glow: string;
  description: string;
}

interface Props {
  totalFailed?: number;
  eligible?: number;
  actioned?: number;
  recovered?: number;
}

export const RecoveryFunnel: React.FC<Props> = ({
  totalFailed = 100,
  eligible = 88,
  actioned = 80,
  recovered = 65,
}) => {
  const steps: FunnelStep[] = [
    {
      label: "1. Failed Ingestion",
      count: totalFailed,
      color: "#F87171",
      glow: "0 0 10px rgba(248, 113, 113, 0.4)",
      description: "Failed payments intercepted by webhook / simulator",
    },
    {
      label: "2. Policy & Guardrail Verified",
      count: eligible,
      color: "#38BDF8",
      glow: "0 0 10px rgba(56, 189, 248, 0.4)",
      description: "Passed 12 deterministic safety guardrails & positive ENR",
    },
    {
      label: "3. Action Candidate Dispatched",
      count: actioned,
      color: "#F7931A",
      glow: "0 0 12px rgba(247, 147, 26, 0.5)",
      description: "Optimal action dispatched via controlled adapter",
    },
    {
      label: "4. Settlement Recovered",
      count: recovered,
      color: "#FFD600",
      glow: "0 0 15px rgba(255, 214, 0, 0.6)",
      description: "Payment verified & ledger updated",
    },
  ];

  const maxVal = Math.max(...steps.map((s) => s.count), 1);

  return (
    <div className="flex flex-col gap-4 w-full py-2">
      {steps.map((step, idx) => {
        const pctOfTotal = ((step.count / maxVal) * 100).toFixed(0);
        const prevCount = idx > 0 ? steps[idx - 1].count : null;
        const convRate = prevCount && prevCount > 0 ? ((step.count / prevCount) * 100).toFixed(1) : null;

        return (
          <div key={step.label} className="flex flex-col gap-1.5">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="font-heading font-medium text-white text-sm">{step.label}</span>
              <div className="flex items-center gap-3">
                {convRate && (
                  <span className="text-[11px] text-[#94A3B8] bg-white/5 px-2 py-0.5 rounded">
                    {convRate}% conversion
                  </span>
                )}
                <span className="font-bold text-sm" style={{ color: step.color }}>
                  {step.count.toLocaleString()} ({pctOfTotal}%)
                </span>
              </div>
            </div>

            <div className="w-full h-3 rounded-full bg-[#1E293B] overflow-hidden p-0.5 border border-white/5">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${pctOfTotal}%`,
                  backgroundColor: step.color,
                  boxShadow: step.glow,
                }}
              />
            </div>

            <span className="text-[11px] font-mono text-[#64748B]">{step.description}</span>
          </div>
        );
      })}
    </div>
  );
};
export default RecoveryFunnel;
