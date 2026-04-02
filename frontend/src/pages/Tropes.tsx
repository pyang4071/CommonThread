import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Trope } from '../api/client'
import { Table } from '../components/Table'
import { useAuth } from '../contexts/AuthContext'

const EMPTY = { name: '', description: '', category: '' }

export function Tropes() {
  const { isAdmin } = useAuth()
  const [tropes, setTropes] = useState<Trope[]>([])
  const [form, setForm] = useState(EMPTY)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

      {loading && <p className="text-gray-400 text-sm">Loading…</p>}
      {error && <p className="text-red-500 text-sm">{error}</p>}

      <Table
        data={tropes}
        onDelete={isAdmin ? remove : undefined}
        deleteLabel={(t) => t.name}
        columns={[
          { header: 'ID', accessor: (t) => t.trope_id },
          { header: 'Name', accessor: (t) => t.name },
          { header: 'Category', accessor: (t) => t.category },
          { header: 'Description', accessor: (t) => t.description },
        ]}
      />
    </div>
  )
}
