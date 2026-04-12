import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Archetype, Book, BookDetail as BookDetailType, Review, SimilarBook, Trope, UserTags } from '../api/client'
import { ConfirmModal } from '../components/ConfirmModal'
import { RatingModal } from '../components/RatingModal'
import { ReadingStatusButton } from '../components/ReadingStatusButton'
import type { StatusValue } from '../components/ReadingStatusButton'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'

function WeightBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color =
    pct >= 80 ? 'bg-indigo-500' : pct >= 50 ? 'bg-indigo-300' : 'bg-indigo-200'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 w-8 text-right">{pct}%</span>
    </div>
  )
}

function ImportanceDots({ value }: { value: number }) {
  return (
    <div className="flex gap-1">
      {Array.from({ length: 10 }).map((_, i) => (
        <div
          key={i}
          className={`w-2 h-2 rounded-full ${i < value ? 'bg-indigo-500' : 'bg-gray-200'}`}
        />
      ))}
    </div>
  )
}

const CATEGORY_COLORS: Record<string, string> = {
  Romance: 'bg-pink-100 text-pink-700',
  Fantasy: 'bg-purple-100 text-purple-700',
  Character: 'bg-blue-100 text-blue-700',
  Narrative: 'bg-amber-100 text-amber-700',
  Setting: 'bg-green-100 text-green-700',
}


