import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface Props {
  children: React.ReactNode
  adminOnly?: boolean
}

export function ProtectedRoute({ children, adminOnly = false }: Props) {
  const { session, isAdmin, loading } = useAuth()

  if (loading) return <p className="text-gray-400 text-sm p-8">Loading…</p>
  if (!session) return <Navigate to="/auth/login" replace />
  if (adminOnly && !isAdmin) return <Navigate to="/404" replace />

  return <>{children}</>
}
