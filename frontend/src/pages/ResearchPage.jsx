import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function ResearchPage() {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedIds, setExpandedIds] = useState({})

  const loadSessions = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/research-sessions')
      if (!res.ok) throw new Error('Recherche-Sessions konnten nicht geladen werden')
      const data = await res.json()
      setSessions(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message || 'Fehler beim Laden')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSessions()
  }, [])

  const filteredSessions = useMemo(() => {
    const needle = searchTerm.trim().toLowerCase()
    if (!needle) return sessions

    return sessions.filter(session => {
      const query = (session.query || '').toLowerCase()
      const tags = (session.tags || '').toLowerCase()
      return query.includes(needle) || tags.includes(needle)
    })
  }, [sessions, searchTerm])

  const toggleSession = (sessionId) => {
    setExpandedIds(prev => ({ ...prev, [sessionId]: !prev[sessionId] }))
  }

  const openInDashboard = (query) => {
    const target = `/dashboard?task=${encodeURIComponent(query)}`
    navigate(target)
  }

  const parseTags = (tagsString) => {
    if (!tagsString) return []
    return tagsString.split(',').map(tag => tag.trim()).filter(Boolean)
  }

  const hasSessions = sessions.length > 0
  const hasFilteredResults = filteredSessions.length > 0
  const counterLabel = loading
    ? 'Lädt…'
    : `${filteredSessions.length} gefunden`

  const emptyMessage = !hasSessions
    ? 'Noch keine Recherche-Sessions vorhanden. Starte im Dashboard eine Recherche und speichere sie, damit sie hier erscheint.'
    : `Keine Treffer für „${searchTerm.trim()}“. Passe deinen Suchbegriff an oder nutze einen Tag.`

  return (
    <div style={{ padding: '2rem 2.5rem', maxWidth: '1000px', margin: '0 auto' }}>
      <div style={{ marginBottom: '1.2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.8rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ margin: '0 0 0.35rem', fontSize: '1.6rem' }}>🔍 Recherche-Sessions</h1>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.88rem' }}>
            Übersicht deiner gespeicherten Recherchen aus dem Dashboard.
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={() => navigate('/?focus=recherche_info&subcategory=Informationsrecherche')}
        >
          Neue Recherche starten
        </button>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem', flexWrap: 'wrap' }}>
          <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', margin: 0 }}>
            Sessions filtern nach Query oder Tags
          </label>
          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>{counterLabel}</span>
        </div>
        <input
          className="input-field"
          placeholder="z. B. klimawandel, geschichte, quellen"
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
        />
      </div>

      {error && (
        <div style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: '10px', padding: '0.8rem', marginBottom: '1rem', color: 'var(--danger)', fontSize: '0.83rem' }}>
          ⚠️ {error}
        </div>
      )}

      {loading ? (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.84rem' }}>Lade Sessions…</p>
      ) : (
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          {filteredSessions.map(session => {
            const isExpanded = !!expandedIds[session.id]
            const tags = parseTags(session.tags)
            return (
              <div key={session.id} className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => toggleSession(session.id)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text)',
                      textAlign: 'left',
                      cursor: 'pointer',
                      padding: 0,
                      flex: 1,
                    }}
                  >
                    <h3 style={{ margin: '0 0 0.4rem', fontSize: '0.9rem' }}>
                      {isExpanded ? '▾' : '▸'} {session.query}
                    </h3>
                    <p style={{ margin: 0, fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                      {session.created_at ? new Date(session.created_at).toLocaleString() : '—'}
                    </p>
                  </button>

                  <button
                    onClick={() => openInDashboard(session.query)}
                    style={{
                      background: 'var(--bg)',
                      border: '1px solid var(--border)',
                      color: 'var(--text-muted)',
                      padding: '0.35rem 0.65rem',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.78rem'
                    }}
                  >
                    Als Basis nutzen
                  </button>
                </div>

                {!!tags.length && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.55rem' }}>
                    {tags.map((tag, idx) => (
                      <span
                        key={`${session.id}-${tag}-${idx}`}
                        style={{
                          fontSize: '0.72rem',
                          border: '1px solid rgba(96,165,250,0.25)',
                          color: 'var(--accent2)',
                          background: 'rgba(96,165,250,0.1)',
                          borderRadius: '999px',
                          padding: '2px 8px',
                        }}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

                {isExpanded && (
                  <div style={{ marginTop: '0.65rem', display: 'grid', gap: '0.45rem' }}>
                    {session.summary && (
                      <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.45 }}>
                        {session.summary}
                      </p>
                    )}

                    {!!session.sources?.length && (
                      <div style={{ display: 'grid', gap: '0.25rem' }}>
                        {session.sources.slice(0, 6).map((source, idx) => (
                          <a
                            key={idx}
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ fontSize: '0.76rem', color: 'var(--accent2)', textDecoration: 'none' }}
                          >
                            ↗ {source.title || source.url}
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}

          {!hasFilteredResults && (
            <div className="card">
              <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.84rem', lineHeight: 1.5 }}>
                {emptyMessage}
              </p>
              {hasSessions && (
                <button
                  onClick={() => setSearchTerm('')}
                  style={{
                    marginTop: '0.7rem',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    color: 'var(--text-muted)',
                    padding: '0.35rem 0.65rem',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '0.78rem'
                  }}
                >
                  Filter zurücksetzen
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
