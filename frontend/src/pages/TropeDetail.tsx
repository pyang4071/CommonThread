import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Book, Trope } from '../api/client'

const CATEGORY_COLORS: Record<string, string> = {
  Romance: 'bg-pink-100 text-pink-700',
  Fantasy: 'bg-purple-100 text-purple-700',
  Character: 'bg-blue-100 text-blue-700',
  Narrative: 'bg-amber-100 text-amber-700',
  Setting: 'bg-green-100 text-green-700',
}

function WeightBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 80 ? 'bg-indigo-500' : pct >= 50 ? 'bg-indigo-300' : 'bg-indigo-200'
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400 w-7 text-right">{pct}%</span>
    </div>
  )
}

export function TropeDetail() {
  const { id } = useParams<{ id: string }>()
  const [trope, setTrope] = useState<Trope | null>(null)
  const [books, setBooks] = useState<(Book & { weight: number })[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    document.title = trope ? `${trope.name} · Tropes — CommonThread` : 'Tropes — CommonThread'
  }, [trope])

  useEffect(() => {
    if (!id) return
    const tropeId = Number(id)
    Promise.all([
      api.tropes.get(tropeId),
      api.tropes.books(tropeId),
    ])
      .then(([t, b]) => { setTrope(t); setBooks(b) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return (
    <div className="space-y-6 animate-pulse">
      <div className="h-4 w-20 bg-gray-200 rounded" />
      <div className="h-8 w-64 bg-gray-200 rounded" />
      <div className="h-4 w-full bg-gray-200 rounded" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-white border border-gray-200 rounded-lg p-4 flex gap-3">
            <div className="w-10 h-14 bg-gray-200 rounded shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-3/4 bg-gray-200 rounded" />
              <div className="h-3 w-1/2 bg-gray-200 rounded" />
              <div className="h-1.5 w-full bg-gray-200 rounded-full" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
  if (error) return <p className="text-red-500 text-sm">{error}</p>
  if (!trope) return null

  const badgeClass = CATEGORY_COLORS[trope.category] ?? 'bg-gray-100 text-gray-600'

  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-1.5 text-sm text-gray-400">
        <Link to="/tropes" className="text-indigo-600 hover:underline">Tropes</Link>
        <span>›</span>
        <span className="text-gray-600 truncate">{trope.name}</span>
      </nav>

      <div>
        <div className="flex items-center gap-3 mb-1">
          <h1 className="text-2xl font-bold text-gray-900">{trope.name}</h1>
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${badgeClass}`}>
            {trope.category}
          </span>
        </div>
        {trope.description && (
          <p className="text-sm text-gray-500 max-w-2xl">{trope.description}</p>
        )}
        <p className="text-sm text-gray-400 mt-2">
          {books.length} book{books.length !== 1 ? 's' : ''} · sorted by weight
        </p>
      </div>

      {books.length === 0 ? (
        <p className="text-gray-400 text-sm">No books tagged with this trope yet.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {books.map(book => (
            <Link
              key={book.book_id}
              to={`/books/${book.book_id}`}
              className="bg-white border border-gray-200 rounded-lg p-4 hover:border-indigo-300 hover:shadow-sm transition-all flex gap-3"
            >
              {book.cover_url ? (
                <img src={book.cover_url} alt="" className="w-10 h-14 object-cover rounded shrink-0 self-start" />
              ) : (
                <div className="w-10 h-14 bg-gray-100 rounded shrink-0 flex items-center justify-center text-xl select-none">📖</div>
              )}
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-800 text-sm leading-snug truncate">{book.title}</p>
                <p className="text-xs text-gray-500 mt-0.5 truncate">{book.author.name}</p>
                <WeightBar value={book.weight} />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
