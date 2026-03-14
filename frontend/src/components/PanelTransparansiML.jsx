/**
 * components/PanelTransparansiML.jsx
 * Panel Transparansi Algoritma ML — hanya untuk role Peneliti.
 *
 * Menampilkan 5 tahap proses prediksi per produk:
 *   1. Feature Engineering
 *   2. SVR
 *   3. SARIMA
 *   4. Ensemble
 *   5. Keuangan
 *
 * Setiap tahap dianimasikan sebagai terminal log line-by-line.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import {
  ComposedChart, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'

// ── Konstanta warna terminal ──────────────────────────────────────────────────
const C = {
  green:  '#4ade80',
  yellow: '#fbbf24',
  blue:   '#60a5fa',
  red:    '#f87171',
  white:  '#e2e8f0',
  dim:    '#94a3b8',
  purple: '#a78bfa',
}

// ── Urutan & label tab ────────────────────────────────────────────────────────
const TABS = [
  { key: 'fitur',    label: '📊 Fitur' },
  { key: 'svr',      label: '🤖 SVR' },
  { key: 'sarima',   label: '📈 SARIMA' },
  { key: 'ensemble', label: '⚖️ Ensemble' },
  { key: 'keuangan', label: '💵 Keuangan' },
]

// ── Format helpers ────────────────────────────────────────────────────────────
function fmtRp(v) {
  if (v == null || isNaN(v)) return 'N/A'
  return `Rp ${Math.round(v).toLocaleString('id-ID')}`
}

function fmtPct(v) {
  if (v == null || isNaN(v)) return 'N/A'
  return `${(v * 100).toFixed(2)}%`
}

function fmtNum(v, digits = 4) {
  if (v == null || isNaN(v)) return 'N/A'
  return Number(v).toFixed(digits)
}

function nowTs() {
  const d = new Date()
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  const ms = String(d.getMilliseconds()).padStart(3, '0')
  return `${mm}:${ss}.${ms}`
}

function formatMape(p) {
  const e = p?.tahap_4_ensemble
  if (!e) return 'N/A'
  const mape = (e.mape_svr ?? 0) * (e.bobot_svr ?? 0) + (e.mape_sarima ?? 0) * (e.bobot_sarima ?? 0)
  return isNaN(mape) ? 'N/A' : `${mape.toFixed(2)}%`
}

// ── Generasi baris log terminal per tab ───────────────────────────────────────
function generateLogLines(tab, p) {
  const ts = nowTs()
  const t1 = p.tahap_1_fitur || {}
  const t2 = p.tahap_2_svr || {}
  const t3 = p.tahap_3_sarima || {}
  const t4 = p.tahap_4_ensemble || {}
  const t5 = p.tahap_5_keuangan || {}

  switch (tab) {
    case 'fitur': {
      const lines = [
        `[${ts}] [INFO] === Tahap 1: Feature Engineering ===`,
        `[${ts}] [INFO] Produk: ${p.nama_produk} (ID: ${p.produk_id})`,
        `[${ts}] [LOAD] Memuat data histori penjualan dari database...`,
        `[${ts}] [OK]   ✅ Data dimuat: ${t1.n_observasi ?? '?'} observasi setelah feature engineering`,
        `[${ts}] [INFO] Jumlah fitur: ${t1.n_fitur ?? '?'}`,
        `[${ts}] [INFO] Fitur: ${(t1.nama_fitur || []).join(', ')}`,
        `[${ts}] [INFO] --- Lag & Rolling Features ---`,
        ...(t1.nama_fitur || []).slice(0, 4).map((f, i) =>
          `[${ts}] [FEAT] ${f.padEnd(10)} = ${fmtNum(t1.contoh_sebelum_scaling?.[i], 2)}`
        ),
        `[${ts}] [INFO] --- Min-Max Scaling (range [0, 1]) ---`,
        `[${ts}] [SCAL] X_raw shape   : (1, ${t1.n_fitur ?? '?'})`,
        `[${ts}] [SCAL] X_min (lag_1) : ${fmtNum(t1.x_min?.[0], 2)}`,
        `[${ts}] [SCAL] X_max (lag_1) : ${fmtNum(t1.x_max?.[0], 2)}`,
        `[${ts}] [SCAL] Contoh scaled : ${(t1.contoh_sesudah_scaling || []).slice(0, 4).map(v => fmtNum(v, 4)).join(', ')} ...`,
        `[${ts}] [OK]   ✅ Feature engineering selesai`,
      ]
      return lines
    }

    case 'svr': {
      const lines = [
        `[${ts}] [INFO] === Tahap 2: Support Vector Regression ===`,
        `[${ts}] [LOAD] Memuat model: ${t2.file_model ?? 'svr_?.pkl'}`,
        `[${ts}] [OK]   ✅ Model SVR berhasil dimuat`,
        `[${ts}] [INFO] --- Hyperparameter ---`,
        `[${ts}] [PARAM] Kernel  : ${t2.kernel ?? 'rbf'}`,
        `[${ts}] [PARAM] C       : ${t2.C ?? '?'}`,
        `[${ts}] [PARAM] gamma   : ${t2.gamma ?? '?'}`,
        `[${ts}] [PARAM] epsilon : ${t2.epsilon ?? '?'}`,
        `[${ts}] [INFO] Support Vectors: ${t2.n_support_vectors ?? '?'} (dari ${t2.n_training_samples ?? '?'} data training)`,
        `[${ts}] [INFO] --- Prediksi ---`,
        `[${ts}] [PRED] Skala normalized : ${fmtNum(t2.prediksi_scaled, 6)}`,
        `[${ts}] [PRED] Denormalisasi    : scaled × (${fmtNum(t2.y_max, 0)} - ${fmtNum(t2.y_min, 0)}) + ${fmtNum(t2.y_min, 0)}`,
        `[${ts}] [PRED] Prediksi SVR     : ${fmtRp(t2.prediksi_rp)}`,
        `[${ts}] [INFO] --- Epsilon Tube (ε) ---`,
        `[${ts}] [TUBE] ε = ${fmtNum(t2.epsilon, 4)} × (${fmtNum(t2.y_max, 0)} - ${fmtNum(t2.y_min, 0)}) = ${fmtRp(t2.epsilon_tube?.epsilon_rp)}`,
        `[${ts}] [TUBE] Data visualisasi: ${(t2.epsilon_tube?.data_test ?? []).length} titik`,
        `[${ts}] [TIME] Durasi inferensi : ${t2.durasi_ms ?? '?'} ms`,
        `[${ts}] [OK]   ✅ SVR selesai`,
      ]
      return lines
    }

    case 'sarima': {
      const adfStatus = t3.adf_stasioner == null
        ? '? (tidak tersedia)'
        : t3.adf_stasioner
          ? `✅ Stasioner (p=${fmtNum(t3.adf_pvalue, 4)})`
          : `⚠️ Tidak stasioner (p=${fmtNum(t3.adf_pvalue, 4)}, d=1 disarankan)`

      const lines = [
        `[${ts}] [INFO] === Tahap 3: SARIMA Model ===`,
        `[${ts}] [LOAD] Memuat model: ${t3.file_model ?? 'sarima_?.pkl'}`,
        `[${ts}] [OK]   ✅ Model SARIMA berhasil dimuat`,
        `[${ts}] [INFO] Orde model: ${t3.orde ?? '?'}`,
        `[${ts}] [INFO] --- Uji Stasioneritas (ADF) ---`,
        `[${ts}] [ADF]  ${adfStatus}`,
        `[${ts}] [INFO] --- Koefisien AR ---`,
        ...((t3.koefisien_ar || []).length
          ? t3.koefisien_ar.map((v, i) => `[${ts}] [COEF] AR[${i + 1}] = ${fmtNum(v, 6)}`)
          : [`[${ts}] [COEF] (tidak ada koefisien AR)`]),
        `[${ts}] [INFO] --- Koefisien MA ---`,
        ...((t3.koefisien_ma || []).length
          ? t3.koefisien_ma.map((v, i) => `[${ts}] [COEF] MA[${i + 1}] = ${fmtNum(v, 6)}`)
          : [`[${ts}] [COEF] (tidak ada koefisien MA)`]),
        `[${ts}] [INFO] --- Diagnostik Residual ---`,
        `[${ts}] [LB]   Ljung-Box p-value (lag=10): ${fmtNum(t3.ljung_box_pvalue, 4)}`,
        t3.ljung_box_pvalue != null && t3.ljung_box_pvalue > 0.05
          ? `[${ts}] [LB]   ✅ Tidak ada autokorelasi residual`
          : `[${ts}] [LB]   ⚠️ Ada autokorelasi residual (perlu perhatian)`,
        `[${ts}] [INFO] --- Prediksi ---`,
        `[${ts}] [PRED] Prediksi SARIMA: ${fmtRp(t3.prediksi_rp)}`,
        `[${ts}] [TIME] Durasi inferensi: ${t3.durasi_ms ?? '?'} ms`,
        `[${ts}] [OK]   ✅ SARIMA selesai`,
      ]
      return lines
    }

    case 'ensemble': {
      const mapeEnsemble = ((t4.mape_svr ?? 0) * (t4.bobot_svr ?? 0) +
        (t4.mape_sarima ?? 0) * (t4.bobot_sarima ?? 0))
      const lines = [
        `[${ts}] [INFO] === Tahap 4: Ensemble Weighting (Inverse MAPE) ===`,
        `[${ts}] [INFO] --- MAPE per Model ---`,
        `[${ts}] [MAPE] MAPE SVR    : ${fmtNum(t4.mape_svr, 4)}%`,
        `[${ts}] [MAPE] MAPE SARIMA : ${fmtNum(t4.mape_sarima, 4)}%`,
        `[${ts}] [INFO] --- Bobot Invers MAPE ---`,
        `[${ts}] [BOBOT] w_SVR    = 1/MAPE_SVR / (1/MAPE_SVR + 1/MAPE_SARIMA) = ${fmtNum(t4.bobot_svr, 6)}`,
        `[${ts}] [BOBOT] w_SARIMA = 1 - w_SVR = ${fmtNum(t4.bobot_sarima, 6)}`,
        `[${ts}] [INFO] --- Formula Ensemble ---`,
        `[${ts}] [FORM] ${t4.formula ?? 'ŷ = w_svr × ŷ_svr + w_sarima × ŷ_sarima'}`,
        `[${ts}] [PRED] MAPE Ensemble (tertimbang): ${fmtNum(mapeEnsemble, 4)}%`,
        `[${ts}] [PRED] Prediksi Ensemble: ${fmtRp(t4.prediksi_ensemble_rp)}`,
        `[${ts}] [OK]   ✅ Ensemble selesai`,
      ]
      return lines
    }

    case 'keuangan': {
      const lines = [
        `[${ts}] [INFO] === Tahap 5: Analisis Keuangan ===`,
        `[${ts}] [INFO] Kategori produk: ${t5.kategori ?? '?'}`,
        `[${ts}] [INFO] --- Harga ---`,
        `[${ts}] [HRGA] Harga beli per unit: ${fmtRp(t5.harga_beli)}`,
        `[${ts}] [HRGA] Harga jual per unit: ${fmtRp(t5.harga_jual)}`,
        `[${ts}] [INFO] --- Kalkulasi ---`,
        `[${ts}] [CALC] Revenue prediksi  : ${fmtRp(t5.revenue_rp)}`,
        `[${ts}] [CALC] Modal beli        : Revenue × (harga_beli / harga_jual) = ${fmtRp(t5.modal_beli_rp)}`,
        `[${ts}] [CALC] ${t5.rumus_susut ?? 'Susut: N/A'}`,
        `[${ts}] [CALC] Margin ratio      : (Revenue - Modal - Susut) / Modal = ${fmtPct(t5.margin_ratio)}`,
        `[${ts}] [OK]   ✅ Analisis keuangan selesai`,
      ]
      return lines
    }

    default:
      return [`[${ts}] [INFO] Tab tidak dikenal: ${tab}`]
  }
}

// ── Warna baris terminal ──────────────────────────────────────────────────────
function lineColor(line) {
  if (line.includes('✅') || line.includes('[OK]')) return C.green
  if (line.includes('⚠️') || line.includes('WARNING')) return C.yellow
  if (line.includes('===')) return C.blue
  if (line.includes('[PRED]') || line.includes('[FORM]')) return C.purple
  if (line.includes('[TIME]')) return C.dim
  return C.white
}

// ── Gauge SVG sederhana ───────────────────────────────────────────────────────
function Gauge({ nilai, label, warna }) {
  const pct = Math.min(Math.max(nilai || 0, 0), 1)
  const cx = 60, cy = 60, r = 45
  const startAngle = Math.PI
  const endAngle = 2 * Math.PI
  const angle = startAngle + pct * (endAngle - startAngle)

  const x1 = cx + r * Math.cos(startAngle)
  const y1 = cy + r * Math.sin(startAngle)
  const x2 = cx + r * Math.cos(angle)
  const y2 = cy + r * Math.sin(angle)
  const largeArc = pct > 0.5 ? 1 : 0

  const bgX2 = cx + r * Math.cos(endAngle)
  const bgY2 = cy + r * Math.sin(endAngle)

  return (
    <div style={{ textAlign: 'center' }}>
      <svg width={120} height={75} viewBox="0 0 120 75">
        {/* Background arc */}
        <path
          d={`M ${x1} ${y1} A ${r} ${r} 0 1 1 ${bgX2} ${bgY2}`}
          fill="none"
          stroke="#2d3748"
          strokeWidth={10}
          strokeLinecap="round"
        />
        {/* Value arc */}
        {pct > 0 && (
          <path
            d={`M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`}
            fill="none"
            stroke={warna}
            strokeWidth={10}
            strokeLinecap="round"
          />
        )}
        {/* Label */}
        <text x={cx} y={cy + 10} textAnchor="middle" fill={warna} fontSize={14} fontWeight="bold">
          {(pct * 100).toFixed(1)}%
        </text>
      </svg>
      <div style={{ fontSize: 12, color: C.dim, marginTop: -4 }}>{label}</div>
    </div>
  )
}

