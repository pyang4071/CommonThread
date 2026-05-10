# CommonThread — Feature Reference

Complete inventory of all functionality in the frontend and backend as of 2026-05-05.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Frontend Pages & Routes](#frontend-pages--routes)
3. [Backend API Endpoints](#backend-api-endpoints)
4. [Data Models](schema.md) *(see schema.md)*
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
| `/books` | Books | Browse, keyword-search, and filter all books; hybrid search (lexical + semantic RRF); pagination |
| `/books/:id` | BookDetail | Full book view — metadata, tropes, archetypes, cover, series, reviews, similar books, user actions |
| `/books/:id/similar` | SimilarBooks | Full paginated grid of up to 100 books similar to a given book |
| `/for-you` | ForYou | Full paginated grid of up to 50 personalized recommendations |
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
| `/admin` | Admin | Embed status dashboard, trigger batch embedding, trigger cover fetching, vector coverage breakdown |

---

### Per-Page Feature Detail

#### Home (`/`)
- **Logged out**: large hero with app name, tagline, Browse Books + Browse Tropes buttons
- **Logged in**: compact one-line greeting with name; currently-reading shelf (horizontal scroll); want-to-read count with link to `/shelf`; friends activity feed strip (5 most recent events); For You recommendation grid (10 books) with "See all →" link to `/for-you`

#### Books (`/books`)
- **Hybrid search**: single search bar using lexical full-text + semantic description via RRF; alpha slider controls the blend (higher = more lexical, lower = more semantic); 4 example-query chips; books matched by semantic similarity get a "matched by vibe" badge
- **Filter panel**: genres (multi-select chips), book types, tones, pacing (1–5), page count range (min/max number inputs with clear button), trope categories (chip picker), archetypes (chip picker), exclude genres/types/tones/tropes/archetypes, shelf status filter
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
- **Your Tags section** (logged-in): typeahead to add personal trope tags (with weight slider) and archetype tags (with importance slider); remove with confirmation modal; once N users (default 3) tag the same trope/archetype, it is crowd-promoted to canonical
- **Crowd-tagged badge** — teal `crowd-tagged` pill on any trope or archetype in the canonical list where `is_crowd_promoted = true`
- Series strip (horizontal scroll of other books in series)
- Reviews list — sortable by Newest / Oldest / Highest / Lowest (select shown when 2+ reviews)
- Similar Books grid (6 books) with shared-trope/archetype chips and match % badges; "See all →" link to `/books/:id/similar` for the full list of up to 100; empty state for unembedded books
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
- Activity feed auto-refreshes immediately after follow or unfollow
- Empty state messaging

#### UserProfile (`/users/:userId`)
- Breadcrumb: `Friends › Display Name`
- Follow / Unfollow toggle
- Displays public shelf (3-column grid) if profile is public or caller is following
- Shows 403-style message if private and not following

#### Admin (`/admin`)
- Embed status bar (done / pending / failed with percentages)
- Embed All button — kicks off background batch; status auto-refreshes every 4 s until `pending === 0`; "Refreshing…" badge while polling; stall detection stops polling after 5 consecutive polls with no change and shows a warning
- **Vector Coverage panel** — stacked bar + stat cards showing how many books have: (1) genome + description, (2) description only, (3) neither; auto-refreshes after embedding completes
- Fetch Covers button — queues background cover fetch for all books without a cover URL
- **Embedding Models panel** — shows genome / description / review model loading status (ready/loading) fetched from `GET /health` on page load

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
| GET | `/books` | Optional | List books. Query: `skip`, `limit`, `search`, `genre_ids[]`, `book_type_ids[]`, `tone_ids[]`, `categories[]`, `pacing`, `page_count_min`, `page_count_max`, `exclude_trope_ids[]`, `exclude_archetype_ids[]`, `exclude_genre_ids[]`, `exclude_book_type_ids[]`, `exclude_tone_ids[]`, `shelf_status`. Returns `avg_rating`. Respects user's content blocklist if authenticated. |
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
| POST | `/search/hybrid` | Optional | Hybrid search combining PostgreSQL full-text (lexical) and BGE-base description cosine similarity via Reciprocal Rank Fusion. Body: `{q, top_n, alpha (0–1, default 0.5 — higher = more lexical), min_score, genre_ids[], book_type_ids[], tone_ids[], pacing, categories[], exclude_*[]}`. Returns `HybridResult[]` with `{book, score, match_type: "both"\|"lexical"\|"semantic", lex_rank, sem_rank}`. Works for all books including those without genome embeddings. |

### Recommendations — `/recommendations`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/recommendations/for-you` | Required | Personalized recs from user's taste profile. `limit` (default 10). Returns `SimilarBook[]` with `explanation`. |
| GET | `/recommendations/{book_id}/similar` | — | Books structurally similar to a given book. `limit` (default 100). Returns `SimilarBook[]` with `explanation`. |

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
| POST | `/admin/embed-all` | Admin | Queue all pending/failed books for embedding. Returns `{queued: int}`. Runs in background; crashes are caught and remaining `pending` books marked `failed`. |
| GET | `/admin/vector-coverage` | Admin | `{total, both, description_only, neither, genome_eligible}` — counts of books by which embedding streams are populated, plus how many books have ≥ 3 canonical tropes (genome-eligible). Excludes soft-deleted books. |
| POST | `/admin/fetch-covers` | Admin | Queue cover fetching for all books with no `cover_url`. Runs in background. |

### System

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | `{status: "ok", models: {genome: "ready"\|"loading", description: "ready"\|"loading", review: "ready"\|"loading"}}` — polled by Admin page on load |

---

## Data Models

See [schema.md](schema.md) for the full table-by-table schema with column descriptions.

---

## Embedding Architecture

### Three-Stream Design

| Stream | Model | Dimensions | Encodes |
|---|---|---|---|
| Genome | `BAAI/bge-small-en-v1.5` | 384 | Structured literary metadata (tropes + weights, archetypes + importance, genres, tones, pacing, title, author). **Excludes description.** Only computed when book has ≥ 3 canonical tropes. |
| Description | `BAAI/bge-base-en-v1.5` | 768 | Free-text book description only (prose vibe). NULL if no description. Embedded for all books regardless of trope count. |
| Review | `BAAI/bge-base-en-v1.5` | 768 | Aggregated review text from users. NULL until at least one review is embedded. |

### Genome Text Format

```
"Title" by Author.
Tropes: 'Name' (0.85, dominant trope); 'Name' (0.45, supporting trope).
Character archetypes: 'Name' (9/10 importance); 'Name' (5/10 importance).
Genres: Fantasy, Romance.
Tone: Dark, Witty.
Pacing: 4/5.
```

### Hybrid Search Scoring (RRF)

```
rrf(rank, k=60) = 1 / (k + rank)
score = alpha × rrf(lex_rank) + (1 − alpha) × rrf(sem_rank)
```

- `alpha = 0.5` by default (equal lexical/semantic weight)
- Lexical leg uses PostgreSQL `search_vector @@ plainto_tsquery(q)` on the `tsvector` GENERATED column
- Semantic leg uses BGE-base description cosine similarity
- Books present in only one leg still appear if their score clears `min_score = 0.003`
- Works for all books — does not require genome embedding
- Returns `match_type`: `"both"` | `"lexical"` | `"semantic"`

### Tagging Threshold & Embedding Status

`TROPE_THRESHOLD = 3` (configured in `app/config.py` as `settings.TROPE_THRESHOLD`; overridable via env var).

`embedding_status = "done"` now means the **description** is embedded (minimum searchability). Genome is separately gated:

1. Book created → `embedding_status = pending`, both embeddings NULL
2. Description is always embedded when embedding runs, sets status to `done`
3. Genome is additionally embedded only when trope count ≥ 3
4. Removing a trope that drops count below 3 clears only `genome_embedding` — status stays `done`

Books without genome embedding appear in hybrid and keyword search but are excluded from Similar Books and For You (both require `genome_embedding IS NOT NULL`).

### Batch Processing

- Chunk size: 32 books
- Within each chunk, genome-eligible books run genome + description concurrently (`asyncio.gather`); description-only books run description alone
- DB committed after each chunk — partial progress is preserved
- Status per book: `done` or `failed`
- Admin **Embed All** queues books with `embedding_status != "done"` **or** `description IS NOT NULL AND description_embedding IS NULL` — catches books where status is `done` but description was added/updated after the last embed

---

## Recommendation Engine

### For You (`/recommendations/for-you`)

1. Collect user's books: ratings ≥ 4 stars **plus** all shelf entries
2. Aggregate personal trope/archetype tags across those books (avg weight / avg importance)
3. Build a taste genome string in the same format as a book genome
4. Embed taste genome via genome model
5. Run pgvector cosine similarity search against all `done` books
6. Exclude books already rated or on shelf, and books the user has disliked
7. **Review re-scoring**: mean-pool `review_embedding` for the user's high-rated books into a review preference vector; after diversity/series gating, re-score candidates at `0.85 * emb_score + 0.15 * review_cosine` when the candidate has a review embedding (fallback: emb_score unchanged)
8. Return top-N with explanation: `{shared_tropes[], shared_archetypes[], source: "embedding"}`

### Similar Books (`/recommendations/{book_id}/similar`)

1. Retrieve top candidates via pgvector cosine distance on genome (or description) embedding
2. Compute sparse cosine similarity using `book_tropes.weight` and `character_dna.importance / 10` feature vectors
3. **Three-stream blend**: `score = 0.5 * emb + 0.5 * sparse` baseline; when both source and candidate have `review_embedding`, shifts to `0.80 * base + 0.20 * review_cosine`
4. Exclude the source book itself
5. Return top-N with explanation including shared tropes/archetypes

---

## Background Services

### Cover Fetching (`services/covers.py`)

1. If book has ISBN → probe `covers.openlibrary.org/b/isbn/{isbn}-L.jpg` directly
2. Fallback → search OpenLibrary by title + author → use first result's cover ID
3. Retry policy: up to 3 attempts with exponential back-off (1 s → 2 s → 4 s) on network/HTTP errors
4. Clean "no cover" (404 / empty search results) treated as final — not retried
5. Sets `books.cover_url` on success

### Crowd Promotion System

When enough users independently tag the same book+trope or book+archetype, the tag is **crowd-promoted** to canonical via `crud/user_tags.py`.

**Trope promotion rules** (`_promote_or_update_trope`):
1. At least `CROWD_PROMOTION_THRESHOLD` (default 3, env-configurable) users must have tagged the trope
2. Median user weight ≥ `MIN_MEDIAN_WEIGHT` (0.4)
3. **Dominant anchor check**: if no existing canonical trope has `weight ≥ 0.65`, the promoted trope itself must have median ≥ `DOMINANT_WEIGHT_THRESHOLD` (0.65)
4. Atomic upsert via `pg_insert().on_conflict_do_update(where=is_crowd_promoted)` — never clobbers an admin-set row
5. **Ratchet**: once promoted, the row is never removed by the system; weight recalculates to the new median whenever any user adds or removes their tag; re-embeds genome if weight changed

**Archetype promotion rules** (`_promote_or_update_archetype`):
- Same threshold count check; median `importance ≥ MIN_MEDIAN_IMPORTANCE` (5); no dominant-anchor check

**On user tag removal**: `_update_crowd_trope_weight` / `_update_crowd_archetype_importance` recalculate the canonical weight/importance from remaining user tags. If no user tags remain, the canonical row is kept unchanged (ratchet).

### Embedding Triggers

Description embedding runs for all books; genome embedding additionally requires ≥ `TROPE_THRESHOLD` canonical tropes (including crowd-promoted). Both run as FastAPI background tasks in the same-process event loop.

| Event | Description embeds? | Genome embeds? |
|---|---|---|
| Book created | Yes — queued immediately | Only if already ≥ 3 tropes (rare at creation) |
| Book metadata updated | Yes | Yes, if trope count ≥ 3 |
| Trope attached (count reaches 3) | Yes | Yes — threshold commit |
| User crowd-promotes a trope/archetype | — | Yes — genome re-embeds with new canonical entry |
| User tag removed (canonical weight changes) | — | Yes — genome re-embeds with updated median weight |
| Trope attached (count already ≥ 3) | Yes | Yes — re-embed with updated trope set |
| Trope detached (count still ≥ 3) | Yes | Yes — re-embed |
| Trope detached (count drops below 3) | No (keeps existing) | Clears `genome_embedding`; status stays `done` |
| Archetype / genre / tone attached or detached | Yes | Yes, if trope count ≥ 3 |
| Trope or archetype master record deleted | Yes | Re-embeds affected books that still have ≥ 3 tropes |

### Model Pre-warm

Both FastEmbed models are loaded at application startup in the FastAPI lifespan handler via `run_in_executor`. The `/health` endpoint reports `"ready"` once both are loaded. Docker healthcheck gives up to 120 s for first-run model download (~570 MB total).

---

## Admin Tools

| Tool | What it does |
|---|---|
| **Embed Status** | Shows total / done / pending / failed book counts with percentage bars |
| **Embed All** | Queues all `pending` and `failed` books for background embedding. Frontend polls status every 4 s until `pending === 0`. Stall detection: if pending count is unchanged for 5 consecutive polls, polling stops and a warning is shown. Background crash recovery: if the batch task crashes, remaining `pending` books are marked `failed` via bulk UPDATE. |
| **Vector Coverage** | Stacked bar + stat cards showing books with genome+description, description-only, and neither embedding, plus a **genome-eligible** count (books with ≥ 3 canonical tropes). Shows what % of eligible books are actually embedded and how many are awaiting genome. Auto-refreshes when embedding completes. |
| **Embedding Models** | Three status cards (genome / description / review) fetched from `GET /health` showing `ready` or `loading…` for each model. Shown only once data is available. |
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

`ol_work_key`, `ol_cover_id`, `title`, `authors[]`, `isbn`, `isbn13`, `publication_year`, `publisher`, `description`, `page_count`, `subjects[]`, `cover_url`, `discovered_via_subject`, `edition_count`

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

## Data Ingestion — Tagged Books Import

`backend/scripts/import_tagged_books.py` imports pre-tagged books from `backend/webscraper/output/tagged_books.json` (a JSON array) into the database.

### What it does

1. Reads `tagged_books.json` (produced by the AI tagging workflow in `backend/parse_books.md`)
2. Matches each entry to an existing book by ISBN → title+author fallback (case-insensitive)
3. Creates the book if not found
4. Applies all taxonomy associations idempotently: genres, book types, tones, tropes (with weight), archetypes (with importance)
5. Sets `embedding_status = "pending"` on all tagged books so they are re-embedded with the new metadata
6. Optionally embeds all newly tagged books in one batch (omit with `--no-embed`)

### Run

```bash
cd backend

# Import and embed
uv run python scripts/import_tagged_books.py

# Import only (embed separately via Admin page or script)
uv run python scripts/import_tagged_books.py --no-embed
```

The script is **idempotent** — re-running it on already-imported books is safe. Unknown taxonomy names generate a warning but do not abort the import.

### Current data state (2026-04-18)

| Metric | Count |
|---|---|
| Books in database | ~5,772 |
| Tagged with tropes/archetypes | 648 |
| Scraped JSONL files (not yet tagged) | 9,220 remaining |

Tagging progress is checkpointed in `backend/webscraper/output/tagging_progress.json`. See `backend/parse_books.md` for the full tagging workflow and resumption instructions.

---

## Key Constraints & Business Rules

| Rule | Where enforced |
|---|---|
| One rating per user per book | DB unique constraint on `(user_id, book_id)` in `book_ratings` |
| Trope weight: 0.0–1.0 | DB check constraint + frontend tier picker |
| Archetype importance: 1–10 | DB check constraint + frontend tier picker |
| Tropes optional at book creation — genome embedding + recommendations unlock at ≥ 3 tropes | Backend threshold gate (`settings.TROPE_THRESHOLD`, default 3); description embedding always runs |
| Crowd promotion: N users tagging same trope/archetype promotes it to canonical | `CROWD_PROMOTION_THRESHOLD` (default 3) + median weight/importance check + dominant-anchor rule |
| Crowd-promoted canonical tags are never auto-removed (ratchet) | Once `is_crowd_promoted = true`, only admin can remove via `DELETE /books/{id}/tropes/{trope_id}` |
| Review re-embed batched — only when review count grows by ≥ 5 | `review_embed_count` column tracks last-embedded count; `REVIEW_EMBED_BATCH_SIZE = 5` |
| If any tropes are added, at least one must be Major (≥ 0.65) | Frontend validation only |
| Max 12 tropes per book | Frontend validation only |
| Max 8 archetypes per book | Frontend validation only |
| Review max length: 1000 chars | Frontend `maxLength` attribute |
| Content blocklist (genres/types/tones) | Applied server-side in `/books` list query when user is authenticated |
| Soft delete on books | `deleted_at` timestamp; all queries filter `deleted_at IS NULL` |
| Cascade deletes | All user interaction rows (ratings, status, dislikes, tags, follows) cascade on user or book delete |

---

## Key Implementation Notes

### SQLAlchemy Async — Eager Loading Required

All relationships accessed in async route handlers must use explicit `selectinload()` or `joinedload()`. SQLAlchemy async does not support implicit lazy loading — accessing a relationship outside an `await`-able context raises `MissingGreenlet`. See `error_log.md` for details.

### React Router — Data Router Required

`App.tsx` uses `createBrowserRouter` + `RouterProvider` (React Router v7 data router), not the legacy `<BrowserRouter>`. This is required for `useBlocker` (navigation guard in AddBook). Do not revert to `<BrowserRouter>` — it breaks the dirty-form guard.

### AuthContext — Loading Flag

`AuthContext` keeps `loading = true` until both the Supabase session and the `AppUser` profile have been fetched. This prevents `ProtectedRoute` from seeing a transient `isAdmin = false` during the async profile fetch. The `onAuthStateChange` listener skips its first event via `initializedRef` to avoid double-fetching.

### Admin CRUD — Auth Token Required

`api.genres.create/delete`, `api.tones.create/delete`, `api.bookTypes.create/delete`, and `api.archetypes.create/delete` all require an explicit `token` parameter (pass `session!.access_token` from `useAuth()`). They call `authedFetch()` internally. Do not use the generic unauthenticated `post()` / `del()` helpers for any admin write operation.

### Embedding Race Condition Guard

`_embed_in_background` (in `books.py`) checks the trope count both before and after calling `embed_book()`. The post-embed check ensures that if a `detach_trope` races with the background task and drops count below threshold during embedding, the `done` status is immediately reverted to `pending`. Similarly, `detach_trope` resets status whenever `embedding_status != 'pending'` (not just on `done`).

### Authentication Flow

1. User signs in via Supabase Auth (frontend uses Supabase JS SDK)
2. Supabase issues a JWT
3. Frontend sends JWT as `Authorization: Bearer <token>` on every API request
4. FastAPI validates the JWT signature against the Supabase secret
5. `get_current_user()` upserts the corresponding `app_users` row on every request — new Supabase users get their DB profile auto-created on first call

### Background Tasks

Embedding and cover-fetching run as FastAPI `BackgroundTask` objects — they execute after the response is sent, in the same process event loop. For production load, replace with a proper task queue (Celery + Redis, or RQ).

---

## Migration History

| Revision | Description |
|---|---|
| (initial) | Books, Authors, Tropes, Archetypes, associations |
| +genres | Added Genre model and book_genres junction |
| +book_types | Added BookType model |
| +tones | Added Tone model |
| +reading_status | ReadingStatus model |
| +ratings | BookRating model |
| +dislikes | BookDislike model |
| +embeddings | pgvector columns on books (genome 384d, description 768d) |
| +covers | cover_url column |
| +pacing | pacing column (1–5) |
| +description | description column |
| +supabase_auth | Migrated user_id to UUID for Supabase Auth |
| +series | Series model, series_id/series_position on books |
| +user_tags | UserBookTrope, UserBookArchetype models |
| +indexes | Performance indexes |
| +constraints | Check constraints on weights/importance |
| +cascades | ON DELETE CASCADE |
| +embed_status | Renamed/consolidated embedding status field |
| j4k5l6m7n8o9 | Drop `embedding_jobs` and `recommendation_events` (replaced by inline `embedding_status` on books) |
| k5l6m7n8o9p0 | Add `preferences` JSONB to `app_users` (blocked content lists, profile_public) |
| l6m7n8o9p0q1 | Add `user_follows` table (follower_id, followee_id, created_at; composite PK + indexes) |
| n8o9p0q1r2s3 | Add `search_vector` tsvector GENERATED column to books (full-text for hybrid search) |
| o9p0q1r2s3t4 | Add `page_count`, `review_embedding` vector(768) to books |
| s3t4u5v6w7x8 | Drop `language` column from books (Open Library data unreliable; unused in embeddings/search) |
| p0q1r2s3t4u5 | Phase 3 crowd promotion: add `character_dna.is_crowd_promoted`, `books.review_embed_count` |
| q1r2s3t4u5v6 | Drop `app_users.onboarding_completed` (unused column) |
