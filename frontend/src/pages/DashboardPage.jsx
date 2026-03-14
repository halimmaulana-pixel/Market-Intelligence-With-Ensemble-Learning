/**
 * pages/DashboardPage.jsx — Ringkasan sistem: status model dan statistik produk.
 */
import { useEffect, useState } from 'react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function DashboardPage() {
  const { user } = useAuth()
  const [statusModel, setStatusModel] = useState(null)
  const [produkList, setProdukList] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get('/prediksi/status'),
      api.get('/produk'),
    ]).then(([s, p]) => {
      setStatusModel(s.data)
      setProdukList(p.data)
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingCard />

  return (
    <div>
      <h2 style={{ margin: '0 0 20px', color: '#1a237e' }}>
        Selamat datang, {user?.nama_lengkap || user?.username}
      </h2>

      {/* Kartu ringkasan */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
        <StatCard
          icon="🛒"
          label="Total Produk Aktif"
          value={produkList.length}
          color="#1a237e"
        />
        <StatCard
          icon="✅"
          label="Model Siap"
          value={statusModel?.siap ?? 0}
          total={statusModel?.total_produk}
          color="#2e7d32"
        />
        <StatCard
          icon="⏳"
          label="Belum Dilatih"
          value={statusModel?.belum_dilatih ?? 0}
          color={statusModel?.belum_dilatih > 0 ? '#c62828' : '#2e7d32'}
        />
        <StatCard
          icon="🤖"
          label="Status Sistem"
          value={statusModel?.semua_siap ? 'Siap' : 'Perlu Training'}
          color={statusModel?.semua_siap ? '#2e7d32' : '#e65100'}
          isText
        />
      </div>

      {/* Tabel produk dan model */}
      <Card title="Status Model per Produk">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ background: '#f5f5f5' }}>
              <th style={th}>Produk</th>
              <th style={th}>Harga Beli</th>
              <th style={th}>Harga Jual</th>
              <th style={th}>Margin</th>
              <th style={th}>Model</th>
              <th style={th}>MAPE SVR</th>
              <th style={th}>MAPE SARIMA</th>
            </tr>
          </thead>
          <tbody>
            {statusModel?.produk_siap?.map((p) => {
              const produk = produkList.find(pr => pr.id === p.produk_id)
              const margin = produk
                ? (((produk.harga_jual_per_unit - produk.harga_beli_per_unit) / produk.harga_jual_per_unit) * 100).toFixed(1)
                : '-'
              return (
                <tr key={p.produk_id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={td}>{p.nama_produk}</td>
                  <td style={td}>Rp {produk?.harga_beli_per_unit?.toLocaleString('id-ID') ?? '-'}</td>
                  <td style={td}>Rp {produk?.harga_jual_per_unit?.toLocaleString('id-ID') ?? '-'}</td>
                  <td style={td}>{margin}%</td>
                  <td style={td}><Badge ok>Siap</Badge></td>
                  <td style={td}>{p.mape_svr ? `${p.mape_svr.toFixed(2)}%` : '-'}</td>
                  <td style={td}>{p.mape_sarima ? `${p.mape_sarima.toFixed(2)}%` : '-'}</td>
                </tr>
              )
            })}
            {statusModel?.produk_belum_siap?.map((p) => (
              <tr key={p.produk_id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={td}>{p.nama_produk}</td>
                <td style={td} colSpan={3}>-</td>
                <td style={td}><Badge>Belum Dilatih</Badge></td>
                <td style={td}>-</td>
                <td style={td}>-</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}

function StatCard({ icon, label, value, total, color, isText }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 10, padding: 20,
      boxShadow: '0 2px 8px rgba(0,0,0,0.07)', borderLeft: `4px solid ${color}`,
    }}>
      <div style={{ fontSize: 28 }}>{icon}</div>
      <div style={{ fontSize: 13, color: '#666', marginTop: 8 }}>{label}</div>
      <div style={{ fontSize: isText ? 18 : 28, fontWeight: 700, color, marginTop: 4 }}>
        {isText ? value : value}
        {total !== undefined && <span style={{ fontSize: 14, color: '#999' }}>/{total}</span>}
      </div>
    </div>
  )
}

function Card({ title, children }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 10, padding: 20,
      boxShadow: '0 2px 8px rgba(0,0,0,0.07)',
    }}>
      <h3 style={{ margin: '0 0 16px', color: '#333', fontSize: 16 }}>{title}</h3>
      {children}
    </div>
  )
}

function Badge({ ok, children }) {
  return (
    <span style={{
      padding: '2px 8px', borderRadius: 12, fontSize: 12,
      background: ok ? '#e8f5e9' : '#fff3e0',
      color: ok ? '#2e7d32' : '#e65100',
    }}>{children}</span>
  )
}

function LoadingCard() {
  return <div style={{ padding: 40, textAlign: 'center', color: '#666' }}>Memuat data...</div>
}

const th = { padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#555' }
const td = { padding: '10px 12px', color: '#333' }
