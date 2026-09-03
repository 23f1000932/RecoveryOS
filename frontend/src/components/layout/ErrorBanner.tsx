/**
 * RecoveryOS — ErrorBanner component
 *
 * Inline error display with message and optional retry button.
 */

interface Props {
  message: string;
  onRetry?: () => void;
}

export function ErrorBanner({ message, onRetry }: Props) {
  return (
    <div style={{
      background: 'hsl(0,60%,12%)',
      border: '1px solid hsl(0,50%,30%)',
      borderRadius: 8,
      padding: '12px 16px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 16,
    }}>
      <p style={{ color: 'hsl(0,70%,65%)', fontSize: 13, margin: 0 }}>
        ⚠ {message}
      </p>
      {onRetry && (
        <button
          className="btn btn--secondary"
          onClick={onRetry}
          style={{ fontSize: 12, padding: '4px 12px', whiteSpace: 'nowrap' }}
        >
          Retry
        </button>
      )}
    </div>
  );
}
