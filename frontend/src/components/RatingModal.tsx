import { useState } from 'react'
import { api } from '../api/client'
import type { Book } from '../api/client'

const STAR_LABELS = ['', "Didn't like it", 'It was ok', 'Liked it', 'Really liked it', 'It was amazing']

export function RatingModal({ book, currentRating, currentReview, token, onClose, onRate }: {
  book: Book
  currentRating: number | null
  currentReview?: string | null
  token: string
  onClose: () => void
  onRate: (bookId: number, rating: number | null) => void
}) {
  const [selected, setSelected] = useState<number | null>(currentRating)
  const [review, setReview] = useState(currentReview ?? '')
  const [hover, setHover] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const display = hover ?? selected ?? 0

  const save = async () => {
    if (selected === null) return
    setSaving(true)
    setError(null)
    try {
      await api.books.upsertRating(book.book_id, selected, token, review.trim() || null)
      onRate(book.book_id, selected)
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save rating.')
    } finally {
      setSaving(false)
    }
  }

  const remove = async () => {
    setSaving(true)
    setError(null)
    try {
      await api.books.deleteRating(book.book_id, token)
      onRate(book.book_id, null)
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to remove rating.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Book info */}
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Rate this book</p>
          <h2 className="text-lg font-semibold text-gray-900 leading-snug">{book.title}</h2>
          <p className="text-sm text-gray-500">{book.author.name}</p>
        </div>

        {/* Stars */}
        <div className="flex flex-col items-center gap-2 py-2">
          <div className="flex gap-2" role="radiogroup" aria-label="Rating">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                role="radio"
                aria-checked={selected === star}
                aria-label={STAR_LABELS[star]}
                onClick={() => setSelected(selected === star ? null : star)}
                onMouseEnter={() => setHover(star)}
                onMouseLeave={() => setHover(null)}
                className="text-5xl leading-none transition-transform hover:scale-110 focus:outline-none"
              >
                <span className={display >= star ? 'text-amber-400' : 'text-gray-200'}>★</span>
              </button>
            ))}
          </div>
          <p className="text-sm text-gray-500 h-5 transition-all">
            {STAR_LABELS[hover ?? selected ?? 0]}
          </p>
        </div>

        {/* Review */}
        <div>
          <div className="flex items-baseline justify-between mb-1.5">
            <label className="text-xs text-gray-500">
              Review <span className="text-gray-400">(optional)</span>
            </label>
            <span className={`text-xs ${review.length > 900 ? 'text-amber-500' : 'text-gray-400'}`}>
              {review.length} / 1000
            </span>
          </div>
          <textarea
            value={review}
            onChange={e => setReview(e.target.value)}
            placeholder="What did you think?"
            rows={3}
            maxLength={1000}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
          />
        </div>

        {error && (
          <p className="text-xs text-red-500 text-center">{error}</p>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={save}
            disabled={saving || selected === null}
            className="flex-1 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40 transition-colors flex items-center justify-center gap-1.5"
          >
            {saving && (
              <svg className="animate-spin h-3.5 w-3.5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            )}
            {saving ? 'Saving…' : 'Save'}
          </button>
          {currentRating !== null && (
            <button
              onClick={remove}
              disabled={saving}
              className="px-4 py-2 text-sm text-red-500 hover:text-red-700 border border-red-200 rounded-lg disabled:opacity-40 transition-colors flex items-center gap-1.5"
            >
              {saving && (
                <svg className="animate-spin h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              )}
              {saving ? 'Removing…' : 'Remove'}
            </button>
          )}
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
