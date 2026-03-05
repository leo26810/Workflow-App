import { useEffect, useMemo, useState } from 'react'

export default function HistoryPage() {
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [minRating, setMinRating] = useState(0)
  const [page, setPage] = useState(1)
  const [pagination, setPagination] = useState({ page: 1, limit: 20, total: 0, pages: 0 })
  const [expandedId, setExpandedId] = useState(null)

  useEffect(() => {
    let alive = true
    const loadHistory = async () => {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({
          page: String(page),
          limit: '20',
        })
        if (search.trim()) params.set('search', search.trim())
        if (minRating > 0) params.set('min_rating', String(minRating))

        const res = await fetch(`/api/recommendation-feedback?${params.toString()}`)
        if (!res.ok) throw new Error(`Server-Fehler: ${res.status}`)
        const data = await res.json()
        if (!alive) return
        setEntries(Array.isArray(data?.items) ? data.items : [])
        setPagination(data?.pagination || { page: 1, limit: 20, total: 0, pages: 0 })
      } catch (err) {
        if (!alive) return
        setError(err.message || 'Verlauf konnte nicht geladen werden')
      } finally {
        if (alive) setLoading(false)
      }
    }

    loadHistory()
    return () => { alive = false }
  }, [page, search, minRating])

  const historyStats = useMemo(() => {
    const ratings = entries.map((item) => item?.user_rating).filter((value) => typeof value === 'number')
    const avgRating = ratings.length ? (ratings.reduce((acc, cur) => acc + cur, 0) / ratings.length).toFixed(2) : 'n/a'
    const acceptedCount = entries.filter((item) => item?.accepted === true).length
    const reusedCount = entries.filter((item) => item?.reused === true).length
    return {
      avgRating,
      acceptedCount,
      reusedCount,
      displayed: entries.length,
      total: pagination?.total || entries.length,
    }
  }, [entries, pagination])

  const parseRecommendation = (recommendationJson) => {
    try {
      return JSON.parse(recommendationJson || '{}')
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

      <div style={{ ...cardStyle, marginBottom: '0.8rem', display: 'grid', gap: '0.6rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.55rem' }}>
          <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.8)' }}>Ø Rating: {historyStats.avgRating}</div>
          <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.8)' }}>Accepted: {historyStats.acceptedCount}</div>
          <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.8)' }}>Reused: {historyStats.reusedCount}</div>
          <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.8)' }}>Einträge: {historyStats.displayed}/{historyStats.total}</div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 140px', gap: '0.55rem' }}>
          <input
            value={search}
            onChange={(e) => {
              setPage(1)
              setSearch(e.target.value)
            }}
            placeholder="Verlauf durchsuchen..."
            style={{
              width: '100%',
              background: 'transparent',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              outline: 'none',
              color: 'rgba(255,255,255,0.85)',
              fontSize: '14px',
              padding: '0.5rem 0.65rem',
              fontFamily: 'Space Grotesk, sans-serif',
            }}
          />

          <select
            value={minRating}
            onChange={(e) => {
              setPage(1)
              setMinRating(Number(e.target.value))
            }}
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              color: 'rgba(255,255,255,0.82)',
              fontSize: '13px',
              padding: '0.5rem 0.55rem',
              fontFamily: 'Space Grotesk, sans-serif',
            }}
          >
            <option value={0}>Alle Ratings</option>
            <option value={4}>≥ 4 Sterne</option>
            <option value={3}>≥ 3 Sterne</option>
            <option value={2}>≥ 2 Sterne</option>
            <option value={1}>≥ 1 Stern</option>
          </select>
        </div>
      </div>

      {loading && <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: '0.85rem' }}>Lade Verlauf…</p>}
      {error && <p style={{ color: 'var(--danger)', fontSize: '0.85rem' }}>{error}</p>}

      {!loading && !error && !entries.length && (
        <div style={cardStyle}>
          <p style={{ margin: 0, color: 'rgba(255,255,255,0.6)', fontSize: '0.85rem' }}>Keine Einträge gefunden.</p>
        </div>
      )}

      {!loading && !error && entries.length > 0 && (
        <div style={{ display: 'grid', gap: '0.7rem' }}>
          {entries.map((entry) => {
            const recommendation = parseRecommendation(entry?.history?.recommendation_json)
            const workflow = Array.isArray(recommendation.workflow) ? recommendation.workflow : []
            const toolNames = Array.isArray(recommendation.recommended_tools)
              ? recommendation.recommended_tools
                .map((tool) => (typeof tool === 'string' ? tool : tool?.name || ''))
                .filter(Boolean)
              : []
            const isExpanded = expandedId === entry.id

            return (
              <div key={entry.id} style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.8rem', flexWrap: 'wrap' }}>
                  <strong style={{ color: 'rgba(255,255,255,0.9)', fontSize: '14px', fontWeight: 600 }}>
                    #{entry.id} · {entry.task_description || entry?.history?.task_description || 'n/a'}
                  </strong>
                  <span style={{ color: 'rgba(255,255,255,0.45)', fontSize: '12px' }}>
                    {entry.updated_at || entry?.history?.created_at || 'n/a'}
                  </span>
                </div>

                <div style={{ marginTop: '0.55rem', fontSize: '13px', color: 'rgba(255,255,255,0.75)' }}>
                  <p style={{ margin: '0 0 0.35rem' }}>
                    Bewertung: {entry.user_rating ?? '—'} · Accepted: {entry.accepted === true ? 'ja' : entry.accepted === false ? 'nein' : '—'} · Reused: {entry.reused === true ? 'ja' : entry.reused === false ? 'nein' : '—'}
                  </p>
                  <p style={{ margin: '0 0 0.35rem' }}>Zeitersparnis: {entry.time_saved_minutes ?? '—'} Minuten</p>
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

                <div style={{ marginTop: '0.6rem' }}>
                  <button
                    onClick={() => setExpandedId((prev) => prev === entry.id ? null : entry.id)}
                    style={{
                      border: '1px solid rgba(255,255,255,0.1)',
                      background: 'rgba(255,255,255,0.04)',
                      color: 'rgba(255,255,255,0.78)',
                      borderRadius: '8px',
                      fontSize: '12px',
                      padding: '0.3rem 0.55rem',
                      cursor: 'pointer',
                      fontFamily: 'Space Grotesk, sans-serif',
                    }}
                  >
                    {isExpanded ? 'Details schließen' : 'Details öffnen'}
                  </button>
                </div>

                {isExpanded && (
                  <div style={{ marginTop: '0.65rem', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '0.6rem' }}>
                    <p style={{ margin: '0 0 0.3rem', fontSize: '12px', color: 'rgba(255,255,255,0.45)' }}>
                      Bereich: {entry.area || 'n/a'} · Unterkategorie: {entry.subcategory || 'n/a'}
                    </p>
                    {!!(entry.note || '').trim() && (
                      <p style={{ margin: '0 0 0.35rem', fontSize: '12px', color: 'rgba(255,255,255,0.72)' }}>
                        Notiz: {entry.note}
                      </p>
                    )}
                    {!!(recommendation.optimized_prompt || '').trim() && (
                      <pre style={{
                        margin: 0,
                        whiteSpace: 'pre-wrap',
                        fontSize: '11px',
                        color: 'rgba(79,255,176,0.78)',
                        background: 'rgba(0,0,0,0.25)',
                        border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: '8px',
                        padding: '0.55rem',
                      }}>
                        {recommendation.optimized_prompt}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            )
          })}

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.8rem' }}>
            <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>
              Seite {pagination.page} / {Math.max(1, pagination.pages || 1)}
            </span>
            <div style={{ display: 'flex', gap: '0.45rem' }}>
              <button
                onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                disabled={pagination.page <= 1}
                style={{
                  border: '1px solid rgba(255,255,255,0.1)',
                  background: 'rgba(255,255,255,0.04)',
                  color: 'rgba(255,255,255,0.8)',
                  borderRadius: '8px',
                  fontSize: '12px',
                  padding: '0.28rem 0.55rem',
                  cursor: pagination.page <= 1 ? 'default' : 'pointer',
                  opacity: pagination.page <= 1 ? 0.5 : 1,
                  fontFamily: 'Space Grotesk, sans-serif',
                }}
              >
                Zurück
              </button>
              <button
                onClick={() => setPage((prev) => prev + 1)}
                disabled={pagination.page >= (pagination.pages || 1)}
                style={{
                  border: '1px solid rgba(255,255,255,0.1)',
                  background: 'rgba(255,255,255,0.04)',
                  color: 'rgba(255,255,255,0.8)',
                  borderRadius: '8px',
                  fontSize: '12px',
                  padding: '0.28rem 0.55rem',
                  cursor: pagination.page >= (pagination.pages || 1) ? 'default' : 'pointer',
                  opacity: pagination.page >= (pagination.pages || 1) ? 0.5 : 1,
                  fontFamily: 'Space Grotesk, sans-serif',
                }}
              >
                Weiter
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
