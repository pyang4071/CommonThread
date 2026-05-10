import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { ShelfEntry } from '../api/client'
import { ReadingStatusButton } from '../components/ReadingStatusButton'
import type { StatusValue } from '../components/ReadingStatusButton'
import { useAuth } from '../contexts/AuthContext'
import { useSessionState } from '../hooks/useSessionState'

const SECTIONS: { status: StatusValue; label: string; icon: string; emptyLabel: string }[] = [
  { status: 'currently_reading', label: 'Currently Reading', icon: '📖', emptyLabel: 'Nothing in progress yet.' },
  { status: 'want_to_read',      label: 'Want to Read',      icon: '🔖', emptyLabel: 'Nothing queued up yet.' },
  { status: 'read',              label: 'Read',              icon: '✓',  emptyLabel: 'No finished books yet.' },
]

function BookCard({ entry, token, onChange }: {
  entry: ShelfEntry
  token: string
  onChange: (bookId: number, status: StatusValue | null) => void
}) {
  const { book } = entry
  return (
    <div className="bg-white border border-gray-200 rounded-lg hover:border-indigo-300 hover:shadow-sm transition-all flex flex-col">
      <Link to={`/books/${book.book_id}`} state={{ from: '/shelf', fromLabel: 'My Shelf' }} className="flex flex-1 min-h-0">
        <div className="p-2 pr-0 self-stretch flex shrink-0">
          {book.cover_url ? (
            <img src={book.cover_url} alt="" className="w-20 h-full object-cover rounded-lg" />
          ) : (
            <div className="w-20 bg-gray-100 flex items-center justify-center text-gray-300 text-2xl select-none rounded-lg">📖</div>
          )}
        </div>
        <div className="p-3 flex-1 min-w-0">
          <p className="font-medium text-gray-800 text-sm leading-snug line-clamp-2">{book.title}</p>
          <p className="text-xs text-gray-500 mt-0.5">{book.author.name}</p>
          {book.publication_date && (
            <p className="text-xs text-gray-400 mt-0.5">{new Date(book.publication_date).getFullYear()}</p>
          )}
          {book.avg_rating != null ? (
            <span className="mt-1 flex items-center gap-1 text-xs font-medium text-amber-600">
              <span className="text-amber-400">★</span>{book.avg_rating.toFixed(1)}
            </span>
          ) : (
            <span className="mt-1 block text-xs text-gray-300">No ratings</span>
          )}
        </div>
      </Link>
      <div className="px-3 pt-1 pb-3">
        <ReadingStatusButton
          bookId={book.book_id}
          token={token}
          initial={entry.status as StatusValue}
          onChange={s => onChange(book.book_id, s)}
        />
      </div>
    </div>
  )
}

const PAGE_SIZE = 6

type SortKey = 'title' | 'newest' | 'oldest'

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'newest', label: 'Date Added (newest)' },
  { value: 'oldest', label: 'Date Added (oldest)' },
  { value: 'title',  label: 'Title A–Z' },
]

function sortEntries(entries: ShelfEntry[], sort: SortKey): ShelfEntry[] {
  return [...entries].sort((a, b) => {
    if (sort === 'title') return a.book.title.localeCompare(b.book.title)
    if (sort === 'newest') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  })
}

export function Shelf() {
  const { session } = useAuth()
  const [entries, setEntries] = useState<ShelfEntry[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => { document.title = 'My Shelf — CommonThread' }, [])
  const [sort, setSort] = useSessionState<SortKey>('shelf:sort', 'newest')

  useEffect(() => {
    if (!session) return
    setLoading(true)
    api.shelf.my(session.access_token)
      .then(setEntries)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [session])

  const handleChange = (bookId: number, status: StatusValue | null) => {
    if (status === null) {
      setEntries(prev => prev.filter(e => e.book.book_id !== bookId))
    } else {
      setEntries(prev => prev.map(e =>
        e.book.book_id === bookId ? { ...e, status } : e
      ))
    }
  }

  const [query, setQuery] = useSessionState('shelf:query', '')
  const [visible, setVisible] = useState<Record<string, number>>({})

  useEffect(() => { setVisible({}) }, [query, sort])

  const total = entries.length
  const filtered = entries.filter(e =>
    !query.trim() ||
    e.book.title.toLowerCase().includes(query.toLowerCase()) ||
    e.book.author.name.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div className="space-y-10">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold text-gray-800">My Shelf</h1>
          {!loading && (
            <p className="text-sm text-gray-500 mt-1">
              {total === 0 ? 'Your shelf is empty.' : `${total} book${total !== 1 ? 's' : ''} total`}
            </p>
          )}
        </div>
        {!loading && total > 0 && (
          <div className="flex items-center gap-3 shrink-0 flex-wrap">
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Filter by title or author…"
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-indigo-300 w-52"
            />
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Sort:</span>
              <select
                value={sort}
                onChange={e => setSort(e.target.value as SortKey)}
                className="text-xs border border-gray-300 rounded-md px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300"
              >
                {SORT_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {loading ? (
        <div className="space-y-10">
          {[3, 6].map((n, si) => (
            <div key={si}>
              <div className="h-5 w-40 bg-gray-200 rounded animate-pulse mb-4" />
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {Array.from({ length: n }).map((_, i) => (
                  <div key={i} className="bg-white border border-gray-200 rounded-lg overflow-hidden animate-pulse flex">
                    <div className="w-20 shrink-0 bg-gray-200 self-stretch" />
                    <div className="p-3 flex-1 space-y-2">
                      <div className="h-4 w-3/4 bg-gray-200 rounded" />
                      <div className="h-3 w-1/2 bg-gray-200 rounded" />
                      <div className="h-3 w-1/3 bg-gray-200 rounded" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : total === 0 ? (
        <div className="bg-white border border-dashed border-gray-300 rounded-xl p-12 text-center">
          <p className="text-gray-400 text-sm mb-3">
            You haven't added any books to your shelf yet.
          </p>
          <Link to="/books" className="text-sm text-indigo-600 hover:underline">
            Browse books to get started →
          </Link>
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-gray-400">No books match your filter.</p>
      ) : (
        SECTIONS.map(({ status, label, icon }) => {
          const section = sortEntries(filtered.filter(e => e.status === status), sort)
          if (section.length === 0) return null
          const limit = visible[status] ?? PAGE_SIZE
          const shown = section.slice(0, limit)
          const remaining = section.length - limit
          return (
            <div key={status}>
              <div className="flex items-baseline gap-2 mb-4">
                <h2 className="text-lg font-semibold text-gray-800">
                  <span className="mr-1.5">{icon}</span>{label}
                </h2>
                <span className="text-sm text-gray-400">{section.length} book{section.length !== 1 ? 's' : ''}</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {shown.map(entry => (
                  <BookCard
                    key={entry.book.book_id}
                    entry={entry}
                    token={session!.access_token}
                    onChange={handleChange}
                  />
                ))}
              </div>
              {remaining > 0 && (
                <button
                  onClick={() => setVisible(prev => ({ ...prev, [status]: limit + PAGE_SIZE }))}
                  className="mt-4 w-full py-2 text-sm text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50 transition-colors"
                >
                  Show {Math.min(remaining, PAGE_SIZE)} more
                  <span className="ml-1 text-xs text-gray-400">({remaining} remaining)</span>
                </button>
              )}
            </div>
          )
        })
      )}
    </div>
  )
}
