/**
 * pages/ProdukPage.jsx — Manajemen produk (admin + peneliti).
 */
import { useState, useEffect } from 'react'
import api from '../services/api'
import toast from 'react-hot-toast'

const KATEGORI = ['Tahu/Tempe', 'Sayuran', 'Bumbu', 'Mie/Bihun', 'Ikan/Seafood', 'Lainnya']
const SATUAN = ['kg', 'gram', 'porsi', 'bungkus', 'liter', 'buah']

const emptyForm = {
  nama_produk: '', kategori: 'Tahu/Tempe', satuan: 'kg',
  harga_beli_per_unit: '', harga_jual_per_unit: '',
  is_perishable: false, stok_minimum_unit: 0,
}

export default function ProdukPage() {
  const [produkList, setProdukList] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [loading, setLoading] = useState(false)

  const fetchProduk = () =>
    api.get('/produk').then(r => setProdukList(r.data))

  useEffect(() => { fetchProduk() }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const body = {
        ...form,
        harga_beli_per_unit: Number(form.harga_beli_per_unit),
        harga_jual_per_unit: Number(form.harga_jual_per_unit),
        stok_minimum_unit: Number(form.stok_minimum_unit),
      }
      if (editId) {
        await api.put(`/produk/${editId}`, body)
        toast.success('Produk berhasil diperbarui')
      } else {
        await api.post('/produk', body)
        toast.success('Produk berhasil ditambahkan')
      }
      setShowForm(false)
      setEditId(null)
      setForm(emptyForm)
      fetchProduk()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal menyimpan produk')
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (p) => {
    setForm({
      nama_produk: p.nama_produk,
      kategori: p.kategori,
      satuan: p.satuan,
      harga_beli_per_unit: p.harga_beli_per_unit,
      harga_jual_per_unit: p.harga_jual_per_unit,
      is_perishable: p.is_perishable,
      stok_minimum_unit: p.stok_minimum_unit,
    })
    setEditId(p.id)
    setShowForm(true)
  }

  const handleHapus = async (p) => {
    if (!window.confirm(`Nonaktifkan produk '${p.nama_produk}'?`)) return
    try {
      await api.delete(`/produk/${p.id}`)
      toast.success(`'${p.nama_produk}' dinonaktifkan`)
      fetchProduk()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal menonaktifkan')
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0, color: '#1a237e' }}>Manajemen Produk ({produkList.length})</h2>
        <button onClick={() => { setShowForm(!showForm); setEditId(null); setForm(emptyForm) }} style={btnPrimary}>
          {showForm && !editId ? '✕ Tutup' : '+ Tambah Produk'}
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <div style={{ ...cardStyle, marginBottom: 20 }}>
          <h3 style={cardTitle}>{editId ? 'Edit Produk' : 'Tambah Produk Baru'}</h3>
          <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <label style={labelStyle}>Nama Produk *</label>
              <input value={form.nama_produk} required style={inputFull}
                onChange={e => setForm({ ...form, nama_produk: e.target.value })} />
            </div>
            <div>
              <label style={labelStyle}>Kategori</label>
              <select value={form.kategori} style={inputFull}
                onChange={e => setForm({ ...form, kategori: e.target.value })}>
                {KATEGORI.map(k => <option key={k}>{k}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Harga Beli/Unit (Rp) *</label>
              <input type="number" value={form.harga_beli_per_unit} required style={inputFull}
                onChange={e => setForm({ ...form, harga_beli_per_unit: e.target.value })} />
            </div>
            <div>
              <label style={labelStyle}>Harga Jual/Unit (Rp) *</label>
              <input type="number" value={form.harga_jual_per_unit} required style={inputFull}
                onChange={e => setForm({ ...form, harga_jual_per_unit: e.target.value })} />
            </div>
            <div>
              <label style={labelStyle}>Satuan</label>
              <select value={form.satuan} style={inputFull}
                onChange={e => setForm({ ...form, satuan: e.target.value })}>
                {SATUAN.map(s => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Stok Minimum (unit)</label>
              <input type="number" value={form.stok_minimum_unit} style={inputFull}
                onChange={e => setForm({ ...form, stok_minimum_unit: e.target.value })} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input type="checkbox" id="perishable" checked={form.is_perishable}
                onChange={e => setForm({ ...form, is_perishable: e.target.checked })} />
              <label htmlFor="perishable" style={{ fontSize: 14, color: '#555' }}>
                Produk mudah busuk (perishable)
              </label>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
              <button type="submit" disabled={loading} style={btnPrimary}>
                {loading ? 'Menyimpan...' : (editId ? 'Update' : 'Simpan')}
              </button>
              <button type="button" onClick={() => { setShowForm(false); setEditId(null) }} style={btnSecondary}>
                Batal
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tabel */}
      <div style={cardStyle}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ background: '#f5f5f5' }}>
              <th style={th}>Produk</th>
              <th style={th}>Kategori</th>
              <th style={th}>Satuan</th>
              <th style={th}>Harga Beli</th>
              <th style={th}>Harga Jual</th>
              <th style={th}>Margin</th>
              <th style={th}>Perishable</th>
              <th style={th}>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {produkList.map(p => {
              const margin = (((p.harga_jual_per_unit - p.harga_beli_per_unit) / p.harga_jual_per_unit) * 100).toFixed(1)
              return (
                <tr key={p.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ ...td, fontWeight: 500 }}>{p.nama_produk}</td>
                  <td style={td}>{p.kategori}</td>
                  <td style={td}>{p.satuan}</td>
                  <td style={td}>Rp {p.harga_beli_per_unit.toLocaleString('id-ID')}</td>
                  <td style={td}>Rp {p.harga_jual_per_unit.toLocaleString('id-ID')}</td>
                  <td style={{ ...td, color: parseFloat(margin) >= 20 ? '#2e7d32' : '#e65100' }}>
                    {margin}%
                  </td>
                  <td style={td}>{p.is_perishable ? '✓' : '-'}</td>
                  <td style={td}>
                    <button onClick={() => handleEdit(p)} style={btnXs('#1a237e')}>Edit</button>
                    {' '}
                    <button onClick={() => handleHapus(p)} style={btnXs('#c62828')}>Nonaktifkan</button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const cardStyle = { background: '#fff', borderRadius: 10, padding: 20, boxShadow: '0 2px 8px rgba(0,0,0,0.07)' }
const cardTitle = { margin: '0 0 16px', color: '#1a237e', fontSize: 16 }
const labelStyle = { display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6, color: '#555' }
const inputFull = { width: '100%', padding: '9px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14, boxSizing: 'border-box' }
const btnPrimary = { padding: '9px 20px', background: '#1a237e', color: '#fff', border: 'none', borderRadius: 8, fontSize: 14, cursor: 'pointer', fontWeight: 600 }
const btnSecondary = { padding: '9px 20px', background: '#fff', color: '#555', border: '1px solid #ddd', borderRadius: 8, fontSize: 14, cursor: 'pointer' }
const btnXs = (bg) => ({ padding: '4px 10px', background: bg, color: '#fff', border: 'none', borderRadius: 6, fontSize: 12, cursor: 'pointer' })
const th = { padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#555' }
const td = { padding: '10px 12px', color: '#333' }
