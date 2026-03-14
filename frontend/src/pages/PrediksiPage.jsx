/**
 * pages/PrediksiPage.jsx — Form prediksi permintaan harian + grafik hasil.
 */
import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import api from '../services/api'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import PanelTransparansiML from '../components/PanelTransparansiML'

const CUACA_OPT = [
  { value: 'cerah', label: '☀️ Cerah' },
  { value: 'mendung', label: '☁️ Mendung' },
  { value: 'hujan', label: '🌧️ Hujan' },
]

function today() {
  return new Date().toISOString().split('T')[0]
}

export default function PrediksiPage() {
  const { isRole } = useAuth()
  const [tanggal, setTanggal] = useState(today())
  const [cuaca, setCuaca] = useState('cerah')
  const [hariBesar, setHariBesar] = useState('')
  const [hasil, setHasil] = useState(null)
  const [loading, setLoading] = useState(false)
  const [prosesDetail, setProsesDetail] = useState([])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setHasil(null)
    setProsesDetail([])
    try {
      const body = { tanggal, cuaca }
      if (hariBesar) body.hari_besar = hariBesar

      if (isRole('peneliti')) {
        const res = await api.post('/prediksi/verbose', body)
        setHasil(res.data)
        setProsesDetail(res.data.proses_detail || [])
        toast.success(`Prediksi verbose berhasil untuk ${res.data.prediksi.length} produk`)
      } else {
        const res = await api.post('/prediksi', body)
        setHasil(res.data)
        toast.success(`Prediksi berhasil untuk ${res.data.prediksi.length} produk`)
      }
    } catch (err) {
      const msg = err.response?.data?.detail
      toast.error(typeof msg === 'string' ? msg : 'Prediksi gagal.')
    } finally {
      setLoading(false)
    }
  }

  const chartData = hasil?.prediksi?.map(p => ({
    name: p.nama_produk.replace(' ', '\n'),
    SVR: Math.round(p.prediksi_svr_rp),
    SARIMA: Math.round(p.prediksi_sarima_rp),
    Ensemble: Math.round(p.prediksi_ensemble_rp),
  })) || []

  return (
    <div>
      {/* Form */}
      <div style={cardStyle}>
        <h3 style={cardTitle}>Parameter Prediksi</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <label style={labelStyle}>Tanggal</label>
            <input type="date" value={tanggal} onChange={e => setTanggal(e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Cuaca</label>
            <select value={cuaca} onChange={e => setCuaca(e.target.value)} style={inputStyle}>
              {CUACA_OPT.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Hari Besar (opsional)</label>
            <input
              type="text"
              value={hariBesar}
              onChange={e => setHariBesar(e.target.value)}
              placeholder="cth: Lebaran"
              style={inputStyle}
            />
          </div>
          <button type="submit" disabled={loading} style={btnPrimary}>
            {loading ? 'Memproses...' : '🔮 Jalankan Prediksi'}
          </button>
        </form>
      </div>

      {/* Grafik */}
      {hasil && (
        <>
          <div style={{ ...cardStyle, marginTop: 20 }}>
            <h3 style={cardTitle}>Prediksi Penjualan Harian (Rp)</h3>
            <p style={{ color: '#666', fontSize: 13, margin: '0 0 16px' }}>
              Tanggal: {hasil.tanggal} | Cuaca: {cuaca} | {hasil.prediksi.length} produk
            </p>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={chartData} margin={{ top: 5, right: 20, left: 20, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} interval={0} angle={-30} textAnchor="end" />
                <YAxis tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                <Tooltip formatter={v => `Rp ${(v ?? 0).toLocaleString('id-ID')}`} />
                <Legend />
                <Bar dataKey="SVR" fill="#5c6bc0" />
                <Bar dataKey="SARIMA" fill="#26a69a" />
                <Bar dataKey="Ensemble" fill="#ef5350" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Tabel detail */}
          <div style={{ ...cardStyle, marginTop: 20 }}>
            <h3 style={cardTitle}>Detail Prediksi</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ background: '#f5f5f5' }}>
                  <th style={th}>Produk</th>
                  <th style={th}>SVR (Rp)</th>
                  <th style={th}>SARIMA (Rp)</th>
                  <th style={th}>Ensemble (Rp)</th>
                  <th style={th}>Bobot SVR</th>
                  <th style={th}>Modal Beli (Rp)</th>
                  <th style={th}>Est. Profit (Rp)</th>
                </tr>
              </thead>
              <tbody>
                {hasil.prediksi.map(p => (
                  <tr key={p.produk_id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={td}>{p.nama_produk}</td>
                    <td style={td}>{Math.round(p.prediksi_svr_rp ?? 0).toLocaleString('id-ID')}</td>
                    <td style={td}>{Math.round(p.prediksi_sarima_rp ?? 0).toLocaleString('id-ID')}</td>
                    <td style={{ ...td, fontWeight: 600, color: '#1a237e' }}>
                      {Math.round(p.prediksi_ensemble_rp ?? 0).toLocaleString('id-ID')}
                    </td>
                    <td style={td}>{((p.bobot_svr ?? 0) * 100).toFixed(1)}%</td>
                    <td style={td}>{Math.round(p.modal_beli_rp ?? 0).toLocaleString('id-ID')}</td>
                    <td style={{ ...td, color: '#2e7d32' }}>
                      {Math.round(p.estimasi_profit_rp ?? 0).toLocaleString('id-ID')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Panel Transparansi ML — hanya untuk Peneliti */}
          <PanelTransparansiML prosesDetail={prosesDetail} />
        </>
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
const th = { padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#555' }
const td = { padding: '10px 12px', color: '#333' }
