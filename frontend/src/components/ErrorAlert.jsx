export default function ErrorAlert({ error, onRetry, onDismiss, isRetrying = false, variant = 'inline' }) {
  if (!error) return null

  const message = typeof error === 'string' ? error : (error?.message || 'Unbekannter Fehler')

  const baseStyle = {
    border: '1px solid rgba(255,120,120,0.35)',
    background: 'rgba(120,20,20,0.25)',
    color: 'rgba(255,230,230,0.95)',
    borderRadius: '8px',
    padding: '0.65rem 0.75rem',
    fontSize: '12px',
  }

  const containerStyle = variant === 'toast'
    ? {
      ...baseStyle,
      position: 'fixed',
      right: '1rem',
      bottom: '1rem',
      zIndex: 300,
      maxWidth: '360px',
    }
    : baseStyle

  return (
    <div role="alert" style={containerStyle}>
      <div style={{ marginBottom: '0.5rem' }}>{message}</div>
      <div style={{ display: 'flex', gap: '0.45rem' }}>
        {onRetry && (
          <button
            onClick={onRetry}
            disabled={isRetrying}
            style={{
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: '6px',
              background: 'rgba(255,255,255,0.08)',
              color: 'rgba(255,255,255,0.92)',
              fontSize: '12px',
              padding: '0.22rem 0.5rem',
              cursor: isRetrying ? 'default' : 'pointer',
              opacity: isRetrying ? 0.7 : 1,
            }}
          >
            {isRetrying ? 'Retry...' : 'Retry'}
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            style={{
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: '6px',
              background: 'transparent',
              color: 'rgba(255,255,255,0.82)',
              fontSize: '12px',
              padding: '0.22rem 0.5rem',
              cursor: 'pointer',
            }}
          >
            Schliessen
          </button>
        )}
      </div>
    </div>
  )
}
