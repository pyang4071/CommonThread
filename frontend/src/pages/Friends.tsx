import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { FeedEntry, UserPublicProfile } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'

// ── User search + follow ──────────────────────────────────────────────────────

function UserSearchPanel({
  token,
  followingIds,
  onFollow,
  onUnfollow,
}: {
  token: string
  followingIds: Set<string>
  onFollow: (u: UserPublicProfile) => void
  onUnfollow: (userId: string) => void
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<UserPublicProfile[]>([])
  const [loading, setLoading] = useState(false)
  const toast = useToast()
  const navigate = useNavigate()
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const tid = setTimeout(async () => {
      if (!query.trim()) { setResults([]); return }
      setLoading(true)
      try {
        setResults(await api.users.search(token, query.trim()))
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 300)
    return () => clearTimeout(tid)
  }, [query, token])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setResults([])
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleFollow = async (u: UserPublicProfile) => {
    try {
      await api.users.follow(token, u.user_id)
      onFollow(u)
      setQuery('')
      setResults([])
      toast.success(`Following ${u.name ?? u.email}`)
    } catch {
      toast.error('Could not follow user.')
    }
  }

  const handleUnfollow = async (u: UserPublicProfile) => {
    try {
      await api.users.unfollow(token, u.user_id)
      onUnfollow(u.user_id)
      toast.success(`Unfollowed ${u.name ?? u.email}`)
    } catch {
      toast.error('Could not unfollow user.')
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5">
      <h2 className="text-base font-semibold text-gray-800 mb-3">Find readers</h2>
      <div ref={ref} className="relative">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search by name or email…"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
        {loading && (
          <p className="mt-2 text-xs text-gray-400">Searching…</p>
        )}
        {results.length > 0 && (
          <ul className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
            {results.map(u => (
              <li key={u.user_id} className="flex items-center justify-between px-3 py-2.5 hover:bg-gray-50">
                <button
                  type="button"
                  onClick={() => { setResults([]); setQuery(''); navigate(`/users/${u.user_id}`) }}
                  className="min-w-0 flex-1 text-left"
                >
                  <p className="text-sm font-medium text-gray-800 truncate hover:text-indigo-600 transition-colors">{u.name ?? u.email}</p>
                  {u.name && <p className="text-xs text-gray-400 truncate">{u.email}</p>}
                </button>
                {followingIds.has(u.user_id) ? (
                  <button
                    onClick={() => handleUnfollow(u)}
                    className="ml-3 shrink-0 px-3 py-1 text-xs border border-gray-300 text-gray-600 rounded-full hover:bg-gray-100"
                  >
                    Following
                  </button>
                ) : (
                  <button
                    onClick={() => handleFollow(u)}
                    className="ml-3 shrink-0 px-3 py-1 text-xs bg-indigo-600 text-white rounded-full hover:bg-indigo-700"
                  >
                    Follow
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
        {!loading && query.trim() && results.length === 0 && (
          <p className="mt-2 text-xs text-gray-400">No public users found.</p>
        )}
      </div>
    </div>
  )
}

// ── Following list ────────────────────────────────────────────────────────────

function FollowingList({
  users,
  token,
  onUnfollow,
}: {
  users: UserPublicProfile[]
  token: string
  onUnfollow: (userId: string) => void
}) {
  const toast = useToast()

  const handleUnfollow = async (u: UserPublicProfile) => {
    try {
      await api.users.unfollow(token, u.user_id)
      onUnfollow(u.user_id)
      toast.success(`Unfollowed ${u.name ?? u.email}`)
    } catch {
      toast.error('Could not unfollow.')
    }
  }

  if (users.length === 0) {
    return (
      <p className="text-sm text-gray-400 text-center py-4">
        You're not following anyone yet. Search above to find readers.
      </p>
    )
  }

  return (
    <ul className="divide-y divide-gray-100">
      {users.map(u => (
        <li key={u.user_id} className="flex items-center gap-2 py-2.5">
          <Link to={`/users/${u.user_id}`} className="min-w-0 flex-1 group">
            <p className="text-sm font-medium text-gray-800 truncate group-hover:text-indigo-600 transition-colors">
              {u.name ?? u.email}
            </p>
            {u.name && <p className="text-xs text-gray-400 truncate">{u.email}</p>}
          </Link>
          <button
            onClick={() => handleUnfollow(u)}
            className="shrink-0 text-xs text-gray-400 hover:text-red-500 transition-colors"
          >
            Unfollow
          </button>
        </li>
      ))}
    </ul>
  )
}

// ── Feed ──────────────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  read: 'finished reading',
  currently_reading: 'is reading',
  want_to_read: 'wants to read',
  rating: 'rated',
  review: 'reviewed',
}

function FeedItem({ entry }: { entry: FeedEntry }) {
  const label = STATUS_LABELS[entry.event_type] ?? entry.event_type
  const time = new Date(entry.occurred_at).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
  return (
    <div className="flex gap-3 py-3">
      {entry.book_cover_url ? (
        <img
          src={entry.book_cover_url}
          alt=""
          className="w-10 h-14 object-cover rounded shrink-0 shadow-sm"
        />
      ) : (
        <div className="w-10 h-14 bg-gray-100 rounded shrink-0 flex items-center justify-center text-gray-300 text-lg">
          📖
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-sm text-gray-700 leading-snug">
          <span className="font-medium">{entry.user.name ?? entry.user.email}</span>
          {' '}{label}{' '}
          <Link
            to={`/books/${entry.book_id}`}
            className="font-medium text-indigo-600 hover:underline"
          >
            {entry.book_title}
          </Link>
          {(entry.event_type === 'rating' || entry.event_type === 'review') && entry.rating != null && (
            <span className="ml-1 text-amber-500">{'★'.repeat(entry.rating)}</span>
          )}
        </p>
        {entry.event_type === 'review' && entry.review_text && (
          <p className="mt-1 text-xs text-gray-500 italic line-clamp-2">
            "{entry.review_text}"
          </p>
        )}
        <p className="text-xs text-gray-400 mt-0.5">{time}</p>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function Friends() {
  const { session } = useAuth()
  const [following, setFollowing] = useState<UserPublicProfile[]>([])
  const [feed, setFeed] = useState<FeedEntry[]>([])
  const [feedLoading, setFeedLoading] = useState(true)

  const followingIds = new Set(following.map(u => u.user_id))

  useEffect(() => {
    if (!session) return
    const token = session.access_token

    api.users.following(token).then(setFollowing).catch(() => {})

    setFeedLoading(true)
    api.users.feed(token).then(setFeed).catch(() => {}).finally(() => setFeedLoading(false))
  }, [session])

  if (!session) return null

  const handleFollow = (u: UserPublicProfile) =>
    setFollowing(prev => prev.some(f => f.user_id === u.user_id) ? prev : [...prev, u])

  const handleUnfollow = (userId: string) =>
    setFollowing(prev => prev.filter(u => u.user_id !== userId))

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold text-gray-800">Friends</h1>

      {/* Search */}
      <UserSearchPanel
        token={session.access_token}
        followingIds={followingIds}
        onFollow={handleFollow}
        onUnfollow={handleUnfollow}
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        {/* Following */}
        <div className="sm:col-span-1 bg-white border border-gray-200 rounded-xl p-5">
          <h2 className="text-base font-semibold text-gray-800 mb-3">
            Following <span className="text-gray-400 font-normal text-sm">({following.length})</span>
          </h2>
          <FollowingList
            users={following}
            token={session.access_token}
            onUnfollow={handleUnfollow}
          />
        </div>

        {/* Feed */}
        <div className="sm:col-span-2 bg-white border border-gray-200 rounded-xl p-5">
          <h2 className="text-base font-semibold text-gray-800 mb-1">Activity</h2>
          <p className="text-xs text-gray-400 mb-3">Recent reads and ratings from people you follow</p>

          {feedLoading && (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex gap-3 py-2 animate-pulse">
                  <div className="w-10 h-14 bg-gray-200 rounded shrink-0" />
                  <div className="flex-1 space-y-2 pt-1">
                    <div className="h-3 bg-gray-200 rounded w-3/4" />
                    <div className="h-3 bg-gray-200 rounded w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {!feedLoading && feed.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-6">
              {following.length === 0
                ? 'Follow some readers to see their activity here.'
                : 'No recent activity from people you follow.'}
            </p>
          )}

          {!feedLoading && feed.length > 0 && (
            <div className="divide-y divide-gray-100">
              {feed.map((entry, i) => <FeedItem key={i} entry={entry} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
