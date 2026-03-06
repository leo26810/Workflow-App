import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import ErrorAlert from '../components/ErrorAlert'
import LoadingOverlay from '../components/LoadingOverlay'
import { apiClient } from '../services/apiClient'

const QUICK_TASKS = [
  { label: '🎨 Bild erstellen', value: 'Ich brauche ein Bild für meine Präsentation über ...' },
  { label: '💻 Code-Hilfe', value: 'Ich brauche Hilfe beim Debuggen von ...' },
  { label: '🔍 Recherche', value: 'Ich recherchiere zum Thema ... und brauche belastbare Quellen.' },
  { label: '📄 Dokument', value: 'Ich muss ein strukturiertes Dokument zu ... erstellen.' },
  { label: '📚 Lernen', value: 'Ich möchte für ... lernen und einen klaren Lernplan.' },
  { label: '💡 Analyse', value: 'Analysiere bitte ... und fasse die wichtigsten Punkte zusammen.' },
]

export default function Dashboard() {
  const [searchParams] = useSearchParams()
  const [task, setTask] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [copiedPrompt, setCopiedPrompt] = useState(false)
  const [selectedRating, setSelectedRating] = useState(0)
  const [ratingLoading, setRatingLoading] = useState(false)
  const [ratingSaved, setRatingSaved] = useState(false)
  const [ratingError, setRatingError] = useState(null)
  const [templates, setTemplates] = useState([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [templatesError, setTemplatesError] = useState(null)
  const [sessionSaving, setSessionSaving] = useState(false)
  const [sessionSaved, setSessionSaved] = useState(false)
  const [sessionError, setSessionError] = useState(null)
  const [profileName, setProfileName] = useState('Nutzer')
  const [recentTaskLine, setRecentTaskLine] = useState('')
  const [categoriesData, setCategoriesData] = useState([])
  const [toolsCatalog, setToolsCatalog] = useState([])
  const [kpiSummary, setKpiSummary] = useState(null)
  const [kpiLoading, setKpiLoading] = useState(false)
  const [kpiError, setKpiError] = useState(null)
  const [inputFocused, setInputFocused] = useState(false)
  const [resultVisible, setResultVisible] = useState(false)
  const resultRef = useRef(null)
  const autoTriggeredRef = useRef('')
  const recommendationAbortRef = useRef(null)

  const selectedFocus = searchParams.get('focus') || ''
  const selectedSubcategory = searchParams.get('subcategory') || ''
  const prefilledTask = searchParams.get('task') || ''
  const shouldAutoStart = searchParams.get('autostart') === '1'

  const difficultyColorMap = {
    easy: '#4ADE80',
    medium: '#FACC15',
    hard: '#F87171'
  }

  const greetingText = useMemo(() => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Guten Morgen'
    if (hour < 18) return 'Guten Nachmittag'
    return 'Guten Abend'
  }, [])

  const truncatedRecentLine = useMemo(() => {
    if (!recentTaskLine) return '—'
    return recentTaskLine.length > 50 ? `${recentTaskLine.slice(0, 47)}...` : recentTaskLine
  }, [recentTaskLine])

  const catalogByName = useMemo(() => {
    const map = new Map()
    for (const tool of toolsCatalog) {
      const key = (tool?.name || '').trim().toLowerCase()
      if (!key || map.has(key)) continue
      map.set(key, tool)
    }
    return map
  }, [toolsCatalog])

  const buildFrontendErrorMessage = (errorCode, fallbackMessage, details) => {
    const detailText = typeof details?.provider_message === 'string' ? details.provider_message : ''

    if (errorCode === 'ai_token_limit') {
      return `Tokenlimit erreicht: Anfrage ist zu lang für das aktuelle Modell.${detailText ? ` (${detailText})` : ''}`
    }
    if (errorCode === 'ai_rate_limit') {
      return 'Rate-Limit beim KI-Provider erreicht. Bitte kurz warten und erneut versuchen.'
    }
    if (errorCode === 'ai_auth_error' || errorCode === 'ai_api_key_missing') {
      return 'KI-Key/Authentifizierung fehlerhaft. Prüfe GROQ_API_KEY in backend/.env.'
    }
    if (errorCode === 'ai_provider_unavailable' || errorCode === 'ai_timeout') {
      return 'KI-Provider derzeit nicht erreichbar. Bitte erneut versuchen.'
    }
    if (errorCode === 'TIMEOUT') {
      return 'Zeitüberschreitung bei der Anfrage. Bitte erneut versuchen.'
    }
    if (errorCode === 'NETWORK' || errorCode === 'RETRY_EXHAUSTED') {
      return 'Netzwerkfehler bei der Anfrage. Bitte Verbindung prüfen und erneut versuchen.'
    }
    if (errorCode === 'recommendation_internal_error') {
      return 'Backend-Fehler bei der Empfehlungserstellung. Bitte Logs prüfen.'
    }

    return fallbackMessage || 'Unbekannter Fehler bei der Empfehlung.'
  }

  const parseRecommendationErrorResult = (resultPayload) => {
    const payload = resultPayload?.error?.details?.response_data || {}
    const diagnostics = payload?.ai_diagnostics || payload?.details || {}
    const errorCode = payload?.error_code || diagnostics?.code || resultPayload?.error?.code || null
    const fallbackMessage = payload?.error || resultPayload?.error?.message || `Server-Fehler (${resultPayload?.status || 0})`
    const message = buildFrontendErrorMessage(errorCode, fallbackMessage, diagnostics)

    return {
      message,
      errorCode,
      raw: payload,
    }
  }

  const estimateTemplateTime = (template) => {
    const tags = (template?.tags || '').toLowerCase()
    if (tags.includes('projekt') || tags.includes('facharbeit') || tags.includes('planung')) return '45–90 Min'
    if (tags.includes('quiz') || tags.includes('lernen') || tags.includes('zusammenfassung')) return '20–40 Min'
    return '25–50 Min'
  }

  const getSkillGapTarget = () => {
    const gap = (result?.recommendation?.skill_gap || '').toLowerCase()
    const sub = (result?.subcategory || '').toLowerCase()

    if (gap.includes('code') || gap.includes('programmier') || sub.includes('programmierung')) {
      return { focus: 'ki_code', subcategory: 'Programmierung' }
    }
    if (gap.includes('prompt') || sub.includes('prompt')) {
      return { focus: 'ki_prompt', subcategory: 'Promptgeneration' }
    }
    if (gap.includes('recherche') || gap.includes('quelle') || sub.includes('recherche')) {
      return { focus: 'recherche_info', subcategory: 'Informationsrecherche' }
    }
    if (gap.includes('projekt') || sub.includes('schulprojekte')) {
      return { focus: 'schule_projekt', subcategory: 'Schulprojekte' }
    }
    if (gap.includes('dokument') || sub.includes('dokumente')) {
      return { focus: 'schule_docs', subcategory: 'Mitschreiben & Dokumente' }
    }
    return { focus: 'schule_lernen', subcategory: 'Lernen & Üben' }
  }

  useEffect(() => {
    if (!prefilledTask) return
    setTask(prefilledTask)
  }, [prefilledTask])

  useEffect(() => {
    const autoKey = `${prefilledTask}|${selectedFocus}|${selectedSubcategory}|${shouldAutoStart ? '1' : '0'}`
    if (!shouldAutoStart || !prefilledTask.trim()) return
    if (autoTriggeredRef.current === autoKey) return
    autoTriggeredRef.current = autoKey

    const run = async () => {
      setTask(prefilledTask)
      setLoading(true)
      setError(null)
      setResult(null)
      const controller = new AbortController()
      recommendationAbortRef.current = controller
      try {
        const resultPayload = await apiClient.post('/api/recommendation', {
          task_description: prefilledTask,
        }, {
          timeout: 8000,
          retries: 1,
          signal: controller.signal,
        })
        if (!resultPayload.ok) {
          const parsedError = parseRecommendationErrorResult(resultPayload)
          throw new Error(parsedError.message)
        }
        const data = resultPayload.data
        setResult(data)
      } catch (err) {
        if (err?.name === 'AbortError') {
          setError('Empfehlungsanfrage wurde abgebrochen.')
        } else {
          setError(err.message || 'Verbindungsfehler. Ist das Backend gestartet?')
        }
      } finally {
        setLoading(false)
        recommendationAbortRef.current = null
      }
    }

    run()
  }, [prefilledTask, selectedFocus, selectedSubcategory, shouldAutoStart])

  useEffect(() => {
    if (!selectedSubcategory) {
      setTemplates([])
      setTemplatesError(null)
      return
    }

    let alive = true
    const loadTemplates = async () => {
      setTemplatesLoading(true)
      setTemplatesError(null)
      try {
        const resultPayload = await apiClient.get(`/api/task-templates?subcategory=${encodeURIComponent(selectedSubcategory)}`, {
          timeout: 5000,
          retries: 2,
        })
        if (!resultPayload.ok) throw new Error(resultPayload.error?.message || 'Templates konnten nicht geladen werden')
        const data = resultPayload.data
        if (!alive) return
        setTemplates(Array.isArray(data.templates) ? data.templates : [])
      } catch (err) {
        if (!alive) return
        setTemplates([])
        setTemplatesError(err.message || 'Fehler beim Laden der Templates')
      } finally {
        if (alive) setTemplatesLoading(false)
      }
    }

    loadTemplates()
    return () => { alive = false }
  }, [selectedSubcategory])

  useEffect(() => {
    if (!result) {
      setResultVisible(false)
      return
    }
    setResultVisible(false)
    const timer = setTimeout(() => setResultVisible(true), 10)
    return () => clearTimeout(timer)
  }, [result])

  useEffect(() => {
    let alive = true
    const loadHeaderData = async () => {
      setKpiLoading(true)
      setKpiError(null)
      try {
        const profileResult = await apiClient.get('/api/profile', { timeout: 5000, retries: 2 })
        if (profileResult.ok) {
          const profileData = profileResult.data
          if (alive) setProfileName(profileData?.user?.name || 'Nutzer')
        }

        const historyResult = await apiClient.get('/api/workflow-history', { timeout: 5000, retries: 2 })
        if (historyResult.ok) {
          const historyData = historyResult.data
          if (alive && Array.isArray(historyData) && historyData.length) {
            const randomIndex = Math.floor(Math.random() * historyData.length)
            const randomItem = historyData[randomIndex]
            setRecentTaskLine(randomItem?.task_description || '')
          }
        }

        const categoriesResult = await apiClient.get('/api/categories', { timeout: 5000, retries: 2 })
        if (categoriesResult.ok) {
          const categoriesJson = categoriesResult.data
          if (alive) setCategoriesData(Array.isArray(categoriesJson) ? categoriesJson : [])
        }

        const [kpiResult, toolsResult] = await Promise.all([
          apiClient.get('/api/kpis/report?days=30', { timeout: 5000, retries: 2 }),
          apiClient.get('/api/tools?limit=500&page=1', { timeout: 5000, retries: 2 }),
        ])
        if (kpiResult.ok) {
          const kpiJson = kpiResult.data
          if (alive) setKpiSummary(kpiJson)
        } else if (alive) {
          setKpiError(`KPI nicht verfügbar (${kpiResult.status})`)
        }

        if (toolsResult.ok) {
          const toolsJson = toolsResult.data
          if (alive) setToolsCatalog(Array.isArray(toolsJson?.items) ? toolsJson.items : [])
        }
      } catch {
        if (alive) setKpiError('KPI derzeit nicht erreichbar')
      } finally {
        if (alive) setKpiLoading(false)
      }
    }

    loadHeaderData()
    return () => { alive = false }
  }, [])

  const handleGetRecommendation = async () => {
    if (!task.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    setSelectedRating(0)
    setRatingSaved(false)
    setRatingError(null)
    const controller = new AbortController()
    recommendationAbortRef.current = controller
    try {
      const resultPayload = await apiClient.post('/api/recommendation', {
        task_description: task,
      }, {
        timeout: 8000,
        retries: 1,
        signal: controller.signal,
      })
      if (!resultPayload.ok) {
        const parsedError = parseRecommendationErrorResult(resultPayload)
        throw new Error(parsedError.message)
      }
      const data = resultPayload.data
      setResult(data)
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
    } catch (err) {
      if (err?.name === 'AbortError') {
        setError('Empfehlungsanfrage wurde abgebrochen.')
      } else {
        setError(err.message || 'Verbindungsfehler. Ist das Backend gestartet?')
      }
    } finally {
      setLoading(false)
      recommendationAbortRef.current = null
    }
  }

  const handleCancelRecommendation = () => {
    recommendationAbortRef.current?.abort()
  }

  const handleCopyPrompt = () => {
    navigator.clipboard.writeText(result?.recommendation?.optimized_prompt || '')
    setCopiedPrompt(true)
    setTimeout(() => setCopiedPrompt(false), 2000)
  }

  const handleRateWorkflow = async (rating) => {
    const historyId = result?.history_id
    if (!historyId || ratingLoading) return

    setRatingLoading(true)
    setRatingError(null)
    try {
      const resultPayload = await apiClient.post('/api/workflow-history', {
        id: historyId,
        rating,
      }, {
        timeout: 10000,
        retries: 1,
      })

      if (!resultPayload.ok) throw new Error(resultPayload.error?.message || 'Feedback konnte nicht gespeichert werden')
      setSelectedRating(rating)
      setRatingSaved(true)
    } catch (err) {
      setRatingError(err.message || 'Fehler beim Speichern der Bewertung')
    } finally {
      setRatingLoading(false)
    }
  }

  const handleSaveResearchSession = async () => {
    if (!result) return

    const sources = (result?.recommendation?.recommended_tools || [])
      .filter(item => item?.url)
      .map(item => ({ url: item.url, title: item.name }))

    const summary = [
      ...(result?.recommendation?.workflow || []).slice(0, 4),
      ...(result?.recommendation?.tips || []).slice(0, 2),
    ].join(' | ')

    setSessionSaving(true)
    setSessionError(null)
    try {
      const resultPayload = await apiClient.post('/api/research-session', {
        query: result?.task || task,
        sources,
        summary,
        tags: 'dashboard,recherche,ki',
      }, {
        timeout: 10000,
        retries: 1,
      })
      if (!resultPayload.ok) throw new Error(resultPayload.error?.message || 'Session konnte nicht gespeichert werden')
      setSessionSaved(true)
      setTimeout(() => setSessionSaved(false), 1800)
    } catch (err) {
      setSessionError(err.message || 'Fehler beim Speichern der Session')
    } finally {
      setSessionSaving(false)
    }
  }

  const baseCardStyle = {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: '10px',
    padding: '1.25rem',
  }

  const cardTitleStyle = {
    margin: '0 0 0.9rem',
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: 'rgba(255,255,255,0.4)',
    fontWeight: 500,
  }

  const diagnosticDetailText = (result?.ai_diagnostics?.provider_message || '').trim()
  const shortDiagnosticDetail = diagnosticDetailText.length > 180
    ? `${diagnosticDetailText.slice(0, 177)}...`
    : diagnosticDetailText
  const whyTheseToolsText = (result?.recommendation?.why_these_tools || '').trim() || 'Die Tools passen zu Aufgabe, Skill-Level und bisherigen positiven Bewertungen.'

  const getToolMeta = (tool) => {
    const key = (tool?.name || '').trim().toLowerCase()
    if (!key) return tool || {}
    const catalogItem = catalogByName.get(key)
    return catalogItem ? { ...catalogItem, ...tool } : (tool || {})
  }

  const getTagList = (text) => {
    if (!text) return []
    return String(text)
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean)
      .slice(0, 4)
  }

  return (
    <div style={{ padding: '2.4rem 2.7rem', maxWidth: '980px', margin: '0 auto' }}>
      <LoadingOverlay
        isVisible={loading}
        message="Empfehlung wird erstellt..."
        variant="full"
        onCancel={handleCancelRecommendation}
      />
      <div style={{ marginBottom: '2.2rem' }}>
        <h1 style={{ margin: '0 0 0.45rem', fontSize: '2rem', fontWeight: 300, color: 'rgba(255,255,255,0.95)' }}>
          {greetingText}, {profileName}.
        </h1>
        <p style={{ margin: 0, color: 'rgba(255,255,255,0.4)', fontSize: '13px' }}>
          {`Zuletzt: ${truncatedRecentLine}`}
        </p>
      </div>

      <div
        style={{
          background: 'rgba(255,255,255,0.06)',
          borderRadius: '12px',
          padding: '0.9rem 0.95rem 0.65rem',
          boxShadow: inputFocused ? '0 0 0 1px #4FFFB0, 0 0 20px rgba(79,255,176,0.1)' : 'none',
          transition: 'box-shadow 0.2s ease',
          marginBottom: '1rem',
        }}
      >
        <textarea
          placeholder="Was willst du heute erledigen?"
          value={task}
          onChange={e => setTask(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleGetRecommendation() }}
          onFocus={() => setInputFocused(true)}
          onBlur={() => setInputFocused(false)}
          rows={3}
          style={{
            width: '100%',
            resize: 'vertical',
            border: 'none',
            outline: 'none',
            background: 'transparent',
            color: 'rgba(255,255,255,0.9)',
            fontSize: '0.95rem',
            lineHeight: 1.5,
            fontFamily: 'Space Grotesk, sans-serif',
            minHeight: '88px',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.45rem' }}>
          <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.25)' }}>↵ Enter</span>
          <button
            onClick={handleGetRecommendation}
            disabled={!task.trim() || loading}
            style={{
              border: '1px solid rgba(255,255,255,0.12)',
              background: 'rgba(255,255,255,0.04)',
              color: 'rgba(255,255,255,0.82)',
              padding: '0.35rem 0.62rem',
              borderRadius: '8px',
              fontSize: '0.76rem',
              cursor: !task.trim() || loading ? 'default' : 'pointer',
              opacity: !task.trim() || loading ? 0.6 : 1,
              fontFamily: 'Space Grotesk, sans-serif',
            }}
          >
            {loading ? '⏳ Analysiere…' : '✦ Empfehlung anfordern'}
          </button>
        </div>
      </div>

      <div style={{ marginBottom: '1.2rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
        {QUICK_TASKS.map((item) => (
          <button
            key={item.label}
            onClick={() => setTask(item.value)}
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.08)',
              color: 'rgba(255,255,255,0.86)',
              padding: '0.32rem 0.62rem',
              borderRadius: '999px',
              fontSize: '12px',
              cursor: 'pointer',
              fontFamily: 'Space Grotesk, sans-serif',
              transition: 'all 0.14s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(79,255,176,0.08)'
              e.currentTarget.style.color = '#4FFFB0'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
              e.currentTarget.style.color = 'rgba(255,255,255,0.86)'
            }}
          >
            {item.label}
          </button>
        ))}
      </div>

      {selectedSubcategory && (
        <div style={{ ...baseCardStyle, marginBottom: '1.4rem', padding: '0.95rem 1rem' }}>
          <p style={{ ...cardTitleStyle, marginBottom: '0.7rem' }}>Templates · {selectedSubcategory}</p>
          {templatesLoading && <p style={{ margin: 0, fontSize: '0.82rem', color: 'rgba(255,255,255,0.55)' }}>Templates werden geladen…</p>}
          {templatesError && <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--danger)' }}>{templatesError}</p>}
          {!templatesLoading && !templatesError && (
            <div style={{ display: 'grid', gap: '0.45rem' }}>
              {templates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => setTask(template.example_input || template.description || template.title)}
                  style={{
                    textAlign: 'left',
                    background: 'transparent',
                    border: '1px solid rgba(255,255,255,0.08)',
                    color: 'rgba(255,255,255,0.85)',
                    borderRadius: '8px',
                    padding: '0.58rem 0.7rem',
                    cursor: 'pointer',
                    fontFamily: 'Space Grotesk, sans-serif',
                  }}
                >
                  <strong style={{ fontSize: '0.82rem' }}>{template.title}</strong>
                  <p style={{ margin: '0.22rem 0 0', fontSize: '0.76rem', color: 'rgba(255,255,255,0.5)' }}>
                    {template.example_input || template.description} · ⏱ {estimateTemplateTime(template)}
                  </p>
                </button>
              ))}
              {!templates.length && <p style={{ margin: 0, fontSize: '0.8rem', color: 'rgba(255,255,255,0.45)' }}>Keine Templates gefunden.</p>}
            </div>
          )}
        </div>
      )}

      {error && (
        <ErrorAlert
          error={error}
          variant="inline"
          onDismiss={() => setError(null)}
          onRetry={() => handleGetRecommendation()}
        />
      )}

      {result && (
        <div
          ref={resultRef}
          style={{
            opacity: resultVisible ? 1 : 0,
            transform: resultVisible ? 'translateY(0px)' : 'translateY(12px)',
            transition: 'opacity 350ms ease-out, transform 350ms ease-out',
          }}
        >
          <div style={{ display: 'grid', gap: '0.8rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.62)' }}>✅ KI-Analyse</span>
                {!!(result.recommendation?.difficulty || '').trim() && (
                  <span style={{
                    fontSize: '0.68rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    fontWeight: 700,
                    color: '#0B1020',
                    background: difficultyColorMap[result.recommendation.difficulty] || '#CBD5E1',
                    padding: '0.15rem 0.44rem',
                    borderRadius: '999px'
                  }}>
                    {result.recommendation.difficulty}
                  </span>
                )}
                {!!(result.recommendation?.estimated_time || '').trim() && (
                  <span style={{ fontSize: '0.74rem', color: 'rgba(255,255,255,0.55)' }}>
                    ⏱ {result.recommendation.estimated_time}
                  </span>
                )}
              </div>
              {(result.area || result.subcategory) && (
                <span style={{ fontSize: '0.73rem', color: 'rgba(255,255,255,0.4)' }}>
                  {result.area || 'Bereich'} · {result.subcategory || 'Unterkategorie'}
                </span>
              )}
            </div>

            {!!(result.personalization_note || '').trim() && (
              <p style={{ margin: 0, fontSize: '0.8rem', color: 'rgba(255,255,255,0.45)', fontStyle: 'italic' }}>
                👤 {result.personalization_note}
              </p>
            )}

            {result.mode === 'demo' && (
              <div style={{ ...baseCardStyle, border: '1px solid rgba(251,191,36,0.2)', padding: '0.65rem 0.9rem' }}>
                <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--warning)' }}>
                  ⚠️ Demo-Modus aktiv.
                </p>
              </div>
            )}

            {result.ai_diagnostics?.code && result.ai_diagnostics.code !== 'ai_ok' && (
              <div style={{ ...baseCardStyle, border: '1px solid rgba(248,113,113,0.22)', padding: '0.72rem 0.9rem' }}>
                <p style={{ margin: '0 0 0.2rem', fontSize: '0.8rem', color: 'var(--danger)' }}>
                  KI-Diagnose: {result.ai_diagnostics.user_message || result.ai_diagnostics.code}
                </p>
                {!!shortDiagnosticDetail && (
                  <p style={{ margin: 0, fontSize: '0.73rem', color: 'rgba(255,255,255,0.52)', lineHeight: 1.4 }}>
                    {shortDiagnosticDetail}
                  </p>
                )}
              </div>
            )}

            {!!(result.next_step || '').trim() && (
              <div style={{ ...baseCardStyle, borderLeft: '2px solid #4FFFB0' }}>
                <p style={cardTitleStyle}>▶ Jetzt sofort:</p>
                <p style={{ margin: 0, fontSize: '16px', color: '#FFFFFF', lineHeight: 1.45 }}>
                  {result.next_step}
                </p>
              </div>
            )}

            {result.recommendation?.workflow?.length > 0 && (
              <div style={baseCardStyle}>
                <p style={cardTitleStyle}>Workflow</p>
                <div>
                  {result.recommendation.workflow.map((step, i) => (
                    <div key={i} style={{ padding: '0.52rem 0', borderBottom: i < result.recommendation.workflow.length - 1 ? '1px solid rgba(255,255,255,0.08)' : 'none' }}>
                      <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'flex-start' }}>
                        <span style={{ fontSize: '0.82rem', color: 'rgba(255,255,255,0.25)', minWidth: '16px' }}>{i + 1}</span>
                        <p style={{ margin: 0, fontSize: '14px', color: 'rgba(255,255,255,0.8)', lineHeight: 1.5 }}>{step}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.recommendation?.recommended_tools?.length > 0 && (
              <div style={baseCardStyle}>
                <p style={cardTitleStyle}>Empfohlene Tools</p>
                <div>
                  {result.recommendation.recommended_tools.map((tool, i) => (
                    (() => {
                      const metaTool = getToolMeta(tool)
                      const toolTags = getTagList(metaTool.tags)
                      return (
                    <div key={i} style={{ padding: '0.58rem 0', borderBottom: i < result.recommendation.recommended_tools.length - 1 ? '1px solid rgba(255,255,255,0.08)' : 'none' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.8rem' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
                            <p style={{ margin: 0, fontSize: '14px', color: '#FFFFFF', fontWeight: 600 }}>{metaTool.name || tool.name}</p>
                            {typeof tool.match_score === 'number' && tool.match_score > 0 && (
                              <span className="inline-flex items-center rounded-full border border-gray-500/40 bg-gray-500/20 px-2 py-0.5 text-[11px] leading-none text-gray-300">
                                {Math.round(tool.match_score)} Pkt
                              </span>
                            )}
                            {!!(metaTool.domain || '').trim() && (
                              <span className="inline-flex items-center rounded-full border border-cyan-400/40 bg-cyan-500/10 px-2 py-0.5 text-[11px] leading-none text-cyan-200">
                                {metaTool.domain}
                              </span>
                            )}
                            {!!(metaTool.pricing_model || '').trim() && (
                              <span className="inline-flex items-center rounded-full border border-emerald-400/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] leading-none text-emerald-200">
                                {metaTool.pricing_model}
                              </span>
                            )}
                            {!!(metaTool.skill_requirement || '').trim() && (
                              <span className="inline-flex items-center rounded-full border border-amber-400/30 bg-amber-500/10 px-2 py-0.5 text-[11px] leading-none text-amber-200">
                                Level: {metaTool.skill_requirement}
                              </span>
                            )}
                          </div>
                          <p style={{ margin: '0.2rem 0 0', fontSize: '13px', color: 'rgba(255,255,255,0.5)' }}>
                            {tool.reason || tool.match_reason || metaTool.best_for || tool.best_for || ''}
                          </p>
                          {!!(metaTool.use_case || '').trim() && (
                            <p style={{ margin: '0.25rem 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.62)' }}>
                              {metaTool.use_case}
                            </p>
                          )}
                          {toolTags.length > 0 && (
                            <div style={{ marginTop: '0.28rem', display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                              {toolTags.map((tag) => (
                                <span key={`${metaTool.name}-${tag}`} className="tag">#{tag}</span>
                              ))}
                            </div>
                          )}
                          {!!(metaTool.platform || '').trim() && (
                            <p style={{ margin: '0.25rem 0 0', fontSize: '11px', color: 'rgba(255,255,255,0.45)' }}>
                              Plattform: {metaTool.platform}
                            </p>
                          )}
                          {!!(tool.specific_tip || '').trim() && (
                            <p style={{ margin: '0.24rem 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.52)', fontStyle: 'italic' }}>
                              💡 {tool.specific_tip}
                            </p>
                          )}
                        </div>
                        {!!(metaTool.url || tool.url || '').trim() && (
                          <a
                            href={metaTool.url || tool.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ fontSize: '12px', color: 'var(--accent2)', textDecoration: 'none', whiteSpace: 'nowrap' }}
                          >
                            Öffnen ↗
                          </a>
                        )}
                      </div>
                    </div>
                      )
                    })()
                  ))}
                </div>

                <div style={{ marginTop: '0.75rem', paddingTop: '0.72rem', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                  <p style={{ ...cardTitleStyle, marginBottom: '0.35rem' }}>🧠 Warum diese Tools</p>
                  <p style={{ margin: 0, fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: 1.5 }}>
                    {whyTheseToolsText}
                  </p>
                </div>

                {result.area === 'Internet-Recherche' && (
                  <div style={{ marginTop: '0.75rem', paddingTop: '0.72rem', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                    <button
                      onClick={handleSaveResearchSession}
                      disabled={sessionSaving}
                      style={{
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        color: 'rgba(255,255,255,0.8)',
                        padding: '0.34rem 0.62rem',
                        borderRadius: '8px',
                        fontSize: '0.76rem',
                        cursor: sessionSaving ? 'default' : 'pointer',
                        fontFamily: 'Space Grotesk, sans-serif',
                      }}
                    >
                      {sessionSaving ? 'Speichere…' : 'Session speichern'}
                    </button>
                    {sessionSaved && <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: 'var(--accent)' }}>✓ gespeichert</span>}
                    {sessionError && <p style={{ margin: '0.35rem 0 0', fontSize: '0.75rem', color: 'var(--danger)' }}>{sessionError}</p>}
                  </div>
                )}
              </div>
            )}

            {!!(result.recommendation?.optimized_prompt || '').trim() && (
              <div style={baseCardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.7rem' }}>
                  <p style={{ ...cardTitleStyle, margin: 0 }}>Optimierter Prompt</p>
                  <button
                    onClick={handleCopyPrompt}
                    style={{
                      border: '1px solid rgba(255,255,255,0.1)',
                      background: 'rgba(255,255,255,0.04)',
                      color: copiedPrompt ? '#4FFFB0' : 'rgba(255,255,255,0.72)',
                      width: '28px',
                      height: '28px',
                      borderRadius: '7px',
                      cursor: 'pointer',
                      fontSize: '0.82rem',
                    }}
                    title="Prompt kopieren"
                  >
                    ⧉
                  </button>
                </div>
                <div style={{
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid rgba(255,255,255,0.07)',
                  borderRadius: '8px',
                  padding: '0.9rem',
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                  fontSize: '0.84rem',
                  lineHeight: 1.5,
                  color: 'rgba(79,255,176,0.8)',
                  whiteSpace: 'pre-wrap',
                }}>
                  {result.recommendation.optimized_prompt}
                </div>
              </div>
            )}

            {result.recommendation?.tips?.length > 0 && (
              <div style={baseCardStyle}>
                <p style={cardTitleStyle}>Tipps</p>
                <ul style={{ margin: 0, paddingLeft: '1.1rem', display: 'grid', gap: '0.24rem' }}>
                  {result.recommendation.tips.map((tip, i) => (
                    <li key={i} style={{ fontSize: '14px', color: 'rgba(255,255,255,0.8)', lineHeight: 1.5 }}>{tip}</li>
                  ))}
                </ul>
              </div>
            )}

            {!!(result.recommendation?.skill_gap || '').trim() && (
              <div style={baseCardStyle}>
                <p style={cardTitleStyle}>📈 Dein nächster Lernschritt</p>
                <p style={{ margin: 0, fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: 1.5 }}>
                  {result.recommendation.skill_gap}
                </p>
                <div style={{ marginTop: '0.52rem' }}>
                  <Link
                    to={`/?focus=${encodeURIComponent(getSkillGapTarget().focus)}&subcategory=${encodeURIComponent(getSkillGapTarget().subcategory)}`}
                    style={{ fontSize: '0.77rem', color: 'var(--accent2)', textDecoration: 'none' }}
                  >
                    Mehr dazu ↗
                  </Link>
                </div>
              </div>
            )}

            {!!(result.model_used || '').trim() && (
              <div style={{ textAlign: 'right', fontSize: '0.68rem', color: 'rgba(255,255,255,0.45)' }}>
                via {result.model_used}
              </div>
            )}

            {result.history_id && (
              <div style={{ marginTop: '0.1rem', padding: '0.2rem 0' }}>
                <p style={{ margin: '0 0 0.36rem', fontSize: '0.78rem', color: 'rgba(255,255,255,0.52)' }}>
                  War diese Empfehlung hilfreich?
                </p>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', flexWrap: 'wrap' }}>
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => handleRateWorkflow(star)}
                      disabled={ratingLoading}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        cursor: ratingLoading ? 'default' : 'pointer',
                        fontSize: '1.18rem',
                        lineHeight: 1,
                        color: star <= selectedRating ? '#FBBF24' : 'rgba(255,255,255,0.2)',
                        opacity: ratingLoading ? 0.7 : 1,
                        padding: '0.05rem 0.12rem'
                      }}
                      aria-label={`${star} Sterne`}
                      title={`${star} Sterne`}
                    >
                      ★
                    </button>
                  ))}
                  {ratingLoading && <span style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.45)' }}>Speichere…</span>}
                </div>
                {ratingSaved && (
                  <p style={{ margin: '0.36rem 0 0', fontSize: '0.74rem', color: '#4FFFB0' }}>
                    Danke für dein Feedback!
                  </p>
                )}
                {ratingError && (
                  <p style={{ margin: '0.3rem 0 0', fontSize: '0.74rem', color: 'var(--danger)' }}>
                    {ratingError}
                  </p>
                )}
              </div>
            )}
          </div>
      </div>
      )}

      {!result && !loading && !error && (
        <div style={{ textAlign: 'center', padding: '3.2rem 2rem', color: 'var(--text-muted)' }}>
          <div style={{ marginBottom: '0.75rem', display: 'flex', justifyContent: 'center' }}>
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <circle cx="20" cy="20" r="14" stroke="rgba(255,255,255,0.08)" strokeWidth="1.5" />
              <path d="M20 26V14M20 14L15.8 18.2M20 14L24.2 18.2" stroke="rgba(255,255,255,0.08)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <p style={{ fontSize: '0.9rem', margin: '0 0 0.35rem' }}>Bereit für deinen nächsten Workflow</p>
          <p style={{ fontSize: '0.78rem', margin: 0 }}>Beschreibe kurz deine Aufgabe und starte direkt.</p>
        </div>
      )}
    </div>
  )
}
