/**
 * RecoveryOS — Action Expected-Value Bar Chart
 *
 * Horizontal bar chart showing Expected Net Revenue per action candidate.
 * Highlights the selected/recommended action.
 * Uses Recharts BarChart.
 */

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
} from 'recharts';
import type { ActionCandidate } from '../../types';
import { formatAction, formatINR } from '../../services/api';

interface Props {
  candidates: ActionCandidate[];
  recommendedAction: string | null;
}

const COLOR_SELECTED = 'hsl(35, 85%, 60%)';
const COLOR_ALLOWED  = 'hsl(210, 60%, 55%)';
const COLOR_BLOCKED  = 'hsl(0, 0%, 38%)';

function fmt(v: string | null | undefined): string {
  if (!v) return '₹0';
  const n = parseFloat(v);
  if (isNaN(n)) return '₹0';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0,
  }).format(n);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as ActionCandidate;
  return (
    <div style={{
      background: 'hsl(0,0%,10%)', border: '1px solid hsl(0,0%,20%)',
      borderRadius: 8, padding: '10px 14px', fontSize: 13,
    }}>
      <p style={{ color: 'hsl(35,85%,60%)', fontWeight: 700, marginBottom: 4 }}>
        {formatAction(d.action)}
      </p>
      <p style={{ color: '#ccc' }}>P(success): <b>{(d.probability * 100).toFixed(1)}%</b></p>
      <p style={{ color: '#ccc' }}>Exp. Net Revenue: <b>{fmt(d.expected_net_revenue)}</b></p>
      <p style={{ color: d.allowed ? '#6fc' : '#f88' }}>
        {d.allowed ? '✓ Allowed' : `✗ Blocked: ${d.blocked_reason ?? ''}`}
      </p>
    </div>
  );
}

export function ActionBarChart({ candidates, recommendedAction }: Props) {
  if (!candidates.length) return null;

  const sorted = [...candidates].sort((a, b) =>
    parseFloat(b.expected_net_revenue || '0') - parseFloat(a.expected_net_revenue || '0')
  );

  const data = sorted.map(c => ({
    ...c,
    label: formatAction(c.action),
    enr: Math.max(parseFloat(c.expected_net_revenue || '0'), 0),
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 60, bottom: 4, left: 90 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(0,0%,18%)" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: '#888', fontSize: 11 }}
          tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
          axisLine={{ stroke: 'hsl(0,0%,20%)' }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="label"
          tick={{ fill: '#ccc', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={86}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'hsl(0,0%,12%)' }} />
        <Bar dataKey="enr" radius={[0, 4, 4, 0]}>
          <LabelList
            dataKey="enr"
            position="right"
            formatter={(v: number) => fmt(String(v))}
            style={{ fill: '#aaa', fontSize: 11 }}
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
}
