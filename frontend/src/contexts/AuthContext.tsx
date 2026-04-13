import { createContext, useCallback, useContext, useEffect, useState } from 'react'
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
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  useEffect(() => {
    if (!session) { setProfile(null); return }
    api.users.me(session.access_token).then(setProfile).catch(() => {})
  }, [session])

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
