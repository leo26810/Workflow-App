import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

const STATUS_COLUMNS = [
  { key: 'offen', label: 'Offen' },
  { key: 'in_arbeit', label: 'In Arbeit' },
  { key: 'fertig', label: 'Fertig' },
]

export default function SchoolPage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedProject, setSelectedProject] = useState(null)
  const [panelSaving, setPanelSaving] = useState(false)
  const [panelStatus, setPanelStatus] = useState('')

  const [title, setTitle] = useState('')
  const [subject, setSubject] = useState('')
  const [deadline, setDeadline] = useState('')
  const [description, setDescription] = useState('')
  const [creating, setCreating] = useState(false)

  const subjectColors = {
    Mathematik: { background: 'rgba(96,165,250,0.15)', color: '#93C5FD', border: 'rgba(96,165,250,0.35)' },
    Deutsch: { background: 'rgba(250,204,21,0.15)', color: '#FDE047', border: 'rgba(250,204,21,0.35)' },
    Englisch: { background: 'rgba(52,211,153,0.15)', color: '#6EE7B7', border: 'rgba(52,211,153,0.35)' },
    Biologie: { background: 'rgba(74,222,128,0.15)', color: '#86EFAC', border: 'rgba(74,222,128,0.35)' },
    Geschichte: { background: 'rgba(192,132,252,0.15)', color: '#D8B4FE', border: 'rgba(192,132,252,0.35)' },
    Geographie: { background: 'rgba(56,189,248,0.15)', color: '#7DD3FC', border: 'rgba(56,189,248,0.35)' },
  }

  const loadProjects = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/school-projects')
      if (!res.ok) throw new Error('Projekte konnten nicht geladen werden')
      const data = await res.json()
      setProjects(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message || 'Fehler beim Laden')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProjects()
  }, [])

  const groupedProjects = useMemo(() => {
    return {
      offen: projects.filter(p => p.status === 'offen'),
      in_arbeit: projects.filter(p => p.status === 'in_arbeit'),
      fertig: projects.filter(p => p.status === 'fertig'),
    }
  }, [projects])

  const getDaysLeft = (deadlineValue) => {
    if (!deadlineValue) return null
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const deadlineDate = new Date(deadlineValue)
    deadlineDate.setHours(0, 0, 0, 0)
    const diff = deadlineDate.getTime() - today.getTime()
    return Math.ceil(diff / (1000 * 60 * 60 * 24))
  }

  const getDeadlineStyles = (daysLeft) => {
    if (daysLeft === null) return { color: 'var(--text-muted)' }
    if (daysLeft < 0) return { color: '#F87171' }
    if (daysLeft <= 3) return { color: '#EF4444' }
    if (daysLeft <= 7) return { color: '#F59E0B' }
    return { color: 'var(--text-muted)' }
  }

  const getCountdownLabel = (daysLeft) => {
    if (daysLeft === null) return 'Keine Deadline'
    if (daysLeft < 0) return `Überfällig seit ${Math.abs(daysLeft)} Tagen`
    if (daysLeft === 0) return 'Heute fällig'
    if (daysLeft === 1) return 'Noch 1 Tag'
    return `Noch ${daysLeft} Tage`
  }

  const getSubjectTagStyle = (subjectName) => {
    return subjectColors[subjectName] || {
      background: 'rgba(148,163,184,0.12)',
      color: '#CBD5E1',
      border: 'rgba(148,163,184,0.35)',
    }
  }

  const handleCreateProject = async (e) => {
    e.preventDefault()
    if (!title.trim() || !subject.trim()) return

    setCreating(true)
    setError(null)
    try {
      const res = await fetch('/api/school-projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'add',
          title,
          subject,
          deadline,
          status: 'offen',
          description,
          notes: '',
        })
      })
      if (!res.ok) throw new Error('Projekt konnte nicht erstellt werden')
      setTitle('')
      setSubject('')
      setDeadline('')
      setDescription('')
      await loadProjects()
    } catch (err) {
      setError(err.message || 'Fehler beim Erstellen')
    } finally {
      setCreating(false)
    }
  }

  const updateProjectField = async (projectId, changes) => {
    setPanelSaving(true)
    setPanelStatus('Speichere…')
    try {
      const res = await fetch('/api/school-projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'update',
          id: projectId,
          ...changes,
        })
      })
      if (!res.ok) throw new Error('Änderung konnte nicht gespeichert werden')
      const data = await res.json()
      const updated = data?.project

      if (updated) {
        setProjects(prev => prev.map(item => (item.id === updated.id ? updated : item)))
        setSelectedProject(updated)
      }
      setPanelStatus('✓ Gespeichert')
      setTimeout(() => setPanelStatus(''), 1200)
    } catch (err) {
      setPanelStatus('⚠ Fehler beim Speichern')
      setTimeout(() => setPanelStatus(''), 1800)
    } finally {
      setPanelSaving(false)
    }
  }

  const handlePanelChange = (field, value) => {
    setSelectedProject(prev => (prev ? { ...prev, [field]: value } : prev))
  }

  const openRecommendationForProject = (project) => {
    const detailText = (project.description || '').trim() || 'ohne zusätzliche Beschreibung'
    const task = `Schulprojekt: ${project.title} in ${project.subject} – ${detailText}`
    const target = `/?focus=schule_projekt&subcategory=${encodeURIComponent('Schulprojekte')}&task=${encodeURIComponent(task)}&autostart=1`
    navigate(target)
  }

  return (
    <div style={{ padding: '2rem 2.5rem', maxWidth: '1150px', margin: '0 auto' }}>
      <div style={{ marginBottom: '1.4rem' }}>
        <h1 style={{ margin: '0 0 0.35rem', fontSize: '1.6rem' }}>📚 Schulprojekte</h1>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.88rem' }}>
          Verwalte Projekte im Mini-Kanban und starte direkt eine passende Empfehlung im Dashboard.
        </p>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3 style={{ marginTop: 0, marginBottom: '0.85rem', fontSize: '0.92rem' }}>Neues Projekt anlegen</h3>
        <form onSubmit={handleCreateProject} style={{ display: 'grid', gap: '0.6rem' }}>
          <input className="textarea-field" placeholder="Titel" value={title} onChange={e => setTitle(e.target.value)} />
          <input className="textarea-field" placeholder="Fach" value={subject} onChange={e => setSubject(e.target.value)} />
          <input className="textarea-field" type="date" value={deadline} onChange={e => setDeadline(e.target.value)} />
          <textarea className="textarea-field" placeholder="Beschreibung" value={description} onChange={e => setDescription(e.target.value)} rows={3} />
          <div>
            <button className="btn-primary" type="submit" disabled={creating || !title.trim() || !subject.trim()}>
              {creating ? 'Speichere…' : 'Projekt speichern'}
            </button>
          </div>
        </form>
      </div>

      {error && (
        <div style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: '10px', padding: '0.8rem', marginBottom: '1rem', color: 'var(--danger)', fontSize: '0.83rem' }}>
          ⚠️ {error}
        </div>
      )}

      {loading ? (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Lade Projekte…</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: selectedProject ? 'minmax(0, 1fr) 360px' : 'minmax(0, 1fr)', gap: '1rem', alignItems: 'start' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '0.8rem' }}>
            {STATUS_COLUMNS.map(col => (
              <div key={col.key} className="card" style={{ minHeight: '320px' }}>
                <h3 style={{ margin: '0 0 0.7rem', fontSize: '0.9rem' }}>{col.label}</h3>
                <div style={{ display: 'grid', gap: '0.5rem' }}>
                  {groupedProjects[col.key].map(project => {
                    const daysLeft = getDaysLeft(project.deadline)
                    const deadlineStyles = getDeadlineStyles(daysLeft)
                    const subjectStyle = getSubjectTagStyle(project.subject)
                    return (
                      <button
                        key={project.id}
                        onClick={() => setSelectedProject(project)}
                        style={{
                          textAlign: 'left',
                          background: selectedProject?.id === project.id ? 'rgba(79,255,176,0.06)' : 'var(--bg)',
                          border: selectedProject?.id === project.id ? '1px solid rgba(79,255,176,0.25)' : '1px solid var(--border)',
                          borderRadius: '8px',
                          padding: '0.65rem',
                          cursor: 'pointer',
                          color: 'var(--text)'
                        }}
                      >
                        <strong style={{ fontSize: '0.82rem', display: 'block', marginBottom: '0.3rem' }}>{project.title}</strong>
                        <span style={{
                          display: 'inline-block',
                          padding: '1px 8px',
                          borderRadius: '10px',
                          fontSize: '0.7rem',
                          marginBottom: '0.35rem',
                          border: `1px solid ${subjectStyle.border}`,
                          background: subjectStyle.background,
                          color: subjectStyle.color,
                        }}>
                          {project.subject}
                        </span>
                        <p style={{ margin: '0.1rem 0', fontSize: '0.74rem', color: deadlineStyles.color }}>
                          {project.deadline ? `Deadline: ${project.deadline}` : 'Keine Deadline'}
                        </p>
                        <p style={{ margin: '0.1rem 0', fontSize: '0.74rem', color: deadlineStyles.color }}>
                          {getCountdownLabel(daysLeft)}
                        </p>
                        <p style={{ margin: '0.1rem 0 0', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                          Status: {project.status}
                        </p>
                      </button>
                    )
                  })}
                  {!groupedProjects[col.key].length && (
                    <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--text-muted)' }}>Keine Einträge</p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {selectedProject && (
            <aside className="card" style={{ position: 'sticky', top: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem', marginBottom: '0.7rem' }}>
                <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Projekt-Details</h3>
                <button className="btn-secondary" onClick={() => setSelectedProject(null)}>Schließen</button>
              </div>

              <div style={{ display: 'grid', gap: '0.55rem' }}>
                <label style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                  Titel
                  <input className="input-field" value={selectedProject.title || ''} onChange={e => handlePanelChange('title', e.target.value)} onBlur={e => updateProjectField(selectedProject.id, { title: e.target.value })} />
                </label>

                <label style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                  Fach
                  <input className="input-field" value={selectedProject.subject || ''} onChange={e => handlePanelChange('subject', e.target.value)} onBlur={e => updateProjectField(selectedProject.id, { subject: e.target.value })} />
                </label>

                <label style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                  Status
                  <select className="input-field" value={selectedProject.status || 'offen'} onChange={e => handlePanelChange('status', e.target.value)} onBlur={e => updateProjectField(selectedProject.id, { status: e.target.value })}>
                    <option value="offen">Offen</option>
                    <option value="in_arbeit">In Arbeit</option>
                    <option value="fertig">Fertig</option>
                  </select>
                </label>

                <label style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                  Deadline
                  <input className="input-field" type="date" value={selectedProject.deadline || ''} onChange={e => handlePanelChange('deadline', e.target.value)} onBlur={e => updateProjectField(selectedProject.id, { deadline: e.target.value })} />
                </label>

                <label style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                  Beschreibung
                  <textarea className="textarea-field" rows={3} value={selectedProject.description || ''} onChange={e => handlePanelChange('description', e.target.value)} onBlur={e => updateProjectField(selectedProject.id, { description: e.target.value })} />
                </label>

                <label style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                  Notizen
                  <textarea className="textarea-field" rows={4} value={selectedProject.notes || ''} onChange={e => handlePanelChange('notes', e.target.value)} onBlur={e => updateProjectField(selectedProject.id, { notes: e.target.value })} />
                </label>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.2rem' }}>
                  <span style={{ fontSize: '0.74rem', color: panelSaving ? 'var(--text-muted)' : 'var(--accent)' }}>{panelStatus}</span>
                  <button className="btn-primary" onClick={() => openRecommendationForProject(selectedProject)}>
                    Workflow für dieses Projekt anfordern
                  </button>
                </div>
              </div>
            </aside>
          )}
        </div>
      )}
    </div>
  )
}
