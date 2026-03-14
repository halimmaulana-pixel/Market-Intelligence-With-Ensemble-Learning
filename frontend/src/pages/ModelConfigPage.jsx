/**
 * pages/ModelConfigPage.jsx — Konfigurasi model ML + trigger training (peneliti).
 */
import { useState, useEffect } from 'react'
import api from '../services/api'
import toast from 'react-hot-toast'

export default function ModelConfigPage() {
  const [configs, setConfigs] = useState([])
  const [evaluasi, setEvaluasi] = useState(null)
  const [editId, setEditId] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [trainingId, setTrainingId] = useState(null)
  const [trainingAll, setTrainingAll] = useState(false)
  const [loading, setLoading] = useState(false)

  const fetchConfigs = () =>
    api.get('/model-config').then(r => setConfigs(r.data))

  const fetchEvaluasi = () =>
    api.get('/model-config/evaluasi/all').then(r => setEvaluasi(r.data)).catch(() => {})

  useEffect(() => {
    fetchConfigs()
    fetchEvaluasi()
  }, [])

  const handleEdit = (c) => {
    setEditId(c.produk_id)
    setEditForm({
      svr_C: c.svr_C, svr_gamma: c.svr_gamma, svr_epsilon: c.svr_epsilon,
      sarima_p: c.sarima_p, sarima_d: c.sarima_d, sarima_q: c.sarima_q,
      sarima_sp: c.sarima_sp, sarima_sd: c.sarima_sd, sarima_sq: c.sarima_sq,
      sarima_s: c.sarima_s, auto_tune: c.auto_tune,
    })
  }

  const handleSaveEdit = async () => {
    try {
      await api.put(`/model-config/${editId}`, editForm)
      toast.success('Konfigurasi berhasil disimpan')
      setEditId(null)
      fetchConfigs()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal menyimpan')
    }
  }

  const handleTraining = async (produkId, nama) => {
    setTrainingId(produkId)
    toast.loading(`Melatih model ${nama}...`, { id: 'train' })
    try {
      const res = await api.post(`/model-config/training/${produkId}`)
      toast.success(`${nama}: ${res.data.pesan} (${res.data.durasi_detik}s)`, { id: 'train' })
      fetchConfigs()
      fetchEvaluasi()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Training gagal', { id: 'train' })
    } finally {
      setTrainingId(null)
    }
  }

  const handleTrainingAll = async () => {
    if (!window.confirm('Latih ulang SEMUA model? Proses ini bisa memakan beberapa menit.')) return
    setTrainingAll(true)
    toast.loading('Melatih semua model...', { id: 'trainAll', duration: 600000 })
    try {
      const res = await api.post('/model-config/training/all')
      toast.success(`${res.data.pesan} (${res.data.durasi_detik}s)`, { id: 'trainAll' })
      fetchConfigs()
      fetchEvaluasi()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Training gagal', { id: 'trainAll' })
    } finally {
      setTrainingAll(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, alignItems: 'center' }}>
        <h2 style={{ margin: 0, color: '#1a237e' }}>Konfigurasi Model ML</h2>
        <button onClick={handleTrainingAll} disabled={trainingAll} style={btnDanger}>
          {trainingAll ? '⏳ Melatih...' : '🚀 Latih Semua Model'}
        </button>
      </div>

      {/* Tabel konfigurasi */}
      <div style={cardStyle}>
        <h3 style={cardTitle}>Parameter Model per Produk</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f5f5f5' }}>
                <th style={th}>Produk</th>
                <th style={th}>Auto-Tune</th>
                <th style={th}>SVR C/γ/ε</th>
                <th style={th}>SARIMA p,d,q</th>
                <th style={th}>Seasonal P,D,Q,s</th>
                <th style={th}>MAPE SVR</th>
                <th style={th}>MAPE SARIMA</th>
                <th style={th}>Model</th>
                <th style={th}>Aksi</th>
              </tr>
            </thead>
            <tbody>
              {configs.map(c => (
                <tr key={c.produk_id} style={{ borderBottom: '1px solid #eee' }}>
                  {editId === c.produk_id ? (
                    <>
                      <td style={td}><strong>{c.nama_produk}</strong></td>
                      <td style={td}>
                        <input type="checkbox" checked={editForm.auto_tune}
                          onChange={e => setEditForm({ ...editForm, auto_tune: e.target.checked })} />
                      </td>
                      <td style={td}>
                        {['svr_C', 'svr_gamma', 'svr_epsilon'].map(k => (
                          <input key={k} type="number" step="0.001" value={editForm[k]}
                            style={{ width: 60, margin: '0 2px' }}
                            onChange={e => setEditForm({ ...editForm, [k]: Number(e.target.value) })} />
                        ))}
                      </td>
                      <td style={td}>
                        {['sarima_p', 'sarima_d', 'sarima_q'].map(k => (
                          <input key={k} type="number" value={editForm[k]}
                            style={{ width: 40, margin: '0 2px' }}
                            onChange={e => setEditForm({ ...editForm, [k]: Number(e.target.value) })} />
                        ))}
                      </td>
                      <td style={td}>
                        {['sarima_sp', 'sarima_sd', 'sarima_sq', 'sarima_s'].map(k => (
                          <input key={k} type="number" value={editForm[k]}
                            style={{ width: 40, margin: '0 2px' }}
                            onChange={e => setEditForm({ ...editForm, [k]: Number(e.target.value) })} />
                        ))}
                      </td>
                      <td style={td} colSpan={3}>
                        <button onClick={handleSaveEdit} style={btnXs('#1a237e')}>Simpan</button>
                        {' '}
                        <button onClick={() => setEditId(null)} style={btnXs('#757575')}>Batal</button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td style={td}><strong>{c.nama_produk}</strong></td>
                      <td style={td}>{c.auto_tune ? '✓ Auto' : '✗ Manual'}</td>
                      <td style={td}>{c.svr_C}/{c.svr_gamma}/{c.svr_epsilon}</td>
                      <td style={td}>{c.sarima_p},{c.sarima_d},{c.sarima_q}</td>
                      <td style={td}>{c.sarima_sp},{c.sarima_sd},{c.sarima_sq} s={c.sarima_s}</td>
                      <td style={td}>{c.mape_svr ? `${c.mape_svr.toFixed(2)}%` : '-'}</td>
                      <td style={td}>{c.mape_sarima ? `${c.mape_sarima.toFixed(2)}%` : '-'}</td>
                      <td style={td}>
                        <span style={{
                          fontSize: 11, padding: '2px 7px', borderRadius: 12,
                          background: c.model_tersedia ? '#e8f5e9' : '#fff3e0',
                          color: c.model_tersedia ? '#2e7d32' : '#e65100',
                        }}>
                          {c.model_tersedia ? 'Siap' : 'Belum'}
                        </span>
                      </td>
                      <td style={td}>
                        <button onClick={() => handleEdit(c)} style={btnXs('#1a237e')}>Edit</button>
                        {' '}
                        <button
                          onClick={() => handleTraining(c.produk_id, c.nama_produk)}
                          disabled={trainingId === c.produk_id}
                          style={btnXs('#2e7d32')}
                        >
                          {trainingId === c.produk_id ? '⏳' : '▶ Latih'}
                        </button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Evaluasi */}
      {evaluasi && evaluasi.length > 0 && (
        <div style={{ ...cardStyle, marginTop: 20 }}>
          <h3 style={cardTitle}>Evaluasi Model</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f5f5f5' }}>
                  <th style={th}>Produk</th>
                  <th style={th}>MAPE SVR</th>
                  <th style={th}>RMSE SVR</th>
                  <th style={th}>R² SVR</th>
                  <th style={th}>MAPE SARIMA</th>
                  <th style={th}>RMSE SARIMA</th>
                  <th style={th}>MAPE Ensemble</th>
                </tr>
              </thead>
              <tbody>
                {evaluasi.map(e => (
                  <tr key={e.produk_id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={td}>{e.nama_produk}</td>
                    <td style={{ ...td, color: mapeColor(e.svr?.mape) }}>{fmt(e.svr?.mape)}%</td>
                    <td style={td}>{e.svr?.rmse ? Math.round(e.svr.rmse).toLocaleString('id-ID') : '-'}</td>
                    <td style={td}>{e.svr?.r2 ? e.svr.r2.toFixed(4) : '-'}</td>
                    <td style={{ ...td, color: mapeColor(e.sarima?.mape) }}>{fmt(e.sarima?.mape)}%</td>
                    <td style={td}>{e.sarima?.rmse ? Math.round(e.sarima.rmse).toLocaleString('id-ID') : '-'}</td>
                    <td style={{ ...td, fontWeight: 600, color: mapeColor(e.ensemble?.mape) }}>
                      {fmt(e.ensemble?.mape)}%
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

const fmt = (v) => v ? v.toFixed(2) : '-'
const mapeColor = (v) => !v ? '#333' : v < 10 ? '#2e7d32' : v < 20 ? '#e65100' : '#c62828'

const cardStyle = { background: '#fff', borderRadius: 10, padding: 20, boxShadow: '0 2px 8px rgba(0,0,0,0.07)' }
const cardTitle = { margin: '0 0 16px', color: '#1a237e', fontSize: 16 }
const btnDanger = { padding: '9px 20px', background: '#c62828', color: '#fff', border: 'none', borderRadius: 8, fontSize: 14, cursor: 'pointer', fontWeight: 600 }
const btnXs = (bg) => ({ padding: '4px 10px', background: bg, color: '#fff', border: 'none', borderRadius: 6, fontSize: 12, cursor: 'pointer' })
const th = { padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: '#555' }
const td = { padding: '8px 10px', color: '#333' }
