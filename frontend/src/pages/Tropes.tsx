import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Trope } from '../api/client'
import { ConfirmModal } from '../components/ConfirmModal'
import { useAuth } from '../contexts/AuthContext'

const EMPTY = { name: '', description: '', category: '' }

const CATEGORY_COLORS: Record<string, string> = {
  Romance: 'bg-pink-100 text-pink-700',
  Fantasy: 'bg-purple-100 text-purple-700',
  Character: 'bg-blue-100 text-blue-700',
  Narrative: 'bg-amber-100 text-amber-700',
  Setting: 'bg-green-100 text-green-700',
}

export function Tropes() {
  const { isAdmin } = useAuth()
  const [tropes, setTropes] = useState<Trope[]>([])
  const [form, setForm] = useState(EMPTY)
  useEffect(() => { document.title = 'Tropes — CommonThread' }, [])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [tropeToDelete, setTropeToDelete] = useState<Trope | null>(null)

  const load = () =>
    api.tropes.list().then(setTropes).catch((e) => setError(e.message)).finally(() => setLoading(false))

  useEffect(() => { load() }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.tropes.create({
      name: form.name,
      description: form.description || null,
      category: form.category,
    })
    setForm(EMPTY)
    load()
  }

  const remove = async (trope: Trope) => {
    await api.tropes.delete(trope.trope_id)
    load()
  }

  const categories = Array.from(new Set(tropes.map(t => t.category))).sort()

  const filtered = tropes.filter(t => {
    const matchesQuery = !query.trim() || t.name.toLowerCase().includes(query.toLowerCase()) || (t.description ?? '').toLowerCase().includes(query.toLowerCase())
    const matchesCategory = !categoryFilter || t.category === categoryFilter
    return matchesQuery && matchesCategory
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-800">Tropes</h1>

      {isAdmin && (
        <form onSubmit={submit} className="grid grid-cols-2 gap-3 bg-gray-50 p-4 rounded-lg border border-gray-200">
          <input required placeholder="Name" value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
          <input required placeholder="Category" value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
          <input placeholder="Description" value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="col-span-2 px-3 py-2 border border-gray-300 rounded-md text-sm" />
          <button type="submit"
            className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700">
            Add Trope
          </button>
        </form>
      )}

      {/* Search + filter */}
      <div className="flex flex-wrap gap-3 items-center">
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search tropes…"
          className="flex-1 min-w-48 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
        <select
          value={categoryFilter}
          onChange={e => setCategoryFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300"
        >
          <option value="">All categories</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        {(query || categoryFilter) && (
          <button onClick={() => { setQuery(''); setCategoryFilter('') }}
            className="text-sm text-gray-400 hover:text-gray-600">
            Clear
          </button>
        )}
        {!loading && (
          <span className="text-sm text-gray-400">{filtered.length} trope{filtered.length !== 1 ? 's' : ''}</span>
        )}
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-lg p-4 animate-pulse space-y-2">
              <div className="h-4 w-2/3 bg-gray-200 rounded" />
              <div className="h-3 w-1/3 bg-gray-200 rounded" />
              <div className="h-3 w-full bg-gray-200 rounded" />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-gray-400 text-sm">No tropes match your search.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(trope => {
            const badgeClass = CATEGORY_COLORS[trope.category] ?? 'bg-gray-100 text-gray-600'
            return (
              <div key={trope.trope_id} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-indigo-300 hover:shadow-sm transition-all flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <Link
                    to={`/tropes/${trope.trope_id}`}
                    className="font-medium text-gray-800 hover:text-indigo-600 transition-colors text-sm leading-snug"
                  >
                    {trope.name}
                  </Link>
                  <span className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${badgeClass}`}>
                    {trope.category}
                  </span>
                </div>
                {trope.description && (
                  <p className="text-xs text-gray-500 line-clamp-2">{trope.description}</p>
                )}
                {isAdmin && (
                  <div className="mt-auto pt-1 flex justify-end">
                    <button
                      onClick={() => setTropeToDelete(trope)}
                      className="text-xs text-gray-400 hover:text-red-500 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
      {tropeToDelete && (
        <ConfirmModal
          title="Delete trope"
          message={`Delete "${tropeToDelete.name}"? This will remove it from all books and trigger re-embedding.`}
          confirmLabel="Delete"
          onConfirm={() => { remove(tropeToDelete); setTropeToDelete(null) }}
          onCancel={() => setTropeToDelete(null)}
        />
      )}
    </div>
  )
}
