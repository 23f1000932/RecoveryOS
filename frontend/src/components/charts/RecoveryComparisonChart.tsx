/**
 * RecoveryOS — Recovery Comparison Chart
 *
 * Grouped bar chart: Baseline Recovered vs AI Recovered.
 * Shows incremental recovery visually.
 * Used on SimulatorPage.
 */

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { SimulatorResult } from '../../types';

interface Props {
  result: SimulatorResult;
}

function fmtK(v: string | number): string {
  const n = typeof v === 'string' ? parseFloat(v) : v;
  if (isNaN(n)) return '₹0';
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
  if (n >= 1000) return `₹${(n / 1000).toFixed(0)}K`;
  return `₹${n.toFixed(0)}`;
}

export function RecoveryComparisonChart({ result }: Props) {
  const data = [
    {
      name: 'Recovered',
      Baseline: parseFloat(result.baseline_recovered) || 0,
      'RecoveryOS AI': parseFloat(result.ai_recovered) || 0,
    },
    {
      name: 'Recovery Rate',
      Baseline: parseFloat((result.baseline_recovery_rate * 100).toFixed(1)) || 0,
      'RecoveryOS AI': parseFloat((result.ai_recovery_rate * 100).toFixed(1)) || 0,
    },
  ];

  // Two separate charts — amounts + rate
  const amountData = [
    { name: 'Baseline', value: parseFloat(result.baseline_recovered) || 0, fill: 'hsl(210,50%,45%)' },
    { name: 'RecoveryOS AI', value: parseFloat(result.ai_recovered) || 0, fill: 'hsl(35,85%,60%)' },
    { name: 'Incremental', value: parseFloat(result.incremental_recovery) || 0, fill: 'hsl(140,50%,45%)' },
    { name: 'Net Incremental', value: parseFloat(result.net_incremental_recovery) || 0, fill: 'hsl(280,50%,55%)' },
  ];

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={amountData} margin={{ top: 8, right: 16, bottom: 8, left: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(0,0%,18%)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: '#ccc', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#888', fontSize: 11 }}
          tickFormatter={fmtK}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(value: number) => fmtK(value)}
          contentStyle={{
            background: 'hsl(0,0%,10%)',
            border: '1px solid hsl(0,0%,20%)',
            borderRadius: 8,
            fontSize: 13,
          }}
          labelStyle={{ color: '#ccc' }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {amountData.map((entry) => (
            <Cell key={entry.name} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
