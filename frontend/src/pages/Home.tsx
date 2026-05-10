import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { FeedEntry, ShelfEntry, SimilarBook } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'

function BookCard({ book, score, explanation }: SimilarBook) {
  const sharedTags = [
    ...(explanation?.shared_tropes ?? []),
    ...(explanation?.shared_archetypes ?? []),
  ]
  return (
    <Link
      to={`/books/${book.book_id}`}
      className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:border-indigo-300 hover:shadow-sm transition-all flex"
    >
      {book.cover_url ? (
        <img src={book.cover_url} alt={`Cover of ${book.title}`} className="w-24 shrink-0 object-cover self-stretch" />
      ) : (
        <div className="w-24 shrink-0 bg-gray-100 flex items-center justify-center text-gray-300 text-3xl select-none">
          📖
        </div>
      )}
      <div className="p-3 flex-1 flex flex-col gap-1 min-w-0">
        <div className="flex items-start justify-between gap-1">
          <p className="font-medium text-gray-800 text-sm leading-snug">{book.title}</p>
          <div className="flex flex-col items-end gap-1 shrink-0">
            <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
              {Math.round(score * 100)}%
            </span>
            {explanation?.source === 'collaborative' && (
              <span className="text-xs text-gray-400">👥 readers like you</span>
            )}
            {explanation?.source === 'description' && (
              <span className="text-xs text-gray-400">matched by description</span>
            )}
            {explanation?.source === 'review' && (
              <span className="text-xs text-gray-400">matched by reviews</span>
            )}
          </div>
        </div>
        <p className="text-xs text-gray-500">{book.author.name}</p>
        {sharedTags.length > 0 && (
          <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">
            {sharedTags.join(' · ')}
          </p>
        )}
      </div>
    </Link>
  )
}

