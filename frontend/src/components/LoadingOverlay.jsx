export default function LoadingOverlay({ isVisible, message = 'Laden...', onCancel, variant = 'full' }) {
  if (!isVisible) return null

  const isFull = variant === 'full'
  const style = isFull
    ? {
      position: 'fixed',
      inset: 0,
      zIndex: 250,
      background: 'rgba(8,12,24,0.66)',
      display: 'grid',
      placeItems: 'center',
    }
    : {
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: '8px',
      background: 'rgba(255,255,255,0.03)',
      padding: '0.5rem 0.65rem',
      fontSize: '12px',
      color: 'rgba(255,255,255,0.82)',
    }

  const cardStyle = isFull
    ? {
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: '10px',
      background: 'rgba(10,22,40,0.95)',
      padding: '0.75rem 0.95rem',
      color: 'rgba(255,255,255,0.95)',
      fontSize: '13px',
      display: 'grid',
      gap: '0.5rem',
      minWidth: '220px',
    }
    : null

  const content = (
    <>
      <div>{message}</div>
      {onCancel && (
        <button
          onClick={onCancel}
          style={{
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: '6px',
            background: 'transparent',
            color: 'rgba(255,255,255,0.86)',
            fontSize: '12px',
            padding: '0.22rem 0.5rem',
            cursor: 'pointer',
            justifySelf: 'start',
          }}
        >
          Abbrechen
        </button>
      )}
    </>
  )

  if (isFull) {
    return <div style={style}><div style={cardStyle}>{content}</div></div>
  }

  return <div style={style}>{content}</div>
}
