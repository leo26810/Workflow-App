import { useEffect, useMemo, useState } from 'react'
import { apiClient } from '../services/apiClient'

const ENDPOINTS = [
  { key: 'health', label: 'Health', url: '/api/health' },
  { key: 'systemStats', label: 'System Stats', url: '/api/system/stats' },
  { key: 'domains', label: 'Domains', url: '/api/domains' },
  { key: 'categories', label: 'Categories', url: '/api/categories' },
  { key: 'tools', label: 'Tools', url: '/api/tools?page=1&limit=500' },
  { key: 'history', label: 'Workflow History', url: '/api/workflow-history' },
  { key: 'feedback', label: 'Recommendation Feedback', url: '/api/recommendation-feedback?page=1&limit=100' },
  { key: 'researchSessions', label: 'Research Sessions', url: '/api/research-sessions' },
  { key: 'kpiSnapshot', label: 'KPI Snapshot', url: '/api/kpis?days=30' },
  { key: 'kpiReport', label: 'KPI Report', url: '/api/kpis/report?days=30' },
  { key: 'kpiTargets', label: 'KPI Targets', url: '/api/kpis/targets' },
  { key: 'kpiScheduler', label: 'KPI Scheduler', url: '/api/kpis/scheduler-status' },
  { key: 'telegram', label: 'Telegram Status', url: '/api/telegram/status' },
  { key: 'profile', label: 'Profile', url: '/api/profile?page=1&limit=100' },
  { key: 'userContext', label: 'User Context', url: '/api/user-context' },
]

function toPercent(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return 'n/a'
  return `${value.toFixed(1)}%`
}

function formatNumber(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return 'n/a'
  return String(value)
}

