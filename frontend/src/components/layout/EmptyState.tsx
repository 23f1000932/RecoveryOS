/**
 * RecoveryOS — EmptyState component
 *
 * Consistent empty state: icon, title, optional description + CTA.
 */

interface Props {
  icon?: string;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({ icon = '◌', title, description, action }: Props) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', gap: 12, padding: '48px 24px',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 40, opacity: 0.25 }}>{icon}</div>
      <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-text-primary)', margin: 0 }}>
        {title}
      </p>
      {description && (
        <p style={{ fontSize: 13, color: 'var(--color-text-muted)', margin: 0, maxWidth: 360 }}>
          {description}
        </p>
      )}
      {action && (
        <button className="btn btn--secondary" onClick={action.onClick} style={{ marginTop: 8 }}>
          {action.label}
        </button>
      )}
    </div>
  );
}
