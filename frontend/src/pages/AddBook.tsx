import { useEffect, useRef, useState } from 'react'
import { useBlocker, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Archetype, Author, BookType, Genre, Tone, Trope } from '../api/client'
import { ConfirmModal } from '../components/ConfirmModal'
import { useToast } from '../contexts/ToastContext'

const WEIGHT_TIERS = [
  { value: 1.0,  label: '1.0 — Structural', description: 'The story is a deconstruction of this trope' },
  { value: 0.85, label: '0.85 — Dominant',   description: 'A primary plot engine, present throughout' },
  { value: 0.65, label: '0.65 — Major',       description: 'Significant subplot or recurring theme' },
  { value: 0.45, label: '0.45 — Supporting',  description: 'Present and meaningful but not central' },
  { value: 0.25, label: '0.25 — Minor',       description: 'A brief arc or secondary character trait' },
  { value: 0.10, label: '0.10 — Flavor',      description: 'A single scene or blink-and-miss-it nod' },
]

const IMPORTANCE_TIERS = [
  { value: 10, label: '10 — Central',     description: 'Defines the character entirely' },
  { value: 9,  label: '9 — Dominant',     description: 'The primary lens for the character' },
  { value: 8,  label: '8 — Strong',       description: 'A major, consistent character trait' },
  { value: 7,  label: '7 — Significant',  description: 'Clearly present throughout the story' },
  { value: 6,  label: '6 — Moderate',     description: 'Present and meaningful' },
  { value: 5,  label: '5 — Notable',      description: 'Noticeable but not defining' },
  { value: 4,  label: '4 — Supporting',   description: 'A secondary character quality' },
  { value: 3,  label: '3 — Minor',        description: 'Occasionally surfaces' },
  { value: 2,  label: '2 — Subtle',       description: 'Barely perceptible' },
  { value: 1,  label: '1 — Background',   description: 'A fleeting hint only' },
]

const MAX_TROPES = 12
const MAX_ARCHETYPES = 8
const MIN_DOMINANT_WEIGHT = 0.65

type SelectedTrope = { trope: Trope; weight: number }
type SelectedArchetype = { archetype: Archetype; importance: number }