// ── Komponen utama ────────────────────────────────────────────────────────────
export default function PanelTransparansiML({ prosesDetail }) {
  const [openProduct, setOpenProduct] = useState(null)
  const [activeTab, setActiveTab] = useState({})
  const [animDone, setAnimDone] = useState({})
  const [animLines, setAnimLines] = useState({})
  const intervalRefs = useRef({})

  // Bersihkan semua interval saat unmount
  useEffect(() => {
    const refs = intervalRefs.current
    return () => {
      Object.values(refs).forEach(id => clearInterval(id))
    }
  }, [])

  const makeKey = (produkId, tab) => `${produkId}__${tab}`

  const isAnimDone = useCallback(
    (produkId, tab) => !!(animDone[makeKey(produkId, tab)]),
    [animDone]
  )

  const getAnimLines = useCallback(
    (produkId, tab) => animLines[makeKey(produkId, tab)] || [],
    [animLines]
  )

  // Mulai animasi terminal untuk (produkId, tab) jika belum dimulai
  const startAnimation = useCallback((produkId, tab, p) => {
    const key = makeKey(produkId, tab)
    if (animDone[key] !== undefined) return // sudah selesai atau sedang jalan

    const lines = generateLogLines(tab, p)
    let idx = 0

    setAnimLines(prev => ({ ...prev, [key]: [] }))
    setAnimDone(prev => ({ ...prev, [key]: false }))

    const intervalId = setInterval(() => {
      idx++
      setAnimLines(prev => ({
        ...prev,
        [key]: lines.slice(0, idx),
      }))
      if (idx >= lines.length) {
        clearInterval(intervalId)
        delete intervalRefs.current[key]
        setAnimDone(prev => ({ ...prev, [key]: true }))
      }
    }, 80)

    intervalRefs.current[key] = intervalId
  }, [animDone])

  const skipAnimation = useCallback((produkId, tab, p) => {
    const key = makeKey(produkId, tab)
    // Hentikan interval jika masih berjalan
    if (intervalRefs.current[key]) {
      clearInterval(intervalRefs.current[key])
      delete intervalRefs.current[key]
    }
    const lines = generateLogLines(tab, p)
    setAnimLines(prev => ({ ...prev, [key]: lines }))
    setAnimDone(prev => ({ ...prev, [key]: true }))
  }, [])

  const toggleProduct = useCallback((produkId, p) => {
    setOpenProduct(prev => {
      const isOpening = prev !== produkId
      if (isOpening) {
        // Set tab default dan mulai animasi tab pertama
        const defaultTab = 'fitur'
        setActiveTab(at => ({ ...at, [produkId]: defaultTab }))
        setTimeout(() => startAnimation(produkId, defaultTab, p), 50)
        return produkId
      }
      return null
    })
  }, [startAnimation])

  const changeTab = useCallback((produkId, tab, p) => {
    setActiveTab(at => ({ ...at, [produkId]: tab }))
    startAnimation(produkId, tab, p)
  }, [startAnimation])

  if (!prosesDetail || prosesDetail.length === 0) return null

  return (
    <div style={{ marginTop: 24 }}>
      {/* Print CSS */}
      <style>{`
        @media print {
          body > *:not(.panel-transparansi-ml) { display: none !important; }
          .panel-transparansi-ml { display: block !important; }
        }
        .tab-btn:hover { opacity: 0.85; }
        .accordion-header:hover { opacity: 0.92; }
        .terminal-line { transition: opacity 0.1s; }
      `}</style>

      <div className="panel-transparansi-ml" style={styles.container}>
        {/* Header panel */}
        <div style={styles.panelHeader}>
          <div>
            <h3 style={styles.panelTitle}>Panel Transparansi Algoritma ML</h3>
            <p style={styles.panelSubtitle}>
              Detail proses prediksi 5 tahap per produk — khusus Peneliti
            </p>
          </div>
          <button
            onClick={() => window.print()}
            style={styles.btnExport}
            title="Export PDF"
          >
            📄 Export PDF Proses
          </button>
        </div>

        {/* Accordion per produk */}
        {prosesDetail.map(p => {
          const isOpen = openProduct === p.produk_id
          const tab = activeTab[p.produk_id] || 'fitur'

          return (
            <div key={p.produk_id} style={styles.accordion}>
              {/* Accordion header */}
              <div
                className="accordion-header"
                onClick={() => toggleProduct(p.produk_id, p)}
                style={{
                  ...styles.accordionHeader,
                  background: isOpen ? '#1a1a2e' : '#0d1117',
                }}
              >
                <span style={{ fontSize: 14 }}>
                  {isOpen ? '▼' : '▶'}{' '}
                  <strong style={{ color: '#90caf9' }}>{p.nama_produk}</strong>
                </span>
                <span style={{ fontSize: 12, color: '#90caf9' }}>
                  MAPE Ensemble: {formatMape(p)} | {' '}
                  {p.tahap_4_ensemble?.prediksi_ensemble_rp != null
                    ? fmtRp(p.tahap_4_ensemble.prediksi_ensemble_rp)
                    : 'N/A'}
                </span>
              </div>

              {/* Accordion body */}
              {isOpen && (
                <div style={styles.accordionBody}>
                  {/* Tab bar */}
                  <div style={styles.tabBar}>
                    {TABS.map(t => (
                      <button
                        key={t.key}
                        className="tab-btn"
                        onClick={() => changeTab(p.produk_id, t.key, p)}
                        style={{
                          ...styles.tabBtn,
                          background: tab === t.key ? '#1e3a5f' : 'transparent',
                          borderBottom: tab === t.key ? '2px solid #60a5fa' : '2px solid transparent',
                          color: tab === t.key ? '#60a5fa' : '#94a3b8',
                        }}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>

                  {/* Terminal + visualisasi */}
                  <TabContent
                    p={p}
                    tab={tab}
                    produkId={p.produk_id}
                    lines={getAnimLines(p.produk_id, tab)}
                    done={isAnimDone(p.produk_id, tab)}
                    onSkip={() => skipAnimation(p.produk_id, tab, p)}
                  />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Konten tab ────────────────────────────────────────────────────────────────
function TabContent({ p, tab, produkId, lines, done, onSkip }) {
  const terminalRef = useRef(null)

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [lines])

  return (
    <div>
      {/* Terminal */}
      <div style={{ position: 'relative' }}>
        <div ref={terminalRef} style={styles.terminal}>
          {lines.map((line, i) => (
            <div key={i} className="terminal-line" style={{ color: lineColor(line), marginBottom: 2 }}>
              {line}
            </div>
          ))}
          {!done && lines.length > 0 && (
            <span style={{ color: C.green, animation: 'blink 1s step-end infinite' }}>█</span>
          )}
        </div>
        {!done && (
          <button onClick={onSkip} style={styles.btnSkip}>
            ⏭ Lewati Animasi
          </button>
        )}
      </div>

      {/* Visualisasi (tampil setelah animasi selesai) */}
      {done && <Visualisasi p={p} tab={tab} />}
    </div>
  )
}

// ── Visualisasi per tab ───────────────────────────────────────────────────────
function Visualisasi({ p, tab }) {
  const t1 = p.tahap_1_fitur || {}
  const t2 = p.tahap_2_svr || {}
  const t3 = p.tahap_3_sarima || {}
  const t4 = p.tahap_4_ensemble || {}
  const t5 = p.tahap_5_keuangan || {}

  switch (tab) {
    case 'fitur':
      return <VisFitur t1={t1} />
    case 'svr':
      return <VisSvr t2={t2} />
    case 'sarima':
      return <VisSarima t3={t3} />
    case 'ensemble':
      return <VisEnsemble t4={t4} />
    case 'keuangan':
      return <VisKeuangan t5={t5} />
    default:
      return null
  }
}

// ── Tab FITUR: tabel fitur ────────────────────────────────────────────────────
function VisFitur({ t1 }) {
  const fitur = t1.nama_fitur || []
  const sebelum = t1.contoh_sebelum_scaling || []
  const sesudah = t1.contoh_sesudah_scaling || []

  return (
    <div style={styles.visBox}>
      <h4 style={styles.visTitle}>Tabel Nilai Fitur (Prediksi Hari Ini)</h4>
      <div style={{ overflowX: 'auto' }}>
        <table style={styles.table}>
          <thead>
            <tr style={{ background: '#1e2a3a' }}>
              <th style={styles.th}>Fitur</th>
              <th style={styles.th}>Nilai Asli</th>
              <th style={styles.th}>Nilai Scaled [0,1]</th>
            </tr>
          </thead>
          <tbody>
            {fitur.map((f, i) => {
              const raw = sebelum[i]
              const scaled = sesudah[i]
              const changed = raw != null && scaled != null && Math.abs(raw - scaled) > 0.01
              return (
                <tr key={f} style={{ background: changed ? '#1a2535' : 'transparent' }}>
                  <td style={styles.td}>
                    <code style={{ color: '#93c5fd' }}>{f}</code>
                  </td>
                  <td style={{ ...styles.td, textAlign: 'right' }}>
                    {raw != null ? Number(raw).toFixed(2) : '-'}
                  </td>
                  <td style={{
                    ...styles.td,
                    textAlign: 'right',
                    color: changed ? '#4ade80' : '#e2e8f0',
                    fontWeight: changed ? 600 : 400,
                  }}>
                    {scaled != null ? Number(scaled).toFixed(4) : '-'}
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

// ── Tab SVR: epsilon tube chart ───────────────────────────────────────────────
function VisSvr({ t2 }) {
  const tubeData = (t2.epsilon_tube?.data_test || []).slice(-30)
  const epsilonRp = t2.epsilon_tube?.epsilon_rp || 0

  const chartData = tubeData.map(d => ({
    x: d.x,
    actual: d.y_actual,
    pred: d.y_pred,
    upper: d.y_pred + epsilonRp,
    lower: d.y_pred - epsilonRp,
    inTube: d.in_tube,
  }))

  return (
    <div style={styles.visBox}>
      <h4 style={styles.visTitle}>
        Epsilon Tube SVR (ε = {fmtRp(epsilonRp)})
      </h4>
      <p style={styles.visDesc}>
        Biru: nilai aktual | Hijau: prediksi SVR | Area abu: epsilon tube
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 20, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
          <XAxis dataKey="x" tick={{ fill: '#94a3b8', fontSize: 11 }} label={{ value: 'Indeks data', fill: '#94a3b8', position: 'insideBottom', offset: -5 }} />
          <YAxis tickFormatter={v => `${(v / 1000).toFixed(0)}k`} tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: '#1e2a3a', border: '1px solid #2d3748', color: '#e2e8f0' }}
            formatter={(v, name) => [fmtRp(v), name === 'actual' ? 'Aktual' : name === 'pred' ? 'Prediksi SVR' : name]}
          />
          <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
          {/* Epsilon tube bounds */}
          <Line type="monotone" dataKey="upper" stroke="#374151" strokeDasharray="4 2" dot={false} name="ε atas" strokeWidth={1} />
          <Line type="monotone" dataKey="lower" stroke="#374151" strokeDasharray="4 2" dot={false} name="ε bawah" strokeWidth={1} />
          {/* Actual & prediction */}
          <Line type="monotone" dataKey="actual" stroke="#3b82f6" dot={false} name="Aktual" strokeWidth={2} />
          <Line type="monotone" dataKey="pred" stroke="#22c55e" dot={false} name="Prediksi SVR" strokeWidth={2} />
        </ComposedChart>
      </ResponsiveContainer>

      <div style={{ marginTop: 12, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <StatCard label="Support Vectors" value={t2.n_support_vectors} />
        <StatCard label="Data Training" value={t2.n_training_samples} />
        <StatCard label="Kernel" value={t2.kernel} />
        <StatCard label="C" value={t2.C} />
        <StatCard label="γ (gamma)" value={t2.gamma} />
        <StatCard label="ε (epsilon)" value={t2.epsilon} />
      </div>
    </div>
  )
}

// ── Tab SARIMA: ACF/PACF chart ────────────────────────────────────────────────
function VisSarima({ t3 }) {
  const acfVals = t3.acf_values || []
  const pacfVals = t3.pacf_values || []
  const lags = t3.acf_lags || acfVals.map((_, i) => i)
  const band = t3.confidence_band || 0

  const acfData = acfVals.map((v, i) => ({
    lag: lags[i] ?? i,
    acf: v,
    significant: Math.abs(v) > band,
  }))

  const pacfData = pacfVals.map((v, i) => ({
    lag: lags[i] ?? i,
    pacf: v,
    significant: Math.abs(v) > band,
  }))

  return (
    <div style={styles.visBox}>
      <h4 style={styles.visTitle}>
        Diagnostik Residual SARIMA {t3.orde}
      </h4>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* ACF */}
        <div>
          <p style={{ ...styles.visDesc, marginBottom: 8 }}>
            Autocorrelation Function (ACF) — batas ±{fmtNum(band, 3)}
          </p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={acfData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
              <XAxis dataKey="lag" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <YAxis domain={[-1, 1]} tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#1e2a3a', border: '1px solid #2d3748', color: '#e2e8f0' }} />
              <ReferenceLine y={band} stroke="#fbbf24" strokeDasharray="4 2" />
              <ReferenceLine y={-band} stroke="#fbbf24" strokeDasharray="4 2" />
              <ReferenceLine y={0} stroke="#94a3b8" />
              <Bar dataKey="acf" name="ACF" fill="#6366f1" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* PACF */}
        <div>
          <p style={{ ...styles.visDesc, marginBottom: 8 }}>
            Partial ACF (PACF) — batas ±{fmtNum(band, 3)}
          </p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={pacfData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
              <XAxis dataKey="lag" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <YAxis domain={[-1, 1]} tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#1e2a3a', border: '1px solid #2d3748', color: '#e2e8f0' }} />
              <ReferenceLine y={band} stroke="#fbbf24" strokeDasharray="4 2" />
              <ReferenceLine y={-band} stroke="#fbbf24" strokeDasharray="4 2" />
              <ReferenceLine y={0} stroke="#94a3b8" />
              <Bar dataKey="pacf" name="PACF" fill="#6366f1" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ marginTop: 16, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <StatCard label="Orde" value={t3.orde} />
        <StatCard label="ADF p-value" value={fmtNum(t3.adf_pvalue, 4)} />
        <StatCard
          label="Stasioner"
          value={t3.adf_stasioner == null ? 'N/A' : t3.adf_stasioner ? 'Ya ✅' : 'Tidak ⚠️'}
        />
        <StatCard label="Ljung-Box p" value={fmtNum(t3.ljung_box_pvalue, 4)} />
      </div>
    </div>
  )
}

// ── Tab ENSEMBLE: Gauge + tabel ───────────────────────────────────────────────
function VisEnsemble({ t4 }) {
  const mapeEnsemble = ((t4.mape_svr ?? 0) * (t4.bobot_svr ?? 0) +
    (t4.mape_sarima ?? 0) * (t4.bobot_sarima ?? 0))

  return (
    <div style={styles.visBox}>
      <h4 style={styles.visTitle}>Bobot Ensemble Adaptif (Inverse MAPE)</h4>

      {/* Gauge */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 48, marginBottom: 20 }}>
        <Gauge nilai={t4.bobot_svr} label="Bobot SVR" warna="#3b82f6" />
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <div style={{ fontSize: 12, color: C.dim, marginBottom: 8 }}>Formula</div>
          <div style={{ fontFamily: 'monospace', fontSize: 12, color: C.purple, maxWidth: 200, wordBreak: 'break-all' }}>
            {t4.formula || 'ŷ = w₁×SVR + w₂×SARIMA'}
          </div>
          <div style={{ marginTop: 12, fontSize: 13, color: C.green, fontWeight: 600 }}>
            {fmtRp(t4.prediksi_ensemble_rp)}
          </div>
        </div>
        <Gauge nilai={t4.bobot_sarima} label="Bobot SARIMA" warna="#22c55e" />
      </div>

      {/* Tabel MAPE */}
      <table style={styles.table}>
        <thead>
          <tr style={{ background: '#1e2a3a' }}>
            <th style={styles.th}>Model</th>
            <th style={styles.th}>MAPE (%)</th>
            <th style={styles.th}>Bobot</th>
            <th style={styles.th}>Kontribusi MAPE</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style={styles.td}>SVR</td>
            <td style={{ ...styles.td, textAlign: 'right' }}>{fmtNum(t4.mape_svr, 4)}</td>
            <td style={{ ...styles.td, textAlign: 'right' }}>{fmtNum(t4.bobot_svr, 4)}</td>
            <td style={{ ...styles.td, textAlign: 'right', color: '#3b82f6' }}>
              {fmtNum((t4.mape_svr ?? 0) * (t4.bobot_svr ?? 0), 4)}
            </td>
          </tr>
          <tr>
            <td style={styles.td}>SARIMA</td>
            <td style={{ ...styles.td, textAlign: 'right' }}>{fmtNum(t4.mape_sarima, 4)}</td>
            <td style={{ ...styles.td, textAlign: 'right' }}>{fmtNum(t4.bobot_sarima, 4)}</td>
            <td style={{ ...styles.td, textAlign: 'right', color: '#22c55e' }}>
              {fmtNum((t4.mape_sarima ?? 0) * (t4.bobot_sarima ?? 0), 4)}
            </td>
          </tr>
          <tr style={{ background: '#1e2a3a', fontWeight: 600 }}>
            <td style={styles.td}>Ensemble</td>
            <td style={{ ...styles.td, textAlign: 'right', color: '#fbbf24' }}>
              {fmtNum(mapeEnsemble, 4)}
            </td>
            <td style={{ ...styles.td, textAlign: 'right' }}>1.0000</td>
            <td style={{ ...styles.td, textAlign: 'right', color: '#fbbf24' }}>
              {fmtNum(mapeEnsemble, 4)}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

// ── Tab KEUANGAN: kartu + formula ─────────────────────────────────────────────
function VisKeuangan({ t5 }) {
  const isPerishable = t5.kategori === 'perishable'

  return (
    <div style={styles.visBox}>
      <h4 style={styles.visTitle}>
        Analisis Keuangan{' '}
        <span style={{
          fontSize: 11,
          padding: '2px 8px',
          borderRadius: 12,
          background: isPerishable ? '#7f1d1d' : '#14532d',
          color: isPerishable ? '#fca5a5' : '#86efac',
          marginLeft: 8,
          fontWeight: 400,
        }}>
          {t5.kategori || 'unknown'}
        </span>
      </h4>

      {/* Kartu keuangan */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
        <KeuCard
          label="Revenue Prediksi"
          value={fmtRp(t5.revenue_rp)}
          color="#3b82f6"
          icon="💰"
        />
        <KeuCard
          label="Modal Beli"
          value={fmtRp(t5.modal_beli_rp)}
          color="#f59e0b"
          icon="🛒"
        />
        <KeuCard
          label="Rugi Susut"
          value={fmtRp(t5.rugi_susut_rp)}
          color={isPerishable ? '#ef4444' : '#6b7280'}
          icon="📉"
        />
      </div>

      {/* Formula susut */}
      <div style={{ background: '#0d1117', borderRadius: 8, padding: '10px 14px', marginBottom: 12 }}>
        <code style={{ fontSize: 12, color: '#93c5fd' }}>
          {t5.rumus_susut || 'Susut: N/A'}
        </code>
      </div>

      {/* Margin ratio */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <StatCard label="Margin Ratio" value={fmtPct(t5.margin_ratio)} />
        <StatCard label="Harga Beli/unit" value={fmtRp(t5.harga_beli)} />
        <StatCard label="Harga Jual/unit" value={fmtRp(t5.harga_jual)} />
      </div>
    </div>
  )
}

// ── Sub-komponen kecil ────────────────────────────────────────────────────────
function StatCard({ label, value }) {
  return (
    <div style={styles.statCard}>
      <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 13, color: '#e2e8f0', fontWeight: 600 }}>
        {value ?? 'N/A'}
      </div>
    </div>
  )
}

function KeuCard({ label, value, color, icon }) {
  return (
    <div style={{ ...styles.keuCard, borderLeft: `3px solid ${color}` }}>
      <div style={{ fontSize: 20, marginBottom: 4 }}>{icon}</div>
      <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 14, color, fontWeight: 700 }}>{value}</div>
    </div>
  )
}

// ── Style object ──────────────────────────────────────────────────────────────
const styles = {
  container: {
    background: '#0f172a',
    borderRadius: 10,
    border: '1px solid #1e293b',
    overflow: 'hidden',
  },
  panelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    background: '#1a1a2e',
    borderBottom: '1px solid #2d3748',
  },
  panelTitle: {
    margin: 0,
    fontSize: 16,
    fontWeight: 700,
    color: '#90caf9',
  },
  panelSubtitle: {
    margin: '4px 0 0',
    fontSize: 12,
    color: '#64748b',
  },
  btnExport: {
    padding: '7px 14px',
    background: '#1e3a5f',
    color: '#90caf9',
    border: '1px solid #2d4a7a',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 500,
  },
  accordion: {
    borderBottom: '1px solid #1e293b',
  },
  accordionHeader: {
    padding: '12px 20px',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    color: '#e2e8f0',
    userSelect: 'none',
  },
  accordionBody: {
    padding: '16px 20px',
    background: '#0d1117',
  },
  tabBar: {
    display: 'flex',
    gap: 4,
    marginBottom: 12,
    borderBottom: '1px solid #1e293b',
    paddingBottom: 0,
    overflowX: 'auto',
  },
  tabBtn: {
    padding: '8px 14px',
    border: 'none',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 500,
    borderRadius: '4px 4px 0 0',
    whiteSpace: 'nowrap',
  },
  terminal: {
    background: '#0d1117',
    color: '#e2e8f0',
    fontFamily: "'Courier New', Consolas, monospace",
    fontSize: 13,
    padding: 16,
    borderRadius: 8,
    maxHeight: 300,
    overflowY: 'auto',
    lineHeight: 1.6,
    border: '1px solid #1e293b',
  },
  btnSkip: {
    position: 'absolute',
    top: 8,
    right: 8,
    padding: '4px 10px',
    background: '#1e2a3a',
    color: '#94a3b8',
    border: '1px solid #2d3748',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
  },
  visBox: {
    marginTop: 16,
    padding: '14px 16px',
    background: '#111827',
    borderRadius: 8,
    border: '1px solid #1e293b',
  },
  visTitle: {
    margin: '0 0 12px',
    fontSize: 14,
    fontWeight: 600,
    color: '#e2e8f0',
  },
  visDesc: {
    margin: '0 0 8px',
    fontSize: 12,
    color: '#64748b',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 13,
    color: '#e2e8f0',
  },
  th: {
    padding: '8px 12px',
    textAlign: 'left',
    fontWeight: 600,
    color: '#94a3b8',
    fontSize: 12,
    borderBottom: '1px solid #2d3748',
  },
  td: {
    padding: '7px 12px',
    color: '#e2e8f0',
    borderBottom: '1px solid #1e293b',
  },
  statCard: {
    background: '#1e2a3a',
    border: '1px solid #2d3748',
    borderRadius: 6,
    padding: '8px 12px',
    minWidth: 100,
  },
  keuCard: {
    background: '#1e2a3a',
    border: '1px solid #2d3748',
    borderRadius: 6,
    padding: '12px 16px',
  },
}
