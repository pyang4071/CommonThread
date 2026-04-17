import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Archetype, Book, BookType, Genre, SimilarBook, Tone, Trope } from '../api/client'
import { ConfirmModal } from '../components/ConfirmModal'
import { ReadingStatusButton } from '../components/ReadingStatusButton'
import type { StatusValue } from '../components/ReadingStatusButton'
import { useAuth } from '../contexts/AuthContext'
import { useSessionState } from '../hooks/useSessionState'

const PAGE_SIZE = 25

const SHELF_OPTIONS = [
  { value: 'want_to_read',      label: '🔖 Want to Read', active: 'bg-indigo-600 text-white',  inactive: 'bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100' },
  { value: 'currently_reading', label: '📖 Reading',       active: 'bg-amber-500 text-white',   inactive: 'bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100' },
  { value: 'read',              label: '✓ Read',           active: 'bg-emerald-600 text-white',  inactive: 'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100' },
  { value: 'not_on_shelf',      label: '✕ Not on shelf',   active: 'bg-gray-600 text-white',    inactive: 'bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200' },
]

// ── typeahead picker ──────────────────────────────────────────────────────────

function ChipPicker<T>({
  label,
  placeholder,
  selected,
  options,
  getKey,
  getName,
  getSecondary,
  onAdd,
  onRemove,
  chipColor = 'include',
}: {
  label: string
  placeholder: string
  selected: T[]
  options: T[]
  getKey: (item: T) => string | number
  getName: (item: T) => string
  getSecondary?: (item: T) => string | undefined
  onAdd: (item: T) => void
  onRemove: (item: T) => void
  chipColor?: 'include' | 'exclude'
}) {
  const [query, setQuery] = useState('')
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const ref = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const selectedKeys = new Set(selected.map(getKey))

  const filtered = query.trim()
    ? options.filter(o => !selectedKeys.has(getKey(o)) && getName(o).toLowerCase().includes(query.toLowerCase()))
    : []
  const visible = filtered.slice(0, 8)

  // Reset highlight when filtered list changes
  useEffect(() => { setHighlightedIndex(-1) }, [query])

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const el = listRef.current.children[highlightedIndex] as HTMLElement | undefined
      el?.scrollIntoView({ block: 'nearest' })
    }
  }, [highlightedIndex])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setQuery('')
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!visible.length) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlightedIndex(i => Math.min(i + 1, visible.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlightedIndex(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && highlightedIndex >= 0) {
      e.preventDefault()
      onAdd(visible[highlightedIndex])
      setQuery('')
    } else if (e.key === 'Escape') {
      setQuery('')
    }
  }

  const chipClass = chipColor === 'exclude'
    ? 'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200'
    : 'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200'
  const ringClass = chipColor === 'exclude' ? 'focus:ring-red-300' : 'focus:ring-indigo-300'
  const hoverClass = chipColor === 'exclude' ? 'hover:bg-red-50' : 'hover:bg-indigo-50'
  const highlightClass = chipColor === 'exclude' ? 'bg-red-50' : 'bg-indigo-50'

  return (
    <div>
      <p className="text-xs text-gray-500 mb-1.5">{label}</p>
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {selected.map(item => (
            <span key={getKey(item)} className={chipClass}>
              {getName(item)}
              <button type="button" onClick={() => onRemove(item)} className="leading-none opacity-60 hover:opacity-100">×</button>
            </span>
          ))}
        </div>
      )}
      <div ref={ref} className="relative w-56">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={`w-full px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 ${ringClass}`}
          aria-autocomplete="list"
          aria-expanded={visible.length > 0}
        />
        {visible.length > 0 && (
          <ul ref={listRef} className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg max-h-44 overflow-y-auto" role="listbox">
            {visible.map((item, idx) => (
              <li key={getKey(item)} role="option" aria-selected={idx === highlightedIndex}>
                <button
                  type="button"
                  onMouseEnter={() => setHighlightedIndex(idx)}
                  onClick={() => { onAdd(item); setQuery('') }}
                  className={`w-full text-left px-3 py-2 text-sm text-gray-800 ${idx === highlightedIndex ? highlightClass : hoverClass}`}
                >
                  <span className="font-medium">{getName(item)}</span>
                  {getSecondary?.(item) && (
                    <span className="ml-1.5 text-xs text-gray-400">{getSecondary(item)}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

export function Books() {
  const { session, profile, isAdmin } = useAuth()
  useEffect(() => { document.title = 'Browse Books — CommonThread' }, [])

  // Reference data
  const [genres, setGenres] = useState<Genre[]>([])
  const [bookTypes, setBookTypes] = useState<BookType[]>([])
  const [tones, setTones] = useState<Tone[]>([])
  const [tropeCategories, setTropeCategories] = useState<string[]>([])
  const [allTropes, setAllTropes] = useState<Trope[]>([])
  const [allArchetypes, setAllArchetypes] = useState<Archetype[]>([])
  const [refDataError, setRefDataError] = useState(false)

  // Book list
  const [books, setBooks] = useState<Book[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useSessionState('books:page', 0)
  const [shelfMap, setShelfMap] = useState<Record<number, StatusValue>>({})
  const [shelfVersion, setShelfVersion] = useState(0)

  // Panel visibility — persisted so panels stay open on return
  const [filtersOpen, setFiltersOpen] = useSessionState('books:filtersOpen', false)
  const [vibeOpen, setVibeOpen] = useSessionState('books:vibeOpen', false)

  // ── shared filter state — all persisted across navigation ──
  const [selectedGenres, setSelectedGenres] = useSessionState<Genre[]>('books:selectedGenres', [])
  const [selectedBookTypes, setSelectedBookTypes] = useSessionState<BookType[]>('books:selectedBookTypes', [])
  const [selectedTones, setSelectedTones] = useSessionState<Tone[]>('books:selectedTones', [])
  const [selectedCategories, setSelectedCategories] = useSessionState<string[]>('books:selectedCategories', [])
  const [pacing, setPacing] = useSessionState<number | undefined>('books:pacing', undefined)
  const [excludedTropes, setExcludedTropes] = useSessionState<Trope[]>('books:excludedTropes', [])
  const [excludedArchetypes, setExcludedArchetypes] = useSessionState<Archetype[]>('books:excludedArchetypes', [])

  // ── shelf filter ──
  const [shelfFilter, setShelfFilter] = useSessionState<string | undefined>('books:shelfFilter', undefined)

  // ── keyword search ──
  const [searchInput, setSearchInput] = useSessionState('books:searchInput', '')
  const [search, setSearch] = useSessionState('books:search', '')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ── vibe search ──
  const [promptInput, setPromptInput] = useSessionState('books:promptInput', '')
  const [alpha, setAlpha] = useSessionState('books:alpha', 0.7)
  const [semanticResults, setSemanticResults] = useState<SimilarBook[] | null>(null)
  const [semanticLoading, setSemanticLoading] = useState(false)
  const [semanticError, setSemanticError] = useState<string | null>(null)

  // ── derived ──
  const blocked = profile?.preferences ?? { blocked_genre_ids: [], blocked_book_type_ids: [], blocked_tone_ids: [] }

  const sharedFilterParams = {
    categories: selectedCategories,
    genreIds: selectedGenres.map(g => g.genre_id),
    bookTypeIds: selectedBookTypes.map(bt => bt.book_type_id),
    toneIds: selectedTones.map(t => t.tone_id),
    pacing,
    excludeTropeIds: excludedTropes.map(t => t.trope_id),
    excludeArchetypeIds: excludedArchetypes.map(a => a.archetype_id),
    excludeGenreIds: blocked.blocked_genre_ids,
    excludeBookTypeIds: blocked.blocked_book_type_ids,
    excludeToneIds: blocked.blocked_tone_ids,
  }

  const activeFilterCount =
    selectedGenres.length + selectedBookTypes.length + selectedTones.length +
    selectedCategories.length + (pacing != null ? 1 : 0) +
    excludedTropes.length + excludedArchetypes.length +
    (shelfFilter ? 1 : 0)

  // ── data loading ──
  useEffect(() => {
    const onError = () => setRefDataError(true)
    api.genres.list().then(setGenres).catch(onError)
    api.bookTypes.list().then(setBookTypes).catch(onError)
    api.tones.list().then(setTones).catch(onError)
    api.tropes.categories().then(setTropeCategories).catch(onError)
    api.tropes.list().then(setAllTropes).catch(onError)
    api.archetypes.list().then(setAllArchetypes).catch(onError)
  }, [])

  const filterKey = [
    search,
    sharedFilterParams.categories.join(),
    sharedFilterParams.genreIds.join(),
    sharedFilterParams.bookTypeIds.join(),
    sharedFilterParams.toneIds.join(),
    pacing,
    sharedFilterParams.excludeTropeIds.join(),
    sharedFilterParams.excludeArchetypeIds.join(),
    shelfFilter ?? '',
  ].join('|')

  // Reset to page 0 when filters change
  const prevFilterKey = useRef(filterKey)
  if (prevFilterKey.current !== filterKey) {
    prevFilterKey.current = filterKey
    if (page !== 0) setPage(0)
  }

  const pageKey = `${filterKey}|${page}|${shelfVersion}`

  useEffect(() => {
    if (semanticResults) return
    setLoading(true)
    api.books
      .list({
        search: search || undefined,
        ...sharedFilterParams,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE + 1,
        shelfStatus: shelfFilter,
        token: (shelfFilter && session?.access_token) ? session.access_token : undefined,
      })
      .then(setBooks)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [pageKey])

  // ── handlers ──
  const handleSearchChange = (value: string) => {
    setSearchInput(value)
    setSemanticResults(null)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => setSearch(value), 300)
  }

  const runSemanticSearch = async () => {
    if (!promptInput.trim()) return
    setSemanticLoading(true)
    setSemanticError(null)
    try {
      const results = await api.search.semantic(promptInput.trim(), 10, alpha, sharedFilterParams)
      setSemanticResults(results)
    } catch (e: unknown) {
      setSemanticError(e instanceof Error ? e.message : 'Search failed.')
    } finally {
      setSemanticLoading(false)
    }
  }

  const clearAll = () => {
    setSearchInput(''); setSearch('')
    setSelectedGenres([]); setSelectedBookTypes([]); setSelectedTones([])
    setSelectedCategories([]); setPacing(undefined)
    setExcludedTropes([]); setExcludedArchetypes([])
    setShelfFilter(undefined)
    setSemanticResults(null); setPromptInput(''); setSemanticError(null)
  }

  useEffect(() => {
    if (!session) { setShelfMap({}); return }
    api.shelf.my(session.access_token)
      .then(entries => {
        const map: Record<number, StatusValue> = {}
        for (const e of entries) map[e.book.book_id] = e.status as StatusValue
        setShelfMap(map)
      })
      .catch(() => {})
  }, [session])

  const remove = async (book: Book) => {
    await api.books.delete(book.book_id)
    api.books.list({
      search: search || undefined, ...sharedFilterParams,
      skip: page * PAGE_SIZE, limit: PAGE_SIZE + 1,
      shelfStatus: shelfFilter,
      token: (shelfFilter && session?.access_token) ? session.access_token : undefined,
    }).then(setBooks).catch(() => {})
  }

  const [bookToDelete, setBookToDelete] = useState<Book | null>(null)

  const hasAnything = activeFilterCount > 0 || search || semanticResults

  // ── render ──
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-800">Books</h1>
        <Link to="/books/new" className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">
          + Add Book
        </Link>
      </div>

      {/* ── Search bar ── */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Search by title or author…"
          value={searchInput}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
        <button
          onClick={() => setFiltersOpen(o => !o)}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
            filtersOpen || activeFilterCount > 0
              ? 'bg-indigo-600 text-white border-indigo-600'
              : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
          }`}
        >
          Filters
          {activeFilterCount > 0 && (
            <span className={`text-xs font-semibold px-1.5 py-0.5 rounded-full ${filtersOpen ? 'bg-white text-indigo-600' : 'bg-indigo-100 text-indigo-700'}`}>
              {activeFilterCount}
            </span>
          )}
          <span className="text-xs opacity-60">{filtersOpen ? '▲' : '▼'}</span>
        </button>
        <button
          onClick={() => setVibeOpen(o => !o)}
          title="Describe a feeling or theme in plain language — e.g. 'cozy mystery with a slow-burn romance'. The slider controls how much weight goes to plot structure vs. prose vibe."
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
            vibeOpen || semanticResults
              ? 'bg-indigo-600 text-white border-indigo-600'
              : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
          }`}
        >
          Vibe Search
          <span className="text-xs opacity-60">{vibeOpen ? '▲' : '▼'}</span>
        </button>
        {hasAnything && (
          <button onClick={clearAll} className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg bg-white">
            Clear all
          </button>
        )}
      </div>

      {/* ── Filter / result summary ── */}
      {(activeFilterCount > 0 || search || semanticResults) && (
        <div className="flex items-center gap-2 text-sm text-gray-500 -mt-1">
          {semanticResults ? (
            <span>
              {semanticResults.length} vibe result{semanticResults.length !== 1 ? 's' : ''}
              {' '}for &ldquo;{promptInput}&rdquo;
            </span>
          ) : loading ? (
            <span>Loading…</span>
          ) : (
            <span>
              {Math.min(books.length, PAGE_SIZE)}{books.length > PAGE_SIZE ? '+' : ''} book{books.length !== 1 ? 's' : ''}
              {activeFilterCount > 0 && (
                <> · <span className="font-medium text-indigo-600">{activeFilterCount} filter{activeFilterCount !== 1 ? 's' : ''} active</span></>
              )}
              {search && !activeFilterCount && (
                <> · keyword &ldquo;{search}&rdquo;</>
              )}
            </span>
          )}
        </div>
      )}

      {/* ── Filter panel ── */}
      {filtersOpen && (
        <div className="animate-panel-in bg-white border border-gray-200 rounded-xl p-5 space-y-5">

          {refDataError && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              Some filter options failed to load. Refresh the page to try again.
            </p>
          )}

          {/* Include section */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">Narrow down</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              <ChipPicker
                label="Genres"
                placeholder="Add a genre…"
                selected={selectedGenres}
                options={genres}
                getKey={g => g.genre_id}
                getName={g => g.name}
                onAdd={g => setSelectedGenres(prev => [...prev, g])}
                onRemove={g => setSelectedGenres(prev => prev.filter(x => x.genre_id !== g.genre_id))}
              />
              <ChipPicker
                label="Book Types"
                placeholder="Add a type…"
                selected={selectedBookTypes}
                options={bookTypes}
                getKey={bt => bt.book_type_id}
                getName={bt => bt.name}
                onAdd={bt => setSelectedBookTypes(prev => [...prev, bt])}
                onRemove={bt => setSelectedBookTypes(prev => prev.filter(x => x.book_type_id !== bt.book_type_id))}
              />
              <ChipPicker
                label="Tones"
                placeholder="Add a tone…"
                selected={selectedTones}
                options={tones}
                getKey={t => t.tone_id}
                getName={t => t.name}
                onAdd={t => setSelectedTones(prev => [...prev, t])}
                onRemove={t => setSelectedTones(prev => prev.filter(x => x.tone_id !== t.tone_id))}
              />
              <ChipPicker
                label="Trope Categories"
                placeholder="Add a category…"
                selected={selectedCategories.map(c => ({ id: c, name: c }))}
                options={tropeCategories.map(c => ({ id: c, name: c }))}
                getKey={c => c.id}
                getName={c => c.name}
                onAdd={c => setSelectedCategories(prev => [...prev, c.id])}
                onRemove={c => setSelectedCategories(prev => prev.filter(x => x !== c.id))}
              />
            </div>

            {/* Pacing — ordinal, button group */}
            <div className="mt-4">
              <p className="text-xs text-gray-500 mb-2">Pacing</p>
              <div className="flex gap-2">
                {(['Very Slow', 'Slow', 'Moderate', 'Fast', 'Very Fast'] as const).map((label, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setPacing(pacing === i + 1 ? undefined : i + 1)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                      pacing === i + 1
                        ? 'bg-emerald-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Shelf filter — only shown when logged in */}
          {session && (
            <div className="mt-4">
              <p className="text-xs text-gray-500 mb-2">My Shelf</p>
              <div className="flex flex-wrap gap-2">
                {SHELF_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setShelfFilter(shelfFilter === opt.value ? undefined : opt.value)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                      shelfFilter === opt.value ? opt.active : opt.inactive
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="border-t border-gray-100" />

          {/* Exclude section */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">Avoid</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <ChipPicker
                label="Tropes to exclude"
                placeholder="Search tropes to exclude…"
                selected={excludedTropes}
                options={allTropes}
                getKey={t => t.trope_id}
                getName={t => t.name}
                getSecondary={t => t.category}
                onAdd={t => setExcludedTropes(prev => [...prev, t])}
                onRemove={t => setExcludedTropes(prev => prev.filter(x => x.trope_id !== t.trope_id))}
                chipColor="exclude"
              />
              <ChipPicker
                label="Archetypes to exclude"
                placeholder="Search archetypes to exclude…"
                selected={excludedArchetypes}
                options={allArchetypes}
                getKey={a => a.archetype_id}
                getName={a => a.name}
                onAdd={a => setExcludedArchetypes(prev => [...prev, a])}
                onRemove={a => setExcludedArchetypes(prev => prev.filter(x => x.archetype_id !== a.archetype_id))}
                chipColor="exclude"
              />
            </div>
          </div>
        </div>
      )}

      {/* ── Vibe search panel ── */}
      {vibeOpen && (
        <div className="animate-panel-in bg-indigo-50 border border-indigo-100 rounded-xl p-4 space-y-3">
          <div>
            <p className="text-sm font-semibold text-indigo-800">Vibe Search</p>
            <p className="text-xs text-indigo-500 mt-0.5">
              Describe a feeling, theme, or story in plain language — the engine matches by meaning, not just keywords.
              {activeFilterCount > 0 && <> Filters are still active and will narrow results.</>}
            </p>
          </div>

          {/* Example prompts */}
          <div>
            <p className="text-xs text-indigo-400 mb-1.5">Try an example:</p>
            <div className="flex flex-wrap gap-1.5">
              {[
                'cozy mystery with a found family',
                'slow-burn romance in a fantasy setting',
                'dark academia with an unreliable narrator',
                'heartwarming coming-of-age in a small town',
              ].map(example => (
                <button
                  key={example}
                  type="button"
                  onClick={() => setPromptInput(example)}
                  className="px-2.5 py-1 text-xs rounded-full bg-white border border-indigo-200 text-indigo-600 hover:bg-indigo-100 transition-colors"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>

          {/* Alpha slider */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-indigo-500">
              <span>More vibe &amp; prose</span>
              <span className="text-indigo-700 font-medium">
                {alpha >= 0.8 ? 'Structure-heavy' : alpha <= 0.2 ? 'Vibe-heavy' : `${Math.round(alpha * 100)}% structure`}
              </span>
              <span>More tropes &amp; archetypes</span>
            </div>
            <input
              type="range" min={0} max={1} step={0.05} value={alpha}
              onChange={e => setAlpha(Number(e.target.value))}
              className="w-full accent-indigo-600"
            />
          </div>

          {/* Query input + submit */}
          <div className="flex gap-2">
            <input
              type="text"
              value={promptInput}
              onChange={e => setPromptInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && runSemanticSearch()}
              placeholder="Describe what you're in the mood for…"
              className="flex-1 px-3 py-2 border border-indigo-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <button
              onClick={runSemanticSearch}
              disabled={semanticLoading || !promptInput.trim()}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {semanticLoading ? 'Searching…' : 'Find Books'}
            </button>
          </div>
          {semanticError && <p className="text-xs text-red-500">{semanticError}</p>}
        </div>
      )}

      {/* ── Vibe results ── */}
      {semanticResults && (
        <div>
          <p className="text-sm text-gray-500 mb-3">
            {semanticResults.length} result{semanticResults.length !== 1 ? 's' : ''} for &ldquo;{promptInput}&rdquo;
          </p>
          {semanticResults.length === 0 ? (
            <p className="text-gray-400 text-sm">No matches found.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {semanticResults.map(({ book, score }) => (
                <div key={book.book_id} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-indigo-300 hover:shadow-sm transition-all flex flex-col gap-2">
                  <Link to={`/books/${book.book_id}`} className="flex items-start gap-3 flex-1">
                    {book.cover_url && (
                      <img src={book.cover_url} alt="" className="w-12 shrink-0 rounded object-cover" />
                    )}
                    <div className="flex-1 min-w-0 flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-medium text-gray-800 text-sm truncate">{book.title}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{book.author.name}</p>
                        {book.publication_date && (
                          <p className="text-xs text-gray-400 mt-0.5">{new Date(book.publication_date).getFullYear()}</p>
                        )}
                      </div>
                      <span className="shrink-0 text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                        {Math.round(score * 100)}%
                      </span>
                    </div>
                  </Link>
                  {book.description && (
                    <p className="text-xs text-gray-400 line-clamp-2">{book.description}</p>
                  )}
                  <div className="pt-1 border-t border-gray-100">
                    {book.avg_rating != null ? (
                      <span className="flex items-center gap-1 text-xs font-medium text-amber-600">
                        <span className="text-amber-400">★</span>
                        {book.avg_rating.toFixed(1)}
                        <span className="text-gray-400 font-normal">/ 5</span>
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">No ratings yet</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Regular book table ── */}
      {!semanticResults && (
        <>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="bg-white border border-gray-200 rounded-lg overflow-hidden animate-pulse flex">
                  <div className="w-20 shrink-0 bg-gray-200 self-stretch" />
                  <div className="p-3 flex-1 space-y-2">
                    <div className="h-4 w-3/4 bg-gray-200 rounded" />
                    <div className="h-3 w-1/2 bg-gray-200 rounded" />
                    <div className="h-3 w-1/3 bg-gray-200 rounded" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <>
              {!error && books.length === 0 && (
                <p className="text-gray-400 text-sm">No books match your filters.</p>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {books.slice(0, PAGE_SIZE).map(b => (
                  <div key={b.book_id} className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:border-indigo-300 hover:shadow-sm transition-all flex flex-col">
                    <Link to={`/books/${b.book_id}`} className="flex flex-1 min-h-0">
                      {b.cover_url ? (
                        <img src={b.cover_url} alt="" className="w-20 shrink-0 object-cover self-stretch" />
                      ) : (
                        <div className="w-20 shrink-0 bg-gray-100 flex items-center justify-center text-gray-300 text-2xl select-none">📖</div>
                      )}
                      <div className="p-3 flex-1 min-w-0">
                        <p className="font-medium text-gray-800 text-sm leading-snug line-clamp-2">{b.title}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{b.author.name}</p>
                        {b.publication_date && (
                          <p className="text-xs text-gray-400 mt-0.5">{new Date(b.publication_date).getFullYear()}</p>
                        )}
                        {b.avg_rating != null ? (
                          <span className="mt-1 flex items-center gap-1 text-xs font-medium text-amber-600">
                            <span className="text-amber-400">★</span>{b.avg_rating.toFixed(1)}
                          </span>
                        ) : (
                          <span className="mt-1 block text-xs text-gray-300">No ratings</span>
                        )}
                      </div>
                    </Link>
                    {(session || isAdmin) && (
                      <div className="px-3 pb-3 flex items-center justify-between gap-2">
                        {session ? (
                          <ReadingStatusButton
                            bookId={b.book_id}
                            token={session.access_token}
                            initial={shelfMap[b.book_id] ?? null}
                            onChange={s => {
                              setShelfMap(prev => {
                                const next = { ...prev }
                                if (s === null) delete next[b.book_id]
                                else next[b.book_id] = s
                                return next
                              })
                              if (shelfFilter) setShelfVersion(v => v + 1)
                            }}
                          />
                        ) : <span />}
                        {isAdmin && (
                          <button
                            onClick={() => setBookToDelete(b)}
                            className="text-xs text-gray-400 hover:text-red-500 transition-colors shrink-0"
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
              {/* Pagination controls */}
              {(page > 0 || books.length > PAGE_SIZE) && (
                <div className="flex items-center justify-between pt-2">
                  <button
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="px-4 py-2 text-sm font-medium text-gray-600 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    ← Previous
                  </button>
                  <span className="text-sm text-gray-500">
                    Page {page + 1}
                    {' · '}
                    {page * PAGE_SIZE + 1}–{page * PAGE_SIZE + Math.min(books.length, PAGE_SIZE)}
                    {books.length > PAGE_SIZE ? '+' : ''}
                  </span>
                  <button
                    onClick={() => setPage(p => p + 1)}
                    disabled={books.length <= PAGE_SIZE}
                    className="px-4 py-2 text-sm font-medium text-gray-600 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}

      {bookToDelete && (
        <ConfirmModal
          title="Delete book"
          message={`Delete "${bookToDelete.title}" permanently? This cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={() => { remove(bookToDelete); setBookToDelete(null) }}
          onCancel={() => setBookToDelete(null)}
        />
      )}
    </div>
  )
}
