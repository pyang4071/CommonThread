import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'
import { api } from '../api/client'
import type { AppUser, UserPreferences } from '../api/client'

interface AuthContextType {
  session: Session | null
  user: User | null
  profile: AppUser | null
  isAdmin: boolean
  loading: boolean
  signOut: () => Promise<void>
  updateProfile: (data: { name?: string | null; preferences?: UserPreferences }) => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<AppUser | null>(null)
  // loading stays true until BOTH the session check AND the initial profile fetch complete.
  // This prevents ProtectedRoute from seeing isAdmin=false during the async profile fetch.
  const [loading, setLoading] = useState(true)
  // Track whether the initial getSession() load is done so the onAuthStateChange
  // listener doesn't re-fetch redundantly on the very first event.
  const initializedRef = useRef(false)

  useEffect(() => {
    // Step 1: resolve session + profile together, then unlock loading.
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      setSession(session)
      if (session) {
        try {
          const p = await api.users.me(session.access_token)
          setProfile(p)
        } catch {
          setProfile(null)
        }
      }
      initializedRef.current = true
      setLoading(false)
    })

    // Step 2: keep profile in sync on subsequent auth changes (login, logout, token refresh).
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
      // Skip the very first event — getSession() already handled it above.
      if (!initializedRef.current) return

      setSession(session)
      if (!session) {
        setProfile(null)
        return
      }
      try {
        const p = await api.users.me(session.access_token)
        setProfile(p)
      } catch {
        setProfile(null)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  const signOut = async () => {
    await supabase.auth.signOut()
  }

  const updateProfile = useCallback(async (data: { name?: string | null; preferences?: UserPreferences }) => {
    if (!session) return
    const updated = await api.users.updateMe(session.access_token, data)
    setProfile(updated)
  }, [session])

  return (
    <AuthContext.Provider value={{
      session,
      user: session?.user ?? null,
      profile,
      isAdmin: profile?.is_admin ?? false,
      loading,
      signOut,
      updateProfile,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
