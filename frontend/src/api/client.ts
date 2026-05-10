const BASE = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api/v1`
  : '/api/v1'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  if (res.status === 204) return undefined as T
  return res.json()
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  if (res.status === 204) return undefined as T
  return res.json()
}

async function del(path: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
}

async function authedFetch(method: string, path: string, token: string, body?: unknown) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res
}

export type UserPreferences = {
  blocked_genre_ids: number[]
  blocked_book_type_ids: number[]
  blocked_tone_ids: number[]
  profile_public: boolean
}

export type UserPublicProfile = {
  user_id: string
  name: string | null
  email: string
}

export type FollowStatus = {
  following: boolean
}

export type FeedEntry = {
  user: UserPublicProfile
  book_id: number
  book_title: string
  book_cover_url: string | null
  event_type: 'read' | 'rating' | 'review' | 'want_to_read' | 'currently_reading'
  rating: number | null
  review_text: string | null
  occurred_at: string
}

export type AppUser = {
  user_id: string
  name: string | null
  email: string
  created_at: string
  is_admin: boolean
  preferences: UserPreferences
}

export type Series = {
  series_id: number
  name: string
  description: string | null
}

export type UserTrope = {
  trope: Trope
  weight: number
}

export type UserArchetype = {
  archetype: Archetype
  importance: number
}

export type UserTags = {
  tropes: UserTrope[]
  archetypes: UserArchetype[]
}

export type BookTagsEntry = {
  book: Book
  tropes: UserTrope[]
  archetypes: UserArchetype[]
}

export type Author = {
  author_id: number
  name: string
}

export type Tone = {
  tone_id: number
  name: string
}

export type Book = {
  book_id: number
  title: string
  author: Author
  isbn: string | null
  publication_date: string | null
  description: string | null
  pacing: number | null
  page_count: number | null
  cover_url: string | null
  avg_rating: number | null
  created_at: string
  updated_at: string
  embedding_status: 'pending' | 'done' | 'failed'
  series: Series | null
  series_position: number | null
}

export type BookType = {
  book_type_id: number
  name: string
  description: string | null
}

export type Genre = {
  genre_id: number
  name: string
  description: string | null
}

export type Trope = {
  trope_id: number
  name: string
  description: string | null
  category: string
}

export type Archetype = {
  archetype_id: number
  name: string
  description: string | null
}

export type BookTropeEntry = {
  trope: Trope
  weight: number
  is_crowd_promoted: boolean
}

export type CharacterDNAEntry = {
  archetype: Archetype
  importance: number
  is_crowd_promoted: boolean
}

export type BookDetail = Book & {
  book_tropes: BookTropeEntry[]
  character_dna: CharacterDNAEntry[]
  genres: Genre[]
  book_types: BookType[]
  tones: Tone[]
}

export type RecommendationExplanation = {
  shared_tropes: string[]
  shared_archetypes: string[]
  source?: string  // "embedding" | "collaborative"
}

export type Review = {
  rating_id: number
  book_id: number
  rating: number
  review_text: string
  reviewer_name: string | null
  created_at: string
}

export type SimilarBook = {
  book: Book
  score: number
  explanation: RecommendationExplanation | null
}

export type HybridResult = {
  book: Book
  score: number
  match_type: 'both' | 'lexical' | 'semantic'
  lex_rank: number | null
  sem_rank: number | null
}

export type HybridSearchRequest = {
  q: string
  top_n?: number
  alpha?: number
  min_score?: number
  genre_ids?: number[]
  book_type_ids?: number[]
  tone_ids?: number[]
  pacing?: number
  categories?: string[]
  archetype_ids?: number[]
  exclude_trope_ids?: number[]
  exclude_archetype_ids?: number[]
  exclude_genre_ids?: number[]
  exclude_book_type_ids?: number[]
  exclude_tone_ids?: number[]
  page_count_min?: number
  page_count_max?: number
}

export type ReadingStatus = {
  book_id: number
  status: 'want_to_read' | 'currently_reading' | 'read'
  created_at: string
  updated_at: string
}

export type ShelfEntry = {
  book: Book
  status: 'want_to_read' | 'currently_reading' | 'read'
  created_at: string
  updated_at: string
}

export type Rating = {
  rating_id: number
  user_id: string
  book_id: number
  rating: number
  review_text: string | null
  created_at: string
  updated_at: string
}

export const api = {
  books: {
    list: (params?: {
      search?: string
      categories?: string[]
      genreIds?: number[]
      bookTypeIds?: number[]
      pacing?: number
      toneIds?: number[]
      archetypeIds?: number[]
      excludeTropeIds?: number[]
      excludeArchetypeIds?: number[]
      excludeGenreIds?: number[]
      excludeBookTypeIds?: number[]
      excludeToneIds?: number[]
      skip?: number
      limit?: number
      shelfStatus?: string
      pageCountMin?: number
      pageCountMax?: number
      token?: string
    }) => {
      const qs = new URLSearchParams()
      if (params?.search) qs.set('search', params.search)
      for (const c of params?.categories ?? []) qs.append('categories', c)
      for (const id of params?.genreIds ?? []) qs.append('genre_ids', String(id))
      for (const id of params?.bookTypeIds ?? []) qs.append('book_type_ids', String(id))
      if (params?.pacing != null) qs.set('pacing', String(params.pacing))
      for (const id of params?.toneIds ?? []) qs.append('tone_ids', String(id))
      for (const id of params?.archetypeIds ?? []) qs.append('archetype_ids', String(id))
      for (const id of params?.excludeTropeIds ?? []) qs.append('exclude_trope_ids', String(id))
      for (const id of params?.excludeArchetypeIds ?? []) qs.append('exclude_archetype_ids', String(id))
      for (const id of params?.excludeGenreIds ?? []) qs.append('exclude_genre_ids', String(id))
      for (const id of params?.excludeBookTypeIds ?? []) qs.append('exclude_book_type_ids', String(id))
      for (const id of params?.excludeToneIds ?? []) qs.append('exclude_tone_ids', String(id))
      if (params?.skip != null) qs.set('skip', String(params.skip))
      if (params?.limit != null) qs.set('limit', String(params.limit))
      if (params?.shelfStatus) qs.set('shelf_status', params.shelfStatus)
      if (params?.pageCountMin != null) qs.set('page_count_min', String(params.pageCountMin))
      if (params?.pageCountMax != null) qs.set('page_count_max', String(params.pageCountMax))
      const path = '/books/' + (qs.toString() ? `?${qs.toString()}` : '')
      if (params?.token) return authedFetch('GET', path, params.token).then(r => r.json() as Promise<Book[]>)
      return get<Book[]>(path)
    },
    authors: () => get<Author[]>('/books/authors'),
    get: (id: number) => get<BookDetail>(`/books/${id}`),
    similar: (id: number, limit = 100) => get<SimilarBook[]>(`/recommendations/${id}/similar?limit=${limit}`),
    attachTrope: (bookId: number, tropeId: number, weight: number) =>
      post<void>(`/books/${bookId}/tropes`, { trope_id: tropeId, weight }),
    attachArchetype: (bookId: number, archetypeId: number, importance: number) =>
      post<void>(`/books/${bookId}/archetypes`, { archetype_id: archetypeId, importance }),
    attachGenre: (bookId: number, genreId: number) =>
      post<void>(`/books/${bookId}/genres`, { genre_id: genreId }),
    detachGenre: (bookId: number, genreId: number) =>
      del(`/books/${bookId}/genres/${genreId}`),
    attachBookType: (bookId: number, bookTypeId: number) =>
      post<void>(`/books/${bookId}/book-types`, { book_type_id: bookTypeId }),
    detachBookType: (bookId: number, bookTypeId: number) =>
      del(`/books/${bookId}/book-types/${bookTypeId}`),
    attachTone: (bookId: number, toneId: number) =>
      post<void>(`/books/${bookId}/tones`, { tone_id: toneId }),
    detachTone: (bookId: number, toneId: number) =>
      del(`/books/${bookId}/tones/${toneId}`),
    forYou: (token: string, limit = 10) =>
      authedFetch('GET', `/recommendations/for-you?limit=${limit}`, token)
        .then(r => r.json() as Promise<SimilarBook[]>),
    getRating: (id: number, token: string) =>
      authedFetch('GET', `/books/${id}/rating`, token)
        .then(r => r.status === 200 ? r.json() as Promise<Rating> : null),
    upsertRating: (id: number, rating: number, token: string, reviewText?: string | null) =>
      authedFetch('PUT', `/books/${id}/rating`, token, { rating, review_text: reviewText ?? null })
        .then(async r => {
          if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
          return r.json() as Promise<Rating>
        }),
    deleteRating: (id: number, token: string) =>
      authedFetch('DELETE', `/books/${id}/rating`, token)
        .then(r => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`) }),
    getReviews: (id: number) => get<Review[]>(`/books/${id}/reviews`),
    create: (data: { title: string; author: string; isbn: string | null; publication_date: string | null; description: string | null; series_name?: string | null; series_position?: number | null }) => post<Book>('/books/', data),
    update: (id: number, data: { title?: string; author?: string; isbn?: string | null; publication_date?: string | null; description?: string | null; pacing?: number | null; series_name?: string | null; series_position?: number | null }) =>
      put<Book>(`/books/${id}`, data),
    getSeries: (id: number) => get<(Book & { weight?: number; importance?: number })[]>(`/books/${id}/series`),
    detachTrope: (bookId: number, tropeId: number) => del(`/books/${bookId}/tropes/${tropeId}`),
    detachArchetype: (bookId: number, archetypeId: number) => del(`/books/${bookId}/archetypes/${archetypeId}`),
    delete: (id: number) => del(`/books/${id}`),
  },
  tropes: {
    list: (category?: string) =>
      get<Trope[]>('/tropes/' + (category ? `?category=${encodeURIComponent(category)}` : '')),
    categories: () => get<string[]>('/tropes/categories'),
    get: (id: number) => get<Trope>(`/tropes/${id}`),
    books: (id: number) => get<(Book & { weight: number })[]>(`/tropes/${id}/books`),
    create: (data: Omit<Trope, 'trope_id'>) => post<Trope>('/tropes/', data),
    delete: (id: number) => del(`/tropes/${id}`),
  },
  tones: {
    list: () => get<Tone[]>('/tones/'),
    create: (name: string, token: string) =>
      authedFetch('POST', '/tones/', token, { name }).then(r => r.json() as Promise<Tone>),
    delete: (id: number, token: string) =>
      authedFetch('DELETE', `/tones/${id}`, token).then(() => {}),
  },
  archetypes: {
    list: () => get<Archetype[]>('/archetypes/'),
    get: (id: number) => get<Archetype>(`/archetypes/${id}`),
    books: (id: number) => get<(Book & { importance: number })[]>(`/archetypes/${id}/books`),
    create: (data: Omit<Archetype, 'archetype_id'>, token: string) =>
      authedFetch('POST', '/archetypes/', token, data).then(r => r.json() as Promise<Archetype>),
    delete: (id: number, token: string) =>
      authedFetch('DELETE', `/archetypes/${id}`, token).then(() => {}),
  },
  genres: {
    list: () => get<Genre[]>('/genres/'),
    create: (data: Omit<Genre, 'genre_id'>, token: string) =>
      authedFetch('POST', '/genres/', token, data).then(r => r.json() as Promise<Genre>),
    delete: (id: number, token: string) =>
      authedFetch('DELETE', `/genres/${id}`, token).then(() => {}),
  },
  bookTypes: {
    list: () => get<BookType[]>('/book-types/'),
    create: (data: Omit<BookType, 'book_type_id'>, token: string) =>
      authedFetch('POST', '/book-types/', token, data).then(r => r.json() as Promise<BookType>),
    delete: (id: number, token: string) =>
      authedFetch('DELETE', `/book-types/${id}`, token).then(() => {}),
  },
  dislikes: {
    get: (bookId: number, token: string) =>
      authedFetch('GET', `/books/${bookId}/dislike`, token).then(r => r.json() as Promise<{ disliked: boolean }>),
    set: (bookId: number, token: string) =>
      authedFetch('PUT', `/books/${bookId}/dislike`, token).then(r => { if (!r.ok) throw new Error(`${r.status}`) }),
    remove: (bookId: number, token: string) =>
      authedFetch('DELETE', `/books/${bookId}/dislike`, token).then(r => { if (!r.ok && r.status !== 404) throw new Error(`${r.status}`) }),
  },
  shelf: {
    my: (token: string) =>
      authedFetch('GET', '/shelf/my', token).then(r => r.json() as Promise<ShelfEntry[]>),
    get: (bookId: number, token: string) =>
      authedFetch('GET', `/books/${bookId}/reading-status`, token)
        .then(r => r.status === 200 ? r.json() as Promise<ReadingStatus> : null),
    set: (bookId: number, status: string, token: string) =>
      authedFetch('PUT', `/books/${bookId}/reading-status`, token, { status })
        .then(async r => {
          if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
          return r.json() as Promise<ReadingStatus>
        }),
    remove: (bookId: number, token: string) =>
      authedFetch('DELETE', `/books/${bookId}/reading-status`, token)
        .then(r => { if (!r.ok && r.status !== 404) throw new Error(`${r.status}`) }),
  },
  users: {
    me: (token: string) =>
      authedFetch('GET', '/users/me', token).then(r => r.json() as Promise<AppUser>),
    updateMe: (token: string, data: { name?: string | null; preferences?: UserPreferences }) =>
      authedFetch('PUT', '/users/me', token, data).then(async r => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.json() as Promise<AppUser>
      }),
    myTags: (token: string) =>
      authedFetch('GET', '/users/me/tags', token).then(r => r.json() as Promise<BookTagsEntry[]>),
    search: (token: string, q: string) =>
      authedFetch('GET', `/users/search?q=${encodeURIComponent(q)}`, token)
        .then(r => r.json() as Promise<UserPublicProfile[]>),
    following: (token: string) =>
      authedFetch('GET', '/users/me/following', token).then(r => r.json() as Promise<UserPublicProfile[]>),
    followers: (token: string) =>
      authedFetch('GET', '/users/me/followers', token).then(r => r.json() as Promise<UserPublicProfile[]>),
    follow: (token: string, userId: string) =>
      authedFetch('POST', `/users/me/following/${userId}`, token, {}).then(async r => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.json() as Promise<FollowStatus>
      }),
    unfollow: (token: string, userId: string) =>
      authedFetch('DELETE', `/users/me/following/${userId}`, token).then(async r => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.json() as Promise<FollowStatus>
      }),
    followStatus: (token: string, userId: string) =>
      authedFetch('GET', `/users/me/following/${userId}/status`, token)
        .then(r => r.json() as Promise<FollowStatus>),
    feed: (token: string, limit = 30, before?: string) => {
      const params = new URLSearchParams({ limit: String(limit) })
      if (before) params.set('before', before)
      return authedFetch('GET', `/users/me/feed?${params}`, token).then(r => r.json() as Promise<FeedEntry[]>)
    },
    profile: (token: string, userId: string) =>
      authedFetch('GET', `/users/${userId}/profile`, token).then(async r => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.json() as Promise<UserPublicProfile>
      }),
    shelf: (token: string, userId: string) =>
      authedFetch('GET', `/users/${userId}/shelf`, token).then(r => r.json() as Promise<ShelfEntry[]>),
  },
  admin: {
    embedStatus: (token: string) =>
      authedFetch('GET', '/admin/embed-status', token).then(r => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.json() as Promise<{ total: number; done: number; pending: number; failed: number }>
      }),
    vectorCoverage: (token: string) =>
      authedFetch('GET', '/admin/vector-coverage', token).then(r => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.json() as Promise<{ total: number; both: number; description_only: number; neither: number; genome_eligible: number; review_embedded: number }>
      }),
    embedAll: (token: string) =>
      authedFetch('POST', '/admin/embed-all', token, {}).then(r => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.json() as Promise<{ queued: number }>
      }),
    fetchCovers: (token: string) =>
      authedFetch('POST', '/admin/fetch-covers', token, {}).then(r => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.json() as Promise<{ queued: number }>
      }),
  },
  myTags: {
    get: (bookId: number, token: string) =>
      authedFetch('GET', `/books/${bookId}/my-tags`, token).then(r => r.json() as Promise<UserTags>),
    addTrope: (bookId: number, tropeId: number, weight: number, token: string) =>
      authedFetch('POST', `/books/${bookId}/my-tags/tropes`, token, { trope_id: tropeId, weight })
        .then(async r => {
          if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
          return r.json() as Promise<UserTrope>
        }),
    removeTrope: (bookId: number, tropeId: number, token: string) =>
      authedFetch('DELETE', `/books/${bookId}/my-tags/tropes/${tropeId}`, token)
        .then(r => { if (!r.ok) throw new Error(`${r.status}`) }),
    addArchetype: (bookId: number, archetypeId: number, importance: number, token: string) =>
      authedFetch('POST', `/books/${bookId}/my-tags/archetypes`, token, { archetype_id: archetypeId, importance })
        .then(async r => {
          if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
          return r.json() as Promise<UserArchetype>
        }),
    removeArchetype: (bookId: number, archetypeId: number, token: string) =>
      authedFetch('DELETE', `/books/${bookId}/my-tags/archetypes/${archetypeId}`, token)
        .then(r => { if (!r.ok) throw new Error(`${r.status}`) }),
  },
  series: {
    list: () => get<Series[]>('/series/'),
    get: (id: number) => get<Series>(`/series/${id}`),
    create: (data: { name: string; description?: string | null }) => post<Series>('/series/', data),
    update: (id: number, data: { name: string; description?: string | null }) => put<Series>(`/series/${id}`, data),
    delete: (id: number) => del(`/series/${id}`),
  },
  health: {
    get: () => get<{ status: string; models: { genome: string; description: string; review: string } }>('/health'),
  },
  search: {
    hybrid: (body: HybridSearchRequest) =>
      fetch(`${BASE}/search/hybrid`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }).then(async r => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.json() as Promise<HybridResult[]>
      }),
  },
}
