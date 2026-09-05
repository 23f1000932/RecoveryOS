/**
 * RecoveryOS — Recovery Funnel Component (design.md §20)
 *
 * Funnel stages: Failed -> Eligible -> Actioned -> Recovered.
 * Renders conversion rate drop-offs and counts between pipeline stages.
 */

interface FunnelStep {
  label: string;
  count: number;
  color: string;
  description: string;
}

interface Props {
  totalFailed?: number;
  eligible?: number;
  actioned?: number;
  recovered?: number;
}

export function RecoveryFunnel({
  totalFailed = 100,
  eligible = 88,
  actioned = 80,
  recovered = 65,
}: Props) {
  const steps: FunnelStep[] = [
    {
      label: 'Failed Payments',
      count: totalFailed,
      color: 'hsl(0, 65%, 50%)',
      description: 'Ingested via webhook or simulator',
    },
    {
      label: 'Policy Eligible',
      count: eligible,
      color: 'hsl(210, 60%, 55%)',
      description: 'Passed guardrails & positive ENR',
    },
    {
      label: 'Intervention Actioned',
      count: actioned,
      color: 'hsl(35, 85%, 60%)',
      description: 'Optimal intervention dispatched',
    },
    {
      label: 'Successfully Recovered',
      count: recovered,
      color: 'hsl(140, 60%, 45%)',
      description: 'Payment settled & verified',
    },
  ];

  const maxVal = Math.max(...steps.map((s) => s.count), 1);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', width: '100%', padding: '8px 0' }}>
      {steps.map((step, idx) => {
        const pctOfTotal = ((step.count / maxVal) * 100).toFixed(0);
        const prevCount = idx > 0 ? steps[idx - 1].count : null;
        const convRate = prevCount && prevCount > 0 ? ((step.count / prevCount) * 100).toFixed(1) : null;

        return (
          <div key={step.label} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '13px' }}>
              <span style={{ fontWeight: 500, color: '#ddd' }}>{step.label}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {convRate && (
                  <span style={{ fontSize: '11px', color: '#888' }}>
                    {convRate}% from prev
                  </span>
                )}
                <span style={{ fontWeight: 600, color: step.color }}>
                  {step.count.toLocaleString()} ({pctOfTotal}%)
                </span>
              </div>
            </div>
            <div
              style={{
                width: '100%',
                height: '14px',
                background: 'hsl(0, 0%, 14%)',
                borderRadius: '4px',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${pctOfTotal}%`,
                  height: '100%',
                  background: step.color,
                  borderRadius: '4px',
                  transition: 'width 0.4s ease',
                }}
              />
            </div>
            <span style={{ fontSize: '11px', color: '#666' }}>{step.description}</span>
          </div>
        );
      })}
    </div>
  );
}
