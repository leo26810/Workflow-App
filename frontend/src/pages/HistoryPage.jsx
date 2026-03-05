import { useEffect, useMemo, useState } from 'react'

export default function HistoryPage() {
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    let alive = true
    const loadHistory = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch('/api/workflow-history')
        if (!res.ok) throw new Error(`Server-Fehler: ${res.status}`)
        const data = await res.json()
        if (!alive) return
        setEntries(Array.isArray(data) ? data : [])
      } catch (err) {
        if (!alive) return
        setError(err.message || 'Verlauf konnte nicht geladen werden')
      } finally {
        if (alive) setLoading(false)
      }
    }

    loadHistory()
    return () => { alive = false }
  }, [])

  const filteredEntries = useMemo(() => {
    const needle = search.trim().toLowerCase()
    if (!needle) return entries

    return entries.filter((item) => {
      const task = (item?.task_description || '').toLowerCase()
      const json = (item?.recommendation_json || '').toLowerCase()
      return task.includes(needle) || json.includes(needle)
    })
  }, [entries, search])

  const parseRecommendation = (entry) => {
    try {
      return JSON.parse(entry?.recommendation_json || '{}')
    } catch {
      return {}
    }
  }

  const cardStyle = {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: '10px',
    padding: '1rem',
  }

  return (
    <div style={{ padding: '2.2rem 2.7rem', maxWidth: '980px', margin: '0 auto' }}>
      <div style={{ marginBottom: '1.2rem' }}>
        <h1 style={{ margin: '0 0 0.35rem', fontSize: '1.9rem', fontWeight: 300, color: 'rgba(255,255,255,0.95)' }}>
          Verlauf
        </h1>
        <p style={{ margin: 0, color: 'rgba(255,255,255,0.45)', fontSize: '13px' }}>
          Alle bisherigen Empfehlungen, Bewertungen und Ergebnisse.
        </p>
      </div>

      <div style={{ ...cardStyle, marginBottom: '1rem', padding: '0.8rem' }}>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Verlauf durchsuchen..."
          style={{
            width: '100%',
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'rgba(255,255,255,0.85)',
            fontSize: '14px',
            fontFamily: 'Space Grotesk, sans-serif',
          }}
        />
      </div>

      {loading && <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: '0.85rem' }}>Lade Verlauf…</p>}
      {error && <p style={{ color: 'var(--danger)', fontSize: '0.85rem' }}>{error}</p>}

      {!loading && !error && !filteredEntries.length && (
        <div style={cardStyle}>
          <p style={{ margin: 0, color: 'rgba(255,255,255,0.6)', fontSize: '0.85rem' }}>Keine Einträge gefunden.</p>
        </div>
      )}

      {!loading && !error && filteredEntries.length > 0 && (
        <div style={{ display: 'grid', gap: '0.7rem' }}>
          {filteredEntries.map((entry) => {
            const recommendation = parseRecommendation(entry)
            const workflow = Array.isArray(recommendation.workflow) ? recommendation.workflow : []
            const toolNames = Array.isArray(recommendation.recommended_tools)
              ? recommendation.recommended_tools
                .map((tool) => (typeof tool === 'string' ? tool : tool?.name || ''))
                .filter(Boolean)
              : []

            return (
              <div key={entry.id} style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.8rem', flexWrap: 'wrap' }}>
                  <strong style={{ color: 'rgba(255,255,255,0.9)', fontSize: '14px', fontWeight: 600 }}>
                    #{entry.id} · {entry.task_description}
                  </strong>
                  <span style={{ color: 'rgba(255,255,255,0.45)', fontSize: '12px' }}>
                    {entry.created_at || 'n/a'}
                  </span>
                </div>

                <div style={{ marginTop: '0.55rem', fontSize: '13px', color: 'rgba(255,255,255,0.75)' }}>
                  <p style={{ margin: '0 0 0.35rem' }}>Bewertung: {entry.user_rating ?? '—'}</p>
                  {!!workflow.length && (
                    <p style={{ margin: '0 0 0.35rem' }}>
                      Schritte: {workflow.slice(0, 3).join(' | ')}
                    </p>
                  )}
                  {!!toolNames.length && (
                    <p style={{ margin: 0 }}>
                      Tools: {toolNames.slice(0, 5).join(', ')}
                    </p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
