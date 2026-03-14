import { useNavigate } from 'react-router-dom'

export default function UnauthorizedPage() {
  const navigate = useNavigate()
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f7fa' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 64 }}>🚫</div>
        <h1 style={{ color: '#c62828', marginTop: 16 }}>Akses Ditolak</h1>
        <p style={{ color: '#666' }}>Anda tidak memiliki izin untuk mengakses halaman ini.</p>
        <button onClick={() => navigate('/dashboard')} style={{
          marginTop: 16, padding: '10px 24px', background: '#1a237e', color: '#fff',
          border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 15,
        }}>
          Kembali ke Dashboard
        </button>
      </div>
    </div>
  )
}
