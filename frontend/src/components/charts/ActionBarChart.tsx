/**
 * RecoveryOS — Action Expected-Value Bar Chart (Premium Fintech Theme)
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

const COLOR_SELECTED = "#F59E0B"; // Fintech Amber Gold
const COLOR_ALLOWED = "#10B981";  // Emerald Green
const COLOR_BLOCKED = "#475569";  // Charcoal Gray

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
    <div className="bg-[#0E131F] border border-[#F59E0B]/40 rounded-lg p-3.5 shadow-lg text-xs font-mono">
      <p className="text-[#F59E0B] font-heading font-bold text-sm mb-1">
        {formatAction(d.action)}
      </p>
      <div className="space-y-1 text-[#94A3B8]">
        <p>P(Success): <strong className="text-white">{(d.probability * 100).toFixed(1)}%</strong></p>
        <p>Expected Net Revenue: <strong className="text-[#F59E0B]">{fmt(d.expected_net_revenue)}</strong></p>
        <p className={`font-semibold ${d.allowed ? "text-[#10B981]" : "text-[#EF4444]"}`}>
          {d.allowed ? "✓ Guardrail Passed" : `✗ Blocked: ${d.blocked_reason ?? "Policy Limit"}`}
        </p>
      </div>
    </div>
  );
}

export const ActionBarChart: React.FC<Props> = ({ candidates, recommendedAction }) => {
  const chartData = candidates.map((c) => {
    const isSelected = c.action === recommendedAction;
    const net = parseFloat(c.expected_net_revenue) || 0;
    const fill = isSelected ? COLOR_SELECTED : c.allowed ? COLOR_ALLOWED : COLOR_BLOCKED;
    return {
      ...c,
      displayName: formatAction(c.action),
      netValue: Math.max(0, net),
      fill,
      isSelected,
    };
  });

  return (
    <div className="w-full h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 20, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" vertical={false} />
          <XAxis
            dataKey="displayName"
            tick={{ fill: "#94A3B8", fontSize: 11, fontFamily: "var(--font-body)" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#94A3B8", fontSize: 10, fontFamily: "var(--font-mono)" }}
            tickFormatter={(v: number) => `₹${v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v}`}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="netValue" radius={[4, 4, 0, 0]}>
            <LabelList
              dataKey="netValue"
              position="top"
              formatter={(val: unknown) => {
                const n = Number(val);
                return n > 0 ? (n >= 1000 ? `₹${(n / 1000).toFixed(1)}k` : `₹${n}`) : "₹0";
              }}
              style={{ fill: "#F8FAFC", fontSize: 10, fontFamily: "var(--font-mono)" }}
            />
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.fill}
                stroke={entry.isSelected ? "#F59E0B" : "transparent"}
                strokeWidth={entry.isSelected ? 2 : 0}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ActionBarChart;
