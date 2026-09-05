/**
 * RecoveryOS — Recovery Comparison Chart (Premium Fintech Theme)
 */

import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SimulatorResult } from "../../types";

interface Props {
  result: SimulatorResult;
}

function fmtK(v: string | number): string {
  const n = typeof v === "string" ? parseFloat(v) : v;
  if (isNaN(n)) return "₹0";
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
  if (n >= 1000) return `₹${(n / 1000).toFixed(0)}K`;
  return `₹${n.toFixed(0)}`;
}

export const RecoveryComparisonChart: React.FC<Props> = ({ result }) => {
  const amountData = [
    { name: "Baseline Retry", value: parseFloat(result.baseline_recovered) || 0, fill: "#475569" },
    { name: "RecoveryOS AI", value: parseFloat(result.ai_recovered) || 0, fill: "#F59E0B" },
    { name: "Incremental Recovery", value: parseFloat(result.incremental_recovery) || 0, fill: "#D97706" },
    { name: "Net Incremental", value: parseFloat(result.net_incremental_recovery) || 0, fill: "#10B981" },
  ];

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={amountData} margin={{ top: 12, right: 16, bottom: 8, left: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: "#F8FAFC", fontSize: 11, fontFamily: "var(--font-body)" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "#94A3B8", fontSize: 11, fontFamily: "var(--font-mono)" }}
          tickFormatter={fmtK}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(value: any) => [fmtK(value), "Amount"]}
          contentStyle={{
            background: "#0E131F",
            border: "1px solid rgba(245, 158, 11, 0.3)",
            borderRadius: "8px",
            fontSize: "12px",
            color: "#F8FAFC",
            fontFamily: "var(--font-mono)",
            boxShadow: "0 4px 14px rgba(0, 0, 0, 0.5)",
          }}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]}>
          {amountData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

export default RecoveryComparisonChart;
