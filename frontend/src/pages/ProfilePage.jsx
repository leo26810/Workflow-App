import { useState, useEffect } from 'react'

const LEVELS = ['Anfänger', 'Fortgeschritten', 'Experte']
const CATEGORIES = ['KI-Textgenerierung', 'Bilderstellung', 'Recherche', 'Design & Präsentation', 'Lernen & Schule', 'Mathe & Wissenschaft', 'Übersetzung', 'Literaturverwaltung', 'Allgemein']

export default function ProfilePage() {
  const [profile, setProfile] = useState({ user: {}, skills: [], goals: [], tools: [] })
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('skills')
  const [contextData, setContextData] = useState({
    schule: {
      schulform: '',
      hauptfaecher: '',
      staerken: '',
      schwaechen: '',
    },
    ki: {
      ki_erfahrung: 'Anfänger',
      genutzte_tools: '',
      bevorzugte_tool_typen: '',
    },
    allgemein: {
      lernstil: 'Visuell',
      interessen: '',
      ziele: '',
      schwierigkeitsgrad: 'Mittel',
    },
  })
  const [savedFields, setSavedFields] = useState({})

  // Formular-States
  const [newSkill, setNewSkill] = useState({ name: '', level: 'Anfänger' })
  const [newGoal, setNewGoal] = useState('')
  const [newTool, setNewTool] = useState({ name: '', category: 'Allgemein', url: '', notes: '' })
  const [editName, setEditName] = useState('')
  const [editingName, setEditingName] = useState(false)
  const [saving, setSaving] = useState(false)

  // Profil beim Laden der Seite abrufen
  useEffect(() => {
    fetchProfile()
  }, [])

  const fetchProfile = async () => {
    try {
      const res = await fetch('/api/profile')
      const data = await res.json()
      setProfile(data)
      setEditName(data.user?.name || '')

      const contextRes = await fetch('/api/user-context')
      if (contextRes.ok) {
        const contextItems = await contextRes.json()
        const nextData = {
          schule: {
            schulform: '',
            hauptfaecher: '',
            staerken: '',
            schwaechen: '',
          },
          ki: {
            ki_erfahrung: 'Anfänger',
            genutzte_tools: '',
            bevorzugte_tool_typen: '',
          },
          allgemein: {
            lernstil: 'Visuell',
            interessen: '',
            ziele: '',
            schwierigkeitsgrad: 'Mittel',
          }
        }

        if (Array.isArray(contextItems)) {
          contextItems.forEach(item => {
            if (item?.area && item?.key && Object.prototype.hasOwnProperty.call(nextData[item.area] || {}, item.key)) {
              nextData[item.area][item.key] = item.value || ''
            }
          })
        }

        setContextData(nextData)
      }
    } catch (e) {
      console.error('Profil konnte nicht geladen werden:', e)
    } finally {
      setLoading(false)
    }
  }

  const apiPost = async (body) => {
    setSaving(true)
    try {
      await fetch('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      await fetchProfile()
    } finally {
      setSaving(false)
    }
  }

  const addSkill = async () => {
    if (!newSkill.name.trim()) return
    await apiPost({ action: 'add_skill', name: newSkill.name, level: newSkill.level })
    setNewSkill({ name: '', level: 'Anfänger' })
  }

  const deleteSkill = (id) => apiPost({ action: 'delete_skill', id })

  const addGoal = async () => {
    if (!newGoal.trim()) return
    await apiPost({ action: 'add_goal', description: newGoal })
    setNewGoal('')
  }

  const deleteGoal = (id) => apiPost({ action: 'delete_goal', id })

  const addTool = async () => {
    if (!newTool.name.trim()) return
    await apiPost({ action: 'add_tool', ...newTool })
    setNewTool({ name: '', category: 'Allgemein', url: '', notes: '' })
  }

  const deleteTool = (id) => apiPost({ action: 'delete_tool', id })

  const saveName = async () => {
    await apiPost({ action: 'update_name', name: editName })
    setEditingName(false)
  }

  const setContextField = (area, key, value) => {
    setContextData(prev => ({
      ...prev,
      [area]: {
        ...prev[area],
        [key]: value,
      }
    }))
  }

  const saveContextField = async (area, key, value) => {
    const fieldToken = `${area}.${key}`
    try {
      const res = await fetch('/api/user-context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ area, key, value })
      })
      if (!res.ok) throw new Error('Speichern fehlgeschlagen')
      setSavedFields(prev => ({ ...prev, [fieldToken]: true }))
      setTimeout(() => {
        setSavedFields(prev => {
          const next = { ...prev }
          delete next[fieldToken]
          return next
        })
      }, 2000)
    } catch {
    }
  }

  const isFieldSaved = (area, key) => !!savedFields[`${area}.${key}`]

  const parseToolsPreference = (value) => {
    if (!value) return []
    return value
      .split(',')
      .map(item => item.trim())
      .filter(Boolean)
  }

  const TOOL_TYPE_OPTIONS = ['Text-KI', 'Bilderstellung', 'Recherche', 'Lerntools', 'Coding']

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: 'var(--text-muted)' }}>
        <p>⏳ Lade Profil...</p>
      </div>
    )
  }

  const tabs = [
    { id: 'skills', label: 'Fähigkeiten', count: profile.skills.length },
    { id: 'goals', label: 'Ziele', count: profile.goals.length },
    { id: 'tools', label: 'Tools', count: profile.tools.length },
    { id: 'context', label: 'Mein Kontext' },
  ]

  return (
    <div style={{ padding: '2rem 2.5rem', maxWidth: '900px', margin: '0 auto' }}>

      {/* Header mit Nutzer-Name */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ margin: '0 0 0.4rem', fontSize: '1.75rem', fontWeight: 700 }}>👤 Mein Profil</h1>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.9rem' }}>Verwalte deine Fähigkeiten, Ziele und Tool-Datenbank</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {editingName ? (
            <>
              <input className="input-field" value={editName} onChange={e => setEditName(e.target.value)} style={{ width: '180px' }} />
              <button className="btn-primary" onClick={saveName}>Speichern</button>
              <button className="btn-secondary" onClick={() => setEditingName(false)}>Abbrechen</button>
            </>
          ) : (
            <>
              <span style={{ color: 'var(--text)', fontWeight: 600 }}>{profile.user?.name}</span>
              <button className="btn-secondary" onClick={() => setEditingName(true)}>✎ Bearbeiten</button>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', width: 'fit-content' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '0.55rem 0.2rem',
              borderRadius: 0,
              border: 'none',
              cursor: 'pointer',
              fontFamily: 'Inter, system-ui, sans-serif',
              fontSize: '0.875rem',
              fontWeight: activeTab === tab.id ? 600 : 400,
              background: 'transparent',
              color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-muted)',
              transition: 'all 0.15s',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              borderBottom: activeTab === tab.id ? '2px solid var(--accent)' : '2px solid transparent',
              marginBottom: '-1px',
            }}
          >
            {tab.label}
            {typeof tab.count === 'number' && (
              <span style={{
                background: 'rgba(255,255,255,0.06)',
                color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-muted)',
                padding: '1px 7px',
                borderRadius: '10px',
                fontSize: '0.7rem',
              }}>{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {activeTab === 'context' && (
        <div className="animate-slide-in" style={{ display: 'grid', gap: '1rem' }}>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.82rem' }}>
            Änderungen werden beim Verlassen des Feldes automatisch gespeichert.
          </p>

          <div style={{ display: 'grid', gap: '0.65rem' }}>
            <p className="label" style={{ margin: 0 }}>Schule</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem' }}>
              <div className="card" style={{ padding: '0.85rem' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Schulform
                </label>
                <input
                  className="input-field"
                  placeholder="z.B. 11. Klasse Gymnasium"
                  value={contextData.schule.schulform}
                  onChange={e => setContextField('schule', 'schulform', e.target.value)}
                  onBlur={e => saveContextField('schule', 'schulform', e.target.value)}
                />
                {isFieldSaved('schule', 'schulform') && <p style={{ margin: '0.35rem 0 0', fontSize: '0.75rem', color: 'var(--accent)' }}>✓ Gespeichert</p>}
              </div>

              <div className="card" style={{ padding: '0.85rem' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Hauptfächer
                </label>
                <input
                  className="input-field"
                  placeholder="z.B. Mathe, Deutsch, Informatik"
                  value={contextData.schule.hauptfaecher}
                  onChange={e => setContextField('schule', 'hauptfaecher', e.target.value)}
                  onBlur={e => saveContextField('schule', 'hauptfaecher', e.target.value)}
                />
                {isFieldSaved('schule', 'hauptfaecher') && <p style={{ margin: '0.35rem 0 0', fontSize: '0.75rem', color: 'var(--accent)' }}>✓ Gespeichert</p>}
              </div>

              <div className="card" style={{ padding: '0.85rem' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Stärken
                </label>
                <input
                  className="input-field"
                  value={contextData.schule.staerken}
                  onChange={e => setContextField('schule', 'staerken', e.target.value)}
                  onBlur={e => saveContextField('schule', 'staerken', e.target.value)}
                />
                {isFieldSaved('schule', 'staerken') && <p style={{ margin: '0.35rem 0 0', fontSize: '0.75rem', color: 'var(--accent)' }}>✓ Gespeichert</p>}
              </div>

              <div className="card" style={{ padding: '0.85rem' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Schwächen
                </label>
                <input
                  className="input-field"
                  value={contextData.schule.schwaechen}
                  onChange={e => setContextField('schule', 'schwaechen', e.target.value)}
                  onBlur={e => saveContextField('schule', 'schwaechen', e.target.value)}
                />
                {isFieldSaved('schule', 'schwaechen') && <p style={{ margin: '0.35rem 0 0', fontSize: '0.75rem', color: 'var(--accent)' }}>✓ Gespeichert</p>}
              </div>

              <div className="card" style={{ padding: '0.85rem' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Lernstil
                </label>
                <select
                  className="input-field"
                  value={contextData.allgemein.lernstil}
                  onChange={e => setContextField('allgemein', 'lernstil', e.target.value)}
                  onBlur={e => saveContextField('allgemein', 'lernstil', e.target.value)}
                >
                  {['Visuell', 'Durch Lesen', 'Durch Üben', 'Durch Erklären'].map(option => <option key={option}>{option}</option>)}
                </select>
                {isFieldSaved('allgemein', 'lernstil') && <p style={{ margin: '0.35rem 0 0', fontSize: '0.75rem', color: 'var(--accent)' }}>✓ Gespeichert</p>}
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gap: '0.65rem' }}>
            <p className="label" style={{ margin: 0 }}>KI &amp; Tools</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem' }}>
              <div className="card" style={{ padding: '0.85rem' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  KI-Erfahrung
                </label>
                <select
                  className="input-field"
                  value={contextData.ki.ki_erfahrung}
                  onChange={e => setContextField('ki', 'ki_erfahrung', e.target.value)}
                  onBlur={e => saveContextField('ki', 'ki_erfahrung', e.target.value)}
                >
                  {['Anfänger', 'Mittel', 'Fortgeschritten'].map(option => <option key={option}>{option}</option>)}
                </select>
                {isFieldSaved('ki', 'ki_erfahrung') && <p style={{ margin: '0.35rem 0 0', fontSize: '0.75rem', color: 'var(--accent)' }}>✓ Gespeichert</p>}
              </div>

              <div className="card" style={{ padding: '0.85rem' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Bereits genutzte Tools
                </label>
                <input
                  className="input-field"
                  value={contextData.ki.genutzte_tools}
                  onChange={e => setContextField('ki', 'genutzte_tools', e.target.value)}
                  onBlur={e => saveContextField('ki', 'genutzte_tools', e.target.value)}
                />
                {isFieldSaved('ki', 'genutzte_tools') && <p style={{ margin: '0.35rem 0 0', fontSize: '0.75rem', color: 'var(--accent)' }}>✓ Gespeichert</p>}
              </div>

              <div className="card" style={{ padding: '0.85rem', gridColumn: '1 / -1' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.45rem' }}>
                  Bevorzugte Tool-Typen
                </label>
                <div style={{ display: 'flex', gap: '0.9rem', flexWrap: 'wrap' }}>
                  {TOOL_TYPE_OPTIONS.map(option => {
                    const selectedTypes = parseToolsPreference(contextData.ki.bevorzugte_tool_typen)
                    const checked = selectedTypes.includes(option)
                    return (
                      <label key={option} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => {
                            const current = parseToolsPreference(contextData.ki.bevorzugte_tool_typen)
                            const next = e.target.checked
                              ? [...current, option]
                              : current.filter(item => item !== option)
                            setContextField('ki', 'bevorzugte_tool_typen', next.join(', '))
                          }}
                          onBlur={() => saveContextField('ki', 'bevorzugte_tool_typen', contextData.ki.bevorzugte_tool_typen)}
                        />
                        {option}
                      </label>
                    )
                  })}
                </div>
                {isFieldSaved('ki', 'bevorzugte_tool_typen') && <p style={{ margin: '0.45rem 0 0', fontSize: '0.75rem', color: 'var(--accent)' }}>✓ Gespeichert</p>}
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gap: '0.65rem' }}>
            <p className="label" style={{ margin: 0 }}>Allgemein</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem' }}>
              <div className="card" style={{ padding: '0.85rem' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Interessen &amp; Hobbys
                </label>
                <input
                  className="input-field"
                  value={contextData.allgemein.interessen}
                  onChange={e => setContextField('allgemein', 'interessen', e.target.value)}
                  onBlur={e => saveContextField('allgemein', 'interessen', e.target.value)}
                />
                {isFieldSaved('allgemein', 'interessen') && <p style={{ margin: '0.35rem 0 0', fontSize: '0.75rem', color: 'var(--accent)' }}>✓ Gespeichert</p>}
              </div>

              <div className="card" style={{ padding: '0.85rem' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Schwierigkeitsgrad-Präferenz
                </label>
                <select
                  className="input-field"
                  value={contextData.allgemein.schwierigkeitsgrad}
                  onChange={e => setContextField('allgemein', 'schwierigkeitsgrad', e.target.value)}
                  onBlur={e => saveContextField('allgemein', 'schwierigkeitsgrad', e.target.value)}
                >
                  {['Einfach', 'Mittel', 'Herausfordernd'].map(option => <option key={option}>{option}</option>)}
                </select>
                {isFieldSaved('allgemein', 'schwierigkeitsgrad') && <p style={{ margin: '0.35rem 0 0', fontSize: '0.75rem', color: 'var(--accent)' }}>✓ Gespeichert</p>}
              </div>

              <div className="card" style={{ padding: '0.85rem', gridColumn: '1 / -1' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Ziele dieses Schuljahr
                </label>
                <textarea
                  className="textarea-field"
                  rows={3}
                  value={contextData.allgemein.ziele}
                  onChange={e => setContextField('allgemein', 'ziele', e.target.value)}
                  onBlur={e => saveContextField('allgemein', 'ziele', e.target.value)}
                  style={{ minHeight: 'unset', maxHeight: '120px' }}
                />
                {isFieldSaved('allgemein', 'ziele') && <p style={{ margin: '0.35rem 0 0', fontSize: '0.75rem', color: 'var(--accent)' }}>✓ Gespeichert</p>}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SKILLS TAB */}
      {activeTab === 'skills' && (
        <div className="animate-slide-in">
          {/* Neue Fähigkeit hinzufügen */}
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: '0.95rem', fontWeight: 600 }}>+ Fähigkeit hinzufügen</h3>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <input
                className="input-field"
                placeholder="Fähigkeit (z.B. Python-Grundlagen)"
                value={newSkill.name}
                onChange={e => setNewSkill(p => ({ ...p, name: e.target.value }))}
                onKeyDown={e => e.key === 'Enter' && addSkill()}
                style={{ flex: 1, minWidth: '200px' }}
              />
              <select className="input-field" value={newSkill.level} onChange={e => setNewSkill(p => ({ ...p, level: e.target.value }))} style={{ width: '160px' }}>
                {LEVELS.map(l => <option key={l}>{l}</option>)}
              </select>
              <button className="btn-ghost" style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }} onClick={addSkill} disabled={saving || !newSkill.name.trim()}>
                + Hinzufügen
              </button>
            </div>
          </div>

          {/* Skills Liste */}
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            {profile.skills.length === 0 && (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                Noch keine Fähigkeiten eingetragen.
              </div>
            )}
            {profile.skills.map(skill => (
              <div key={skill.id} className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem 1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>{skill.name}</span>
                  <span className="tag" style={skill.level === 'Experte' ? { borderColor: 'rgba(79,255,176,0.3)' } : undefined}>{skill.level}</span>
                </div>
                <button className="icon-btn" onClick={() => deleteSkill(skill.id)} aria-label="Skill entfernen" title="Entfernen">×</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* GOALS TAB */}
      {activeTab === 'goals' && (
        <div className="animate-slide-in">
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: '0.95rem', fontWeight: 600 }}>+ Ziel hinzufügen</h3>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <input
                className="input-field"
                placeholder="Ziel (z.B. Note in Mathe verbessern)"
                value={newGoal}
                onChange={e => setNewGoal(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addGoal()}
                style={{ flex: 1 }}
              />
              <button className="btn-ghost" style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }} onClick={addGoal} disabled={saving || !newGoal.trim()}>
                + Hinzufügen
              </button>
            </div>
          </div>

          <div style={{ display: 'grid', gap: '0.5rem' }}>
            {profile.goals.length === 0 && (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                Noch keine Ziele eingetragen.
              </div>
            )}
            {profile.goals.map(goal => (
              <div key={goal.id} className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem 1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span style={{ color: 'var(--accent)', fontSize: '0.9rem' }}>◎</span>
                  <span style={{ fontSize: '0.9rem' }}>{goal.description}</span>
                </div>
                <button className="icon-btn" onClick={() => deleteGoal(goal.id)} aria-label="Ziel entfernen" title="Entfernen">×</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TOOLS TAB */}
      {activeTab === 'tools' && (
        <div className="animate-slide-in">
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: '0.95rem', fontWeight: 600 }}>+ Tool hinzufügen</h3>
            <div style={{ display: 'grid', gap: '0.75rem' }}>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <input className="input-field" placeholder="Tool-Name" value={newTool.name} onChange={e => setNewTool(p => ({ ...p, name: e.target.value }))} style={{ flex: 1 }} />
                <select className="input-field" value={newTool.category} onChange={e => setNewTool(p => ({ ...p, category: e.target.value }))} style={{ width: '200px' }}>
                  {CATEGORIES.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <input className="input-field" placeholder="URL (https://...)" value={newTool.url} onChange={e => setNewTool(p => ({ ...p, url: e.target.value }))} />
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <input className="input-field" placeholder="Notizen (z.B. Kostenlos, 10 Bilder/Tag)" value={newTool.notes} onChange={e => setNewTool(p => ({ ...p, notes: e.target.value }))} style={{ flex: 1 }} />
                <button className="btn-ghost" style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }} onClick={addTool} disabled={saving || !newTool.name.trim()}>+ Hinzufügen</button>
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gap: '0.5rem' }}>
            {profile.tools.length === 0 && (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                Keine Tools in der Datenbank.
              </div>
            )}
            {profile.tools.map(tool => (
              <div key={tool.id} className="card" style={{ padding: '0.875rem 1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.25rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <strong style={{ fontSize: '0.9rem' }}>{tool.name}</strong>
                    <span style={{ background: 'rgba(96,165,250,0.12)', color: 'var(--accent2)', border: '1px solid rgba(96,165,250,0.2)', padding: '1px 8px', borderRadius: '10px', fontSize: '0.72rem' }}>{tool.category}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {tool.url && (
                      <a href={tool.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent2)', fontSize: '0.78rem', textDecoration: 'none' }}>↗ Link</a>
                    )}
                    <button className="icon-btn" onClick={() => deleteTool(tool.id)} aria-label="Tool entfernen" title="Entfernen">×</button>
                  </div>
                </div>
                {tool.notes && <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>{tool.notes}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
