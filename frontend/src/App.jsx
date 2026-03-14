/**
 * App.jsx — Routing utama aplikasi SalSa Market.
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'

import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import PrediksiPage from './pages/PrediksiPage'
import AlokasiPage from './pages/AlokasiPage'
import HistoriPage from './pages/HistoriPage'
import ProdukPage from './pages/ProdukPage'
import ModelConfigPage from './pages/ModelConfigPage'
import PenggunaPage from './pages/PenggunaPage'
import UnauthorizedPage from './pages/UnauthorizedPage'

function AppRoutes() {
  return (
    <Routes>
      {/* Publik */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* Semua role yang login */}
      <Route path="/dashboard" element={
        <ProtectedRoute><Layout><DashboardPage /></Layout></ProtectedRoute>
      } />
      <Route path="/prediksi" element={
        <ProtectedRoute><Layout><ErrorBoundary><PrediksiPage /></ErrorBoundary></Layout></ProtectedRoute>
      } />
      <Route path="/alokasi" element={
        <ProtectedRoute><Layout><AlokasiPage /></Layout></ProtectedRoute>
      } />
      <Route path="/histori" element={
        <ProtectedRoute><Layout><HistoriPage /></Layout></ProtectedRoute>
      } />

      {/* Admin + Peneliti */}
      <Route path="/produk" element={
        <ProtectedRoute roles={['admin', 'peneliti']}>
          <Layout><ProdukPage /></Layout>
        </ProtectedRoute>
      } />

      {/* Peneliti only */}
      <Route path="/model-config" element={
        <ProtectedRoute roles={['peneliti']}>
          <Layout><ModelConfigPage /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/pengguna" element={
        <ProtectedRoute roles={['peneliti']}>
          <Layout><PenggunaPage /></Layout>
        </ProtectedRoute>
      } />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: { fontSize: 14, borderRadius: 8 },
          }}
        />
      </AuthProvider>
    </BrowserRouter>
  )
}
