# CommonThread — Feature Reference

Complete inventory of all functionality in the frontend and backend as of 2026-04-14.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Frontend Pages & Routes](#frontend-pages--routes)
3. [Backend API Endpoints](#backend-api-endpoints)
4. [Data Models](#data-models)
5. [Embedding Architecture](#embedding-architecture)
6. [Recommendation Engine](#recommendation-engine)
7. [Background Services](#background-services)
8. [Admin Tools](#admin-tools)
9. [Social / Follow System](#social--follow-system)
10. [End-to-End Testing](#end-to-end-testing)
11. [Data Ingestion — Open Library Scraper](#data-ingestion--open-library-scraper)

---

## Authentication

### Flow
1. User signs up or logs in via **Supabase Auth** (email + password)
2. Supabase issues a signed JWT
3. Frontend (`AuthContext.tsx`) stores the session and attaches the JWT as `Authorization: Bearer <token>` on every API call
4. FastAPI validates the JWT against the Supabase secret in `get_current_user()` / `get_optional_user()`
5. On first authenticated request, a matching `app_users` row is **auto-created** (upsert) using the Supabase `sub` UUID and email from the token claims
6. Admin status is checked via `app_users.is_admin`; non-admins hitting admin-gated endpoints get `403`

### Frontend Auth Pages

| Route | Purpose |
|---|---|
| `/auth/login` | Email/password sign-in |
| `/auth/signup` | New account registration |
| `/auth/forgot-password` | Request password-reset email |
| `/auth/reset-password` | Set new password from reset link |

### Route Protection
- `<ProtectedRoute>` — requires any authenticated session; redirects to `/auth/login` if not logged in
- `<ProtectedRoute adminOnly>` — additionally requires `is_admin = true`; redirects to `/unauthorized` (403 page)

### AuthContext Loading Guarantee

`AuthContext` keeps `loading = true` until BOTH the Supabase session AND the `AppUser` profile have been fetched. This prevents `ProtectedRoute` from seeing a transient `isAdmin = false` during the brief window after `getSession()` returns but before `api.users.me()` resolves. The `onAuthStateChange` listener skips the initial event (handled by `getSession()`) via an `initializedRef` flag.

### Router Architecture

`App.tsx` uses React Router v7's **data router** (`createBrowserRouter` + `RouterProvider`) rather than the legacy `<BrowserRouter>`. This is required for `useBlocker` (navigation guard in AddBook) and any other data-router features. A `RootLayout` component wraps all routes with `<ToastProvider><AuthProvider><Outlet /></AuthProvider></ToastProvider>`.

---

## Frontend Pages & Routes

### Public / Optional Auth

| Route | Page | Description |
|---|---|---|
| `/` | Home | Hero for logged-out visitors; compact greeting + currently reading + For You recommendations + friends feed strip for logged-in users |
| `/tropes/:id` | TropeDetail | Trope name, description, category, and list of books tagged with this trope (with weight) |
| `/archetypes/:id` | ArchetypeDetail | Archetype name, description, and list of books tagged with this archetype (with importance) |
| `/unauthorized` | Unauthorized | 403 page shown when a non-admin user hits an admin-only route |

### Authenticated (any user)

| Route | Page | Description |
|---|---|---|
| `/books` | Books | Browse, keyword-search, and filter all books; semantic vibe search; pagination |
| `/books/:id` | BookDetail | Full book view — metadata, tropes, archetypes, cover, series, reviews, similar books, user actions |
| `/tropes` | Tropes | Browse tropes by category, searchable |
| `/archetypes` | Archetypes | Browse archetypes, searchable |
| `/shelf` | Shelf | Personal reading shelf sorted by status; sort and title/author filter |
| `/my-tags` | MyTags | All books where the user has added personal trope/archetype tags; searchable |
| `/profile` | Profile | Edit display name; manage content blocklist (genres, book types, tones); privacy toggle |
| `/friends` | Friends | User search; follow/unfollow; following list; friend activity feed |
| `/users/:userId` | UserProfile | Another user's public profile and shelf (respects privacy settings) |

### Admin only

| Route | Page | Description |
|---|---|---|
| `/books/new` | AddBook | Create a new book with full trope/archetype/genre/type/tone/series tagging |
| `/books/:id/edit` | EditBook | Edit all book metadata and associations |
| `/genres` | Genres | Create, search, and delete genres |
| `/book-types` | BookTypes | Create, search, and delete book types |
| `/tones` | Tones | Create, search, and delete tones |
| `/admin` | Admin | Embed status dashboard, trigger batch embedding, trigger cover fetching |

---

### Per-Page Feature Detail

#### Home (`/`)
- **Logged out**: large hero with app name, tagline, Browse Books + Browse Tropes buttons
- **Logged in**: compact one-line greeting with name; currently-reading shelf (horizontal scroll); want-to-read count with link to `/shelf`; friends activity feed strip (5 most recent events); For You recommendation grid

#### Books (`/books`)
- Keyword search by title/author
- **Vibe (semantic) search**: text query, alpha slider (`More tropes & archetypes` ↔ `More vibe & prose`), 4 example-query chips
- **Filter panel**: genres (multi-select chips), book types, tones, pacing (1–5), trope categories (chip picker), archetypes (chip picker), exclude genres/types/tones/tropes/archetypes, shelf status filter
- Active filter summary bar ("N books · X filters active")
- Keyboard navigation on all typeahead pickers (↑↓ Enter Escape)
- Card grid results with cover, title, author, pub year, avg rating, ReadingStatusButton
- Admin delete button per card (with confirmation modal)
- Pagination: `Page N · X–Y shown` with disabled Next on last page

#### BookDetail (`/books/:id`)
- Book header: cover, title, author, series position, publication year, ISBN, embedding status badge
- Genre / book type / tone / pacing chips
- Description text
- **Reading status button** (Want to Read / Currently Reading / Read / remove) with spinner
- **Rating button** — opens RatingModal (1–5 stars with hover preview, review textarea with 1000-char counter/limit)
- **Dislike button** — confirm modal before adding; spinner during in-flight
- Tropes list with weight bars and category badges (linked to TropeDetail)
- Character archetypes list with importance dot rows (linked to ArchetypeDetail)
- **Your Tags section** (logged-in): typeahead to add personal trope tags (with weight slider) and archetype tags (with importance slider); remove with confirmation modal
- Series strip (horizontal scroll of other books in series)
- Reviews list — sortable by Newest / Oldest / Highest / Lowest (select shown when 2+ reviews)
- Similar Books grid with shared-trope/archetype chips and match % badges; empty state for unembedded books
- Back-to-top floating button (appears after 300 px scroll)
- Admin Edit button (admin only)

#### Shelf (`/shelf`)
- Three sections: Currently Reading, Want to Read, Read
- Sort: Date Added (newest/oldest), Title A–Z
- Inline title/author filter input with clear button
- Each entry shows cover, title, author, ReadingStatusButton, star rating
- Skeleton loading state

#### MyTags (`/my-tags`)
- Filter input (searches book title, author name, or any tag name)
- Cards per book showing all personal tropes (weight bar) and archetypes (importance dots)
- Remove tag button → ConfirmModal
- Explanation callout banner
- Skeleton loading

#### Profile (`/profile`)
- Edit display name (inline save)
- Content blocklist pickers for genres, book types, and tones (typeahead with keyboard nav; items stored in `preferences` JSONB)
- `profile_public` privacy toggle

#### Friends (`/friends`)
- User search by name/email (debounced 300 ms, results dropdown)
- Follow / Unfollow from search results
- Following list with Unfollow buttons
- Activity feed: read, currently reading, wants to read, rated, reviewed — with relative timestamps (Today / Yesterday / N days ago)
- Empty state messaging

#### UserProfile (`/users/:userId`)
- Breadcrumb: `Friends › Display Name`
- Follow / Unfollow toggle
- Displays public shelf (3-column grid) if profile is public or caller is following
- Shows 403-style message if private and not following

#### Admin (`/admin`)
- Embed status bar (done / pending / failed with percentages)
- Embed All button — kicks off background batch; status auto-refreshes every 4 s until `pending === 0`; "Refreshing…" badge while polling
- Fetch Covers button — queues background cover fetch for all books without a cover URL

#### AddBook / EditBook
- Metadata: title (required), author (autocomplete from existing authors), ISBN (required), publication date (required), description (optional), series name + position (optional)
- Pacing picker (1 Very Slow → 5 Very Fast)
- Genre / book type / tone chip toggles
- Trope typeahead with weight tier select (Flavor 0.10 → Structural 1.0); max 12 tropes; **optional at creation** — recommendations unlock at 3 tropes; if any tropes are added at least one must be Major (≥ 0.65)
- Archetype typeahead with importance tier select (Background 1 → Central 10); max 8 archetypes; optional
- AddBook counter turns amber at 1–2 tropes (threshold not yet met) and green at ≥ 3
- EditBook diffs original vs new state and only sends changed associations
- Toast on success (`Book added.` / `Changes saved.`)

---

## Backend API Endpoints

Base path: `/api/v1`

### Books — `/books`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/books` | Optional | List books. Query: `skip`, `limit`, `search`, `genre_ids[]`, `book_type_ids[]`, `tone_ids[]`, `categories[]`, `pacing`, `exclude_trope_ids[]`, `exclude_archetype_ids[]`, `exclude_genre_ids[]`, `exclude_book_type_ids[]`, `exclude_tone_ids[]`, `shelf_status`. Returns `avg_rating`. Respects user's content blocklist if authenticated. |
| POST | `/books` | Admin | Create book. Triggers background: embed + cover fetch. |
| GET | `/books/{id}` | Optional | Full book detail (tropes, archetypes, genres, types, tones, series, embedding status). |
| PUT | `/books/{id}` | Admin | Update metadata. Re-embeds in background. |
| DELETE | `/books/{id}` | Admin | Soft delete. |
| GET | `/books/authors` | — | List all authors. |
| GET | `/books/{id}/series` | — | All books in the same series. |
| POST | `/books/{id}/tropes` | Admin | Attach trope `{trope_id, weight}`. Re-embeds. |
| DELETE | `/books/{id}/tropes/{trope_id}` | Admin | Detach trope. Re-embeds. |
| POST | `/books/{id}/archetypes` | Admin | Attach archetype `{archetype_id, importance}`. Re-embeds. |
| DELETE | `/books/{id}/archetypes/{archetype_id}` | Admin | Detach archetype. Re-embeds. |
| POST | `/books/{id}/genres` | Admin | Attach genre. Re-embeds. |
| DELETE | `/books/{id}/genres/{genre_id}` | Admin | Detach genre. Re-embeds. |
| POST | `/books/{id}/book-types` | Admin | Attach book type. |
| DELETE | `/books/{id}/book-types/{book_type_id}` | Admin | Detach book type. |
| POST | `/books/{id}/tones` | Admin | Attach tone. Re-embeds. |
| DELETE | `/books/{id}/tones/{tone_id}` | Admin | Detach tone. Re-embeds. |

### Ratings & Reviews — `/books`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/books/{id}/rating` | Required | Own rating for a book (or null). |
| PUT | `/books/{id}/rating` | Required | Upsert rating `{rating: 1–5, review_text?}`. |
| DELETE | `/books/{id}/rating` | Required | Delete own rating. |
| GET | `/books/{id}/reviews` | — | All reviews for a book (reviewer name, rating, review text, timestamp). |
| GET | `/ratings/my` | Required | All of the current user's ratings. |

### Reading Status — `/books`, `/shelf`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/books/{id}/reading-status` | Required | Own reading status (or null). |
| PUT | `/books/{id}/reading-status` | Required | Upsert `{status: want_to_read \| currently_reading \| read}`. |
| DELETE | `/books/{id}/reading-status` | Required | Remove status. |
| GET | `/shelf/my` | Required | Full shelf grouped by status. |

### Dislikes — `/books`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/books/{id}/dislike` | Required | `{disliked: bool}`. |
| PUT | `/books/{id}/dislike` | Required | Mark disliked. |
| DELETE | `/books/{id}/dislike` | Required | Remove dislike. |

### Personal Tags — `/books`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/books/{id}/my-tags` | Required | Own trope + archetype tags for this book. |
| POST | `/books/{id}/my-tags/tropes` | Required | Add trope tag `{trope_id, weight}`. |
| DELETE | `/books/{id}/my-tags/tropes/{trope_id}` | Required | Remove trope tag. |
| POST | `/books/{id}/my-tags/archetypes` | Required | Add archetype tag `{archetype_id, importance}`. |
| DELETE | `/books/{id}/my-tags/archetypes/{archetype_id}` | Required | Remove archetype tag. |

### Search — `/search`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/search` | Optional | Semantic search. `q` (query), `alpha` (0–1, default 0.7), `limit`, plus same filter params as `/books`. Returns ranked `SearchResult` list with scores. |

### Recommendations — `/recommendations`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/recommendations/for-you` | Required | Personalized recs from user's taste profile. `limit` (default 10). Returns `SimilarBook[]` with `explanation`. |
| GET | `/recommendations/{book_id}/similar` | — | Books structurally similar to a given book. `limit` (default 5). Returns `SimilarBook[]` with `explanation`. |

### Reference Data

| Method | Path | Auth | Description |
|---|---|---|---|
| GET/POST | `/tropes` | Admin (write) | List all tropes; create trope `{name, description, category}`. |
| PUT/DELETE | `/tropes/{id}` | Admin | Update or delete. Delete re-embeds affected books. |
| GET | `/tropes/categories` | — | All distinct trope categories. |
| GET | `/tropes/{id}/books` | — | Books tagged with this trope (with weight). |
| GET | `/tropes/by-category/{category}` | — | Tropes in a specific category. |
| GET/POST | `/archetypes` | Admin (write) | List all archetypes; create `{name, description}`. |
| PUT/DELETE | `/archetypes/{id}` | Admin | Update or delete. Delete re-embeds affected books. |
| GET | `/archetypes/{id}/books` | — | Books tagged with this archetype (with importance). |
| GET/POST/PUT/DELETE | `/genres` | Admin (write) | Full CRUD on genres. |
| GET/POST/PUT/DELETE | `/book-types` | Admin (write) | Full CRUD on book types. |
| GET/POST/DELETE | `/tones` | Admin (write) | List, create, delete tones. |
| GET/POST/PUT/DELETE | `/series` | — | Full CRUD on series (no admin gate). |

### Users — `/users`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | Required | Own profile (name, email, is_admin, preferences JSONB). |
| PUT | `/users/me` | Required | Update name and/or preferences (blocked lists, profile_public). |
| GET | `/users/me/tags` | Required | All personal tags grouped by book. |
| GET | `/users/search` | Required | Search public users by name/email. `q` (min length 1). |
| POST | `/users/me/following/{user_id}` | Required | Follow a user. |
| DELETE | `/users/me/following/{user_id}` | Required | Unfollow. |
| GET | `/users/me/following/{user_id}/status` | Required | `{following: bool}`. |
| GET | `/users/me/following` | Required | List of users the caller follows. |
| GET | `/users/me/followers` | Required | List of users who follow the caller. |
| GET | `/users/me/feed` | Required | Activity feed from followed users. `limit` (default 30, max 100). Event types: `read`, `want_to_read`, `currently_reading`, `rating`, `review`. |
| GET | `/users/{user_id}/profile` | Required | Public profile. 403 if `profile_public=false` and caller is not following. |
| GET | `/users/{user_id}/shelf` | Required | User's shelf. Same privacy rules as profile. |

### Admin — `/admin`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/embed-status` | Admin | `{total, done, pending, failed}` counts. |
| POST | `/admin/embed-all` | Admin | Queue all pending/failed books for embedding. Returns `{queued: int}`. Runs in background. |
| POST | `/admin/fetch-covers` | Admin | Queue cover fetching for all books with no `cover_url`. Runs in background. |

### System

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | `{status: "ok", models: {genome: "ready"\|"loading", description: "ready"\|"loading"}}` |

---

## Data Models

### Core Tables

**`app_users`**
| Field | Type | Notes |
|---|---|---|
| user_id | UUID PK | Auto (uuid4) |
| name | VARCHAR | Nullable |
| email | VARCHAR | Unique |
| is_admin | BOOLEAN | Default false |
| onboarding_completed | BOOLEAN | Default false |
| preferences | JSONB | `{blocked_genre_ids[], blocked_book_type_ids[], blocked_tone_ids[], profile_public}` |
| created_at | TIMESTAMP | Auto |

**`books`**
| Field | Type | Notes |
|---|---|---|
| book_id | INT PK | Auto |
| title | VARCHAR | Indexed |
| author_id | INT FK → authors | |
| isbn | VARCHAR | Unique, nullable |
| publication_date | DATE | Nullable |
| description | TEXT | Nullable |
| pacing | INT 1–5 | Nullable |
| cover_url | VARCHAR | Nullable |
| genome_embedding | vector(384) | Structural signal |
| description_embedding | vector(768) | Prose/vibe signal |
| embedding_status | VARCHAR | `pending` \| `done` \| `failed` |
| series_id | INT FK → series | Nullable, SET NULL on delete |
| series_position | INT | Nullable |
| created_at / updated_at / deleted_at | TIMESTAMP | Soft-delete via deleted_at |

**`authors`** — `author_id`, `name` (indexed), `bio`

**`tropes`** — `trope_id`, `name` (unique), `description`, `category` (indexed)

**`archetypes`** — `archetype_id`, `name` (unique), `description`

**`genres`** — `genre_id`, `name` (unique, indexed), `description`

**`book_types`** — `book_type_id`, `name` (unique, indexed), `description`

**`tones`** — `tone_id`, `name` (unique)

**`series`** — `series_id`, `name` (unique), `description`

### Relationship Tables

| Table | Key Fields | Constraints |
|---|---|---|
| `book_tropes` | `(book_id, trope_id)` PK | `weight` float 0.0–1.0 |
| `character_dna` | `(book_id, archetype_id)` PK | `importance` int 1–10 |
| `book_genres` | `(book_id, genre_id)` PK | — |
| `book_book_types` | `(book_id, book_type_id)` PK | — |
| `book_tones` | `(book_id, tone_id)` PK | — |

### User Interaction Tables

| Table | Key Fields | Notes |
|---|---|---|
| `reading_statuses` | `(user_id, book_id)` PK | status: `want_to_read \| currently_reading \| read`; cascade delete |
| `book_ratings` | `rating_id` PK; unique `(user_id, book_id)` | rating 1–5; review_text TEXT nullable; cascade delete |
| `book_dislikes` | `(user_id, book_id)` PK | cascade delete |
| `user_book_tropes` | `(user_id, book_id, trope_id)` PK | weight float 0.0–1.0; cascade delete |
| `user_book_archetypes` | `(user_id, book_id, archetype_id)` PK | importance int 1–10; cascade delete |
| `user_follows` | `(follower_id, followee_id)` PK | unique constraint; cascade delete |

---

## Embedding Architecture

### Two-Stream Design

| Stream | Model | Dimensions | Encodes |
|---|---|---|---|
| Genome | `BAAI/bge-small-en-v1.5` | 384 | Structured literary metadata (tropes + weights, archetypes + importance, genres, tones, pacing, title, author). **Excludes description.** |
| Description | `BAAI/bge-base-en-v1.5` | 768 | Free-text book description only (prose vibe). NULL if no description. |

### Genome Text Format

```
"Title" by Author.
Tropes: 'Name' (0.85, dominant trope); 'Name' (0.45, supporting trope).
Character archetypes: 'Name' (9/10 importance); 'Name' (5/10 importance).
Genres: Fantasy, Romance.
Tone: Dark, Witty.
Pacing: 4/5.
```

### Search Scoring

```
score = alpha × cosine(query_genome, book_genome)
      + (1 − alpha) × cosine(query_description, book_description)
```

- Default `alpha = 0.7` (70% structural, 30% vibe)
- Books with no description use genome score alone regardless of alpha
- Query instruction prefix applied to both streams before encoding
- pgvector HNSW index with `hnsw.ef_search = 40` for approximate nearest-neighbor

### Tagging Threshold

`TROPE_THRESHOLD = 3` (defined in `app/routers/books.py` and `app/routers/admin.py`).

Genome embedding is **not** triggered at book creation. Instead:

1. Admin creates the book with basic metadata → `embedding_status = pending`, `genome_embedding = NULL`
2. Admin attaches tropes via the book page or AddBook form
3. After each `POST /books/{id}/tropes`, the backend counts canonical tropes; if count ≥ 3, `_embed_in_background` fires
4. Removing a trope that drops count below 3 clears `genome_embedding` and resets status to `pending`

Books below the threshold appear in text search (title/author) but are excluded from Similar Books and For You (both require `genome_embedding IS NOT NULL`).

### Batch Processing

- Chunk size: 32 books
- Genome and description models run **concurrently** within each chunk (`asyncio.gather`)
- DB committed after each chunk — partial progress is preserved
- Status per book: `done` or `failed`
- Admin **Embed All** only queues books with ≥ `TROPE_THRESHOLD` tropes — books awaiting tagging are skipped

---

## Recommendation Engine

### For You (`/recommendations/for-you`)

1. Collect user's books: ratings ≥ 4 stars **plus** all shelf entries
2. Aggregate personal trope/archetype tags across those books (avg weight / avg importance)
3. Build a taste genome string in the same format as a book genome
4. Embed taste genome via genome model
5. Run pgvector cosine similarity search against all `done` books
6. Exclude books already rated or on shelf, and books the user has disliked
7. Return top-N with explanation: `{shared_tropes[], shared_archetypes[], source: "embedding"}`

### Similar Books (`/recommendations/{book_id}/similar`)

1. Compute sparse cosine similarity using `book_tropes.weight` and `character_dna.importance / 10` feature vectors
2. Blend with pgvector genome embedding cosine similarity
3. Exclude the source book itself
4. Return top-N with explanation including shared tropes/archetypes

---

## Background Services

### Cover Fetching (`services/covers.py`)

1. If book has ISBN → probe `covers.openlibrary.org/b/isbn/{isbn}-L.jpg` directly
2. Fallback → search OpenLibrary by title + author → use first result's cover ID
3. Retry policy: up to 3 attempts with exponential back-off (1 s → 2 s → 4 s) on network/HTTP errors
4. Clean "no cover" (404 / empty search results) treated as final — not retried
5. Sets `books.cover_url` on success

### Embedding Triggers

Re-embed is queued as a FastAPI background task (same-process event loop) only when the book has ≥ `TROPE_THRESHOLD` canonical tropes:

| Event | Embeds? |
|---|---|
| Book created | No — embedding deferred until tagging threshold |
| Book metadata updated | Yes, if trope count ≥ 3 |
| Trope attached (count reaches 3) | Yes — threshold commit |
| Trope attached (count already ≥ 3) | Yes — re-embed with updated trope set |
| Trope detached (count still ≥ 3) | Yes — re-embed |
| Trope detached (count drops below 3) | Clears genome embedding, resets status to `pending` |
| Archetype / genre / tone attached or detached | Yes, if trope count ≥ 3 |
| Trope or archetype master record deleted | Re-embeds all affected books that still have ≥ 3 tropes |

### Model Pre-warm

Both FastEmbed models are loaded at application startup in the FastAPI lifespan handler via `run_in_executor`. The `/health` endpoint reports `"ready"` once both are loaded. Docker healthcheck gives up to 120 s for first-run model download (~570 MB total).

---

## Admin Tools

| Tool | What it does |
|---|---|
| **Embed Status** | Shows total / done / pending / failed book counts with percentage bars |
| **Embed All** | Queues all `pending` and `failed` books for background embedding. Frontend polls status every 4 s until `pending === 0`. |
| **Fetch Covers** | Queues background cover fetch for every book where `cover_url IS NULL`. |
| **Master data CRUD** | Create / search / delete Genres, Book Types, and Tones from dedicated admin pages. |
| **Add / Edit Book** | Full book creation and editing UI including trope/archetype/genre/type/tone tagging with weight and importance tiers. |

---

## Social / Follow System

### Data
- `user_follows (follower_id UUID, followee_id UUID, created_at)` — composite PK, unique constraint, cascade-delete

### Endpoints
- Follow / unfollow a user
- Check follow status
- List who the caller is following / who follows the caller
- Activity feed of followed users' shelf and rating events

### Privacy
- `app_users.preferences.profile_public` (boolean) controls visibility
- If `profile_public = false`: profile and shelf require the viewer to be a follower; otherwise returns 403
- User search only returns users who have `profile_public = true`

### Feed Event Types
| Type | Triggered when |
|---|---|
| `want_to_read` | User adds book to want-to-read |
| `currently_reading` | User marks book as currently reading |
| `read` | User marks book as read |
| `rating` | User rates a book (includes rating value) |
| `review` | User rates with review text (includes text snippet) |

---

## End-to-End Testing

### Stack

- **Playwright** (`@playwright/test`) with three projects: `public` (no auth), `user` (regular user session), `admin` (admin session)
- Tests live in `e2e/tests/` and are run with `npm test` from the `e2e/` directory
- `workers: 1`, `fullyParallel: false` — serial execution to avoid flakiness on a shared DB

### Authentication Setup

`e2e/global-setup.ts` authenticates both the test user and admin user via **Supabase magic links** (no passwords needed):
1. Calls `POST /auth/v1/admin/generate_link` with the Supabase service role key
2. Navigates Playwright to the one-time magic link URL
3. Waits for `sb-*-auth-token` to appear in `localStorage` (Supabase JS writes it asynchronously)
4. Saves `storageState` to `.auth/user.json` and `.auth/admin.json`

Credentials are read from `e2e/.env`:
```
TEST_EMAIL=<regular user email>
ADMIN_EMAIL=<admin user email>
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
```

### Test Coverage

| File | Project | Tests | What it covers |
|---|---|---|---|
| `1-home.spec.ts` | public | 4 | Home page loads, hero visible, 404 for unknown routes, login redirect |
| `2-auth.spec.ts` | public | 3 | Login page renders, invalid creds error, forgot-password form |
| `3-books.spec.ts` | user | 6 | Browse books, keyword search, filter panel, pagination, vibe search |
| `4-book-detail.spec.ts` | user | 5 | Book detail page, tropes section, reading status, rating modal |
| `5-tropes-archetypes.spec.ts` | user | 4 | Tropes browse, Archetypes browse, TropeDetail, ArchetypeDetail |
| `6-shelf.spec.ts` | user | 3 | Shelf loads, reading status change, filter by status |
| `7-my-tags.spec.ts` | user | 2 | MyTags page load, filter input |
| `8-friends.spec.ts` | user | 3 | Friends page, user search, activity feed |
| `9-profile.spec.ts` | user | 3 | Profile page, edit name, privacy toggle |
| `10-admin.spec.ts` | admin | 13 | Genres/BookTypes/Tones CRUD, Admin dashboard embed controls, route protection |
| `11-tagging-threshold.spec.ts` | admin | 11 | AddBook optional-trope UI, threshold progress badge, BookDetail badge lifecycle, embed-all skips below-threshold |

**Total: 57 tests (1 skip — intentional when admin creds are present)**

All 57 tests pass with valid credentials in `e2e/.env`. The `public` project (14 tests) needs no credentials.

### Running Tests

```bash
cd e2e
npm install

# All tests (requires e2e/.env with user + admin credentials)
npm test

# Public tests only (no credentials needed)
npx playwright test --project=public

# Admin tests only
npx playwright test --project=admin

# Single file
npx playwright test 11-tagging-threshold.spec.ts --project=admin

# With UI
npx playwright test --ui
```

---

## Data Ingestion — Open Library Scraper

Located at `backend/webscraper/`. Fetches book metadata from the Open Library API and writes JSONL files for later database import. No browser required — pure async HTTP via `httpx`.

### Files

| File | Purpose |
|---|---|
| `models.py` | `ScrapedBook` + `ScrapeProgress` Pydantic models |
| `scraper.py` | `OpenLibraryScraper` — search pagination + concurrent description fetch |
| `run.py` | CLI entry point with argparse |
| `output/` | JSONL output, progress checkpoint, summary, log (gitignored) |

### API Endpoints Used

| Endpoint | Purpose |
|---|---|
| `GET https://openlibrary.org/search.json?subject={s}&limit=100&page=N` | Paginated subject search — returns up to 100 works per page |
| `GET https://openlibrary.org/works/{id}.json` | Full description for a single work |
| `https://covers.openlibrary.org/b/id/{cover_id}-L.jpg` | Cover image URL (constructed from `cover_i` field) |

### ScrapedBook Fields

`ol_work_key`, `ol_cover_id`, `title`, `authors[]`, `isbn`, `isbn13`, `publication_year`, `publisher`, `description`, `page_count`, `language`, `subjects[]`, `cover_url`, `discovered_via_subject`, `edition_count`

### Subjects (20 built-in)

`fantasy`, `mystery`, `romance`, `science fiction`, `thriller`, `historical fiction`, `horror`, `young adult`, `biography`, `self-help`, `classics`, `literary fiction`, `adventure`, `crime`, `philosophy`, `psychology`, `humor`, `poetry`, `graphic novels`, `short stories`

### CLI

```bash
# All 20 subjects, 500 books each
uv run python -m webscraper.run

# Subset
uv run python -m webscraper.run --subjects fantasy mystery --books-per-subject 100

# Resume interrupted run
uv run python -m webscraper.run --resume
```

### Performance

- Search pages fetched sequentially; description fetches run concurrently (default: 5 in parallel)
- Default delay: 200 ms between requests
- ~500 books per subject takes ~2–3 minutes; full 20-subject run ~45–60 minutes
- Progress checkpointed after every subject — safe to interrupt and resume

---

## Key Constraints & Business Rules

| Rule | Where enforced |
|---|---|
| One rating per user per book | DB unique constraint on `(user_id, book_id)` in `book_ratings` |
| Trope weight: 0.0–1.0 | DB check constraint + frontend tier picker |
| Archetype importance: 1–10 | DB check constraint + frontend tier picker |
| Tropes optional at book creation — recommendations unlock at ≥ 3 tropes | Backend threshold gate (`TROPE_THRESHOLD = 3`) |
| If any tropes are added, at least one must be Major (≥ 0.65) | Frontend validation only |
| Max 12 tropes per book | Frontend validation only |
| Max 8 archetypes per book | Frontend validation only |
| Review max length: 1000 chars | Frontend `maxLength` attribute |
| Content blocklist (genres/types/tones) | Applied server-side in `/books` list query when user is authenticated |
| Soft delete on books | `deleted_at` timestamp; all queries filter `deleted_at IS NULL` |
| Cascade deletes | All user interaction rows (ratings, status, dislikes, tags, follows) cascade on user or book delete |
