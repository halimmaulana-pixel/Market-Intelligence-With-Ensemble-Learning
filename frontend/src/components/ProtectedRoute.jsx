/**
 * components/ProtectedRoute.jsx — Guard route berdasarkan autentikasi dan role.
 */
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * @param {string[]} [roles] — Jika diisi, hanya role yang disebutkan yang boleh akses.
 */
export default function ProtectedRoute({ children, roles }) {
  const { user } = useAuth()
  const location = useLocation()

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />
  }

  return children
}
