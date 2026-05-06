import { useEffect, useState } from 'react'
import { Link, useParams, useLocation } from 'react-router-dom'
import { api } from '../api/client'
import type { Archetype, Book } from '../api/client'

function ImportanceDots({ value }: { value: number }) {
  return (
    <div className="flex gap-0.5 mt-1">
      {Array.from({ length: 10 }).map((_, i) => (
        <div key={i} className={`w-2 h-2 rounded-full ${i < value ? 'bg-indigo-500' : 'bg-gray-200'}`} />
      ))}
    </div>
  )
}

export function ArchetypeDetail() {
  const { id } = useParams<{ id: string }>()
  const { pathname } = useLocation()
  const [archetype, setArchetype] = useState<Archetype | null>(null)
  const [books, setBooks] = useState<(Book & { importance: number })[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    document.title = archetype ? `${archetype.name} · Archetypes — CommonThread` : 'Archetypes — CommonThread'
  }, [archetype])

  useEffect(() => {
    if (!id) return
    const archetypeId = Number(id)
    Promise.all([
      api.archetypes.get(archetypeId),
      api.archetypes.books(archetypeId),
    ])
      .then(([a, b]) => { setArchetype(a); setBooks(b) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return (
    <div className="space-y-6 animate-pulse">
      <div className="h-4 w-24 bg-gray-200 rounded" />
      <div className="h-8 w-64 bg-gray-200 rounded" />
      <div className="h-4 w-full bg-gray-200 rounded" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-white border border-gray-200 rounded-lg p-4 flex gap-3">
            <div className="w-10 h-14 bg-gray-200 rounded shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-3/4 bg-gray-200 rounded" />
              <div className="h-3 w-1/2 bg-gray-200 rounded" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
  if (error) return <p className="text-red-500 text-sm">{error}</p>
  if (!archetype) return null

  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-1.5 text-sm text-gray-400">
        <Link to="/archetypes" className="text-indigo-600 hover:underline">Archetypes</Link>
        <span>›</span>
        <span className="text-gray-600 truncate">{archetype.name}</span>
      </nav>

      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-1">{archetype.name}</h1>
        {archetype.description && (
          <p className="text-sm text-gray-500 max-w-2xl">{archetype.description}</p>
        )}
        <p className="text-sm text-gray-400 mt-2">
          {books.length} book{books.length !== 1 ? 's' : ''} · sorted by importance
        </p>
      </div>

      {books.length === 0 ? (
        <p className="text-gray-400 text-sm">No books tagged with this archetype yet.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {books.map(book => (
            <Link
              key={book.book_id}
              to={`/books/${book.book_id}`}
              state={{ from: pathname, fromLabel: archetype.name }}
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
                <div className="flex items-center gap-2 mt-1">
                  <ImportanceDots value={book.importance} />
                  <span className="text-xs text-gray-400">{book.importance}/10</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