function CurrentlyReadingShelf({ entries }: { entries: ShelfEntry[] }) {
  if (entries.length === 0) return null
  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-1">Currently Reading</h2>
      <p className="text-sm text-gray-500 mb-4">{entries.length} book{entries.length !== 1 ? 's' : ''} in progress</p>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {entries.map(({ book }) => (
          <Link
            key={book.book_id}
            to={`/books/${book.book_id}`}
            className="shrink-0 w-32 group"
          >
            <div className="relative">
              {book.cover_url ? (
                <img
                  src={book.cover_url}
                  alt={`Cover of ${book.title}`}
                  className="w-32 h-48 object-cover rounded-lg shadow-sm group-hover:shadow-md transition-shadow"
                />
              ) : (
                <div className="w-32 h-48 bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg shadow-sm flex items-center justify-center text-4xl group-hover:shadow-md transition-shadow">
                  📖
                </div>
              )}
              <span className="absolute top-2 right-2 bg-amber-400 text-white text-xs font-bold px-1.5 py-0.5 rounded-full shadow-sm">
                📖
              </span>
            </div>
            <p className="mt-2 text-xs font-medium text-gray-800 line-clamp-2 leading-snug">{book.title}</p>
            <p className="text-xs text-gray-400 mt-0.5 truncate">{book.author.name}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}

const FEED_STATUS_LABELS: Record<string, string> = {
  read: 'finished',
  currently_reading: 'reading',
  want_to_read: 'wants to read',
  rating: 'rated',
  review: 'reviewed',
}

function relativeTime(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function FriendFeedStrip({ feed }: { feed: FeedEntry[] }) {
  if (feed.length === 0) return null
  return (
    <div>
      <div className="flex items-baseline gap-3 mb-3">
        <h2 className="text-xl font-semibold text-gray-800">Friends</h2>
        <Link to="/friends" className="text-sm text-indigo-600 hover:underline">See all →</Link>
      </div>
      <div className="space-y-2">
        {feed.slice(0, 5).map((entry, i) => (
          <div key={i} className="flex items-center gap-3 bg-white border border-gray-100 rounded-lg px-3 py-2.5">
            {entry.book_cover_url ? (
              <img src={entry.book_cover_url} alt="" className="w-8 h-11 object-cover rounded shrink-0 shadow-sm" />
            ) : (
              <div className="w-8 h-11 bg-gray-100 rounded shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700 leading-snug">
                <span className="font-medium">{entry.user.name ?? entry.user.email}</span>
                {' '}{FEED_STATUS_LABELS[entry.event_type]}{' '}
                <Link to={`/books/${entry.book_id}`} className="font-medium text-indigo-600 hover:underline">
                  {entry.book_title}
                </Link>
                {(entry.event_type === 'rating' || entry.event_type === 'review') && entry.rating != null && (
                  <span className="ml-1 text-amber-500 text-xs">{'★'.repeat(entry.rating)}</span>
                )}
              </p>
              {entry.event_type === 'review' && entry.review_text && (
                <p className="text-xs text-gray-400 italic truncate">"{entry.review_text}"</p>
              )}
              <p className="text-xs text-gray-400 mt-0.5">{relativeTime(new Date(entry.occurred_at))}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function Home() {
  const { session } = useAuth()
  const toast = useToast()
  const [recs, setRecs] = useState<SimilarBook[]>([])
  const [recsLoading, setRecsLoading] = useState(false)
  const [shelf, setShelf] = useState<ShelfEntry[]>([])
  const [shelfLoading, setShelfLoading] = useState(false)
  const [feed, setFeed] = useState<FeedEntry[]>([])

  useEffect(() => {
    document.title = 'CommonThread'
  }, [])

  useEffect(() => {
    if (!session) { setShelf([]); setRecs([]); setFeed([]); return }

    setShelfLoading(true)
    api.shelf.my(session.access_token)
      .then(setShelf)
      .catch(() => toast.error('Failed to load your shelf.'))
      .finally(() => setShelfLoading(false))

    setRecsLoading(true)
    api.books.forYou(session.access_token)
      .then(setRecs)
      .catch(() => toast.error('Failed to load recommendations.'))
      .finally(() => setRecsLoading(false))

    api.users.feed(session.access_token, 10)
      .then(setFeed)
      .catch(() => toast.error('Failed to load activity feed.'))
  }, [session])

  const currentlyReading = shelf.filter(e => e.status === 'currently_reading')
  const wantToRead = shelf.filter(e => e.status === 'want_to_read')

  return (
    <div className="space-y-12">
      {/* Hero — compact for logged-in users */}
      {session ? (
        <div className="flex items-center justify-between">
          <p className="text-base font-medium text-gray-700">
            Welcome back, {session.user.user_metadata?.name ?? session.user.email?.split('@')[0] ?? 'reader'}
          </p>
          <div className="flex gap-2">
            <Link to="/books" className="px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">
              Browse Books
            </Link>
          </div>
        </div>
      ) : (
        <div className="text-center py-12">
          <h1 className="text-3xl font-bold text-gray-800 mb-3">CommonThread</h1>
          <p className="text-gray-500">Book recommendations powered by tropes &amp; archetypes</p>
          <div className="mt-6 flex justify-center gap-3">
            <Link to="/books" className="px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">
              Browse Books
            </Link>
            <Link to="/tropes" className="px-5 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50">
              Browse Tropes
            </Link>
          </div>
        </div>
      )}

      {session && (
        <>
          {/* Currently Reading */}
          {shelfLoading ? (
            <div className="flex gap-3 overflow-hidden">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="shrink-0 w-32 animate-pulse">
                  <div className="w-32 h-48 bg-gray-200 rounded-lg" />
                  <div className="mt-2 h-3 bg-gray-200 rounded w-full" />
                  <div className="mt-1 h-3 bg-gray-200 rounded w-2/3" />
                </div>
              ))}
            </div>
          ) : (
            <CurrentlyReadingShelf entries={currentlyReading} />
          )}

          {/* Want to Read count */}
          {!shelfLoading && wantToRead.length > 0 && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">
                🔖 <strong>{wantToRead.length}</strong> book{wantToRead.length !== 1 ? 's' : ''} on your want-to-read list
              </span>
              <Link to="/shelf" className="text-sm text-indigo-600 hover:underline">
                Browse →
              </Link>
            </div>
          )}

          {/* Friends feed */}
          <FriendFeedStrip feed={feed} />

          {/* For You */}
          <div>
            <div className="flex items-baseline justify-between mb-1">
              <h2 className="text-xl font-semibold text-gray-800">For You</h2>
              {recs.length > 0 && (
                <Link to="/for-you" className="text-sm text-indigo-600 hover:underline">See all →</Link>
              )}
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Matched by tropes &amp; archetypes from your ratings and shelf
            </p>

            {recsLoading && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="bg-white border border-gray-200 rounded-lg overflow-hidden flex animate-pulse">
                    <div className="w-24 shrink-0 bg-gray-200 self-stretch" />
                    <div className="p-3 flex-1 space-y-2">
                      <div className="h-4 w-3/4 bg-gray-200 rounded" />
                      <div className="h-3 w-1/2 bg-gray-200 rounded" />
                      <div className="h-3 w-2/3 bg-gray-200 rounded" />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!recsLoading && recs.length === 0 && (
              <div className="bg-white border border-dashed border-gray-300 rounded-xl p-8 text-center">
                <p className="text-gray-500 text-sm">
                  Rate books 4–5 stars or add them to your shelf and we'll recommend books with similar tropes and archetypes.
                </p>
                <Link to="/books" className="mt-3 inline-block text-sm text-indigo-600 hover:underline">
                  Browse books to get started →
                </Link>
              </div>
            )}

            {!recsLoading && recs.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {recs.map(r => <BookCard key={r.book.book_id} {...r} />)}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
