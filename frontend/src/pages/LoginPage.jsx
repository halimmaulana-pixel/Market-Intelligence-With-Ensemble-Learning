/**
 * pages/LoginPage.jsx — Halaman login.
 */
import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const from = location.state?.from?.pathname || '/dashboard'

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username || !password) {
      toast.error('Username dan password wajib diisi.')
      return
    }
    setLoading(true)
    try {
      await login(username, password)
      toast.success('Login berhasil!')
      navigate(from, { replace: true })
    } catch (err) {
      const msg = err.response?.data?.detail || 'Username atau password salah.'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #1a237e 0%, #283593 60%, #3949ab 100%)',
    }}>
      <div style={{
        background: '#fff', borderRadius: 12, padding: 40, width: 380,
        boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontSize: 48 }}>🏪</div>
          <h1 style={{ margin: '8px 0 4px', fontSize: 22, color: '#1a237e' }}>SalSa Market</h1>
          <p style={{ color: '#666', fontSize: 13, margin: 0 }}>Market Intelligence System</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6, color: '#333' }}>
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              autoFocus
              style={inputStyle}
              placeholder="Masukkan username"
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6, color: '#333' }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              style={inputStyle}
              placeholder="Masukkan password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '12px', background: loading ? '#9fa8da' : '#1a237e',
              color: '#fff', border: 'none', borderRadius: 8,
              fontSize: 15, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Memproses...' : 'Masuk'}
          </button>
        </form>

        <p style={{ textAlign: 'center', fontSize: 12, color: '#999', marginTop: 24 }}>
          Sistem prediksi permintaan &amp; optimisasi alokasi modal
        </p>
      </div>
    </div>
  )
}

const inputStyle = {
  width: '100%', padding: '10px 12px', border: '1px solid #ddd',
  borderRadius: 8, fontSize: 14, boxSizing: 'border-box',
  outline: 'none',
}
