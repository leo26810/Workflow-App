import { useEffect, useState } from 'react'

export default function ConfigPage() {
  const [health, setHealth] = useState(null)
  const [kpiSnapshot, setKpiSnapshot] = useState(null)
  const [kpis, setKpis] = useState(null)
  const [kpiTargets, setKpiTargets] = useState(null)
  const [schedulerStatus, setSchedulerStatus] = useState(null)
  const [profile, setProfile] = useState(null)
  const [contextItems, setContextItems] = useState([])
  const [categories, setCategories] = useState([])
  const [feedbackRows, setFeedbackRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true

    const loadConfigData = async () => {
      setLoading(true)
      setError(null)
      try {
        const [healthRes, kpiRes, kpiSnapshotRes, kpiTargetsRes, schedulerRes, profileRes, contextRes, categoriesRes, feedbackRes] = await Promise.all([
          fetch('/api/health'),
          fetch('/api/kpis/report?days=30'),
          fetch('/api/kpis?days=30'),
          fetch('/api/kpis/targets'),
          fetch('/api/kpis/scheduler-status'),
          fetch('/api/profile?page=1&limit=100'),
          fetch('/api/user-context'),
          fetch('/api/categories'),
          fetch('/api/recommendation-feedback?page=1&limit=50'),
        ])

        if (!alive) return

        if (healthRes.ok) setHealth(await healthRes.json())
        if (kpiRes.ok) setKpis(await kpiRes.json())
        if (kpiSnapshotRes.ok) setKpiSnapshot(await kpiSnapshotRes.json())
        if (kpiTargetsRes.ok) setKpiTargets(await kpiTargetsRes.json())
        if (schedulerRes.ok) setSchedulerStatus(await schedulerRes.json())
        if (profileRes.ok) setProfile(await profileRes.json())
        if (contextRes.ok) {
          const contextJson = await contextRes.json()
          setContextItems(Array.isArray(contextJson) ? contextJson : [])
        }
        if (categoriesRes.ok) {
          const categoriesJson = await categoriesRes.json()
          setCategories(Array.isArray(categoriesJson) ? categoriesJson : [])
        }
        if (feedbackRes.ok) {
          const feedbackJson = await feedbackRes.json()
          setFeedbackRows(Array.isArray(feedbackJson?.items) ? feedbackJson.items : [])
        }
      } catch (err) {
        if (!alive) return
        setError(err.message || 'Config-Daten konnten nicht geladen werden')
      } finally {
        if (alive) setLoading(false)
      }
    }

    loadConfigData()
    return () => { alive = false }
  }, [])

  const cardStyle = {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: '10px',
    padding: '1rem',
  }

  const sectionTitle = {
    margin: '0 0 0.65rem',
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: 'rgba(255,255,255,0.45)',
    fontWeight: 500,
  }

  const toolCount = profile?.pagination?.tools_total ?? (Array.isArray(profile?.tools) ? profile.tools.length : 0)
  const skillCount = profile?.pagination?.skills_total ?? (Array.isArray(profile?.skills) ? profile.skills.length : 0)
  const goalCount = Array.isArray(profile?.goals) ? profile.goals.length : 0
  const categoryCount = categories.length
  const subcategoryCount = categories.reduce((acc, category) => acc + ((category.subcategories || []).length), 0)

  const failingTargets = Object.entries(kpiTargets || {})
    .filter(([, target]) => target?.meets_target === false)
    .map(([key]) => key)

  return (
    <div style={{ padding: '2.2rem 2.7rem', maxWidth: '980px', margin: '0 auto' }}>
      <div style={{ marginBottom: '1.2rem' }}>
        <h1 style={{ margin: '0 0 0.35rem', fontSize: '1.9rem', fontWeight: 300, color: 'rgba(255,255,255,0.95)' }}>
          Config
        </h1>
        <p style={{ margin: 0, color: 'rgba(255,255,255,0.45)', fontSize: '13px' }}>
          Übersicht über gespeicherte Daten, Konfiguration und Qualitätswerte.
        </p>
      </div>

      {loading && <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: '0.85rem' }}>Lade Config-Daten…</p>}
      {error && <p style={{ color: 'var(--danger)', fontSize: '0.85rem' }}>{error}</p>}

      {!loading && !error && (
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          <div style={{ ...cardStyle, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '0.7rem' }}>
            <div>
              <p style={sectionTitle}>System</p>
              <p style={{ margin: 0, color: 'rgba(255,255,255,0.82)', fontSize: '14px' }}>Status: {health?.status || 'n/a'}</p>
              <p style={{ margin: '0.2rem 0 0', color: 'rgba(255,255,255,0.62)', fontSize: '13px' }}>KI: {health?.groq_configured ? 'aktiv' : 'demo'}</p>
            </div>
            <div>
              <p style={sectionTitle}>KPI</p>
              <p style={{ margin: 0, color: 'rgba(255,255,255,0.82)', fontSize: '14px' }}>Health Index: {kpiSnapshot?.kpi_health_index ?? kpis?.snapshot?.kpi_health_index ?? 'n/a'}</p>
              <p style={{ margin: '0.2rem 0 0', color: 'rgba(255,255,255,0.62)', fontSize: '13px' }}>Avg Rating: {kpiSnapshot?.avg_user_rating ?? kpis?.snapshot?.avg_user_rating ?? 'n/a'}</p>
            </div>
            <div>
              <p style={sectionTitle}>Daten</p>
              <p style={{ margin: 0, color: 'rgba(255,255,255,0.82)', fontSize: '14px' }}>Tools: {toolCount}</p>
              <p style={{ margin: '0.2rem 0 0', color: 'rgba(255,255,255,0.62)', fontSize: '13px' }}>Skills/Ziele: {skillCount}/{goalCount}</p>
            </div>
            <div>
              <p style={sectionTitle}>Taxonomie</p>
              <p style={{ margin: 0, color: 'rgba(255,255,255,0.82)', fontSize: '14px' }}>Kategorien: {categoryCount}</p>
              <p style={{ margin: '0.2rem 0 0', color: 'rgba(255,255,255,0.62)', fontSize: '13px' }}>Subkategorien: {subcategoryCount}</p>
            </div>
          </div>

          <div style={cardStyle}>
            <p style={sectionTitle}>KPI Runtime & Targets</p>
            <div style={{ display: 'grid', gap: '0.35rem' }}>
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>
                Empfehlungen: {kpiSnapshot?.recommendation_count ?? 'n/a'} · Feedback: {kpiSnapshot?.feedback_count ?? 'n/a'} · Top3-Hit: {kpiSnapshot?.top3_hit_rate ?? 'n/a'}
              </div>
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>
                Scheduler: {schedulerStatus?.enabled ? 'aktiviert' : 'deaktiviert'} · Gestartet: {schedulerStatus?.started ? 'ja' : 'nein'} · Intervall: {schedulerStatus?.interval_minutes ?? 'n/a'} min
              </div>
              <div style={{ fontSize: '13px', color: failingTargets.length ? 'rgba(255,209,102,0.9)' : 'rgba(79,255,176,0.9)' }}>
                Zielstatus: {failingTargets.length ? `${failingTargets.length} KPI-Ziele unterschritten (${failingTargets.join(', ')})` : 'Alle KPI-Ziele erfüllt'}
              </div>
            </div>
          </div>

          <div style={cardStyle}>
            <p style={sectionTitle}>User Context</p>
            {!contextItems.length && <p style={{ margin: 0, color: 'rgba(255,255,255,0.55)', fontSize: '13px' }}>Keine User-Context-Einträge.</p>}
            {!!contextItems.length && (
              <div style={{ display: 'grid', gap: '0.35rem' }}>
                {contextItems.slice(0, 12).map((item) => (
                  <div key={item.id} style={{ fontSize: '13px', color: 'rgba(255,255,255,0.8)' }}>
                    [{item.area}] {item.key}: <span style={{ color: 'rgba(255,255,255,0.58)' }}>{item.value}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={cardStyle}>
            <p style={sectionTitle}>Kategorien</p>
            {!categories.length && <p style={{ margin: 0, color: 'rgba(255,255,255,0.55)', fontSize: '13px' }}>Keine Kategorien gefunden.</p>}
            {!!categories.length && (
              <div style={{ display: 'grid', gap: '0.35rem' }}>
                {categories.map((category) => (
                  <div key={category.id} style={{ fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>
                    {category.name} <span style={{ color: 'rgba(255,255,255,0.5)' }}>({(category.subcategories || []).length} Subbereiche)</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={cardStyle}>
            <p style={sectionTitle}>Feedback-Verlauf (letzte Einträge)</p>
            {!feedbackRows.length && <p style={{ margin: 0, color: 'rgba(255,255,255,0.55)', fontSize: '13px' }}>Keine Verlaufseinträge vorhanden.</p>}
            {!!feedbackRows.length && (
              <div style={{ display: 'grid', gap: '0.32rem' }}>
                {feedbackRows.slice(0, 10).map((row) => (
                  <div key={row.id} style={{ fontSize: '13px', color: 'rgba(255,255,255,0.78)' }}>
                    #{row.id} · Rating: {row.user_rating ?? '—'} · Accepted: {row.accepted === true ? 'ja' : row.accepted === false ? 'nein' : '—'} · {row.task_description}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