export default function ConfigPage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [responses, setResponses] = useState({})

  useEffect(() => {
    let alive = true

    const loadConfigData = async () => {
      setLoading(true)
      setError(null)

      try {
        const items = await Promise.all(
          ENDPOINTS.map(async (ep) => {
            try {
              const result = await apiClient.get(ep.url, { timeout: 5000, retries: 1 })
              return {
                key: ep.key,
                label: ep.label,
                url: ep.url,
                ok: result.ok,
                status: result.status,
                data: result.ok ? result.data : null,
                error: result.error?.message,
              }
            } catch (e) {
              return {
                key: ep.key,
                label: ep.label,
                url: ep.url,
                ok: false,
                status: 0,
                error: e?.message || 'Request failed',
                data: null,
              }
            }
          })
        )

        if (!alive) return

        const next = {}
        for (const item of items) {
          next[item.key] = item
        }
        setResponses(next)
      } catch (e) {
        if (!alive) return
        setError(e?.message || 'Config-Daten konnten nicht geladen werden')
      } finally {
        if (alive) setLoading(false)
      }
    }

    loadConfigData()
    return () => {
      alive = false
    }
  }, [])

  const health = responses.health?.data || {}
  const systemStats = responses.systemStats?.data || {}
  const tables = systemStats.tables || {}
  const coverage = systemStats.coverage || {}
  const quality = systemStats.quality || {}
  const distributions = systemStats.distributions || {}

  const kpiSnapshot = responses.kpiSnapshot?.data || {}
  const kpiReport = responses.kpiReport?.data || {}
  const kpiTargets = responses.kpiTargets?.data || {}
  const kpiScheduler = responses.kpiScheduler?.data || {}
  const telegram = responses.telegram?.data || {}

  const profile = responses.profile?.data || {}
  const contextItems = Array.isArray(responses.userContext?.data) ? responses.userContext.data : []
  const categories = Array.isArray(responses.categories?.data) ? responses.categories.data : []
  const domains = Array.isArray(responses.domains?.data?.domains) ? responses.domains.data.domains : []
  const toolsPayload = responses.tools?.data || {}
  const toolItems = Array.isArray(toolsPayload.items) ? toolsPayload.items : []
  const workflowHistory = Array.isArray(responses.history?.data) ? responses.history.data : []
  const researchSessions = Array.isArray(responses.researchSessions?.data) ? responses.researchSessions.data : []
  const feedbackPayload = responses.feedback?.data || {}
  const feedbackItems = Array.isArray(feedbackPayload.items) ? feedbackPayload.items : []

  const subcategoryCount = useMemo(
    () => categories.reduce((sum, category) => sum + ((category.subcategories || []).length), 0),
    [categories]
  )

  const templateCount = useMemo(() => {
    return categories.reduce((sum, category) => {
      const subcategories = Array.isArray(category.subcategories) ? category.subcategories : []
      const local = subcategories.reduce((inner, sub) => inner + ((sub.task_templates || []).length), 0)
      return sum + local
    }, 0)
  }, [categories])

  const contextByArea = useMemo(() => {
    const byArea = {}
    for (const item of contextItems) {
      const area = item?.area || 'unbekannt'
      byArea[area] = (byArea[area] || 0) + 1
    }
    return byArea
  }, [contextItems])

  const endpointSummary = useMemo(() => {
    const all = Object.values(responses)
    const online = all.filter((item) => item.ok).length
    return { online, total: ENDPOINTS.length }
  }, [responses])

  const failingTargets = useMemo(() => {
    return Object.entries(kpiTargets)
      .filter(([, target]) => target?.meets_target === false)
      .map(([key]) => key)
  }, [kpiTargets])

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

  const statValue = {
    margin: 0,
    color: 'rgba(255,255,255,0.9)',
    fontSize: '1.05rem',
    fontWeight: 600,
  }

  return (
    <div style={{ padding: '2.2rem 2.7rem', maxWidth: '1060px', margin: '0 auto' }}>
      <div style={{ marginBottom: '1.2rem' }}>
        <h1 style={{ margin: '0 0 0.35rem', fontSize: '1.9rem', fontWeight: 300, color: 'rgba(255,255,255,0.95)' }}>
          Config
        </h1>
        <p style={{ margin: 0, color: 'rgba(255,255,255,0.45)', fontSize: '13px' }}>
          Vollansicht fuer Datenbank-Stand, Backend-Runtime, Endpoint-Status und Datenqualitaet.
        </p>
      </div>

      {loading && <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: '0.85rem' }}>Lade Config-Daten...</p>}
      {error && <p style={{ color: 'var(--danger)', fontSize: '0.85rem' }}>{error}</p>}

      {!loading && !error && (
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          <div style={{ ...cardStyle, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '0.65rem' }}>
            <div>
              <p style={sectionTitle}>Endpoints</p>
              <p style={statValue}>{endpointSummary.online}/{endpointSummary.total}</p>
              <p style={{ margin: '0.15rem 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.55)' }}>online</p>
            </div>
            <div>
              <p style={sectionTitle}>Domains</p>
              <p style={statValue}>{formatNumber(tables.domains ?? domains.length)}</p>
              <p style={{ margin: '0.15rem 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.55)' }}>Wissensdomaenen</p>
            </div>
            <div>
              <p style={sectionTitle}>Taxonomie</p>
              <p style={statValue}>{formatNumber(tables.workflow_categories ?? categories.length)} / {formatNumber(tables.sub_categories ?? subcategoryCount)}</p>
              <p style={{ margin: '0.15rem 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.55)' }}>Kategorien / Subkategorien</p>
            </div>
            <div>
              <p style={sectionTitle}>Templates</p>
              <p style={statValue}>{formatNumber(tables.task_templates ?? templateCount)}</p>
              <p style={{ margin: '0.15rem 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.55)' }}>Task-Templates</p>
            </div>
            <div>
              <p style={sectionTitle}>Tools</p>
              <p style={statValue}>{formatNumber(tables.tools ?? toolsPayload.total ?? toolItems.length)}</p>
              <p style={{ margin: '0.15rem 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.55)' }}>Tool-Datensaetze</p>
            </div>
            <div>
              <p style={sectionTitle}>Feedback</p>
              <p style={statValue}>{formatNumber(tables.recommendation_feedback ?? feedbackPayload.pagination?.total ?? feedbackItems.length)}</p>
              <p style={{ margin: '0.15rem 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.55)' }}>Empfehlungsfeedback</p>
            </div>
            <div>
              <p style={sectionTitle}>History</p>
              <p style={statValue}>{formatNumber(tables.workflow_history ?? workflowHistory.length)}</p>
              <p style={{ margin: '0.15rem 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.55)' }}>Workflow-Eintraege</p>
            </div>
            <div>
              <p style={sectionTitle}>Research</p>
              <p style={statValue}>{formatNumber(tables.research_sessions ?? researchSessions.length)}</p>
              <p style={{ margin: '0.15rem 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.55)' }}>Research-Sessions</p>
            </div>
          </div>

          <div style={{ ...cardStyle, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '0.6rem' }}>
            <div>
              <p style={sectionTitle}>System Runtime</p>
              <p style={{ margin: 0, fontSize: '13px', color: 'rgba(255,255,255,0.85)' }}>Status: {health.status || systemStats.status || 'n/a'}</p>
              <p style={{ margin: '0.2rem 0 0', fontSize: '13px', color: 'rgba(255,255,255,0.7)' }}>KI: {health.groq_configured ? 'aktiv' : 'demo/fallback'}</p>
              <p style={{ margin: '0.2rem 0 0', fontSize: '13px', color: 'rgba(255,255,255,0.7)' }}>Telegram: {telegram.enabled ? `aktiv (${telegram.mode || 'n/a'})` : 'inaktiv'}</p>
            </div>
            <div>
              <p style={sectionTitle}>KPI Snapshot</p>
              <p style={{ margin: 0, fontSize: '13px', color: 'rgba(255,255,255,0.85)' }}>Health Index: {kpiSnapshot.kpi_health_index ?? 'n/a'}</p>
              <p style={{ margin: '0.2rem 0 0', fontSize: '13px', color: 'rgba(255,255,255,0.7)' }}>Avg Rating: {kpiSnapshot.avg_user_rating ?? 'n/a'}</p>
              <p style={{ margin: '0.2rem 0 0', fontSize: '13px', color: 'rgba(255,255,255,0.7)' }}>Top3-Hit: {kpiSnapshot.top3_hit_rate ?? 'n/a'}</p>
            </div>
            <div>
              <p style={sectionTitle}>KPI Scheduler</p>
              <p style={{ margin: 0, fontSize: '13px', color: 'rgba(255,255,255,0.85)' }}>Enabled: {kpiScheduler.enabled ? 'ja' : 'nein'}</p>
              <p style={{ margin: '0.2rem 0 0', fontSize: '13px', color: 'rgba(255,255,255,0.7)' }}>Started: {kpiScheduler.started ? 'ja' : 'nein'}</p>
              <p style={{ margin: '0.2rem 0 0', fontSize: '13px', color: 'rgba(255,255,255,0.7)' }}>Intervall: {kpiScheduler.interval_minutes ?? 'n/a'} min</p>
            </div>
            <div>
              <p style={sectionTitle}>KPI Targets</p>
              <p style={{ margin: 0, fontSize: '13px', color: failingTargets.length ? 'rgba(255,209,102,0.92)' : 'rgba(79,255,176,0.92)' }}>
                {failingTargets.length ? `${failingTargets.length} Ziele unterschritten` : 'Alle Ziele im Soll'}
              </p>
              {!!failingTargets.length && (
                <p style={{ margin: '0.22rem 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>
                  {failingTargets.join(', ')}
                </p>
              )}
            </div>
          </div>

          <div style={{ ...cardStyle, display: 'grid', gap: '0.55rem' }}>
            <p style={sectionTitle}>Datenqualitaet & Coverage</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '0.45rem' }}>
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>Tool-Tags: {toPercent(coverage.tools_tag_coverage)}</div>
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>Tool-Domain: {toPercent(coverage.tools_domain_coverage)}</div>
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>Tool-UseCase: {toPercent(coverage.tools_use_case_coverage)}</div>
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>Tool-Plattform: {toPercent(coverage.tools_platform_coverage)}</div>
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>Tool-Pricing: {toPercent(coverage.tools_pricing_coverage)}</div>
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>Tool-Skill: {toPercent(coverage.tools_skill_coverage)}</div>
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>Category to Domain Link: {toPercent(coverage.category_domain_link_coverage)}</div>
            </div>
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '0.55rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.45rem' }}>
              <div style={{ fontSize: '13px', color: quality.invalid_pricing_values ? 'rgba(255,120,120,0.9)' : 'rgba(79,255,176,0.9)' }}>
                Invalid pricing values: {formatNumber(quality.invalid_pricing_values)}
              </div>
              <div style={{ fontSize: '13px', color: quality.invalid_skill_values ? 'rgba(255,120,120,0.9)' : 'rgba(79,255,176,0.9)' }}>
                Invalid skill values: {formatNumber(quality.invalid_skill_values)}
              </div>
              <div style={{ fontSize: '13px', color: quality.bad_tool_urls ? 'rgba(255,120,120,0.9)' : 'rgba(79,255,176,0.9)' }}>
                Bad tool URLs: {formatNumber(quality.bad_tool_urls)}
              </div>
              <div style={{ fontSize: '13px', color: quality.duplicate_tool_names ? 'rgba(255,120,120,0.9)' : 'rgba(79,255,176,0.9)' }}>
                Duplicate tool names: {formatNumber(quality.duplicate_tool_names)}
              </div>
            </div>
          </div>

          <div style={{ ...cardStyle, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '0.7rem' }}>
            <div>
              <p style={sectionTitle}>Verteilung Tools nach Domain</p>
              {(distributions.tools_by_domain || []).slice(0, 8).map((row) => (
                <div key={`d-${row.key}`} style={{ fontSize: '13px', color: 'rgba(255,255,255,0.8)', marginBottom: '0.22rem' }}>
                  {row.key}: <span style={{ color: 'rgba(255,255,255,0.6)' }}>{row.count}</span>
                </div>
              ))}
            </div>
            <div>
              <p style={sectionTitle}>Verteilung Pricing</p>
              {(distributions.tools_by_pricing || []).slice(0, 8).map((row) => (
                <div key={`p-${row.key}`} style={{ fontSize: '13px', color: 'rgba(255,255,255,0.8)', marginBottom: '0.22rem' }}>
                  {row.key}: <span style={{ color: 'rgba(255,255,255,0.6)' }}>{row.count}</span>
                </div>
              ))}
            </div>
            <div>
              <p style={sectionTitle}>Verteilung Skill-Level</p>
              {(distributions.tools_by_skill || []).slice(0, 8).map((row) => (
                <div key={`s-${row.key}`} style={{ fontSize: '13px', color: 'rgba(255,255,255,0.8)', marginBottom: '0.22rem' }}>
                  {row.key}: <span style={{ color: 'rgba(255,255,255,0.6)' }}>{row.count}</span>
                </div>
              ))}
            </div>
            <div>
              <p style={sectionTitle}>Categories pro Domain</p>
              {(distributions.categories_by_domain || []).slice(0, 8).map((row) => (
                <div key={`c-${row.key}`} style={{ fontSize: '13px', color: 'rgba(255,255,255,0.8)', marginBottom: '0.22rem' }}>
                  {row.key}: <span style={{ color: 'rgba(255,255,255,0.6)' }}>{row.count}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ ...cardStyle, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '0.7rem' }}>
            <div>
              <p style={sectionTitle}>API Endpoint Monitor</p>
              <div style={{ display: 'grid', gap: '0.24rem' }}>
                {ENDPOINTS.map((ep) => {
                  const info = responses[ep.key]
                  const ok = !!info?.ok
                  return (
                    <div key={ep.key} style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', fontSize: '12px' }}>
                      <span style={{ color: 'rgba(255,255,255,0.78)' }}>{ep.label}</span>
                      <span style={{ color: ok ? 'rgba(79,255,176,0.95)' : 'rgba(255,120,120,0.95)' }}>
                        {ok ? `OK (${info.status})` : `FAIL (${info?.status || 'ERR'})`}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
            <div>
              <p style={sectionTitle}>User & Context Daten</p>
              <p style={{ margin: 0, fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>
                Profile Skills/Ziele/Tools: {formatNumber(tables.skills ?? profile.pagination?.skills_total ?? 0)} / {formatNumber(tables.goals ?? (profile.goals || []).length)} / {formatNumber(tables.tools ?? profile.pagination?.tools_total ?? toolItems.length)}
              </p>
              <p style={{ margin: '0.25rem 0 0.35rem', fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>
                User-Context Gesamt: {formatNumber(tables.user_context ?? contextItems.length)}
              </p>
              {Object.keys(contextByArea).length === 0 && (
                <p style={{ margin: 0, fontSize: '12px', color: 'rgba(255,255,255,0.58)' }}>Keine Context-Eintraege vorhanden.</p>
              )}
              {Object.entries(contextByArea).map(([area, count]) => (
                <div key={area} style={{ fontSize: '12px', color: 'rgba(255,255,255,0.72)', marginBottom: '0.18rem' }}>
                  [{area}] {count}
                </div>
              ))}
            </div>
            <div>
              <p style={sectionTitle}>Recent Data Activity</p>
              <p style={{ margin: 0, fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>
                Letzte History-Eintraege geladen: {workflowHistory.length}
              </p>
              <p style={{ margin: '0.2rem 0 0', fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>
                Feedback-Eintraege geladen: {feedbackItems.length}
              </p>
              <p style={{ margin: '0.2rem 0 0.35rem', fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>
                Research Sessions geladen: {researchSessions.length}
              </p>
              {!!workflowHistory[0]?.task_description && (
                <p style={{ margin: 0, fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>
                  Neueste Aufgabe: {workflowHistory[0].task_description}
                </p>
              )}
            </div>
          </div>

          <div style={cardStyle}>
            <p style={sectionTitle}>Domains Preview</p>
            {!domains.length && <p style={{ margin: 0, color: 'rgba(255,255,255,0.58)', fontSize: '13px' }}>Keine Domains vorhanden.</p>}
            {!!domains.length && (
              <div style={{ display: 'grid', gap: '0.28rem' }}>
                {domains.slice(0, 10).map((domain) => (
                  <div key={domain.id} style={{ fontSize: '13px', color: 'rgba(255,255,255,0.82)' }}>
                    {domain.name} <span style={{ color: 'rgba(255,255,255,0.52)' }}>({domain.category_count ?? (domain.categories || []).length} Kategorien)</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', textAlign: 'right' }}>
            Stats generated: {systemStats.generated_at || 'n/a'}
          </div>
        </div>
      )}
    </div>
  )
}
