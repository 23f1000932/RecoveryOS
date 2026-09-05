/**
 * RecoveryOS — Incremental Revenue Chart (design.md §20)
 *
 * Visualizes cumulative net incremental revenue across simulated cases.
 * Uses gold accent token hsl(35, 85%, 60%) to highlight the AI advantage over baseline.
 */

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { SimulatorResult } from '../../types';

interface Props {
  result: SimulatorResult;
}

function fmtCurrency(v: number): string {
  if (isNaN(v)) return '₹0';
  if (Math.abs(v) >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
  if (Math.abs(v) >= 1000) return `₹${(v / 1000).toFixed(1)}K`;
  return `₹${v.toFixed(0)}`;
}

export function IncrementalRevenueChart({ result }: Props) {
  const cases = result.cases || [];

  // Downsample or calculate cumulative curve (up to 50 points for smooth rendering)
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
      <div style={{ height: 240, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#666' }}>
        No case trajectory data available
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: 260 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 12, right: 20, bottom: 8, left: 16 }}>
          <defs>
            <linearGradient id="goldGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="hsl(35, 85%, 60%)" stopOpacity={0.4} />
              <stop offset="95%" stopColor="hsl(35, 85%, 60%)" stopOpacity={0.0} />
            </linearGradient>
            <linearGradient id="baseGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="hsl(210, 50%, 45%)" stopOpacity={0.2} />
              <stop offset="95%" stopColor="hsl(210, 50%, 45%)" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(0, 0%, 18%)" vertical={false} />
          <XAxis
            dataKey="caseIndex"
            tick={{ fill: '#888', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            label={{ value: 'Cases Processed', position: 'insideBottom', offset: -4, fill: '#666', fontSize: 11 }}
          />
          <YAxis
            tick={{ fill: '#888', fontSize: 11 }}
            tickFormatter={fmtCurrency}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(value: any, name: any) => [
              fmtCurrency(Number(value) || 0),
              name === 'cumulativeNetIncremental'
                ? 'Net Incremental (AI - Baseline - Cost)'
                : name === 'cumulativeAi'
                ? 'AI Total Recovered'
                : 'Baseline Recovered',
            ]}
            labelFormatter={(label) => `Case #${label}`}
            contentStyle={{
              background: 'hsl(0, 0%, 10%)',
              border: '1px solid hsl(0, 0%, 25%)',
              borderRadius: '6px',
              fontSize: '12px',
              color: '#fff',
            }}
          />
          <Area
            type="monotone"
            dataKey="cumulativeNetIncremental"
            stroke="hsl(35, 85%, 60%)"
            strokeWidth={2.5}
            fillOpacity={1}
            fill="url(#goldGradient)"
            name="cumulativeNetIncremental"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
