import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { BookTagsEntry } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

function WeightBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 80 ? 'bg-indigo-500' : pct >= 50 ? 'bg-indigo-300' : 'bg-indigo-200'
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400">{pct}%</span>
    </div>
  )
}

function TagCard({ entry, onRemoveTrope, onRemoveArchetype, token }: {
  entry: BookTagsEntry
  token: string
  onRemoveTrope: (bookId: number, tropeId: number) => void
  onRemoveArchetype: (bookId: number, archetypeId: number) => void
}) {
  const { book, tropes, archetypes } = entry
  const sorted_tropes = [...tropes].sort((a, b) => b.weight - a.weight)
  const sorted_archetypes = [...archetypes].sort((a, b) => b.importance - a.importance)

  const handleRemoveTrope = async (tropeId: number) => {
    await api.myTags.removeTrope(book.book_id, tropeId, token)
    onRemoveTrope(book.book_id, tropeId)
  }

  const handleRemoveArchetype = async (archetypeId: number) => {
    await api.myTags.removeArchetype(book.book_id, archetypeId, token)
    onRemoveArchetype(book.book_id, archetypeId)
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      {/* Book header */}
      <div className="flex gap-4 p-4 border-b border-gray-100">
        {book.cover_url ? (
          <img
            src={book.cover_url}
            alt={`Cover of ${book.title}`}
            className="w-12 h-16 object-cover rounded shadow-sm shrink-0"
          />
        ) : (
          <div className="w-12 h-16 bg-gray-100 rounded shadow-sm flex items-center justify-center text-xl shrink-0 select-none">
            📖
          </div>
        )}
        <div className="min-w-0">
          <Link
            to={`/books/${book.book_id}`}
            className="font-semibold text-gray-800 hover:text-indigo-600 transition-colors line-clamp-2 leading-snug"
          >
            {book.title}
          </Link>
          <p className="text-sm text-gray-500 mt-0.5">{book.author.name}</p>
          <p className="text-xs text-gray-400 mt-1">
            {tropes.length + archetypes.length} personal tag{tropes.length + archetypes.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {/* Tags */}
      <div className="p-4 space-y-3">
        {sorted_tropes.map(({ trope, weight }) => (
          <div key={trope.trope_id} className="flex items-center gap-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700 truncate">{trope.name}</p>
              <WeightBar value={weight} />
            </div>
            <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 shrink-0">
              trope
            </span>
            <button
              onClick={() => handleRemoveTrope(trope.trope_id)}
              className="text-gray-300 hover:text-red-500 transition-colors text-xs shrink-0"
              title="Remove tag"
            >
              ✕
            </button>
          </div>
        ))}
        {sorted_archetypes.map(({ archetype, importance }) => (
          <div key={archetype.archetype_id} className="flex items-center gap-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700 truncate">{archetype.name}</p>
              <div className="flex gap-0.5 mt-0.5">
                {Array.from({ length: 10 }).map((_, i) => (
                  <div
                    key={i}
                    className={`w-1.5 h-1.5 rounded-full ${i < importance ? 'bg-indigo-400' : 'bg-gray-100'}`}
                  />
                ))}
                <span className="text-xs text-gray-400 ml-1">{importance}/10</span>
              </div>
            </div>
            <span className="text-xs px-1.5 py-0.5 rounded bg-purple-50 text-purple-600 shrink-0">
              archetype
            </span>
            <button
              onClick={() => handleRemoveArchetype(archetype.archetype_id)}
              className="text-gray-300 hover:text-red-500 transition-colors text-xs shrink-0"
              title="Remove tag"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

export function MyTags() {
  const { session } = useAuth()
  const [entries, setEntries] = useState<BookTagsEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!session) return
    api.users.myTags(session.access_token)
      .then(setEntries)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [session])

  const handleRemoveTrope = (bookId: number, tropeId: number) => {
    setEntries(prev =>
      prev
        .map(e =>
          e.book.book_id === bookId
            ? { ...e, tropes: e.tropes.filter(t => t.trope.trope_id !== tropeId) }
            : e
        )
        .filter(e => e.tropes.length > 0 || e.archetypes.length > 0)
    )
  }

  const handleRemoveArchetype = (bookId: number, archetypeId: number) => {
    setEntries(prev =>
      prev
        .map(e =>
          e.book.book_id === bookId
            ? { ...e, archetypes: e.archetypes.filter(a => a.archetype.archetype_id !== archetypeId) }
            : e
        )
        .filter(e => e.tropes.length > 0 || e.archetypes.length > 0)
    )
  }

  const totalTags = entries.reduce((sum, e) => sum + e.tropes.length + e.archetypes.length, 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">My Tags</h1>
        {!loading && (
          <p className="text-sm text-gray-500 mt-1">
            {totalTags === 0
              ? 'No personal tags yet.'
              : `${totalTags} tag${totalTags !== 1 ? 's' : ''} across ${entries.length} book${entries.length !== 1 ? 's' : ''} — shaping your recommendations`}
          </p>
        )}
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-xl p-4 animate-pulse space-y-3">
              <div className="flex gap-3">
                <div className="w-12 h-16 bg-gray-200 rounded" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-3/4" />
                  <div className="h-3 bg-gray-200 rounded w-1/2" />
                </div>
              </div>
              <div className="h-3 bg-gray-200 rounded w-full" />
              <div className="h-3 bg-gray-200 rounded w-5/6" />
            </div>
          ))}
        </div>
      ) : entries.length === 0 ? (
        <div className="bg-white border border-dashed border-gray-300 rounded-xl p-12 text-center">
          <p className="text-gray-400 text-sm mb-3">
            You haven't added any personal tags yet.
          </p>
          <p className="text-gray-400 text-xs mb-4">
            Open any book and use the "Your Tags" section to tag the tropes and archetypes
            you see in it — this personalizes your recommendations.
          </p>
          <Link to="/books" className="text-sm text-indigo-600 hover:underline">
            Browse books →
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {entries.map(entry => (
            <TagCard
              key={entry.book.book_id}
              entry={entry}
              token={session!.access_token}
              onRemoveTrope={handleRemoveTrope}
              onRemoveArchetype={handleRemoveArchetype}
            />
          ))}
        </div>
      )}
    </div>
  )
}
