import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { session, loading } = useAuth()

  if (loading) return <p className="text-gray-400 text-sm p-8">Loading…</p>
  if (!session) return <Navigate to="/auth/login" replace />

  return <>{children}</>
}
