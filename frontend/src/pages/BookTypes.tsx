import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { BookType } from '../api/client'
import { Table } from '../components/Table'
import { useAuth } from '../contexts/AuthContext'

const EMPTY = { name: '', description: '' }

export function BookTypes() {
  const { isAdmin } = useAuth()
  const [bookTypes, setBookTypes] = useState<BookType[]>([])
  const [form, setForm] = useState(EMPTY)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () =>
    api.bookTypes.list().then(setBookTypes).catch((e) => setError(e.message)).finally(() => setLoading(false))

  useEffect(() => { load() }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.bookTypes.create({ name: form.name, description: form.description || null })
    setForm(EMPTY)
    load()
  }

  const remove = async (bt: BookType) => {
    await api.bookTypes.delete(bt.book_type_id)
    load()
  }

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

      {loading && <p className="text-gray-400 text-sm">Loading…</p>}
      {error && <p className="text-red-500 text-sm">{error}</p>}

      <Table
        data={bookTypes}
        onDelete={isAdmin ? remove : undefined}
        deleteLabel={(bt) => bt.name}
        columns={[
          { header: 'ID', accessor: (bt) => bt.book_type_id },
          { header: 'Name', accessor: (bt) => bt.name },
          { header: 'Description', accessor: (bt) => bt.description },
        ]}
      />
    </div>
  )
}
