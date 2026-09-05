/**
 * RecoveryOS — Action Expected-Value Bar Chart (Bitcoin DeFi Theme)
 */

import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ActionCandidate } from "../../types";
import { formatAction } from "../../services/api";

interface Props {
  candidates: ActionCandidate[];
  recommendedAction: string | null;
}

const COLOR_SELECTED = "#F7931A"; // Bitcoin Orange
const COLOR_ALLOWED = "#38BDF8";  // Cyan / Node
const COLOR_BLOCKED = "#334155";  // Dim boundary

function fmt(v: string | null | undefined): string {
  if (!v) return "₹0";
  const n = parseFloat(v);
  if (isNaN(n)) return "₹0";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as ActionCandidate;
  return (
    <div className="bg-[#0F1115] border border-[#F7931A]/40 rounded-xl p-3.5 shadow-[0_0_20px_rgba(247,147,26,0.25)] text-xs font-mono">
      <p className="text-[#FFD600] font-heading font-bold text-sm mb-1">
        {formatAction(d.action)}
      </p>
      <div className="space-y-1 text-[#94A3B8]">
        <p>P(Success): <strong className="text-white">{(d.probability * 100).toFixed(1)}%</strong></p>
        <p>Expected Net Alpha: <strong className="text-[#F7931A]">{fmt(d.expected_net_revenue)}</strong></p>
        <p className={`font-semibold ${d.allowed ? "text-[#34D399]" : "text-[#F87171]"}`}>
          {d.allowed ? "✓ Guardrail Passed" : `✗ Blocked: ${d.blocked_reason ?? "Policy Limit"}`}
        </p>
      </div>
    </div>
  );
}

export const ActionBarChart: React.FC<Props> = ({ candidates, recommendedAction }) => {
  if (!candidates.length) return null;

  const sorted = [...candidates].sort(
    (a, b) =>
      parseFloat(b.expected_net_revenue || "0") - parseFloat(a.expected_net_revenue || "0")
  );

  const data = sorted.map((c) => ({
    ...c,
    label: formatAction(c.action),
    enr: Math.max(parseFloat(c.expected_net_revenue || "0"), 0),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 8, right: 70, bottom: 8, left: 100 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: "#94A3B8", fontSize: 11, fontFamily: "JetBrains Mono" }}
          tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
          axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="label"
          tick={{ fill: "#FFFFFF", fontSize: 12, fontFamily: "Space Grotesk" }}
          axisLine={false}
          tickLine={false}
          width={95}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(247, 147, 26, 0.05)" }} />
        <Bar dataKey="enr" radius={[0, 6, 6, 0]}>
          <LabelList
            dataKey="enr"
            position="right"
            formatter={(v: any) => fmt(String(v))}
            style={{ fill: "#FFD600", fontSize: 11, fontFamily: "JetBrains Mono", fontWeight: 500 }}
          />
          {data.map((entry) => (
            <Cell
              key={entry.action}
              fill={
                entry.action === recommendedAction
                  ? COLOR_SELECTED
                  : entry.allowed
                  ? COLOR_ALLOWED
                  : COLOR_BLOCKED
              }
              opacity={entry.allowed ? 1 : 0.45}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};
export default ActionBarChart;
