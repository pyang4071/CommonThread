import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Tone } from '../api/client'
import { ConfirmModal } from '../components/ConfirmModal'
import { useAuth } from '../contexts/AuthContext'

export function Tones() {
  const { isAdmin, session } = useAuth()
  const [tones, setTones] = useState<Tone[]>([])
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [toDelete, setToDelete] = useState<Tone | null>(null)

  const load = () =>
    api.tones.list().then(setTones).catch((e) => setError(e.message)).finally(() => setLoading(false))

  useEffect(() => { load() }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.tones.create(name, session!.access_token)
    setName('')
    load()
  }

  const confirmDelete = async () => {
    if (!toDelete) return
    await api.tones.delete(toDelete.tone_id, session!.access_token)
    setToDelete(null)
    load()
  }

  const filtered = search.trim()
    ? tones.filter(t => t.name.toLowerCase().includes(search.toLowerCase()))
    : tones

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-800">Tones</h1>

      {isAdmin && (
        <form onSubmit={submit} className="flex gap-3 bg-gray-50 p-4 rounded-lg border border-gray-200">
          <input required placeholder="Name" value={name}
            onChange={(e) => setName(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm" />
          <button type="submit"
            className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700">
            Add Tone
          </button>
        </form>
      )}

      <input
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Search tones…"
        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
      />

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-10 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-gray-400">{search ? `No tones match "${search}".` : 'No tones yet.'}</p>
      ) : (
        <div className="space-y-1">
          {filtered.map(t => (
            <div key={t.tone_id} className="flex items-center gap-3 px-4 py-3 bg-white border border-gray-200 rounded-lg">
              <p className="text-sm font-medium text-gray-800 flex-1">{t.name}</p>
              <span className="text-xs text-gray-300">#{t.tone_id}</span>
              {isAdmin && (
                <button
                  onClick={() => setToDelete(t)}
                  className="text-xs text-red-400 hover:text-red-600 transition-colors shrink-0"
                >
                  Delete
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {toDelete && (
        <ConfirmModal
          title={`Delete "${toDelete.name}"?`}
          message="This will permanently remove the tone. Books tagged with it will lose this association."
          confirmLabel="Delete"
          onConfirm={confirmDelete}
          onCancel={() => setToDelete(null)}
        />
      )}
    </div>
  )
}
