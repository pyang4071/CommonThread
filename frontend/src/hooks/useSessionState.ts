import { useEffect, useState } from 'react'

/**
 * Like useState, but reads the initial value from sessionStorage and writes
 * back on every change. State is scoped to the browser tab and cleared when
 * the tab closes.
 */
export function useSessionState<T>(key: string, defaultValue: T) {
  const [state, setState] = useState<T>(() => {
    try {
      const stored = sessionStorage.getItem(key)
      return stored !== null ? (JSON.parse(stored) as T) : defaultValue
    } catch {
      return defaultValue
    }
  })

  useEffect(() => {
    try {
      sessionStorage.setItem(key, JSON.stringify(state))
    } catch {
      // storage quota exceeded or private browsing — fail silently
    }
  }, [key, state])

  return [state, setState] as const
}
