import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { ShelfEntry } from '../api/client'
import { ReadingStatusButton } from '../components/ReadingStatusButton'
import type { StatusValue } from '../components/ReadingStatusButton'
import { useAuth } from '../contexts/AuthContext'

const SECTIONS: { status: StatusValue; label: string; icon: string; emptyLabel: string }[] = [
  { status: 'currently_reading', label: 'Currently Reading', icon: '📖', emptyLabel: 'Nothing in progress yet.' },
  { status: 'want_to_read',      label: 'Want to Read',      icon: '🔖', emptyLabel: 'Nothing queued up yet.' },
  { status: 'read',              label: 'Read',              icon: '✓',  emptyLabel: 'No finished books yet.' },
]

function BookCover({ entry, token, onChange }: {
  entry: ShelfEntry
  token: string
  onChange: (bookId: number, status: StatusValue | null) => void
}) {
  const { book } = entry
  return (
    <div className="flex flex-col gap-2">
      <Link to={`/books/${book.book_id}`} className="group block">
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
      <ReadingStatusButton
        bookId={book.book_id}
        token={token}
        initial={entry.status as StatusValue}
        onChange={s => onChange(book.book_id, s)}
      />
    </div>
  )
}

export function Shelf() {
  const { session } = useAuth()
  const [entries, setEntries] = useState<ShelfEntry[]>([])
  const [loading, setLoading] = useState(true)

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

  const total = entries.length

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">My Shelf</h1>
        {!loading && (
          <p className="text-sm text-gray-500 mt-1">
            {total === 0 ? 'Your shelf is empty.' : `${total} book${total !== 1 ? 's' : ''} total`}
          </p>
        )}
      </div>

      {loading ? (
        <div className="space-y-10">
          {[4, 6].map((n, si) => (
            <div key={si}>
              <div className="h-5 w-40 bg-gray-200 rounded animate-pulse mb-4" />
              <div className={`grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-${n === 4 ? '4' : '6'} gap-4`}>
                {Array.from({ length: n }).map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="w-full h-44 bg-gray-200 rounded-lg" />
                    <div className="mt-2 h-3 bg-gray-200 rounded w-full" />
                    <div className="mt-1 h-3 bg-gray-200 rounded w-2/3" />
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
      ) : (
        SECTIONS.map(({ status, label, icon }) => {
          const section = entries.filter(e => e.status === status)
          if (section.length === 0) return null
          return (
            <div key={status}>
              <div className="flex items-baseline gap-2 mb-4">
                <h2 className="text-lg font-semibold text-gray-800">
                  <span className="mr-1.5">{icon}</span>{label}
                </h2>
                <span className="text-sm text-gray-400">{section.length} book{section.length !== 1 ? 's' : ''}</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                {section.map(entry => (
                  <BookCover
                    key={entry.book.book_id}
                    entry={entry}
                    token={session!.access_token}
                    onChange={handleChange}
                  />
                ))}
              </div>
            </div>
          )
        })
      )}
    </div>
  )
}
