import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Archetype } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

const EMPTY = { name: '', description: '' }

export function Archetypes() {
  const { isAdmin, session } = useAuth()
  const [archetypes, setArchetypes] = useState<Archetype[]>([])
  const [form, setForm] = useState(EMPTY)
  useEffect(() => { document.title = 'Archetypes — CommonThread' }, [])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  const load = () =>
    api.archetypes.list().then(setArchetypes).catch((e) => setError(e.message)).finally(() => setLoading(false))

  useEffect(() => { load() }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.archetypes.create({
      name: form.name,
      description: form.description || null,
    }, session!.access_token)
    setForm(EMPTY)
    load()
  }

  const remove = async (arch: Archetype) => {
    await api.archetypes.delete(arch.archetype_id, session!.access_token)
    load()
  }

  const filtered = archetypes.filter(a =>
    !query.trim() ||
    a.name.toLowerCase().includes(query.toLowerCase()) ||
    (a.description ?? '').toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-800">Archetypes</h1>

      {isAdmin && (
        <form onSubmit={submit} className="grid grid-cols-2 gap-3 bg-gray-50 p-4 rounded-lg border border-gray-200">
          <input required placeholder="Name" value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
          <input placeholder="Description" value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
          <button type="submit"
            className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700">
            Add Archetype
          </button>
        </form>
      )}

      {/* Search */}
      <div className="flex flex-wrap gap-3 items-center">
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search archetypes…"
          className="flex-1 min-w-48 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
        {query && (
          <button onClick={() => setQuery('')}
            className="text-sm text-gray-400 hover:text-gray-600">
            Clear
          </button>
        )}
        {!loading && (
          <span className="text-sm text-gray-400">{filtered.length} archetype{filtered.length !== 1 ? 's' : ''}</span>
        )}
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-lg p-4 animate-pulse space-y-2">
              <div className="h-4 w-2/3 bg-gray-200 rounded" />
              <div className="h-3 w-full bg-gray-200 rounded" />
              <div className="h-3 w-4/5 bg-gray-200 rounded" />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-gray-400 text-sm">No archetypes match your search.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(arch => (
            <div key={arch.archetype_id} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-indigo-300 hover:shadow-sm transition-all flex flex-col gap-2">
              <Link
                to={`/archetypes/${arch.archetype_id}`}
                className="font-medium text-gray-800 hover:text-indigo-600 transition-colors text-sm leading-snug"
              >
                {arch.name}
              </Link>
              {arch.description && (
                <p className="text-xs text-gray-500 line-clamp-2">{arch.description}</p>
              )}
              {isAdmin && (
                <div className="mt-auto pt-1 flex justify-end">
                  <button
                    onClick={() => remove(arch)}
                    className="text-xs text-gray-400 hover:text-red-500 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