export function AddBook() {
  const navigate = useNavigate()
  const toast = useToast()

  // Metadata
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [isbn, setIsbn] = useState('')
  const [pubDate, setPubDate] = useState('')
  const [description, setDescription] = useState('')
  const [seriesName, setSeriesName] = useState('')
  const [seriesPosition, setSeriesPosition] = useState('')

  // Author autocomplete
  const [allAuthors, setAllAuthors] = useState<Author[]>([])
  const [showAuthors, setShowAuthors] = useState(false)
  const authorRef = useRef<HTMLDivElement>(null)

  // Trope search
  const [allTropes, setAllTropes] = useState<Trope[]>([])
  const [tropeQuery, setTropeQuery] = useState('')
  const [showTropes, setShowTropes] = useState(false)
  const [tropeHighlight, setTropeHighlight] = useState(-1)
  const tropeRef = useRef<HTMLDivElement>(null)
  const tropeListRef = useRef<HTMLUListElement>(null)

  // Archetype search
  const [allArchetypes, setAllArchetypes] = useState<Archetype[]>([])
  const [archetypeQuery, setArchetypeQuery] = useState('')
  const [showArchetypes, setShowArchetypes] = useState(false)
  const [archetypeHighlight, setArchetypeHighlight] = useState(-1)
  const archetypeRef = useRef<HTMLDivElement>(null)
  const archetypeListRef = useRef<HTMLUListElement>(null)

  // Genres
  const [allGenres, setAllGenres] = useState<Genre[]>([])
  const [selectedGenreIds, setSelectedGenreIds] = useState<Set<number>>(new Set())

  // Book types
  const [allBookTypes, setAllBookTypes] = useState<BookType[]>([])
  const [selectedBookTypeIds, setSelectedBookTypeIds] = useState<Set<number>>(new Set())

  // Tones
  const [allTones, setAllTones] = useState<Tone[]>([])
  const [selectedToneIds, setSelectedToneIds] = useState<Set<number>>(new Set())

  // Pacing
  const [pacing, setPacing] = useState<number | null>(null)

  // Selections
  const [selectedTropes, setSelectedTropes] = useState<SelectedTrope[]>([])
  const [selectedArchetypes, setSelectedArchetypes] = useState<SelectedArchetype[]>([])

  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [navigateTo, setNavigateTo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const isDirty = !submitted && (
    title.trim() !== '' || author.trim() !== '' || isbn.trim() !== '' ||
    selectedTropes.length > 0 || selectedArchetypes.length > 0
  )

  const blocker = useBlocker(isDirty)

  // Navigate only after submitted=true has re-rendered, so the blocker sees isDirty=false.
  useEffect(() => {
    if (navigateTo) navigate(navigateTo)
  }, [navigateTo, navigate])

  useEffect(() => {
    if (!isDirty) return
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault() }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [isDirty])

  useEffect(() => {
    api.tropes.list().then(setAllTropes)
    api.archetypes.list().then(setAllArchetypes)
    api.books.authors().then(setAllAuthors)
    api.genres.list().then(setAllGenres)
    api.bookTypes.list().then(setAllBookTypes)
    api.tones.list().then(setAllTones)
  }, [])

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (authorRef.current && !authorRef.current.contains(e.target as Node))
        setShowAuthors(false)
      if (tropeRef.current && !tropeRef.current.contains(e.target as Node))
        setShowTropes(false)
      if (archetypeRef.current && !archetypeRef.current.contains(e.target as Node))
        setShowArchetypes(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Filtered lists
  const filteredAuthors = author.trim()
    ? allAuthors.filter(a => a.name.toLowerCase().includes(author.toLowerCase()) && a.name !== author)
    : []

  const selectedTropeIds = new Set(selectedTropes.map(s => s.trope.trope_id))
  const filteredTropes = tropeQuery.trim()
    ? allTropes.filter(t => !selectedTropeIds.has(t.trope_id) && t.name.toLowerCase().includes(tropeQuery.toLowerCase()))
    : []

  const selectedArchetypeIds = new Set(selectedArchetypes.map(s => s.archetype.archetype_id))
  const filteredArchetypes = archetypeQuery.trim()
    ? allArchetypes.filter(a => !selectedArchetypeIds.has(a.archetype_id) && a.name.toLowerCase().includes(archetypeQuery.toLowerCase()))
    : []

  const handleTropeKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!filteredTropes.length) return
    if (e.key === 'ArrowDown') { e.preventDefault(); setTropeHighlight(i => Math.min(i + 1, filteredTropes.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setTropeHighlight(i => Math.max(i - 1, 0)) }
    else if (e.key === 'Enter' && tropeHighlight >= 0) { e.preventDefault(); addTrope(filteredTropes[tropeHighlight]); setTropeHighlight(-1) }
    else if (e.key === 'Escape') { setShowTropes(false); setTropeHighlight(-1) }
  }

  const handleArchetypeKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!filteredArchetypes.length) return
    if (e.key === 'ArrowDown') { e.preventDefault(); setArchetypeHighlight(i => Math.min(i + 1, filteredArchetypes.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setArchetypeHighlight(i => Math.max(i - 1, 0)) }
    else if (e.key === 'Enter' && archetypeHighlight >= 0) { e.preventDefault(); addArchetype(filteredArchetypes[archetypeHighlight]); setArchetypeHighlight(-1) }
    else if (e.key === 'Escape') { setShowArchetypes(false); setArchetypeHighlight(-1) }
  }

  // Trope actions
  const addTrope = (trope: Trope) => {
    if (selectedTropes.length >= MAX_TROPES) return
    setSelectedTropes(prev => [...prev, { trope, weight: 0.65 }])
    setTropeQuery('')
    setShowTropes(false)
  }
  const removeTrope = (id: number) =>
    setSelectedTropes(prev => prev.filter(s => s.trope.trope_id !== id))
  const setTropeWeight = (id: number, weight: number) =>
    setSelectedTropes(prev => prev.map(s => s.trope.trope_id === id ? { ...s, weight } : s))

  // Archetype actions
  const addArchetype = (archetype: Archetype) => {
    if (selectedArchetypes.length >= MAX_ARCHETYPES) return
    setSelectedArchetypes(prev => [...prev, { archetype, importance: 7 }])
    setArchetypeQuery('')
    setShowArchetypes(false)
  }
  const removeArchetype = (id: number) =>
    setSelectedArchetypes(prev => prev.filter(s => s.archetype.archetype_id !== id))
  const setArchetypeImportance = (id: number, importance: number) =>
    setSelectedArchetypes(prev => prev.map(s => s.archetype.archetype_id === id ? { ...s, importance } : s))

  const hasDominantTrope = selectedTropes.some(s => s.weight >= MIN_DOMINANT_WEIGHT)

  const validate = (): string | null => {
    if (selectedTropes.length > 0 && !hasDominantTrope)
      return 'At least one trope must be rated Major (0.65) or above.'
    return null
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const err = validate()
    if (err) { setError(err); return }

    setError(null)
    setSubmitting(true)
    try {
      const book = await api.books.create({
        title,
        author,
        isbn: isbn || null,
        publication_date: pubDate || null,
        description: description || null,
        series_name: seriesName.trim() || null,
        series_position: seriesPosition ? Number(seriesPosition) : null,
      })
      await Promise.all([
        ...selectedTropes.map(s => api.books.attachTrope(book.book_id, s.trope.trope_id, s.weight)),
        ...selectedArchetypes.map(s => api.books.attachArchetype(book.book_id, s.archetype.archetype_id, s.importance)),
        ...[...selectedGenreIds].map(gid => api.books.attachGenre(book.book_id, gid)),
        ...[...selectedBookTypeIds].map(tid => api.books.attachBookType(book.book_id, tid)),
        ...[...selectedToneIds].map(tid => api.books.attachTone(book.book_id, tid)),
      ])
      setSubmitted(true)
      toast.success('Book added.')
      setNavigateTo(`/books/${book.book_id}`)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Something went wrong.')
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div>
        <button
          type="button"
          onClick={() => navigate('/books')}
          className="flex items-center gap-1 text-sm text-indigo-600 hover:underline mb-4"
        >
          ← Back to Books
        </button>
        <h1 className="text-2xl font-semibold text-gray-800">Add a Book</h1>
        <p className="text-sm text-gray-500 mt-1">
          Ingest the book now — tropes and archetypes can be added here or on the book page later.
          Recommendations unlock once the book has at least 3 tropes.
        </p>
      </div>

      <form onSubmit={submit} className="space-y-8">

        {/* Metadata */}
        <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Book Details</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input required value={title} onChange={e => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. The Name of the Wind" />
          </div>

          <div ref={authorRef} className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-1">Author</label>
            <input required value={author}
              onChange={e => { setAuthor(e.target.value); setShowAuthors(true) }}
              onFocus={() => setShowAuthors(true)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. Patrick Rothfuss"
            />
            {showAuthors && filteredAuthors.length > 0 && (
              <ul className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg max-h-48 overflow-y-auto">
                {filteredAuthors.map(a => (
                  <li key={a.author_id}>
                    <button type="button" onMouseDown={e => e.preventDefault()}
                      onClick={() => { setAuthor(a.name); setShowAuthors(false) }}
                      className="w-full text-left px-4 py-2 text-sm hover:bg-indigo-50 text-gray-800">
                      {a.name}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
              <span className="ml-1 text-gray-400 font-normal">(optional)</span>
            </label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
              placeholder="A brief synopsis of the book…"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">ISBN</label>
              <input required value={isbn} onChange={e => setIsbn(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="978-0-00-000000-0" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Publication Date</label>
              <input required type="date" value={pubDate} onChange={e => setPubDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Series Name <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <input value={seriesName} onChange={e => setSeriesName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="e.g. The Stormlight Archive" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Book # in Series <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <input type="number" min="1" value={seriesPosition} onChange={e => setSeriesPosition(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="1" />
            </div>
          </div>
        </section>

        {/* Genres */}
        <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Genres
              <span className="ml-1 text-gray-400 font-normal normal-case">(optional)</span>
            </h2>
            <p className="text-xs text-gray-400 mt-1">Select all that apply.</p>
          </div>
          {allGenres.length === 0 ? (
            <p className="text-xs text-gray-400">No genres defined yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {allGenres.map((g) => (
                <button
                  key={g.genre_id}
                  type="button"
                  onClick={() => setSelectedGenreIds(prev => {
                    const next = new Set(prev)
                    if (next.has(g.genre_id)) next.delete(g.genre_id)
                    else next.add(g.genre_id)
                    return next
                  })}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    selectedGenreIds.has(g.genre_id)
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {g.name}
                </button>
              ))}
            </div>
          )}
        </section>

        {/* Book Types */}
        <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Book Type
              <span className="ml-1 text-gray-400 font-normal normal-case">(optional)</span>
            </h2>
            <p className="text-xs text-gray-400 mt-1">e.g. Novel, YA, Short Story. Select all that apply.</p>
          </div>
          {allBookTypes.length === 0 ? (
            <p className="text-xs text-gray-400">No book types defined yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {allBookTypes.map((bt) => (
                <button
                  key={bt.book_type_id}
                  type="button"
                  onClick={() => setSelectedBookTypeIds(prev => {
                    const next = new Set(prev)
                    if (next.has(bt.book_type_id)) next.delete(bt.book_type_id)
                    else next.add(bt.book_type_id)
                    return next
                  })}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    selectedBookTypeIds.has(bt.book_type_id)
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {bt.name}
                </button>
              ))}
            </div>
          )}
        </section>

        {/* Pacing */}
        <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Pacing
              <span className="ml-1 text-gray-400 font-normal normal-case">(optional)</span>
            </h2>
            <p className="text-xs text-gray-400 mt-1">How fast does the story move?</p>
          </div>
          <div className="flex gap-2">
            {[
              { value: 1, label: 'Very Slow' },
              { value: 2, label: 'Slow' },
              { value: 3, label: 'Moderate' },
              { value: 4, label: 'Fast' },
              { value: 5, label: 'Very Fast' },
            ].map(({ value, label }) => (
              <button
                key={value}
                type="button"
                onClick={() => setPacing(pacing === value ? null : value)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                  pacing === value
                    ? 'bg-emerald-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </section>

        {/* Tones */}
        <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Tone
              <span className="ml-1 text-gray-400 font-normal normal-case">(optional)</span>
            </h2>
            <p className="text-xs text-gray-400 mt-1">The emotional feel of the book. Select all that apply.</p>
          </div>
          {allTones.length === 0 ? (
            <p className="text-xs text-gray-400">No tones defined yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {allTones.map((t) => (
                <button
                  key={t.tone_id}
                  type="button"
                  onClick={() => setSelectedToneIds(prev => {
                    const next = new Set(prev)
                    if (next.has(t.tone_id)) next.delete(t.tone_id)
                    else next.add(t.tone_id)
                    return next
                  })}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    selectedToneIds.has(t.tone_id)
                      ? 'bg-amber-500 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {t.name}
                </button>
              ))}
            </div>
          )}
        </section>

        {/* Tropes */}
        <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                Tropes
                <span className="ml-1 text-gray-400 font-normal normal-case">(optional)</span>
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Recommendations unlock at 3 tropes. You can add more on the book page after creation.
              </p>
            </div>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${
              selectedTropes.length >= MAX_TROPES
                ? 'bg-red-100 text-red-600'
                : selectedTropes.length >= 3
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-gray-100 text-gray-500'
            }`}>
              {selectedTropes.length}/{MAX_TROPES}
            </span>
          </div>

          {selectedTropes.length > 0 && selectedTropes.length < 3 && (
            <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
              <span>{selectedTropes.length}/3 tropes — add {3 - selectedTropes.length} more to unlock recommendations.</span>
            </div>
          )}

          <div className="bg-gray-50 rounded-lg p-3 space-y-1.5">
            {WEIGHT_TIERS.map(t => (
              <div key={t.value} className="grid grid-cols-[3rem_6rem_1fr] gap-x-2 text-xs items-baseline">
                <span className="font-mono font-semibold text-indigo-600">{t.value.toFixed(2)}</span>
                <span className="font-medium text-gray-700">{t.label.split('—')[1].trim()}</span>
                <span className="text-gray-400">{t.description}</span>
              </div>
            ))}
          </div>

          <div ref={tropeRef} className="relative">
            <input value={tropeQuery}
              onChange={e => { setTropeQuery(e.target.value); setShowTropes(true); setTropeHighlight(-1) }}
              onFocus={() => setShowTropes(true)}
              onKeyDown={handleTropeKeyDown}
              disabled={selectedTropes.length >= MAX_TROPES}
              placeholder={selectedTropes.length >= MAX_TROPES ? 'Maximum tropes reached' : 'Search tropes…'}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-50 disabled:text-gray-400"
            />
            {showTropes && filteredTropes.length > 0 && (
              <ul ref={tropeListRef} className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg max-h-52 overflow-y-auto">
                {filteredTropes.map((trope, idx) => (
                  <li key={trope.trope_id}>
                    <button type="button"
                      onMouseEnter={() => setTropeHighlight(idx)}
                      onClick={() => { addTrope(trope); setTropeHighlight(-1) }}
                      className={`w-full text-left px-4 py-2.5 text-sm ${idx === tropeHighlight ? 'bg-indigo-50' : 'hover:bg-indigo-50'}`}>
                      <span className="font-medium text-gray-800">{trope.name}</span>
                      <span className="ml-2 text-xs text-gray-400">{trope.category}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {selectedTropes.length > 0 && (
            <ul className="space-y-2">
              {selectedTropes.map(({ trope, weight }) => (
                <li key={trope.trope_id}
                  className="flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{trope.name}</p>
                    <p className="text-xs text-gray-400">{trope.category}</p>
                  </div>
                  <select value={weight} onChange={e => setTropeWeight(trope.trope_id, Number(e.target.value))}
                    className="text-xs border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
                    {WEIGHT_TIERS.map(t => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                  <button type="button" onClick={() => removeTrope(trope.trope_id)}
                    className="text-gray-400 hover:text-red-500 transition-colors text-lg leading-none">×</button>
                </li>
              ))}
            </ul>
          )}

          {selectedTropes.length > 0 && !hasDominantTrope && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
              At least one trope should be rated Major (0.65) or above for a meaningful embedding.
            </p>
          )}
        </section>

        {/* Archetypes */}
        <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Character Archetypes
              <span className="ml-1 text-gray-400 font-normal normal-case">(optional)</span>
            </h2>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
              selectedArchetypes.length >= MAX_ARCHETYPES ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-500'
            }`}>
              {selectedArchetypes.length}/{MAX_ARCHETYPES}
            </span>
          </div>

          <div className="bg-gray-50 rounded-lg p-3 space-y-1.5">
            {IMPORTANCE_TIERS.filter(t => [10, 7, 4, 1].includes(t.value)).map(t => (
              <div key={t.value} className="grid grid-cols-[3rem_6rem_1fr] gap-x-2 text-xs items-baseline">
                <span className="font-mono font-semibold text-indigo-600">{t.value}</span>
                <span className="font-medium text-gray-700">{t.label.split('—')[1].trim()}</span>
                <span className="text-gray-400">{t.description}</span>
              </div>
            ))}
          </div>

          <div ref={archetypeRef} className="relative">
            <input value={archetypeQuery}
              onChange={e => { setArchetypeQuery(e.target.value); setShowArchetypes(true); setArchetypeHighlight(-1) }}
              onFocus={() => setShowArchetypes(true)}
              onKeyDown={handleArchetypeKeyDown}
              disabled={selectedArchetypes.length >= MAX_ARCHETYPES}
              placeholder={selectedArchetypes.length >= MAX_ARCHETYPES ? 'Maximum archetypes reached' : 'Search archetypes…'}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-50 disabled:text-gray-400"
            />
            {showArchetypes && filteredArchetypes.length > 0 && (
              <ul ref={archetypeListRef} className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg max-h-52 overflow-y-auto">
                {filteredArchetypes.map((archetype, idx) => (
                  <li key={archetype.archetype_id}>
                    <button type="button"
                      onMouseEnter={() => setArchetypeHighlight(idx)}
                      onClick={() => { addArchetype(archetype); setArchetypeHighlight(-1) }}
                      className={`w-full text-left px-4 py-2.5 text-sm ${idx === archetypeHighlight ? 'bg-indigo-50' : 'hover:bg-indigo-50'}`}>
                      <span className="font-medium text-gray-800">{archetype.name}</span>
                      {archetype.description && (
                        <span className="ml-2 text-xs text-gray-400 truncate">{archetype.description}</span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {selectedArchetypes.length > 0 && (
            <ul className="space-y-2">
              {selectedArchetypes.map(({ archetype, importance }) => (
                <li key={archetype.archetype_id}
                  className="flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{archetype.name}</p>
                    {archetype.description && (
                      <p className="text-xs text-gray-400 truncate">{archetype.description}</p>
                    )}
                  </div>
                  <select value={importance} onChange={e => setArchetypeImportance(archetype.archetype_id, Number(e.target.value))}
                    className="text-xs border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
                    {IMPORTANCE_TIERS.map(t => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                  <button type="button" onClick={() => removeArchetype(archetype.archetype_id)}
                    className="text-gray-400 hover:text-red-500 transition-colors text-lg leading-none">×</button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-md px-4 py-3">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          <button type="submit" disabled={submitting}
            className="px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
            {submitting ? 'Saving…' : 'Add Book'}
          </button>
        </div>
      </form>

      {blocker.state === 'blocked' && (
        <ConfirmModal
          title="Leave without saving?"
          message="You have unsaved changes. Are you sure you want to leave?"
          confirmLabel="Leave"
          onConfirm={() => blocker.proceed()}
          onCancel={() => blocker.reset()}
        />
      )}
    </div>
  )
}