export function BookDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { state } = useLocation()
  const backTo: string = state?.from ?? '/books'
  const backLabel = backTo === '/shelf' ? '← Back to Shelf' : '← Back to Books'
  const { session } = useAuth()
  const toast = useToast()
  const [book, setBook] = useState<BookDetailType | null>(null)
  const [similar, setSimilar] = useState<SimilarBook[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [myRating, setMyRating] = useState<number | null>(null)
  const [myReview, setMyReview] = useState<string | null>(null)
  const [ratingOpen, setRatingOpen] = useState(false)
  const [readingStatus, setReadingStatus] = useState<StatusValue | null>(null)
  const [disliked, setDisliked] = useState(false)
  const [dislikeLoading, setDislikeLoading] = useState(false)
  const [dislikeConfirmOpen, setDislikeConfirmOpen] = useState(false)
  const [reviews, setReviews] = useState<Review[]>([])
  const [seriesBooks, setSeriesBooks] = useState<Book[]>([])
  const [myTags, setMyTags] = useState<UserTags>({ tropes: [], archetypes: [] })
  const [allTropes, setAllTropes] = useState<Trope[]>([])
  const [allArchetypes, setAllArchetypes] = useState<Archetype[]>([])
  const [addTropeId, setAddTropeId] = useState<number | ''>('')
  const [addTropeWeight, setAddTropeWeight] = useState(0.8)
  const [addArchetypeId, setAddArchetypeId] = useState<number | ''>('')
  const [addArchetypeImportance, setAddArchetypeImportance] = useState(7)
  const [tagSaving, setTagSaving] = useState(false)

  useEffect(() => {
    if (!id) return
    const bookId = Number(id)
    api.books
      .get(bookId)
      .then(setBook)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
    api.books.similar(bookId).then(setSimilar).catch(() => {})
    api.books.getReviews(bookId).then(setReviews).catch(() => {})
    api.books.getSeries(bookId).then(setSeriesBooks).catch(() => {})
  }, [id])

  useEffect(() => {
    if (!session || !id) return
    const bookId = Number(id)
    api.books.getRating(bookId, session.access_token)
      .then(r => { setMyRating(r?.rating ?? null); setMyReview(r?.review_text ?? null) })
      .catch(() => {})
    api.shelf.get(bookId, session.access_token)
      .then(r => setReadingStatus((r?.status as StatusValue) ?? null))
      .catch(() => {})
    api.dislikes.get(bookId, session.access_token)
      .then(r => setDisliked(r.disliked))
      .catch(() => {})
    api.myTags.get(bookId, session.access_token)
      .then(setMyTags)
      .catch(() => {})
    api.tropes.list().then(setAllTropes).catch(() => {})
    api.archetypes.list().then(setAllArchetypes).catch(() => {})
  }, [id, session])

  const taggedTropeIds = new Set(myTags.tropes.map(t => t.trope.trope_id))
  const taggedArchetypeIds = new Set(myTags.archetypes.map(a => a.archetype.archetype_id))

  const handleAddTrope = async () => {
    if (!session || !id || addTropeId === '') return
    setTagSaving(true)
    try {
      const entry = await api.myTags.addTrope(Number(id), addTropeId, addTropeWeight, session.access_token)
      setMyTags(prev => ({
        ...prev,
        tropes: [...prev.tropes.filter(t => t.trope.trope_id !== addTropeId), entry],
      }))
      setAddTropeId('')
      toast.success('Trope tag added.')
    } catch {
      toast.error('Failed to add trope tag.')
    } finally {
      setTagSaving(false)
    }
  }

  const handleRemoveTrope = async (tropeId: number) => {
    if (!session || !id) return
    try {
      await api.myTags.removeTrope(Number(id), tropeId, session.access_token)
      setMyTags(prev => ({ ...prev, tropes: prev.tropes.filter(t => t.trope.trope_id !== tropeId) }))
    } catch {
      toast.error('Failed to remove trope tag.')
    }
  }

  const handleAddArchetype = async () => {
    if (!session || !id || addArchetypeId === '') return
    setTagSaving(true)
    try {
      const entry = await api.myTags.addArchetype(Number(id), addArchetypeId, addArchetypeImportance, session.access_token)
      setMyTags(prev => ({
        ...prev,
        archetypes: [...prev.archetypes.filter(a => a.archetype.archetype_id !== addArchetypeId), entry],
      }))
      setAddArchetypeId('')
      toast.success('Archetype tag added.')
    } catch {
      toast.error('Failed to add archetype tag.')
    } finally {
      setTagSaving(false)
    }
  }

  const handleRemoveArchetype = async (archetypeId: number) => {
    if (!session || !id) return
    try {
      await api.myTags.removeArchetype(Number(id), archetypeId, session.access_token)
      setMyTags(prev => ({ ...prev, archetypes: prev.archetypes.filter(a => a.archetype.archetype_id !== archetypeId) }))
    } catch {
      toast.error('Failed to remove archetype tag.')
    }
  }

  const toggleDislike = async () => {
    if (!session || !id) return
    setDislikeLoading(true)
    try {
      if (disliked) {
        await api.dislikes.remove(Number(id), session.access_token)
        setDisliked(false)
      } else {
        await api.dislikes.set(Number(id), session.access_token)
        setDisliked(true)
      }
    } catch {
      toast.error('Failed to update dislike.')
    } finally {
      setDislikeLoading(false)
    }
  }

  if (loading) return (
    <div className="space-y-8 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="h-4 w-24 bg-gray-200 rounded" />
        <div className="h-8 w-14 bg-gray-200 rounded-md" />
      </div>
      <div className="border-b border-gray-200 pb-6 flex gap-6">
        <div className="w-28 h-40 bg-gray-200 rounded-lg shrink-0" />
        <div className="flex-1 space-y-3">
          <div className="h-8 w-64 bg-gray-200 rounded" />
          <div className="h-5 w-40 bg-gray-200 rounded" />
          <div className="flex gap-3 mt-2">
            <div className="h-4 w-20 bg-gray-200 rounded" />
            <div className="h-4 w-28 bg-gray-200 rounded" />
          </div>
        </div>
      </div>
      <div className="space-y-2">
        <div className="h-4 w-full bg-gray-200 rounded" />
        <div className="h-4 w-5/6 bg-gray-200 rounded" />
        <div className="h-4 w-4/6 bg-gray-200 rounded" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {[0, 1].map(col => (
          <div key={col} className="space-y-4">
            <div className="h-6 w-32 bg-gray-200 rounded" />
            {[0, 1, 2].map(row => (
              <div key={row} className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
                <div className="h-4 w-48 bg-gray-200 rounded" />
                <div className="h-3 w-full bg-gray-200 rounded" />
                <div className="h-2 w-full bg-gray-200 rounded-full" />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
  if (error) return <p className="text-red-500 text-sm">{error}</p>
  if (!book) return null

  const sortedTropes = [...book.book_tropes].sort((a, b) => b.weight - a.weight)
  const sortedDNA = [...book.character_dna].sort((a, b) => b.importance - a.importance)

  return (
    <div className="space-y-8">
      {/* Back */}
      <div className="flex items-center justify-between">
        <Link to={backTo} className="text-sm text-indigo-600 hover:underline">
          {backLabel}
        </Link>
        <button
          onClick={() => navigate(`/books/${id}/edit`)}
          className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Edit
        </button>
      </div>

      {/* Header */}
      <div className="border-b border-gray-200 pb-6 flex gap-6">
        {book.cover_url && (
          <img
            src={book.cover_url}
            alt={`Cover of ${book.title}`}
            className="w-28 shrink-0 rounded-lg shadow-sm object-cover self-start"
          />
        )}
        <div className="flex-1 min-w-0">
        <h1 className="text-3xl font-bold text-gray-900">{book.title}</h1>
        <p className="mt-1 text-lg text-gray-500">{book.author.name}</p>
        <div className="mt-3 flex flex-wrap gap-4 text-sm text-gray-400 items-center">
          {book.series && (
            <span className="text-indigo-600 font-medium">
              {book.series_position != null ? `Book ${book.series_position} of ` : ''}{book.series.name}
            </span>
          )}
          {book.publication_date && (
            <span>Published {new Date(book.publication_date).getFullYear()}</span>
          )}
          {book.isbn && <span>ISBN {book.isbn}</span>}
          {book.embedding_status === 'pending' && (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-50 text-yellow-700 border border-yellow-200">
              ⏳ Indexing in progress
            </span>
          )}
          {book.embedding_status === 'failed' && (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200">
              ✗ Indexing failed
            </span>
          )}
        </div>
        {(book.genres.length > 0 || book.book_types.length > 0 || book.tones.length > 0 || book.pacing != null) && (
          <div className="mt-3 flex flex-wrap gap-2 items-center">
            {book.genres.map((g) => (
              <span key={g.genre_id} className="px-3 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700">
                {g.name}
              </span>
            ))}
            {book.book_types.map((bt) => (
              <span key={bt.book_type_id} className="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                {bt.name}
              </span>
            ))}
            {book.tones.map((t) => (
              <span key={t.tone_id} className="px-3 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700">
                {t.name}
              </span>
            ))}
            {book.pacing != null && (
              <span className="px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">
                Pacing {book.pacing}/5
              </span>
            )}
          </div>
        )}
        {session && (
          <div className="mt-4 flex items-center gap-3 flex-wrap">
            <ReadingStatusButton
              bookId={Number(id)}
              token={session.access_token}
              initial={readingStatus}
              onChange={setReadingStatus}
            />
            <button
              onClick={() => setRatingOpen(true)}
              className={
                myRating != null
                  ? 'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-amber-50 text-amber-600 border border-amber-200 hover:bg-amber-100 transition-colors'
                  : 'px-3 py-1.5 rounded-full text-sm font-medium text-gray-500 border border-gray-200 hover:bg-gray-50 hover:text-gray-700 transition-colors'
              }
            >
              {myRating != null ? <>★ {myRating}/5 · Edit rating</> : '+ Rate this book'}
            </button>
            <button
              onClick={() => disliked ? toggleDislike() : setDislikeConfirmOpen(true)}
              disabled={dislikeLoading}
              title={disliked ? 'Remove "not for me" signal' : 'Not for me — exclude from recommendations'}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-colors disabled:opacity-50 ${
                disliked
                  ? 'bg-red-50 text-red-600 border-red-200 hover:bg-red-100'
                  : 'text-gray-400 border-gray-200 hover:bg-gray-50 hover:text-gray-600'
              }`}
            >
              {dislikeLoading
                ? <span className="w-3 h-3 rounded-full border-2 border-current border-t-transparent animate-spin" />
                : '👎'
              }
              {disliked && ' Not for me'}
            </button>
            {dislikeConfirmOpen && (
              <ConfirmModal
                title="Mark as not for me?"
                message="This book will be excluded from your recommendations. You can undo this at any time by clicking the button again."
                confirmLabel="Mark as not for me"
                onConfirm={() => { setDislikeConfirmOpen(false); toggleDislike() }}
                onCancel={() => setDislikeConfirmOpen(false)}
              />
            )}
            {ratingOpen && (
              <RatingModal
                book={book}
                currentRating={myRating}
                currentReview={myReview}
                token={session.access_token}
                onClose={() => setRatingOpen(false)}
                onRate={(_, r) => setMyRating(r)}
              />
            )}
          </div>
        )}
        </div>
      </div>

      {book.description && (
        <p className="text-gray-600 leading-relaxed">{book.description}</p>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Tropes */}
        <div>
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            Tropes
            <span className="ml-2 text-sm font-normal text-gray-400">
              ({sortedTropes.length})
            </span>
          </h2>
          {sortedTropes.length === 0 ? (
            <p className="text-gray-400 text-sm">No tropes tagged yet.</p>
          ) : (
            <div className="space-y-4">
              {sortedTropes.map(({ trope, weight }) => {
                const badgeClass =
                  CATEGORY_COLORS[trope.category] ?? 'bg-gray-100 text-gray-600'
                return (
                  <div key={trope.trope_id} className="bg-white border border-gray-200 rounded-lg p-4">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <Link
                          to={`/tropes/${trope.trope_id}`}
                          className="font-medium text-gray-800 hover:text-indigo-600 transition-colors"
                        >
                          {trope.name}
                        </Link>
                        <span
                          className={`ml-2 px-2 py-0.5 rounded-full text-xs font-medium ${badgeClass}`}
                        >
                          {trope.category}
                        </span>
                      </div>
                    </div>
                    {trope.description && (
                      <p className="text-sm text-gray-500 mb-3">{trope.description}</p>
                    )}
                    <WeightBar value={weight} />
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Character DNA */}
        <div>
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            Character Archetypes
            <span className="ml-2 text-sm font-normal text-gray-400">
              ({sortedDNA.length})
            </span>
          </h2>
          {sortedDNA.length === 0 ? (
            <p className="text-gray-400 text-sm">No archetypes tagged yet.</p>
          ) : (
            <div className="space-y-4">
              {sortedDNA.map(({ archetype, importance }) => (
                <div key={archetype.archetype_id} className="bg-white border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <Link
                      to={`/archetypes/${archetype.archetype_id}`}
                      className="font-medium text-gray-800 hover:text-indigo-600 transition-colors"
                    >
                      {archetype.name}
                    </Link>
                    <span className="text-xs text-gray-400">{importance}/10</span>
                  </div>
                  {archetype.description && (
                    <p className="text-sm text-gray-500 mb-3">{archetype.description}</p>
                  )}
                  <ImportanceDots value={importance} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Your Tags */}
      {session && (
        <div className="border border-indigo-100 rounded-xl p-5 bg-indigo-50/40">
          <h2 className="text-lg font-semibold text-gray-800 mb-1">Your Tags</h2>
          <p className="text-xs text-gray-500 mb-4">
            Your personal take on this book — used only to improve your recommendations.
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Personal tropes */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Tropes</h3>
              {myTags.tropes.length > 0 && (
                <div className="space-y-2 mb-3">
                  {myTags.tropes.map(({ trope, weight }) => (
                    <div key={trope.trope_id} className="flex items-center gap-2 bg-white rounded-lg px-3 py-2 border border-indigo-100">
                      <span className="text-sm text-gray-800 flex-1">{trope.name}</span>
                      <WeightBar value={weight} />
                      <button
                        onClick={() => handleRemoveTrope(trope.trope_id)}
                        className="text-gray-400 hover:text-red-500 text-xs ml-1"
                        title="Remove"
                      >✕</button>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex gap-2 items-center">
                <select
                  value={addTropeId}
                  onChange={e => setAddTropeId(e.target.value ? Number(e.target.value) : '')}
                  className="flex-1 text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white"
                >
                  <option value="">Add a trope…</option>
                  {allTropes
                    .filter(t => !taggedTropeIds.has(t.trope_id))
                    .map(t => (
                      <option key={t.trope_id} value={t.trope_id}>{t.name}</option>
                    ))}
                </select>
                <input
                  type="range" min={0} max={1} step={0.05}
                  value={addTropeWeight}
                  onChange={e => setAddTropeWeight(Number(e.target.value))}
                  className="w-20"
                  title={`Weight: ${Math.round(addTropeWeight * 100)}%`}
                />
                <span className="text-xs text-gray-500 w-8">{Math.round(addTropeWeight * 100)}%</span>
                <button
                  onClick={handleAddTrope}
                  disabled={addTropeId === '' || tagSaving}
                  className="px-3 py-1.5 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40"
                >Add</button>
              </div>
            </div>

            {/* Personal archetypes */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Character Archetypes</h3>
              {myTags.archetypes.length > 0 && (
                <div className="space-y-2 mb-3">
                  {myTags.archetypes.map(({ archetype, importance }) => (
                    <div key={archetype.archetype_id} className="flex items-center gap-2 bg-white rounded-lg px-3 py-2 border border-indigo-100">
                      <span className="text-sm text-gray-800 flex-1">{archetype.name}</span>
                      <ImportanceDots value={importance} />
                      <span className="text-xs text-gray-400 ml-1">{importance}/10</span>
                      <button
                        onClick={() => handleRemoveArchetype(archetype.archetype_id)}
                        className="text-gray-400 hover:text-red-500 text-xs ml-1"
                        title="Remove"
                      >✕</button>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex gap-2 items-center">
                <select
                  value={addArchetypeId}
                  onChange={e => setAddArchetypeId(e.target.value ? Number(e.target.value) : '')}
                  className="flex-1 text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white"
                >
                  <option value="">Add an archetype…</option>
                  {allArchetypes
                    .filter(a => !taggedArchetypeIds.has(a.archetype_id))
                    .map(a => (
                      <option key={a.archetype_id} value={a.archetype_id}>{a.name}</option>
                    ))}
                </select>
                <input
                  type="range" min={1} max={10} step={1}
                  value={addArchetypeImportance}
                  onChange={e => setAddArchetypeImportance(Number(e.target.value))}
                  className="w-20"
                  title={`Importance: ${addArchetypeImportance}/10`}
                />
                <span className="text-xs text-gray-500 w-8">{addArchetypeImportance}/10</span>
                <button
                  onClick={handleAddArchetype}
                  disabled={addArchetypeId === '' || tagSaving}
                  className="px-3 py-1.5 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40"
                >Add</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Series */}
      {seriesBooks.length > 1 && book.series && (
        <div>
          <h2 className="text-lg font-semibold text-gray-800 mb-4">{book.series.name}</h2>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {seriesBooks.map(sb => (
              <Link
                key={sb.book_id}
                to={`/books/${sb.book_id}`}
                className={`shrink-0 w-28 group ${sb.book_id === book.book_id ? 'opacity-60 pointer-events-none' : ''}`}
              >
                {sb.cover_url ? (
                  <img
                    src={sb.cover_url}
                    alt={`Cover of ${sb.title}`}
                    className="w-28 h-40 object-cover rounded-lg shadow-sm group-hover:shadow-md transition-shadow"
                  />
                ) : (
                  <div className="w-28 h-40 bg-gray-100 rounded-lg shadow-sm flex items-center justify-center text-3xl select-none">📖</div>
                )}
                {sb.series_position != null && (
                  <p className="mt-1 text-xs font-semibold text-indigo-600">#{sb.series_position}</p>
                )}
                <p className="text-xs font-medium text-gray-800 line-clamp-2 leading-snug mt-0.5">{sb.title}</p>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Reviews */}
      {reviews.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            Reviews
            <span className="ml-2 text-sm font-normal text-gray-400">({reviews.length})</span>
          </h2>
          <div className="space-y-4">
            {reviews.map(r => (
              <div key={r.rating_id} className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center gap-3 mb-2">
                  <div className="flex gap-0.5">
                    {[1,2,3,4,5].map(s => (
                      <span key={s} className={`text-sm ${s <= r.rating ? 'text-amber-400' : 'text-gray-200'}`}>★</span>
                    ))}
                  </div>
                  <span className="text-sm font-medium text-gray-700">{r.reviewer_name ?? 'Anonymous'}</span>
                  <span className="text-xs text-gray-400 ml-auto">
                    {new Date(r.created_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed">{r.review_text}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Similar Books */}
      {similar.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-800 mb-1">Books Like This</h2>
          <p className="text-xs text-gray-400 mb-4">Matched by tropes, archetypes &amp; genres</p>
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
                      <span className="shrink-0 text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                        {Math.round(score * 100)}%
                      </span>
                    </div>
                    {sharedTags.length > 0 && (
                      <p className="text-xs text-gray-400 mt-1.5 line-clamp-2">
                        {sharedTags.join(' · ')}
                      </p>
                    )}
                  </div>
                </Link>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
