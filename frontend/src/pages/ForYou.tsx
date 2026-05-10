import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { SimilarBook } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

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

export function ForYou() {
  const { session } = useAuth()
  const [recs, setRecs] = useState<SimilarBook[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!session) return
    api.books.forYou(session.access_token, 50)
      .then(setRecs)
      .finally(() => setLoading(false))
  }, [session])

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-400 flex items-center gap-1.5">
        <Link to="/" className="hover:text-indigo-600 transition-colors">Home</Link>
        <span>›</span>
        <span className="text-gray-600">For You</span>
      </nav>

      <div>
        <h1 className="text-xl font-semibold text-gray-800 mb-1">For You</h1>
        <p className="text-sm text-gray-500">Matched by tropes &amp; archetypes from your ratings and shelf</p>
      </div>

      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {Array.from({ length: 12 }).map((_, i) => (
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

      {!loading && recs.length === 0 && (
        <div className="bg-white border border-dashed border-gray-300 rounded-xl p-8 text-center">
          <p className="text-gray-500 text-sm">
            Rate books 4–5 stars or add them to your shelf and we'll recommend books with similar tropes and archetypes.
          </p>
          <Link to="/books" className="mt-3 inline-block text-sm text-indigo-600 hover:underline">
            Browse books to get started →
          </Link>
        </div>
      )}

      {!loading && recs.length > 0 && (
        <>
          <p className="text-sm text-gray-400">{recs.length} recommendation{recs.length !== 1 ? 's' : ''}</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {recs.map(r => <BookCard key={r.book.book_id} {...r} />)}
          </div>
        </>
      )}
    </div>
  )
}
