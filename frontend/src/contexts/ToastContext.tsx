import { createContext, useCallback, useContext, useRef, useState } from 'react'

// ── types ─────────────────────────────────────────────────────────────────────

type ToastType = 'success' | 'error'

interface ToastItem {
  id: string
  type: ToastType
  message: string
}

interface ToastContextType {
  toast: {
    success: (message: string) => void
    error: (message: string) => void
  }
}

// ── context ───────────────────────────────────────────────────────────────────

const ToastContext = createContext<ToastContextType | undefined>(undefined)

// ── Toaster component (renders the visible toasts) ────────────────────────────

function Toaster({ toasts, onDismiss }: { toasts: ToastItem[]; onDismiss: (id: string) => void }) {
  if (toasts.length === 0) return null
  return (
    <div className="fixed bottom-5 right-5 z-[9999] flex flex-col gap-2 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-lg shadow-lg text-sm font-medium max-w-sm w-full transition-all ${
            t.type === 'success'
              ? 'bg-emerald-600 text-white'
              : 'bg-red-600 text-white'
          }`}
        >
          <span className="mt-px shrink-0">
            {t.type === 'success' ? '✓' : '✕'}
          </span>
          <span className="flex-1 leading-snug">{t.message}</span>
          <button
            onClick={() => onDismiss(t.id)}
            className="shrink-0 opacity-70 hover:opacity-100 text-lg leading-none mt-[-1px]"
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}

// ── provider ──────────────────────────────────────────────────────────────────

let _nextId = 0

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

  const dismiss = useCallback((id: string) => {
    clearTimeout(timers.current[id])
    delete timers.current[id]
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const add = useCallback((type: ToastType, message: string) => {
    const id = String(++_nextId)
    setToasts(prev => [...prev, { id, type, message }])
    // success dismisses after 3 s, error after 5 s
    timers.current[id] = setTimeout(() => dismiss(id), type === 'success' ? 3000 : 5000)
  }, [dismiss])

  const toast = {
    success: (message: string) => add('success', message),
    error: (message: string) => add('error', message),
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <Toaster toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  )
}

// ── hook ──────────────────────────────────────────────────────────────────────

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx.toast
}
