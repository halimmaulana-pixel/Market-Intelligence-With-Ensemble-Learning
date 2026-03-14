/**
 * pages/HistoriPage.jsx — Grafik histori penjualan + statistik + tambah entri.
 */
import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import api from '../services/api'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'

export default function HistoriPage() {
  const { isRole } = useAuth()
  const [produkList, setProdukList] = useState([])
  const [selectedProduk, setSelectedProduk] = useState(null)
  const [limit, setLimit] = useState(90)
  const [histori, setHistori] = useState([])
  const [statistik, setStatistik] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(false)

  // Form tambah histori
  const [form, setForm] = useState({
    tanggal: new Date().toISOString().split('T')[0],
    penjualan_rp: '',
    penjualan_unit: '',
    cuaca: 'cerah',
    hari_besar: '',
  })

  useEffect(() => {
    api.get('/produk').then(r => {
      setProdukList(r.data)
      if (r.data.length > 0) setSelectedProduk(r.data[0].id)
    })
  }, [])

  useEffect(() => {
    if (!selectedProduk) return
    setLoading(true)
    Promise.all([
      api.get(`/histori/${selectedProduk}?limit=${limit}`),
      api.get(`/histori/${selectedProduk}/statistik`),
    ]).then(([h, s]) => {
      setHistori(h.data)
      setStatistik(s.data)
    }).catch(err => {
      const msg = err.response?.data?.detail
      if (err.response?.status !== 404) toast.error(msg || 'Gagal memuat histori')
      setHistori([])
      setStatistik(null)
    }).finally(() => setLoading(false))
  }, [selectedProduk, limit])

  const handleTambah = async (e) => {
    e.preventDefault()
    try {
      await api.post(`/histori/${selectedProduk}`, {
        ...form,
        penjualan_rp: Number(form.penjualan_rp),
        penjualan_unit: form.penjualan_unit ? Number(form.penjualan_unit) : null,
        hari_besar: form.hari_besar || null,
      })
      toast.success('Data berhasil ditambahkan!')
      setShowForm(false)
      // Refresh
      const [h, s] = await Promise.all([
        api.get(`/histori/${selectedProduk}?limit=${limit}`),
        api.get(`/histori/${selectedProduk}/statistik`),
      ])
      setHistori(h.data)
      setStatistik(s.data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal menambah data')
    }
  }

  const chartData = histori.map(h => ({
    tgl: h.tanggal,
    penjualan: h.penjualan_rp,
  }))

  return (
    <div>
      {/* Filter bar */}
      <div style={cardStyle}>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <label style={labelStyle}>Produk</label>
            <select
              value={selectedProduk || ''}
              onChange={e => setSelectedProduk(Number(e.target.value))}
              style={inputStyle}
            >
              {produkList.map(p => (
                <option key={p.id} value={p.id}>{p.nama_produk}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Periode</label>
            <select value={limit} onChange={e => setLimit(Number(e.target.value))} style={inputStyle}>
              <option value={30}>30 hari</option>
              <option value={90}>90 hari</option>
              <option value={180}>180 hari</option>
              <option value={365}>365 hari</option>
            </select>
          </div>
          {isRole('admin', 'peneliti') && (
            <button onClick={() => setShowForm(!showForm)} style={btnSecondary}>
              {showForm ? '✕ Tutup' : '+ Tambah Data'}
            </button>
          )}
        </div>
      </div>

      {/* Form tambah */}
      {showForm && (
        <div style={{ ...cardStyle, marginTop: 16 }}>
          <h3 style={cardTitle}>Tambah Data Penjualan Manual</h3>
          <form onSubmit={handleTambah} style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div>
              <label style={labelStyle}>Tanggal</label>
              <input type="date" value={form.tanggal}
                onChange={e => setForm({ ...form, tanggal: e.target.value })} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Penjualan (Rp)</label>
              <input type="number" value={form.penjualan_rp} required
                onChange={e => setForm({ ...form, penjualan_rp: e.target.value })} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Unit (opsional)</label>
              <input type="number" value={form.penjualan_unit}
                onChange={e => setForm({ ...form, penjualan_unit: e.target.value })} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Cuaca</label>
              <select value={form.cuaca} onChange={e => setForm({ ...form, cuaca: e.target.value })} style={inputStyle}>
                <option value="cerah">Cerah</option>
                <option value="mendung">Mendung</option>
                <option value="hujan">Hujan</option>
              </select>
            </div>
            <div>
              <label style={labelStyle}>Hari Besar</label>
              <input type="text" value={form.hari_besar} placeholder="Opsional"
                onChange={e => setForm({ ...form, hari_besar: e.target.value })} style={inputStyle} />
            </div>
            <button type="submit" style={btnPrimary}>Simpan</button>
          </form>
        </div>
      )}

      {/* Statistik */}
      {statistik && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 16 }}>
          {[
            { label: 'Rata-rata', val: statistik.mean_rp },
            { label: 'Minimum', val: statistik.min_rp },
            { label: 'Maksimum', val: statistik.max_rp },
            { label: 'Std. Deviasi', val: statistik.std_rp },
          ].map(s => (
            <div key={s.label} style={{
              background: '#fff', borderRadius: 8, padding: '14px 16px',
              boxShadow: '0 2px 6px rgba(0,0,0,0.06)', borderTop: '3px solid #1a237e',
            }}>
              <div style={{ fontSize: 12, color: '#666' }}>{s.label}</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#1a237e', marginTop: 4 }}>
                Rp {Math.round(s.val).toLocaleString('id-ID')}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Grafik */}
      {histori.length > 0 && (
        <div style={{ ...cardStyle, marginTop: 16 }}>
          <h3 style={cardTitle}>
            {produkList.find(p => p.id === selectedProduk)?.nama_produk} — {limit} Hari Terakhir
            ({histori.length} data)
          </h3>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>Memuat...</div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="tgl" tick={{ fontSize: 11 }}
                  tickFormatter={v => v.slice(5)} interval={Math.floor(chartData.length / 8)} />
                <YAxis tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                <Tooltip
                  formatter={v => `Rp ${v.toLocaleString('id-ID')}`}
                  labelFormatter={l => `Tanggal: ${l}`}
                />
                <Line type="monotone" dataKey="penjualan" stroke="#1a237e" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      )}

      {/* Tabel */}
      {histori.length > 0 && (
        <div style={{ ...cardStyle, marginTop: 16 }}>
          <h3 style={cardTitle}>Data Histori ({histori.length} baris)</h3>
          <div style={{ overflowX: 'auto', maxHeight: 400, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead style={{ position: 'sticky', top: 0 }}>
                <tr style={{ background: '#f5f5f5' }}>
                  <th style={th}>Tanggal</th>
                  <th style={th}>Penjualan (Rp)</th>
                  <th style={th}>Unit</th>
                  <th style={th}>Cuaca</th>
                  <th style={th}>Hari Besar</th>
                  <th style={th}>Tipe</th>
                </tr>
              </thead>
              <tbody>
                {[...histori].reverse().map(h => (
                  <tr key={h.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={td}>{h.tanggal}</td>
                    <td style={td}>{h.penjualan_rp.toLocaleString('id-ID')}</td>
                    <td style={td}>{h.penjualan_unit ?? '-'}</td>
                    <td style={td}>{h.cuaca}</td>
                    <td style={td}>{h.hari_besar || '-'}</td>
                    <td style={td}>
                      <span style={{
                        fontSize: 11, padding: '2px 7px', borderRadius: 12,
                        background: h.is_dummy ? '#fff3e0' : '#e8f5e9',
                        color: h.is_dummy ? '#e65100' : '#2e7d32',
                      }}>
                        {h.is_dummy ? 'Dummy' : 'Manual'}
                      </span>
                    </td>
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
const btnSecondary = {
  padding: '9px 20px', background: '#fff', color: '#1a237e',
  border: '1px solid #1a237e', borderRadius: 8, fontSize: 14, cursor: 'pointer',
}
const th = { padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: '#555' }
const td = { padding: '8px 10px', color: '#333' }
