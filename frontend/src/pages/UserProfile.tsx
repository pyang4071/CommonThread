import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { FeedEntry, FollowStatus, ShelfEntry, UserPublicProfile } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'

const ACTIVITY_PAGE_SIZE = 5

const STATUS_LABELS: Record<string, string> = {
  read: 'finished reading',
  currently_reading: 'is reading',
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
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function ActivityPanel({ userId, token }: { userId: string; token: string }) {
  const [allEntries, setAllEntries] = useState<FeedEntry[]>([])
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [hasMore, setHasMore] = useState(false)
  const [fetchingMore, setFetchingMore] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.users.activity(token, userId, 50)
      .then(entries => { setAllEntries(entries); setHasMore(entries.length === 50) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [userId, token])

  const fetchNextBatch = async () => {
    if (allEntries.length === 0 || fetchingMore) return
    setFetchingMore(true)
    try {
      const cursor = allEntries[allEntries.length - 1].occurred_at
      const entries = await api.users.activity(token, userId, 50, cursor)
      setAllEntries(prev => [...prev, ...entries])
      setHasMore(entries.length === 50)
    } catch {
      // silently ignore
    } finally {
      setFetchingMore(false)
    }
  }

  const goToPage = async (next: number) => {
    const needed = (next + 1) * ACTIVITY_PAGE_SIZE
    if (needed > allEntries.length && hasMore) await fetchNextBatch()
    setPage(next)
  }

  const totalPages = Math.max(1, Math.ceil(allEntries.length / ACTIVITY_PAGE_SIZE))
  const pageEntries = allEntries.slice(page * ACTIVITY_PAGE_SIZE, (page + 1) * ACTIVITY_PAGE_SIZE)
  const canGoNext = page < totalPages - 1 || hasMore

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-800">Recent Activity</h2>
        {allEntries.length > 0 && (
          <span className="text-xs text-gray-400">{page + 1} / {totalPages}{hasMore ? '+' : ''}</span>
        )}
      </div>

      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex gap-2 animate-pulse">
              <div className="w-8 h-11 bg-gray-200 rounded shrink-0" />
              <div className="flex-1 space-y-1.5 pt-0.5">
                <div className="h-2.5 bg-gray-200 rounded w-3/4" />
                <div className="h-2.5 bg-gray-200 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && allEntries.length === 0 && (
        <p className="text-xs text-gray-400 text-center py-4">No activity yet.</p>
      )}

      {!loading && pageEntries.length > 0 && (
        <div className="divide-y divide-gray-100">
          {pageEntries.map((entry, i) => (
            <div key={i} className="flex gap-2 py-2.5">
              {entry.book_cover_url ? (
                <img src={entry.book_cover_url} alt="" className="w-8 h-11 object-cover rounded shrink-0" />
              ) : (
                <div className="w-8 h-11 bg-gray-100 rounded shrink-0 flex items-center justify-center text-gray-300 text-sm">📖</div>
              )}
              <div className="min-w-0 flex-1">
                <p className="text-xs text-gray-700 leading-snug">
                  <span className="font-medium">{STATUS_LABELS[entry.event_type] ?? entry.event_type}</span>
                  {' '}
                  <Link to={`/books/${entry.book_id}`} className="text-indigo-600 hover:underline">
                    {entry.book_title}
                  </Link>
                  {(entry.event_type === 'rating' || entry.event_type === 'review') && entry.rating != null && (
                    <span className="ml-1 text-amber-500 text-xs">{'★'.repeat(entry.rating)}</span>
                  )}
                </p>
                {entry.event_type === 'review' && entry.review_text && (
                  <p className="text-xs text-gray-400 italic line-clamp-1 mt-0.5">"{entry.review_text}"</p>
                )}
                <p className="text-xs text-gray-400 mt-0.5">{relativeTime(new Date(entry.occurred_at))}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && allEntries.length > ACTIVITY_PAGE_SIZE && (
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-2.5 py-1 text-xs text-gray-600 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            ← Prev
          </button>
          <button
            onClick={() => goToPage(page + 1)}
            disabled={!canGoNext || fetchingMore}
            className="px-2.5 py-1 text-xs text-gray-600 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {fetchingMore ? '…' : 'Next →'}
          </button>
        </div>
      )}
    </div>
  )
}

const SECTIONS: { status: string; label: string; icon: string }[] = [
  { status: 'currently_reading', label: 'Currently Reading', icon: '📖' },
  { status: 'want_to_read',      label: 'Want to Read',      icon: '🔖' },
  { status: 'read',              label: 'Read',              icon: '✓'  },
]

const PAGE_SIZE = 4

function BookCard({ book }: { book: ShelfEntry['book'] }) {
  return (
    <Link
      to={`/books/${book.book_id}`}
      className="bg-white border border-gray-200 rounded-lg hover:border-indigo-300 hover:shadow-sm transition-all flex min-h-0"
    >
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
  )
}

export function UserProfile() {
  const { userId } = useParams<{ userId: string }>()
  const { session } = useAuth()
  const toast = useToast()

  const [profile, setProfile] = useState<UserPublicProfile | null>(null)
  const [shelf, setShelf] = useState<ShelfEntry[]>([])
  const [followStatus, setFollowStatus] = useState<FollowStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toggling, setToggling] = useState(false)
  const [visible, setVisible] = useState<Record<string, number>>({})

  useEffect(() => {
    if (!session || !userId) return
    const token = session.access_token

    setLoading(true)
    setError(null)

    Promise.all([
      api.users.profile(token, userId),
      api.users.followStatus(token, userId),
    ])
      .then(([prof, fs]) => {
        setProfile(prof)
        setFollowStatus(fs)
        return api.users.shelf(token, userId)
      })
      .then(setShelf)
      .catch(err => {
        const msg = err instanceof Error ? err.message : String(err)
        if (msg.startsWith('403')) {
          setError('This profile is private.')
        } else if (msg.startsWith('404')) {
          setError('User not found.')
        } else {
          setError('Could not load profile.')
        }
      })
      .finally(() => setLoading(false))
  }, [session, userId])

  const handleToggleFollow = async () => {
    if (!session || !userId || !followStatus) return
    setToggling(true)
    try {
      if (followStatus.following) {
        const result = await api.users.unfollow(session.access_token, userId)
        setFollowStatus(result)
        toast.success(`Unfollowed ${profile?.name ?? profile?.email}`)
      } else {
        const result = await api.users.follow(session.access_token, userId)
        setFollowStatus(result)
        // After following, reload shelf (it may now be accessible)
        api.users.shelf(session.access_token, userId).then(setShelf).catch(() => {})
        toast.success(`Following ${profile?.name ?? profile?.email}`)
      }
    } catch {
      toast.error('Could not update follow status.')
    } finally {
      setToggling(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-2xl space-y-6 animate-pulse">
        <div className="h-7 w-48 bg-gray-200 rounded" />
        <div className="h-20 bg-gray-200 rounded-xl" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-lg overflow-hidden flex">
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
    )
  }

  if (error) {
    return (
      <div className="max-w-2xl">
        <Link to="/friends" className="text-sm text-indigo-600 hover:underline mb-4 inline-block">
          ← Back to Friends
        </Link>
        <div className="bg-white border border-gray-200 rounded-xl p-10 text-center">
          <p className="text-gray-500 text-sm">{error}</p>
        </div>
      </div>
    )
  }

  if (!profile) return null

  const total = shelf.length

  return (
    <div className="max-w-5xl space-y-6">
      <nav className="flex items-center gap-1.5 text-sm text-gray-400">
        <Link to="/friends" className="text-indigo-600 hover:underline">Friends</Link>
        <span>›</span>
        <span className="text-gray-600 truncate">{profile.name ?? profile.email}</span>
      </nav>

      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-gray-800">{profile.name ?? profile.email}</h1>
          {profile.name && <p className="text-sm text-gray-400 mt-0.5">{profile.email}</p>}
          <p className="text-xs text-gray-400 mt-1">
            {total} book{total !== 1 ? 's' : ''} on their shelf
          </p>
        </div>
        {followStatus && (
          <button
            onClick={handleToggleFollow}
            disabled={toggling}
            className={`shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
              followStatus.following
                ? 'border border-gray-300 text-gray-600 hover:bg-gray-50'
                : 'bg-indigo-600 text-white hover:bg-indigo-700'
            }`}
          >
            {toggling ? '…' : followStatus.following ? 'Following' : 'Follow'}
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Shelf */}
        <div className="lg:col-span-2 space-y-8">
          {shelf.length === 0 ? (
            <div className="bg-white border border-dashed border-gray-300 rounded-xl p-10 text-center">
              <p className="text-gray-400 text-sm">Their shelf is empty.</p>
            </div>
          ) : (
            SECTIONS.map(({ status, label, icon }) => {
              const section = shelf.filter(e => e.status === status)
              if (section.length === 0) return null
              const limit = visible[status] ?? PAGE_SIZE
              const shown = section.slice(0, limit)
              const remaining = section.length - limit
              return (
                <div key={status}>
                  <div className="flex items-baseline gap-2 mb-3">
                    <h2 className="text-base font-semibold text-gray-800">
                      <span className="mr-1.5">{icon}</span>{label}
                    </h2>
                    <span className="text-sm text-gray-400">{section.length} book{section.length !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {shown.map(({ book }) => (
                      <BookCard key={book.book_id} book={book} />
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

        {/* Activity sidebar */}
        <div className="lg:col-span-1">
          <ActivityPanel userId={userId!} token={session!.access_token} />
        </div>
      </div>
    </div>
  )
}
