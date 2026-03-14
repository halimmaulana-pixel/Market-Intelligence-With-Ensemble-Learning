/**
 * components/Layout.jsx — Shell aplikasi: sidebar + header + konten.
 */
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'

const NAV_SEMUA = [
  { path: '/dashboard', label: 'Dashboard', icon: '📊' },
  { path: '/prediksi', label: 'Prediksi', icon: '🔮' },
  { path: '/alokasi', label: 'Alokasi Modal', icon: '💰' },
  { path: '/histori', label: 'Histori Penjualan', icon: '📈' },
]

const NAV_ADMIN = [
  { path: '/produk', label: 'Manajemen Produk', icon: '🛒' },
]

const NAV_PENELITI = [
  { path: '/model-config', label: 'Konfigurasi Model', icon: '⚙️' },
  { path: '/pengguna', label: 'Manajemen Pengguna', icon: '👥' },
]

const ROLE_LABEL = { pedagang: 'Pedagang', admin: 'Admin', peneliti: 'Peneliti' }
const ROLE_COLOR = { pedagang: '#4caf50', admin: '#ff9800', peneliti: '#2196f3' }

export default function Layout({ children }) {
  const { user, logout, isRole } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    toast.success('Berhasil logout')
    navigate('/login')
  }

  const navItems = [
    ...NAV_SEMUA,
    ...(isRole('admin', 'peneliti') ? NAV_ADMIN : []),
    ...(isRole('peneliti') ? NAV_PENELITI : []),
  ]

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>
      {/* Sidebar */}
      <aside style={{
        width: 240, background: '#1a237e', color: '#fff',
        display: 'flex', flexDirection: 'column', flexShrink: 0,
      }}>
        {/* Logo */}
        <div style={{ padding: '20px 16px 12px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>🏪 SalSa Market</div>
          <div style={{ fontSize: 11, opacity: 0.7, marginTop: 4 }}>
            Market Intelligence System
          </div>
        </div>

        {/* User badge */}
        <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>{user?.nama_lengkap || user?.username}</div>
          <span style={{
            fontSize: 11, padding: '2px 8px', borderRadius: 12,
            background: ROLE_COLOR[user?.role] || '#666', marginTop: 4, display: 'inline-block',
          }}>
            {ROLE_LABEL[user?.role] || user?.role}
          </span>
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: '8px 0' }}>
          {navItems.map((item) => {
            const active = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 16px', textDecoration: 'none',
                  color: active ? '#fff' : 'rgba(255,255,255,0.7)',
                  background: active ? 'rgba(255,255,255,0.15)' : 'transparent',
                  borderLeft: active ? '3px solid #90caf9' : '3px solid transparent',
                  fontSize: 14, transition: 'all 0.15s',
                }}
              >
                <span>{item.icon}</span>
                {item.label}
              </Link>
            )
          })}
        </nav>

        {/* Logout */}
        <div style={{ padding: 16, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          <button
            onClick={handleLogout}
            style={{
              width: '100%', padding: '8px', background: 'rgba(255,255,255,0.1)',
              color: '#fff', border: '1px solid rgba(255,255,255,0.2)',
              borderRadius: 6, cursor: 'pointer', fontSize: 13,
            }}
          >
            🚪 Logout
          </button>
        </div>
      </aside>

      {/* Main */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#f5f7fa' }}>
        {/* Header */}
        <header style={{
          background: '#fff', padding: '0 24px', height: 56,
          display: 'flex', alignItems: 'center',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        }}>
          <span style={{ fontSize: 14, color: '#666' }}>
            {navItems.find(n => n.path === location.pathname)?.label || 'SalSa Market'}
          </span>
        </header>

        {/* Content */}
        <div style={{ flex: 1, padding: 24, overflowY: 'auto' }}>
          {children}
        </div>
      </main>
    </div>
  )
}
