import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { FollowStatus, ShelfEntry, UserPublicProfile } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'

const SECTIONS: { status: string; label: string; icon: string }[] = [
  { status: 'currently_reading', label: 'Currently Reading', icon: '📖' },
  { status: 'want_to_read',      label: 'Want to Read',      icon: '🔖' },
  { status: 'read',              label: 'Read',              icon: '✓'  },
]

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
        <div className="h-4 w-32 bg-gray-200 rounded" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i}>
              <div className="w-full h-44 bg-gray-200 rounded-lg" />
              <div className="mt-2 h-3 bg-gray-200 rounded w-full" />
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
    <div className="max-w-2xl space-y-6">
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

      {/* Shelf */}
      {shelf.length === 0 ? (
        <div className="bg-white border border-dashed border-gray-300 rounded-xl p-10 text-center">
          <p className="text-gray-400 text-sm">Their shelf is empty.</p>
        </div>
      ) : (
        SECTIONS.map(({ status, label, icon }) => {
          const section = shelf.filter(e => e.status === status)
          if (section.length === 0) return null
          return (
            <div key={status}>
              <div className="flex items-baseline gap-2 mb-3">
                <h2 className="text-base font-semibold text-gray-800">
                  <span className="mr-1.5">{icon}</span>{label}
                </h2>
                <span className="text-sm text-gray-400">{section.length}</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                {section.map(({ book }) => (
                  <Link key={book.book_id} to={`/books/${book.book_id}`} className="group block">
                    {book.cover_url ? (
                      <img
                        src={book.cover_url}
                        alt={`Cover of ${book.title}`}
                        className="w-full h-44 object-cover rounded-lg shadow-sm group-hover:shadow-md transition-shadow"
                      />
                    ) : (
                      <div className="w-full h-44 bg-gradient-to-br from-gray-100 to-gray-200 rounded-lg shadow-sm flex items-center justify-center text-4xl group-hover:shadow-md transition-shadow select-none">
                        📖
                      </div>
                    )}
                    <p className="mt-2 text-xs font-medium text-gray-800 line-clamp-2 leading-snug">{book.title}</p>
                    <p className="text-xs text-gray-400 mt-0.5 truncate">{book.author.name}</p>
                  </Link>
                ))}
              </div>
            </div>
          )
        })
      )}
    </div>
  )
}
