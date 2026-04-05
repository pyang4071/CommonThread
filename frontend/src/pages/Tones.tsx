import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Tone } from '../api/client'
import { Table } from '../components/Table'
import { useAuth } from '../contexts/AuthContext'

export function Tones() {
  const { isAdmin } = useAuth()
  const [tones, setTones] = useState<Tone[]>([])
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () =>
    api.tones.list().then(setTones).catch((e) => setError(e.message)).finally(() => setLoading(false))

  useEffect(() => { load() }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.tones.create(name)
    setName('')
    load()
  }

  const remove = async (tone: Tone) => {
    await api.tones.delete(tone.tone_id)
    load()
  }

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

      {loading && <p className="text-gray-400 text-sm">Loading…</p>}
      {error && <p className="text-red-500 text-sm">{error}</p>}

      <Table
        data={tones}
        rowKey={(t) => t.tone_id}
        onDelete={isAdmin ? remove : undefined}
        deleteLabel={(t) => t.name}
        columns={[
          { header: 'ID', accessor: (t) => t.tone_id },
          { header: 'Name', accessor: (t) => t.name },
        ]}
      />
    </div>
  )
}
