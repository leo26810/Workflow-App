import { useState, useEffect } from 'react'

const LEVELS = ['Anfänger', 'Fortgeschritten', 'Experte']
const CATEGORIES = ['KI-Textgenerierung', 'Bilderstellung', 'Recherche', 'Design & Präsentation', 'Lernen & Schule', 'Mathe & Wissenschaft', 'Übersetzung', 'Literaturverwaltung', 'Allgemein']

const levelColors = {
  'Anfänger': 'tag-beginner',
  'Fortgeschritten': 'tag-advanced',
  'Experte': 'tag-expert',
}

export default function ProfilePage() {
  const [profile, setProfile] = useState({ user: {}, skills: [], goals: [], tools: [] })
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('skills')

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

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: 'var(--text-muted)' }}>
        <p>⏳ Lade Profil...</p>
      </div>
    )
  }

  const tabs = [
    { id: 'skills', label: '🧠 Fähigkeiten', count: profile.skills.length },
    { id: 'goals', label: '🎯 Ziele', count: profile.goals.length },
    { id: 'tools', label: '🛠 Tools', count: profile.tools.length },
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
      <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '1.5rem', background: 'var(--bg-card)', padding: '0.3rem', borderRadius: '10px', border: '1px solid var(--border)', width: 'fit-content' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '0.5rem 1.25rem',
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              fontFamily: 'Space Grotesk, sans-serif',
              fontSize: '0.875rem',
              fontWeight: activeTab === tab.id ? 600 : 400,
              background: activeTab === tab.id ? 'var(--bg-card2)' : 'transparent',
              color: activeTab === tab.id ? 'var(--accent)' : 'var(--text-muted)',
              transition: 'all 0.15s',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
          >
            {tab.label}
            <span style={{
              background: activeTab === tab.id ? 'rgba(79,255,176,0.15)' : 'rgba(255,255,255,0.06)',
              color: activeTab === tab.id ? 'var(--accent)' : 'var(--text-muted)',
              padding: '1px 7px',
              borderRadius: '10px',
              fontSize: '0.7rem',
            }}>{tab.count}</span>
          </button>
        ))}
      </div>

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
              <button className="btn-primary" onClick={addSkill} disabled={saving || !newSkill.name.trim()}>
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
                  <span className={`tag ${levelColors[skill.level] || 'tag-beginner'}`}>{skill.level}</span>
                </div>
                <button className="btn-danger" onClick={() => deleteSkill(skill.id)}>✕ Entfernen</button>
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
              <button className="btn-primary" onClick={addGoal} disabled={saving || !newGoal.trim()}>
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
                <button className="btn-danger" onClick={() => deleteGoal(goal.id)}>✕ Entfernen</button>
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
                <button className="btn-primary" onClick={addTool} disabled={saving || !newTool.name.trim()}>+ Hinzufügen</button>
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
                    <button className="btn-danger" onClick={() => deleteTool(tool.id)}>✕</button>
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
