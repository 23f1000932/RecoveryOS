/**
 * RecoveryOS — Recovery Comparison Chart (Bitcoin DeFi Theme)
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
    { name: "Fixed Baseline", value: parseFloat(result.baseline_recovered) || 0, fill: "#475569" },
    { name: "RecoveryOS AI", value: parseFloat(result.ai_recovered) || 0, fill: "#F7931A" },
    { name: "Gross Alpha", value: parseFloat(result.incremental_recovery) || 0, fill: "#FFD600" },
    { name: "Net Alpha", value: parseFloat(result.net_incremental_recovery) || 0, fill: "#34D399" },
  ];

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={amountData} margin={{ top: 12, right: 16, bottom: 8, left: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: "#FFFFFF", fontSize: 12, fontFamily: "Space Grotesk" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "#94A3B8", fontSize: 11, fontFamily: "JetBrains Mono" }}
          tickFormatter={fmtK}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(value: any) => [fmtK(value), "Amount"]}
          contentStyle={{
            background: "#0F1115",
            border: "1px solid rgba(247, 147, 26, 0.4)",
            borderRadius: "12px",
            fontSize: "12px",
            fontFamily: "JetBrains Mono",
            boxShadow: "0 0 20px rgba(247, 147, 26, 0.25)",
          }}
          labelStyle={{ color: "#FFFFFF", fontFamily: "Space Grotesk", fontWeight: "bold" }}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]}>
          {amountData.map((entry) => (
            <Cell key={entry.name} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};
export default RecoveryComparisonChart;
