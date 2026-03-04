import { useEffect, useState } from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import SchoolPage from './pages/SchoolPage.jsx'
import ResearchPage from './pages/ResearchPage.jsx'

export default function App() {
  const location = useLocation()
  const [hoveredPath, setHoveredPath] = useState('')
  const [healthStatus, setHealthStatus] = useState({ loading: true, groqConfigured: false })

  const navItems = [
    { to: '/', label: 'Dashboard', isActive: (path) => path === '/' || path === '/dashboard' },
    { to: '/school', label: 'Schulprojekte', isActive: (path) => path === '/school' },
    { to: '/research', label: 'Recherche', isActive: (path) => path === '/research' },
    { to: '/profile', label: 'Mein Profil', isActive: (path) => path === '/profile' },
  ]

  useEffect(() => {
    let alive = true
    const loadHealth = async () => {
      try {
        const res = await fetch('/api/health')
        const data = res.ok ? await res.json() : { groq_configured: false }
        if (!alive) return
        setHealthStatus({ loading: false, groqConfigured: !!data?.groq_configured })
      } catch {
        if (!alive) return
        setHealthStatus({ loading: false, groqConfigured: false })
      }
    }
    loadHealth()
    return () => { alive = false }
  }, [])

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{
        width: '200px',
        background: '#0A1628',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        flexDirection: 'column',
        padding: '1.2rem 0',
        position: 'fixed',
        top: 0,
        left: 0,
        height: '100vh',
        zIndex: 100,
      }}>
        <div style={{ marginBottom: '1.6rem', padding: '0 1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
            <span style={{ fontSize: '1rem' }}>⚡</span>
            <span style={{ fontWeight: 700, fontSize: '1rem', color: '#FFFFFF' }}>FlowAI</span>
          </div>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.1rem' }}>
          {navItems.map(item => {
            const active = item.isActive(location.pathname)
            const hovered = hoveredPath === item.to
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onMouseEnter={() => setHoveredPath(item.to)}
                onMouseLeave={() => setHoveredPath('')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.55rem',
                  padding: '0.62rem 1rem',
                  textDecoration: 'none',
                  fontSize: '0.85rem',
                  borderLeft: active ? '2px solid #4FFFB0' : '2px solid transparent',
                  color: active ? '#FFFFFF' : (hovered ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.45)'),
                  transition: 'color 0.15s ease',
                }}
              >
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: active ? '#4FFFB0' : 'rgba(255,255,255,0.25)',
                    flexShrink: 0,
                  }}
                />
                {item.label}
              </NavLink>
            )
          })}
        </nav>

        <div style={{ marginTop: 'auto', padding: '0 1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: healthStatus.groqConfigured ? '#4ADE80' : '#FACC15',
                display: 'inline-block',
              }}
            />
            <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.88)' }}>KI aktiv</span>
          </div>
        </div>
      </aside>

      <main style={{ marginLeft: '200px', flex: 1, minHeight: '100vh' }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/school" element={<SchoolPage />} />
          <Route path="/research" element={<ResearchPage />} />
        </Routes>
      </main>
    </div>
  )
}
