import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { BookType } from '../api/client'
import { ConfirmModal } from '../components/ConfirmModal'
import { useAuth } from '../contexts/AuthContext'

const EMPTY = { name: '', description: '' }

export function BookTypes() {
  const { isAdmin, session } = useAuth()
  const [bookTypes, setBookTypes] = useState<BookType[]>([])
  const [form, setForm] = useState(EMPTY)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [toDelete, setToDelete] = useState<BookType | null>(null)

  const load = () =>
    api.bookTypes.list().then(setBookTypes).catch((e) => setError(e.message)).finally(() => setLoading(false))

  useEffect(() => { load() }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.bookTypes.create({ name: form.name, description: form.description || null }, session!.access_token)
    setForm(EMPTY)
    load()
  }

  const confirmDelete = async () => {
    if (!toDelete) return
    await api.bookTypes.delete(toDelete.book_type_id, session!.access_token)
    setToDelete(null)
    load()
  }

  const filtered = search.trim()
    ? bookTypes.filter(bt =>
        bt.name.toLowerCase().includes(search.toLowerCase()) ||
        (bt.description ?? '').toLowerCase().includes(search.toLowerCase())
      )
    : bookTypes

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-800">Book Types</h1>

      {isAdmin && (
        <form onSubmit={submit} className="grid grid-cols-2 gap-3 bg-gray-50 p-4 rounded-lg border border-gray-200">
          <input required placeholder="Name" value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
          <input placeholder="Description (optional)" value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
          <button type="submit"
            className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700">
            Add Book Type
          </button>
        </form>
      )}

      <input
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Search book types…"
        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
      />

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-12 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-gray-400">{search ? `No book types match "${search}".` : 'No book types yet.'}</p>
      ) : (
        <div className="space-y-1">
          {filtered.map(bt => (
            <div key={bt.book_type_id} className="flex items-center gap-3 px-4 py-3 bg-white border border-gray-200 rounded-lg">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800">{bt.name}</p>
                {bt.description && <p className="text-xs text-gray-400 truncate">{bt.description}</p>}
              </div>
              <span className="text-xs text-gray-300">#{bt.book_type_id}</span>
              {isAdmin && (
                <button
                  onClick={() => setToDelete(bt)}
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
          message="This will permanently remove the book type. Books tagged with it will lose this association."
          confirmLabel="Delete"
          onConfirm={confirmDelete}
          onCancel={() => setToDelete(null)}
        />
      )}
    </div>
  )
}
