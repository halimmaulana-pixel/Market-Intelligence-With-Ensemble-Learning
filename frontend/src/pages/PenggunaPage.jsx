/**
 * pages/PenggunaPage.jsx — Manajemen akun pengguna (peneliti).
 */
import { useState, useEffect } from 'react'
import api from '../services/api'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'

const ROLES = ['pedagang', 'admin', 'peneliti']
const ROLE_COLOR = { pedagang: '#2e7d32', admin: '#e65100', peneliti: '#1a237e' }

export default function PenggunaPage() {
  const { user: currentUser } = useAuth()
  const [penggunaList, setPenggunaList] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ username: '', password: '', role: 'pedagang', nama_lengkap: '' })
  const [loading, setLoading] = useState(false)

  const fetchPengguna = () =>
    api.get('/pengguna').then(r => setPenggunaList(r.data))

  useEffect(() => { fetchPengguna() }, [])

  const handleBuat = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/pengguna', form)
      toast.success(`Akun '${form.username}' berhasil dibuat`)
      setShowForm(false)
      setForm({ username: '', password: '', role: 'pedagang', nama_lengkap: '' })
      fetchPengguna()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal membuat akun')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleAktif = async (p) => {
    if (p.username === currentUser?.username) {
      toast.error('Tidak bisa menonaktifkan akun sendiri')
      return
    }
    const aksi = p.is_aktif ? 'nonaktifkan' : 'aktifkan'
    if (!window.confirm(`${aksi.charAt(0).toUpperCase() + aksi.slice(1)} akun '${p.username}'?`)) return
    try {
      if (p.is_aktif) {
        await api.delete(`/pengguna/${p.id}`)
      } else {
        await api.put(`/pengguna/${p.id}`, { is_aktif: true })
      }
      toast.success(`Akun '${p.username}' berhasil di${aksi}kan`)
      fetchPengguna()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal update akun')
    }
  }

  const handleUbahRole = async (p, role) => {
    try {
      await api.put(`/pengguna/${p.id}`, { role })
      toast.success(`Role '${p.username}' diubah ke ${role}`)
      fetchPengguna()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal mengubah role')
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, alignItems: 'center' }}>
        <h2 style={{ margin: 0, color: '#1a237e' }}>Manajemen Pengguna ({penggunaList.length})</h2>
        <button onClick={() => setShowForm(!showForm)} style={btnPrimary}>
          {showForm ? '✕ Tutup' : '+ Buat Akun Baru'}
        </button>
      </div>

      {/* Form buat akun */}
      {showForm && (
        <div style={{ ...cardStyle, marginBottom: 20 }}>
          <h3 style={cardTitle}>Buat Akun Baru</h3>
          <form onSubmit={handleBuat} style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div>
              <label style={labelStyle}>Username *</label>
              <input value={form.username} required minLength={3} style={inputStyle}
                onChange={e => setForm({ ...form, username: e.target.value })} />
            </div>
            <div>
              <label style={labelStyle}>Password *</label>
              <input type="password" value={form.password} required minLength={6} style={inputStyle}
                onChange={e => setForm({ ...form, password: e.target.value })} />
            </div>
            <div>
              <label style={labelStyle}>Nama Lengkap</label>
              <input value={form.nama_lengkap} style={inputStyle}
                onChange={e => setForm({ ...form, nama_lengkap: e.target.value })} />
            </div>
            <div>
              <label style={labelStyle}>Role</label>
              <select value={form.role} style={inputStyle}
                onChange={e => setForm({ ...form, role: e.target.value })}>
                {ROLES.map(r => <option key={r}>{r}</option>)}
              </select>
            </div>
            <button type="submit" disabled={loading} style={btnPrimary}>
              {loading ? 'Menyimpan...' : 'Simpan'}
            </button>
          </form>
        </div>
      )}

      {/* Tabel */}
      <div style={cardStyle}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ background: '#f5f5f5' }}>
              <th style={th}>ID</th>
              <th style={th}>Username</th>
              <th style={th}>Nama Lengkap</th>
              <th style={th}>Role</th>
              <th style={th}>Status</th>
              <th style={th}>Login Terakhir</th>
              <th style={th}>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {penggunaList.map(p => (
              <tr key={p.id} style={{ borderBottom: '1px solid #eee', opacity: p.is_aktif ? 1 : 0.55 }}>
                <td style={td}>{p.id}</td>
                <td style={{ ...td, fontWeight: 600 }}>{p.username}</td>
                <td style={td}>{p.nama_lengkap || '-'}</td>
                <td style={td}>
                  <select
                    value={p.role}
                    onChange={e => handleUbahRole(p, e.target.value)}
                    disabled={p.username === currentUser?.username}
                    style={{
                      padding: '3px 8px', borderRadius: 6, border: '1px solid #ddd',
                      background: '#fff', fontSize: 13,
                      color: ROLE_COLOR[p.role] || '#333',
                    }}
                  >
                    {ROLES.map(r => <option key={r}>{r}</option>)}
                  </select>
                </td>
                <td style={td}>
                  <span style={{
                    fontSize: 12, padding: '3px 8px', borderRadius: 12,
                    background: p.is_aktif ? '#e8f5e9' : '#ffebee',
                    color: p.is_aktif ? '#2e7d32' : '#c62828',
                  }}>
                    {p.is_aktif ? 'Aktif' : 'Nonaktif'}
                  </span>
                </td>
                <td style={{ ...td, fontSize: 12, color: '#666' }}>
                  {p.last_login ? new Date(p.last_login).toLocaleString('id-ID') : 'Belum pernah'}
                </td>
                <td style={td}>
                  {p.username !== currentUser?.username && (
                    <button
                      onClick={() => handleToggleAktif(p)}
                      style={btnXs(p.is_aktif ? '#c62828' : '#2e7d32')}
                    >
                      {p.is_aktif ? 'Nonaktifkan' : 'Aktifkan'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const cardStyle = { background: '#fff', borderRadius: 10, padding: 20, boxShadow: '0 2px 8px rgba(0,0,0,0.07)' }
const cardTitle = { margin: '0 0 16px', color: '#1a237e', fontSize: 16 }
const labelStyle = { display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6, color: '#555' }
const inputStyle = { padding: '9px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14 }
const btnPrimary = { padding: '9px 20px', background: '#1a237e', color: '#fff', border: 'none', borderRadius: 8, fontSize: 14, cursor: 'pointer', fontWeight: 600 }
const btnXs = (bg) => ({ padding: '4px 10px', background: bg, color: '#fff', border: 'none', borderRadius: 6, fontSize: 12, cursor: 'pointer' })
const th = { padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#555' }
const td = { padding: '10px 12px', color: '#333' }
