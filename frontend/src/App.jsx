import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import ProfilePage from './pages/ProfilePage.jsx'

// Navigation-Icon Komponenten
const IconDashboard = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
    <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
  </svg>
)

const IconProfile = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
  </svg>
)

export default function App() {
  const location = useLocation()

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar Navigation */}
      <aside style={{
        width: '220px',
        background: 'var(--bg-card)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        padding: '1.5rem 1rem',
        gap: '0.5rem',
        position: 'fixed',
        top: 0,
        left: 0,
        height: '100vh',
        zIndex: 100,
      }}>
        {/* Logo */}
        <div style={{ marginBottom: '2rem', paddingLeft: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.3rem' }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '8px',
              background: 'linear-gradient(135deg, var(--accent), var(--accent2))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '16px',
            }}>⚡</div>
            <span style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text)' }}>FlowAI</span>
          </div>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', margin: 0, paddingLeft: '2.5rem' }}>Workflow Optimizer</p>
        </div>

        {/* Nav Links */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {[
            { to: '/', label: 'Dashboard', icon: <IconDashboard /> },
            { to: '/profile', label: 'Mein Profil', icon: <IconProfile /> },
          ].map(({ to, label, icon }) => {
            const isActive = location.pathname === to
            return (
              <NavLink
                key={to}
                to={to}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.7rem',
                  padding: '0.6rem 0.75rem',
                  borderRadius: '8px',
                  textDecoration: 'none',
                  fontSize: '0.875rem',
                  fontWeight: isActive ? 600 : 400,
                  color: isActive ? 'var(--accent)' : 'var(--text-muted)',
                  background: isActive ? 'rgba(79,255,176,0.08)' : 'transparent',
                  border: isActive ? '1px solid rgba(79,255,176,0.15)' : '1px solid transparent',
                  transition: 'all 0.15s',
                }}
              >
                {icon}
                {label}
              </NavLink>
            )
          })}
        </nav>

        {/* Footer Info */}
        <div style={{ marginTop: 'auto', padding: '0.75rem', background: 'var(--bg)', borderRadius: '8px', border: '1px solid var(--border)' }}>
          <p style={{ margin: 0, fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
            💡 Tipp: Setze deinen<br />
            <strong style={{ color: 'var(--accent)' }}>Groq API-Key</strong> in<br />
            <code style={{ fontSize: '0.65rem' }}>backend/.env</code>
          </p>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ marginLeft: '220px', flex: 1, minHeight: '100vh' }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
      </main>
    </div>
  )
}
