import { useState, useRef } from 'react'

const EXAMPLE_TASKS = [
  "Ich brauche ein Titelbild für meine Präsentation über den Regenwald.",
  "Ein Gedicht über den Frühling analysieren",
  "Vorbereitung auf die Mathe-Klausur über quadratische Gleichungen",
  "Logo erstellen für mein Schulprojekt 'Römisches Reich'",
  "Recherche über die Ursachen des Ersten Weltkriegs",
]

export default function Dashboard() {
  const [task, setTask] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [copiedPrompt, setCopiedPrompt] = useState(false)
  const resultRef = useRef(null)

  const handleGetRecommendation = async () => {
    if (!task.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch('/api/recommendation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_description: task })
      })
      if (!res.ok) throw new Error('Server-Fehler: ' + res.status)
      const data = await res.json()
      setResult(data)
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
    } catch (err) {
      setError(err.message || 'Verbindungsfehler. Ist das Backend gestartet?')
    } finally {
      setLoading(false)
    }
  }

  const handleCopyPrompt = () => {
    navigator.clipboard.writeText(result?.recommendation?.optimized_prompt || '')
    setCopiedPrompt(true)
    setTimeout(() => setCopiedPrompt(false), 2000)
  }

  return (
    <div style={{ padding: '2rem 2.5rem', maxWidth: '900px', margin: '0 auto' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ margin: '0 0 0.4rem', fontSize: '1.75rem', fontWeight: 700 }}>
          ⚡ Workflow Dashboard
        </h1>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Beschreibe deine Aufgabe und erhalte einen optimierten KI-Workflow.
        </p>
      </div>

      {/* Input Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-muted)' }}>
          AKTUELLE AUFGABE
        </label>
        <textarea
          className="textarea-field"
          placeholder="Beispiel: Ich brauche ein Titelbild für meine Präsentation über den Regenwald."
          value={task}
          onChange={e => setTask(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleGetRecommendation() }}
          rows={3}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>⌘+Enter zum Absenden</p>
          <button className="btn-primary" onClick={handleGetRecommendation} disabled={!task.trim() || loading}>
            {loading ? '⏳ Analysiere...' : '✦ Empfehlung anfordern'}
          </button>
        </div>
      </div>

      {/* Example tasks */}
      <div style={{ marginBottom: '2rem' }}>
        <p style={{ margin: '0 0 0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 500 }}>BEISPIELE:</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
          {EXAMPLE_TASKS.map((ex, i) => (
            <button key={i} onClick={() => setTask(ex)} style={{
              background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-muted)',
              padding: '0.3rem 0.75rem', borderRadius: '20px', fontSize: '0.78rem', cursor: 'pointer',
              fontFamily: 'Space Grotesk, sans-serif', transition: 'all 0.15s',
            }}>{ex.length > 55 ? ex.slice(0, 53) + '…' : ex}</button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: '10px', padding: '1rem', marginBottom: '1.5rem', color: 'var(--danger)', fontSize: '0.875rem' }}>
          ⚠️ {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div ref={resultRef} className="animate-slide-in">
          {result.mode === 'demo' && (
            <div style={{ background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.25)', borderRadius: '8px', padding: '0.7rem 1rem', marginBottom: '1rem', fontSize: '0.8rem', color: 'var(--warning)' }}>
              ⚠️ <strong>Demo-Modus:</strong> Setze deinen Groq API-Key in <code>backend/.env</code> für echte KI-Empfehlungen (kostenlos auf console.groq.com).
            </div>
          )}

          <div style={{ display: 'grid', gap: '1rem' }}>

            {/* Workflow */}
            {result.recommendation?.workflow?.length > 0 && (
              <div className="card">
                <h3 style={{ margin: '0 0 1rem', fontSize: '0.95rem', fontWeight: 600, color: 'var(--accent)' }}>
                  📋 Empfohlener Workflow
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                  {result.recommendation.workflow.map((step, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                      <div className="step-number">{i + 1}</div>
                      <p style={{ margin: 0, fontSize: '0.875rem', lineHeight: 1.5, paddingTop: '3px' }}>{step}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tools */}
            {result.recommendation?.recommended_tools?.length > 0 && (
              <div className="card">
                <h3 style={{ margin: '0 0 1rem', fontSize: '0.95rem', fontWeight: 600, color: 'var(--accent2)' }}>
                  🛠 Empfohlene Tools
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {result.recommendation.recommended_tools.map((tool, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '0.75rem', background: 'var(--bg)', borderRadius: '8px', border: '1px solid var(--border)', gap: '1rem' }}>
                      <div>
                        <strong style={{ fontSize: '0.875rem', color: 'var(--text)' }}>⭐ {tool.name}</strong>
                        <p style={{ margin: '0.2rem 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>{tool.reason}</p>
                      </div>
                      {tool.url && (
                        <a href={tool.url} target="_blank" rel="noopener noreferrer" style={{
                          color: 'var(--accent2)', fontSize: '0.78rem', textDecoration: 'none', whiteSpace: 'nowrap',
                          border: '1px solid rgba(96,165,250,0.3)', padding: '0.25rem 0.6rem', borderRadius: '6px', flexShrink: 0,
                        }}>↗ Öffnen</a>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Prompt */}
            {result.recommendation?.optimized_prompt && (
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600, color: '#C4B5FD' }}>✨ Optimierter Prompt</h3>
                  <button onClick={handleCopyPrompt} style={{
                    display: 'flex', alignItems: 'center', gap: '0.3rem',
                    background: copiedPrompt ? 'rgba(79,255,176,0.1)' : 'var(--bg)',
                    border: `1px solid ${copiedPrompt ? 'var(--accent-dim)' : 'var(--border)'}`,
                    color: copiedPrompt ? 'var(--accent)' : 'var(--text-muted)',
                    padding: '0.3rem 0.7rem', borderRadius: '6px', cursor: 'pointer',
                    fontSize: '0.78rem', fontFamily: 'Space Grotesk, sans-serif',
                  }}>
                    {copiedPrompt ? '✓ Kopiert!' : '⧉ Kopieren'}
                  </button>
                </div>
                <p style={{ margin: '0 0 0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>Direkt in dein KI-Tool einfügen:</p>
                <div className="prompt-block">{result.recommendation.optimized_prompt}</div>
              </div>
            )}

            {/* Tips */}
            {result.recommendation?.tips?.length > 0 && (
              <div className="card" style={{ borderColor: 'rgba(79,255,176,0.1)', background: 'rgba(79,255,176,0.02)' }}>
                <h3 style={{ margin: '0 0 0.75rem', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-muted)' }}>💡 Profi-Tipps</h3>
                <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                  {result.recommendation.tips.map((tip, i) => (
                    <li key={i} style={{ fontSize: '0.825rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>{tip}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {!result && !loading && !error && (
        <div style={{ textAlign: 'center', padding: '4rem 2rem', color: 'var(--text-muted)' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎯</div>
          <p style={{ fontSize: '0.95rem', margin: '0 0 0.5rem' }}>Bereit für deinen ersten Workflow</p>
          <p style={{ fontSize: '0.8rem', margin: 0 }}>Gib eine Aufgabe ein und erhalte KI-gestützte Empfehlungen</p>
        </div>
      )}
    </div>
  )
}
