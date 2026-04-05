import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'

export type StatusValue = 'want_to_read' | 'currently_reading' | 'read'

const STATUS_CONFIG: Record<StatusValue, { label: string; icon: string; chip: string; hover: string }> = {
  want_to_read: {
    label: 'Want to Read',
    icon: '🔖',
    chip: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    hover: 'hover:bg-indigo-100',
  },
  currently_reading: {
    label: 'Reading',
    icon: '📖',
    chip: 'bg-amber-50 text-amber-700 border-amber-200',
    hover: 'hover:bg-amber-100',
  },
  read: {
    label: 'Read',
    icon: '✓',
    chip: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    hover: 'hover:bg-emerald-100',
  },
}

const ALL_STATUSES = Object.entries(STATUS_CONFIG) as [StatusValue, (typeof STATUS_CONFIG)[StatusValue]][]

interface Props {
  bookId: number
  token: string
  initial?: StatusValue | null
  onChange?: (status: StatusValue | null) => void
}

export function ReadingStatusButton({ bookId, token, initial = null, onChange }: Props) {
  const [status, setStatus] = useState<StatusValue | null>(initial)
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => { if (initial != null) setStatus(initial) }, [initial])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const apply = async (next: StatusValue | null) => {
    setOpen(false)
    const prev = status
    setStatus(next)
    onChange?.(next)
    try {
      if (next === null) {
        await api.shelf.remove(bookId, token)
      } else {
        await api.shelf.set(bookId, next, token)
      }
    } catch {
      setStatus(prev)
      onChange?.(prev)
    }
  }

  const cfg = status ? STATUS_CONFIG[status] : null

  return (
    <div ref={ref} className="relative inline-block">
      {/* Trigger button */}
      {cfg ? (
        <button
          onClick={() => setOpen(o => !o)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${cfg.chip} ${cfg.hover}`}
        >
          <span>{cfg.icon}</span>
          <span>{cfg.label}</span>
          <span className="text-xs opacity-50">▾</span>
        </button>
      ) : (
        <button
          onClick={() => setOpen(o => !o)}
          className="px-3 py-1.5 rounded-full text-sm font-medium text-gray-500 border border-dashed border-gray-300 hover:border-gray-400 hover:text-gray-700 transition-colors"
        >
          + Add to shelf
        </button>
      )}

      {/* Dropdown */}
      {open && (
        <div className="absolute left-0 mt-1 z-30 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[170px]">
          {ALL_STATUSES.map(([val, c]) => (
            <button
              key={val}
              onClick={() => apply(val)}
              className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2 transition-colors ${
                val === status
                  ? `font-semibold ${c.chip}`
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <span>{c.icon}</span>
              {c.label}
              {val === status && <span className="ml-auto text-xs">✓</span>}
            </button>
          ))}
          {status && (
            <div className="border-t border-gray-100 mt-1 pt-1">
              <button
                onClick={() => apply(null)}
                className="w-full text-left px-3 py-2 text-sm text-gray-400 hover:bg-gray-50 hover:text-gray-600 transition-colors"
              >
                Remove from shelf
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
