/**
 * RecoveryOS — Incremental Revenue Chart (Premium Fintech Theme)
 */

import React from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SimulatorResult } from "../../types";

interface Props {
  result: SimulatorResult;
}

function fmtCurrency(v: number): string {
  if (isNaN(v)) return "₹0";
  if (Math.abs(v) >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
  if (Math.abs(v) >= 1000) return `₹${(v / 1000).toFixed(1)}K`;
  return `₹${v.toFixed(0)}`;
}

export const IncrementalRevenueChart: React.FC<Props> = ({ result }) => {
  const cases = result.cases || [];

  const step = Math.max(1, Math.floor(cases.length / 40));
  let runningIncremental = 0;
  let runningAi = 0;
  let runningBaseline = 0;

  const data: Array<{
    caseIndex: number;
    cumulativeNetIncremental: number;
    cumulativeAi: number;
    cumulativeBaseline: number;
  }> = [];

  cases.forEach((c, idx) => {
    const aiRec = parseFloat(c.ai_recovered) || 0;
    const baseRec = parseFloat(c.baseline_recovered) || 0;
    const cost = parseFloat(c.ai_cost) || 0;
    const netInc = (aiRec - baseRec) - cost;

    runningAi += aiRec;
    runningBaseline += baseRec;
    runningIncremental += netInc;

    if (idx % step === 0 || idx === cases.length - 1) {
      data.push({
        caseIndex: idx + 1,
        cumulativeNetIncremental: Math.round(runningIncremental),
        cumulativeAi: Math.round(runningAi),
        cumulativeBaseline: Math.round(runningBaseline),
      });
    }
  });

  if (data.length === 0) {
    return (
      <div className="h-60 flex items-center justify-center text-[#64748B] font-mono text-xs">
        No case trajectory data available
      </div>
    );
  }

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 12, right: 20, bottom: 8, left: 16 }}>
          <defs>
            <linearGradient id="fintechGlowGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.4} />
              <stop offset="50%" stopColor="#D97706" stopOpacity={0.12} />
              <stop offset="95%" stopColor="#06080D" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" vertical={false} />
          <XAxis
            dataKey="caseIndex"
            tick={{ fill: "#94A3B8", fontSize: 11, fontFamily: "var(--font-mono)" }}
            axisLine={false}
            tickLine={false}
            label={{ value: "Cases Evaluated", position: "insideBottom", offset: -4, fill: "#64748B", fontSize: 10, fontFamily: "var(--font-body)" }}
          />
          <YAxis
            tick={{ fill: "#94A3B8", fontSize: 11, fontFamily: "var(--font-mono)" }}
            tickFormatter={fmtCurrency}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(value: any, name: any) => [
              fmtCurrency(Number(value) || 0),
              name === "cumulativeNetIncremental"
                ? "Net Incremental Recovery"
                : name === "cumulativeAi"
                ? "RecoveryOS Total"
                : "Baseline Total",
            ]}
            labelFormatter={(label) => `Case #${label}`}
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
          <Area
            type="monotone"
            dataKey="cumulativeNetIncremental"
            stroke="#F59E0B"
            strokeWidth={3}
            fillOpacity={1}
            fill="url(#fintechGlowGradient)"
            name="cumulativeNetIncremental"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default IncrementalRevenueChart;
