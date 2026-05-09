import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { BookDetail, SimilarBook } from '../api/client'

export function SimilarBooks() {
  const { id } = useParams<{ id: string }>()
  const bookId = Number(id)

  const [book, setBook] = useState<BookDetail | null>(null)
  const [similar, setSimilar] = useState<SimilarBook[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    Promise.all([
      api.books.get(bookId),
      api.books.similar(bookId, 20),
    ]).then(([b, s]) => {
      setBook(b)
      setSimilar(s)
    }).finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-4">
        <div className="h-4 w-48 bg-gray-100 rounded animate-pulse" />
        <div className="h-20 bg-gray-100 rounded-lg animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="h-32 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (!book) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 text-center text-gray-400">
        Book not found.
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-400 flex items-center gap-1.5">
        <Link to="/books" className="hover:text-indigo-600 transition-colors">Books</Link>
        <span>›</span>
        <Link to={`/books/${bookId}`} className="hover:text-indigo-600 transition-colors truncate max-w-xs">
          {book.title}
        </Link>
        <span>›</span>
        <span className="text-gray-600">Similar Books</span>
      </nav>

      {/* Source book strip */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 flex gap-4 items-start">
        {book.cover_url && (
          <img src={book.cover_url} alt="" className="w-14 rounded object-cover shrink-0 self-start" />
        )}
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Books similar to</p>
          <h1 className="text-lg font-semibold text-gray-900">{book.title}</h1>
          <p className="text-sm text-gray-500">{book.author.name}</p>
        </div>
      </div>

      {/* Results */}
      {similar.length === 0 ? (
        <div className="bg-white border border-dashed border-gray-200 rounded-lg p-8 text-center">
          <p className="text-sm text-gray-400">No similar books found — not enough shared signal with other books in the database.</p>
        </div>
      ) : (
        <>
          <p className="text-sm text-gray-400">{similar.length} similar book{similar.length !== 1 ? 's' : ''} found</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {similar.map(({ book: b, score, explanation }) => {
              const sharedTags = [
                ...(explanation?.shared_tropes ?? []),
                ...(explanation?.shared_archetypes ?? []),
              ]
              return (
                <Link
                  key={b.book_id}
                  to={`/books/${b.book_id}`}
                  className="bg-white border border-gray-200 rounded-lg p-4 hover:border-indigo-300 hover:shadow-sm transition-all flex gap-3"
                >
                  {b.cover_url && (
                    <img src={b.cover_url} alt="" className="w-12 shrink-0 rounded object-cover self-start" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-medium text-gray-800 text-sm truncate">{b.title}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{b.author.name}</p>
                      </div>
                      <div className="flex flex-col items-end gap-1 shrink-0">
                        <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                          {Math.round(score * 100)}%
                        </span>
                        {explanation?.source === 'description' && (
                          <span className="text-xs text-gray-400">by description</span>
                        )}
                        {explanation?.source === 'review' && (
                          <span className="text-xs text-gray-400">by reviews</span>
                        )}
                      </div>
                    </div>
                    {sharedTags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {sharedTags.map(tag => (
                          <span key={tag} className="px-1.5 py-0.5 rounded-full text-xs bg-indigo-50 text-indigo-600 border border-indigo-100">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </Link>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
