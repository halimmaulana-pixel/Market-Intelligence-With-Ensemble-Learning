/**
 * pages/AlokasiPage.jsx — Optimasi alokasi modal dengan slider.
 */
import { useState } from 'react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import api from '../services/api'
import toast from 'react-hot-toast'

const COLORS = ['#1a237e','#283593','#3949ab','#5c6bc0','#7986cb',
                 '#9fa8da','#c5cae9','#e8eaf6']

function today() { return new Date().toISOString().split('T')[0] }

export default function AlokasiPage() {
  const [modal, setModal] = useState(300000)
  const [tanggal, setTanggal] = useState(today())
  const [hasil, setHasil] = useState(null)
  const [loading, setLoading] = useState(false)

  const runAlokasi = async (m) => {
    setLoading(true)
    try {
      const res = await api.get(`/alokasi-modal/simulasi?modal=${m}&tanggal=${tanggal}`)
      setHasil(res.data)
    } catch (err) {
      const detail = err.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : 'Alokasi gagal.')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (modal < 50000) {
      toast.error('Modal minimal Rp 50.000')
      return
    }
    runAlokasi(modal)
  }

  const pieData = hasil?.alokasi?.map(a => ({
    name: a.nama_produk,
    value: Math.round(a.alokasi_rp),
  })) || []

  const totalProfit = hasil?.alokasi?.reduce((s, a) => s + a.estimasi_profit_rp, 0) || 0

  return (
    <div>
      {/* Form input */}
      <div style={cardStyle}>
        <h3 style={cardTitle}>Simulasi Alokasi Modal</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <label style={labelStyle}>Modal Harian (Rp)</label>
            <input
              type="number"
              value={modal}
              min={50000}
              step={10000}
              onChange={e => setModal(Number(e.target.value))}
              style={{ ...inputStyle, width: '100%' }}
            />
            <input
              type="range"
              min={50000}
              max={2000000}
              step={10000}
              value={modal}
              onChange={e => setModal(Number(e.target.value))}
              style={{ width: '100%', marginTop: 8 }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#999' }}>
              <span>Rp 50k</span>
              <span style={{ fontWeight: 600, color: '#1a237e' }}>Rp {modal.toLocaleString('id-ID')}</span>
              <span>Rp 2jt</span>
            </div>
          </div>
          <div>
            <label style={labelStyle}>Tanggal</label>
            <input type="date" value={tanggal} onChange={e => setTanggal(e.target.value)} style={inputStyle} />
          </div>
          <button type="submit" disabled={loading} style={btnPrimary}>
            {loading ? 'Menghitung...' : '💰 Hitung Alokasi'}
          </button>
        </form>
      </div>

      {/* Hasil */}
      {hasil && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginTop: 20 }}>
          {/* Pie chart */}
          <div style={cardStyle}>
            <h3 style={cardTitle}>Distribusi Alokasi</h3>
            <div style={{ fontSize: 13, color: '#666', marginBottom: 12 }}>
              Status LP: <strong style={{ color: hasil.status_lp === 'optimal' ? '#2e7d32' : '#e65100' }}>
                {hasil.status_lp}
              </strong>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100}
                     label={({ name, percent }) => `${(percent*100).toFixed(0)}%`}>
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={v => `Rp ${(v ?? 0).toLocaleString('id-ID')}`} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Tabel */}
          <div style={cardStyle}>
            <h3 style={cardTitle}>Rincian Alokasi per Produk</h3>
            <div style={{ marginBottom: 12, padding: '10px 14px', background: '#e8f5e9', borderRadius: 8 }}>
              <div style={{ fontSize: 13, color: '#555' }}>Total Modal</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#1a237e' }}>
                Rp {modal.toLocaleString('id-ID')}
              </div>
              <div style={{ fontSize: 13, color: '#2e7d32', marginTop: 4 }}>
                Est. Profit: Rp {Math.round(totalProfit).toLocaleString('id-ID')}
              </div>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f5f5f5' }}>
                  <th style={th}>Produk</th>
                  <th style={th}>Alokasi (Rp)</th>
                  <th style={th}>%</th>
                  <th style={th}>Profit (Rp)</th>
                </tr>
              </thead>
              <tbody>
                {hasil.alokasi.map(a => (
                  <tr key={a.produk_id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={td}>{a.nama_produk}</td>
                    <td style={{ ...td, fontWeight: 600 }}>{Math.round(a.alokasi_rp).toLocaleString('id-ID')}</td>
                    <td style={td}>{a.persentase.toFixed(1)}%</td>
                    <td style={{ ...td, color: '#2e7d32' }}>{Math.round(a.estimasi_profit_rp).toLocaleString('id-ID')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

const cardStyle = {
  background: '#fff', borderRadius: 10, padding: 20,
  boxShadow: '0 2px 8px rgba(0,0,0,0.07)',
}
const cardTitle = { margin: '0 0 16px', color: '#1a237e', fontSize: 16 }
const labelStyle = { display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6, color: '#555' }
const inputStyle = { padding: '9px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14 }
const btnPrimary = {
  padding: '9px 20px', background: '#1a237e', color: '#fff',
  border: 'none', borderRadius: 8, fontSize: 14, cursor: 'pointer', fontWeight: 600,
}
const th = { padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: '#555' }
const td = { padding: '8px 10px', color: '#333' }
