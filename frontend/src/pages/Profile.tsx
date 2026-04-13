import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { BookType, Genre, Tone, UserPreferences } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'

// ── small inline chip picker (same pattern as Books.tsx) ─────────────────────

function BlocklistPicker<T>({
  label,
  placeholder,
  blocked,
  options,
  getKey,
  getName,
  onAdd,
  onRemove,
}: {
  label: string
  placeholder: string
  blocked: T[]
  options: T[]
  getKey: (item: T) => number
  getName: (item: T) => string
  onAdd: (item: T) => void
  onRemove: (item: T) => void
}) {
  const [query, setQuery] = useState('')
  const ref = useRef<HTMLDivElement>(null)
  const blockedKeys = new Set(blocked.map(getKey))

  const filtered = query.trim()
    ? options.filter(o => !blockedKeys.has(getKey(o)) && getName(o).toLowerCase().includes(query.toLowerCase()))
    : []

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setQuery('')
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div>
      <p className="text-sm font-medium text-gray-700 mb-2">{label}</p>
      {blocked.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {blocked.map(item => (
            <span
              key={getKey(item)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200"
            >
              {getName(item)}
              <button
                type="button"
                onClick={() => onRemove(item)}
                className="leading-none opacity-60 hover:opacity-100"
              >×</button>
            </span>
          ))}
        </div>
      )}
      <div ref={ref} className="relative w-64">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder={placeholder}
          className="w-full px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
        {filtered.length > 0 && (
          <ul className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg max-h-44 overflow-y-auto">
            {filtered.map(item => (
              <li key={getKey(item)}>
                <button
                  type="button"
                  onClick={() => { onAdd(item); setQuery('') }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-red-50 text-gray-800"
                >
                  {getName(item)}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

// ── main page ─────────────────────────────────────────────────────────────────

export function Profile() {
  const { profile, updateProfile } = useAuth()
  const toast = useToast()

  // Reference data for pickers
  const [genres, setGenres] = useState<Genre[]>([])
  const [bookTypes, setBookTypes] = useState<BookType[]>([])
  const [tones, setTones] = useState<Tone[]>([])

  // Name form
  const [name, setName] = useState(profile?.name ?? '')
  const [nameSaving, setNameSaving] = useState(false)

  // Blacklist — local state derived from profile, saved on change
  const [prefs, setPrefs] = useState<UserPreferences>(() => profile?.preferences ?? {
    blocked_genre_ids: [],
    blocked_book_type_ids: [],
    blocked_tone_ids: [],
    profile_public: true,
  })
  const [prefsSaving, setPrefsSaving] = useState(false)

  useEffect(() => {
    api.genres.list().then(setGenres).catch(() => {})
    api.bookTypes.list().then(setBookTypes).catch(() => {})
    api.tones.list().then(setTones).catch(() => {})
  }, [])

  // Sync prefs from profile when it loads
  useEffect(() => {
    if (profile?.preferences) setPrefs(profile.preferences)
    if (profile?.name) setName(profile.name)
  }, [profile])

  const saveName = async () => {
    setNameSaving(true)
    try {
      await updateProfile({ name: name.trim() || null })
      toast.success('Name updated.')
    } catch {
      toast.error('Failed to update name.')
    } finally {
      setNameSaving(false)
    }
  }

  const savePrefs = async (next: UserPreferences) => {
    setPrefs(next)
    setPrefsSaving(true)
    try {
      await updateProfile({ preferences: next })
    } catch {
      toast.error('Failed to save preferences.')
      // revert
      if (profile?.preferences) setPrefs(profile.preferences)
    } finally {
      setPrefsSaving(false)
    }
  }

  // Derived objects for display from IDs stored in prefs
  const blockedGenres = genres.filter(g => prefs.blocked_genre_ids.includes(g.genre_id))
  const blockedBookTypes = bookTypes.filter(bt => prefs.blocked_book_type_ids.includes(bt.book_type_id))
  const blockedTones = tones.filter(t => prefs.blocked_tone_ids.includes(t.tone_id))

  if (!profile) return null

  return (
    <div className="max-w-2xl space-y-8">
      <h1 className="text-2xl font-semibold text-gray-800">Profile</h1>

      {/* ── Account ── */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-5">
        <h2 className="text-base font-semibold text-gray-800">Account</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
          <p className="text-sm text-gray-500">{profile.email}</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Display name</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && saveName()}
              placeholder="Your name"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />
            <button
              onClick={saveName}
              disabled={nameSaving || name === (profile.name ?? '')}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40 transition-colors"
            >
              {nameSaving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-700">Public profile</p>
            <p className="text-xs text-gray-400 mt-0.5">
              {prefs.profile_public
                ? 'Anyone can find you and see your shelf.'
                : 'Only followers can see your shelf.'}
            </p>
          </div>
          <button
            type="button"
            onClick={() => savePrefs({ ...prefs, profile_public: !prefs.profile_public })}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none ${
              prefs.profile_public ? 'bg-indigo-600' : 'bg-gray-300'
            }`}
            role="switch"
            aria-checked={prefs.profile_public}
          >
            <span
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition-transform ${
                prefs.profile_public ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        <div className="text-xs text-gray-400">
          Member since {new Date(profile.created_at).toLocaleDateString()}
          {profile.is_admin && <span className="ml-3 px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-medium">Admin</span>}
        </div>
      </div>

      {/* ── Content Blacklist ── */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-6">
        <div>
          <h2 className="text-base font-semibold text-gray-800">Content Preferences</h2>
          <p className="text-sm text-gray-500 mt-1">
            Books with any of these labels will never appear in your browse results or recommendations.
            {prefsSaving && <span className="ml-2 text-indigo-500 text-xs">Saving…</span>}
          </p>
        </div>

        <BlocklistPicker
          label="Blocked Genres"
          placeholder="Search genres to block…"
          blocked={blockedGenres}
          options={genres}
          getKey={g => g.genre_id}
          getName={g => g.name}
          onAdd={g => savePrefs({ ...prefs, blocked_genre_ids: [...prefs.blocked_genre_ids, g.genre_id] })}
          onRemove={g => savePrefs({ ...prefs, blocked_genre_ids: prefs.blocked_genre_ids.filter(id => id !== g.genre_id) })}
        />

        <BlocklistPicker
          label="Blocked Book Types"
          placeholder="Search book types to block…"
          blocked={blockedBookTypes}
          options={bookTypes}
          getKey={bt => bt.book_type_id}
          getName={bt => bt.name}
          onAdd={bt => savePrefs({ ...prefs, blocked_book_type_ids: [...prefs.blocked_book_type_ids, bt.book_type_id] })}
          onRemove={bt => savePrefs({ ...prefs, blocked_book_type_ids: prefs.blocked_book_type_ids.filter(id => id !== bt.book_type_id) })}
        />

        <BlocklistPicker
          label="Blocked Tones"
          placeholder="Search tones to block…"
          blocked={blockedTones}
          options={tones}
          getKey={t => t.tone_id}
          getName={t => t.name}
          onAdd={t => savePrefs({ ...prefs, blocked_tone_ids: [...prefs.blocked_tone_ids, t.tone_id] })}
          onRemove={t => savePrefs({ ...prefs, blocked_tone_ids: prefs.blocked_tone_ids.filter(id => id !== t.tone_id) })}
        />

        {(prefs.blocked_genre_ids.length > 0 || prefs.blocked_book_type_ids.length > 0 || prefs.blocked_tone_ids.length > 0) && (
          <button
            onClick={() => savePrefs({ blocked_genre_ids: [], blocked_book_type_ids: [], blocked_tone_ids: [] })}
            className="text-sm text-red-500 hover:text-red-700 transition-colors"
          >
            Clear all blocked content
          </button>
        )}
      </div>
    </div>
  )
}
