import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { BookTagsEntry } from '../api/client'
import { ConfirmModal } from '../components/ConfirmModal'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'

type TagToRemove = {
  type: 'trope' | 'archetype'
  bookId: number
  id: number
  name: string
}

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

function TagCard({ entry, onRequestRemoveTrope, onRequestRemoveArchetype }: {
  entry: BookTagsEntry
  onRequestRemoveTrope: (bookId: number, tropeId: number, name: string) => void
  onRequestRemoveArchetype: (bookId: number, archetypeId: number, name: string) => void
}) {
  const { book, tropes, archetypes } = entry
  const sorted_tropes = [...tropes].sort((a, b) => b.weight - a.weight)
  const sorted_archetypes = [...archetypes].sort((a, b) => b.importance - a.importance)

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
              onClick={() => onRequestRemoveTrope(book.book_id, trope.trope_id, trope.name)}
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
              onClick={() => onRequestRemoveArchetype(book.book_id, archetype.archetype_id, archetype.name)}
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
  const toast = useToast()
  const [entries, setEntries] = useState<BookTagsEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [filterQuery, setFilterQuery] = useState('')
  const [tagToRemove, setTagToRemove] = useState<TagToRemove | null>(null)

  useEffect(() => {
    document.title = 'My Tags — CommonThread'
  }, [])

  useEffect(() => {
    if (!session) return
    api.users.myTags(session.access_token)
      .then(setEntries)
      .catch(() => toast.error('Failed to load your tags.'))
      .finally(() => setLoading(false))
  }, [session])

  const doRemoveTrope = async (bookId: number, tropeId: number) => {
    if (!session) return
    try {
      await api.myTags.removeTrope(bookId, tropeId, session.access_token)
      setEntries(prev =>
        prev
          .map(e => e.book.book_id === bookId
            ? { ...e, tropes: e.tropes.filter(t => t.trope.trope_id !== tropeId) }
            : e
          )
          .filter(e => e.tropes.length > 0 || e.archetypes.length > 0)
      )
    } catch {
      toast.error('Failed to remove tag.')
    }
  }

  const doRemoveArchetype = async (bookId: number, archetypeId: number) => {
    if (!session) return
    try {
      await api.myTags.removeArchetype(bookId, archetypeId, session.access_token)
      setEntries(prev =>
        prev
          .map(e => e.book.book_id === bookId
            ? { ...e, archetypes: e.archetypes.filter(a => a.archetype.archetype_id !== archetypeId) }
            : e
          )
          .filter(e => e.tropes.length > 0 || e.archetypes.length > 0)
      )
    } catch {
      toast.error('Failed to remove tag.')
    }
  }

  const handleConfirmRemove = async () => {
    if (!tagToRemove) return
    const { type, bookId, id } = tagToRemove
    setTagToRemove(null)
    if (type === 'trope') await doRemoveTrope(bookId, id)
    else await doRemoveArchetype(bookId, id)
  }

  const filteredEntries = filterQuery.trim()
    ? entries.filter(e => {
        const q = filterQuery.toLowerCase()
        return (
          e.book.title.toLowerCase().includes(q) ||
          e.book.author.name.toLowerCase().includes(q) ||
          e.tropes.some(t => t.trope.name.toLowerCase().includes(q)) ||
          e.archetypes.some(a => a.archetype.name.toLowerCase().includes(q))
        )
      })
    : entries

  const totalTags = entries.reduce((sum, e) => sum + e.tropes.length + e.archetypes.length, 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">My Tags</h1>
        {!loading && (
          <p className="text-sm text-gray-500 mt-1">
            {totalTags === 0
              ? 'No personal tags yet.'
              : `${totalTags} tag${totalTags !== 1 ? 's' : ''} across ${entries.length} book${entries.length !== 1 ? 's' : ''}`}
          </p>
        )}
        <p className="text-sm text-indigo-700 bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-2 mt-3">
          Your tags are combined with system tropes to build your taste profile — they're how you tell the recommendation engine what actually resonated with you in each book.
        </p>
      </div>

      {/* T-31: Search/filter */}
      {!loading && entries.length > 0 && (
        <div className="flex items-center gap-2">
          <input
            value={filterQuery}
            onChange={e => setFilterQuery(e.target.value)}
            placeholder="Filter by book, author, or tag name…"
            className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          />
          {filterQuery && (
            <button
              onClick={() => setFilterQuery('')}
              className="text-xs text-gray-400 hover:text-gray-600 px-2 py-2"
            >
              Clear
            </button>
          )}
          {filterQuery.trim() && (
            <span className="text-xs text-gray-400 shrink-0">
              {filteredEntries.length} book{filteredEntries.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}

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
      ) : filteredEntries.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-8">No tags match "{filterQuery}".</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredEntries.map(entry => (
            <TagCard
              key={entry.book.book_id}
              entry={entry}
              onRequestRemoveTrope={(bookId, tropeId, name) =>
                setTagToRemove({ type: 'trope', bookId, id: tropeId, name })
              }
              onRequestRemoveArchetype={(bookId, archetypeId, name) =>
                setTagToRemove({ type: 'archetype', bookId, id: archetypeId, name })
              }
            />
          ))}
        </div>
      )}

      {tagToRemove && (
        <ConfirmModal
          title="Remove tag?"
          message={`Remove "${tagToRemove.name}" from your personal tags? This will affect your recommendation profile.`}
          confirmLabel="Remove"
          onConfirm={handleConfirmRemove}
          onCancel={() => setTagToRemove(null)}
        />
      )}
    </div>
  )
}
