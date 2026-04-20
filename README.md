# CommonThread

A book recommendation engine powered by tropes and character archetypes. CommonThread uses a three-stream semantic embedding approach to match readers with books based on structural literary elements (tropes, archetypes, genres), descriptive prose, and user reviews — with hybrid lexical+semantic search for broad discovery.

---

## Project Intent & Goals

CommonThread is being built for ECE 464. The core thesis: traditional book recommendation systems (collaborative filtering, genre tags) miss the actual *feel* of a book. CommonThread models books at the level of narrative DNA — tropes and archetypes with weighted importance — and embeds them into vector space to enable:

- **"More like this"** similarity based on shared story structure
- **Personalized recommendations** derived from a user's rating/shelf history
- **Semantic vibe search** that understands "cozy mystery with a slow-burn romance" as a query
- **Hybrid search** combining full-text keyword matching with semantic description similarity via Reciprocal Rank Fusion
- **User tagging** where readers contribute their own trope/archetype annotations

---

## Current State

| Area | Status |
|---|---|
| Backend API | Feature-complete — all routes functional |
| Database schema | Stable (25 migrations applied) |
| Embedding pipeline | Working — three-stream BGE via FastEmbed; description always embedded, genome gated at ≥ 3 tropes; review embed batched at every 5 new reviews |
| Vibe/semantic search | Working — alpha-blended genome + description (`GET /search`) |
| Hybrid search | Working — RRF combining PostgreSQL full-text + BGE description cosine (`POST /search/hybrid`) |
| Personalized recommendations | Working — user taste vector from history |
| Friends / social | Working — follow system, activity feed, public profiles |
| User preferences | Working — content blacklist (genres/types/tones), privacy toggle |
| Frontend | Feature-complete — data router, navigation guard on AddBook, 403 Unauthorized page, threshold badge, optional tropes, page_count/language filters, crowd-tagged badges |
| Admin dashboard | Working — embed-all (incl. description backfill), stall detection + crash recovery, fetch-covers, vector coverage panel with genome-eligible stat |
| Crowd promotion | Working — user trope/archetype tags promoted to canonical at N≥3 users; median weight; dominant-anchor rule; ratchet (no auto-demotion); archetypes supported |
| Auth | Working via Supabase JWT; AuthContext race condition fixed |
| E2E Testing | **57 tests** — Playwright across public/user/admin projects; 56 pass, 1 skip (all green) |
| Unit Testing | Minimal — pytest scaffolded; crowd promotion tests rewritten for Phase 3 design |
| Deployment | Docker Compose config added (`docker-compose.yml`) |
| Data ingestion | **`backend/webscraper/`** — Open Library scraper (10,020 books scraped); `import_tagged_books.py` — tagged books import; **648 books tagged and live** |

### In-progress / Pending
- `embedding_jobs` and `recommendation_events` tables were dropped in the latest migration (j4k5l6m7n8o9) — they were replaced by the `embedding_status` column directly on the `books` table
- No persistent task queue (Celery/RQ) — background tasks run in the FastAPI event loop
- Backend unit tests — pytest scaffolded but not comprehensive

---

## Tech Stack

### Backend
| Tool | Version | Role |
|---|---|---|
| Python | 3.12 | Runtime |
| FastAPI | ≥0.115.0 | API framework |
| SQLAlchemy | ≥2.0.0 (async) | ORM |
| asyncpg | ≥0.29.0 | Async Postgres driver |
| Alembic | ≥1.13.0 | DB migrations |
| pgvector | ≥0.4.2 | Vector similarity in Postgres |
| FastEmbed | ≥0.8.0 | Local BGE embedding models |
| Supabase | ≥2.28.3 | Auth (JWT) + Postgres hosting |
| PyJWT | ≥2.12.1 | JWT validation |
| httpx | ≥0.27.0 | Async HTTP (cover fetching + Open Library scraper) |
| psycopg2-binary | ≥2.9.0 | Alembic sync driver |
| Pydantic Settings | ≥2.0.0 | Config management |
| Ruff | ≥0.6.0 | Linting/formatting |

### Frontend
| Tool | Version | Role |
|---|---|---|
| React | 19.2.4 | UI framework |
| TypeScript | 5.9.3 | Type safety |
| Vite | 8.0.1 | Build tool / dev server |
| React Router | 7.13.2 | Client-side routing |
| Supabase JS | 2.101.0 | Auth client |
| Tailwind CSS | 4.2.2 | Styling |

### Infrastructure
- **Database**: PostgreSQL (hosted on Supabase) with `pgvector` extension
- **Auth**: Supabase Auth (JWT — validated server-side in FastAPI)
- **Embeddings**: Models downloaded locally at first use via FastEmbed (~2 GB total)

---

## Repository Structure

```
CommonThread/
├── README.md
├── error_log.md
├── FEATURES.md
├── e2e/                             ← Playwright end-to-end test suite
│   ├── tests/
│   │   ├── 1-home.spec.ts           # Public: home, 404, nav
│   │   ├── 2-auth.spec.ts           # Public: login, signup, forgot-password
│   │   ├── 3-books.spec.ts          # User: browse, search, filters
│   │   ├── 4-book-detail.spec.ts    # User: detail page, status, ratings
│   │   ├── 5-tropes-archetypes.spec.ts
│   │   ├── 6-shelf.spec.ts
│   │   ├── 7-my-tags.spec.ts
│   │   ├── 8-friends.spec.ts
│   │   ├── 9-profile.spec.ts
│   │   ├── 10-admin.spec.ts         # Admin: genres/types/tones CRUD, dashboard
│   │   └── 11-tagging-threshold.spec.ts  # Admin: threshold badge, embed race
│   ├── global-setup.ts              # Magic-link Supabase login, saves storageState
│   ├── playwright.config.ts
│   ├── .env                         # TEST_EMAIL, ADMIN_EMAIL, SUPABASE_* (gitignored)
│   └── .auth/                       # Saved session state (gitignored)
├── backend/
│   ├── webscraper/                  ← Open Library data ingestion
│   │   ├── __init__.py
│   │   ├── models.py                # ScrapedBook + ScrapeProgress Pydantic models
│   │   ├── scraper.py               # Async httpx scraper (search + description fetch)
│   │   ├── run.py                   # CLI entry point (argparse)
│   │   └── output/                  # JSONL output + progress.json (gitignored)
│   ├── app/
│   │   ├── main.py              # FastAPI app init, lifespan, CORS
│   │   ├── config.py            # Settings (reads .env)
│   │   ├── auth.py              # Supabase JWT validation
│   │   ├── dependencies.py      # DB session dependency
│   │   ├── database/
│   │   │   ├── engine.py        # Async SQLAlchemy engine
│   │   │   └── base.py          # ORM declarative base
│   │   ├── models/              # SQLAlchemy ORM models (20 files)
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── user_follow.py   ← follow graph
│   │   │   ├── book.py
│   │   │   ├── author.py
│   │   │   ├── trope.py
│   │   │   ├── archetype.py
│   │   │   ├── genre.py
│   │   │   ├── book_type.py
│   │   │   ├── tone.py
│   │   │   ├── series.py
│   │   │   ├── book_trope.py
│   │   │   ├── character_dna.py
│   │   │   ├── book_rating.py
│   │   │   ├── reading_status.py
│   │   │   ├── dislike.py
│   │   │   ├── user_book_trope.py
│   │   │   └── user_book_archetype.py
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── routers/             # API route handlers (14 modules)
│   │   │   ├── books.py
│   │   │   ├── recommendations.py
│   │   │   ├── search.py
│   │   │   ├── ratings.py
│   │   │   ├── reading_status.py
│   │   │   ├── dislikes.py
│   │   │   ├── user_tags.py
│   │   │   ├── users.py         ← extended with social/follow endpoints
│   │   │   ├── admin.py
│   │   │   ├── tropes.py
│   │   │   ├── archetypes.py
│   │   │   ├── genres.py
│   │   │   ├── book_types.py
│   │   │   ├── tones.py
│   │   │   └── series.py
│   │   ├── crud/                # Data access layer (14 modules)
│   │   │   └── follow.py        ← follow/unfollow/feed/search CRUD
│   │   └── services/
│   │       ├── embedding.py     # Dual-stream BGE pipeline
│   │       ├── similarity.py    # Sparse feature vector scoring
│   │       └── covers.py        # Book cover URL fetching
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/            # 21 Alembic migration files
│   ├── scripts/
│   │   ├── seed.py
│   │   ├── seed.sql
│   │   └── embed_all_books.py
│   ├── pyproject.toml
│   ├── alembic.ini
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── main.tsx             # React entry point
    │   ├── App.tsx              # Router + layout
    │   ├── api/
    │   │   └── client.ts        # Typed API wrapper (all endpoints)
    │   ├── contexts/
    │   │   ├── AuthContext.tsx  # Supabase session + AppUser state
    │   │   └── ToastContext.tsx # Global toast/snackbar system
    │   ├── hooks/
    │   │   └── useSessionState.ts  # sessionStorage persistence hook
    │   ├── lib/
    │   │   └── supabase.ts      # Supabase client init
    │   ├── components/
    │   │   ├── ProtectedRoute.tsx  # adminOnly prop for gating
    │   │   ├── RatingModal.tsx
    │   │   ├── ReadingStatusButton.tsx
    │   │   └── ConfirmModal.tsx
    │   └── pages/
    │       ├── Home.tsx            # Recs + currently reading + friend feed strip
    │       ├── Books.tsx           # Browse with filters, vibe search, content blacklist
    │       ├── BookDetail.tsx
    │       ├── Shelf.tsx
    │       ├── MyTags.tsx
    │       ├── Profile.tsx         # Name, privacy toggle, content blacklist
    │       ├── Friends.tsx         # User search, following list, activity feed
    │       ├── UserProfile.tsx     # Public profile view + friend's shelf
    │       ├── Tropes.tsx
    │       ├── TropeDetail.tsx
    │       ├── ArchetypeDetail.tsx
    │       ├── Genres.tsx          # Admin-only
    │       ├── BookTypes.tsx       # Admin-only
    │       ├── Tones.tsx           # Admin-only
    │       ├── Admin.tsx
    │       ├── AddBook.tsx
    │       ├── EditBook.tsx
    │       ├── NotFound.tsx
    │       ├── Unauthorized.tsx    # 403 page for non-admin hitting admin routes
    │       └── auth/
    │           ├── Login.tsx
    │           ├── SignUp.tsx
    │           ├── ForgotPassword.tsx
    │           └── ResetPassword.tsx
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tailwind.config.js
    └── package.json
```

---

## Database Schema

### Core Tables

```
books
  book_id (PK int)
  title, isbn (unique), publication_date
  description (text, nullable)
  pacing (int 1-5, nullable)
  page_count (int, nullable)
  language (varchar, nullable)
  cover_url (nullable)
  search_vector (tsvector GENERATED) ← full-text index for hybrid search
  genome_embedding (vector 384)      ← structural/trope embedding (≥3 tropes required)
  description_embedding (vector 768) ← prose embedding (all books)
  review_embedding (vector 768)      ← aggregated review embedding
  embedding_status ('pending'|'done'|'failed')  ← 'done' = description embedded
  author_id (FK → authors)
  series_id (FK → series, nullable)
  series_position (nullable)
  created_at, updated_at, deleted_at (soft delete)

authors           author_id, name, bio
tropes            trope_id, name, description, category
archetypes        archetype_id, name, description
genres            genre_id, name, description
book_types        book_type_id, name, description
tones             tone_id, name
series            series_id, name, description
app_users         user_id (UUID), name, email, is_admin, onboarding_completed
                  preferences (JSONB) — { blocked_genre_ids, blocked_book_type_ids,
                                          blocked_tone_ids, profile_public }
```

### Association Tables

```
book_tropes (book_id, trope_id, weight 0.0-1.0)
character_dna (book_id, archetype_id, importance 1-10)
book_genres (book_id, genre_id)
book_book_types (book_id, book_type_id)
book_tones (book_id, tone_id)
book_ratings (user_id, book_id, rating 1-5, review_text)
reading_status (user_id, book_id, status)
book_dislikes (user_id, book_id)
user_book_tropes (user_id, book_id, trope_id, weight)    ← personal tags
user_book_archetypes (user_id, book_id, archetype_id, importance) ← personal tags
user_follows (follower_id UUID, followee_id UUID, created_at) ← follow graph (composite PK)
```

### Entity Relationships

```
AppUsers ─── BookRating, ReadingStatus, BookDislike, UserBookTrope, UserBookArchetype
AppUsers ─── UserFollow (follower_id / followee_id, self-referential many-to-many)
Authors ──── Books (one-to-many)
Books ─────── Genres, BookTypes, Tones (many-to-many via plain junction tables)
Books ─────── Tropes (many-to-many via book_tropes with weight)
Books ─────── Archetypes (many-to-many via character_dna with importance)
Books ─────── Series (many-to-one, nullable)
```

---

## API Reference

**Base path**: `/api/v1`

All endpoints returning user-specific data require `Authorization: Bearer <supabase_jwt>`.

### Books — `/books`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/books` | Optional | List books with filters (genres, types, tones, pacing, tropes/archetypes to exclude, shelf status, keyword search) |
| POST | `/books` | Admin | Create book; triggers background embed + cover fetch |
| GET | `/books/{id}` | Optional | Book detail (tropes, archetypes, genres, types, tones) |
| PUT | `/books/{id}` | Admin | Update book; re-embeds |
| DELETE | `/books/{id}` | Admin | Soft delete |
| GET | `/books/{id}/series` | — | Other books in same series |
| POST | `/books/{id}/tropes` | Admin | Attach trope `{trope_id, weight}` |
| DELETE | `/books/{id}/tropes/{trope_id}` | Admin | Detach trope |
| POST | `/books/{id}/archetypes` | Admin | Attach archetype `{archetype_id, importance}` |
| DELETE | `/books/{id}/archetypes/{archetype_id}` | Admin | Detach archetype |
| POST | `/books/{id}/genres` | Admin | Attach genre |
| DELETE | `/books/{id}/genres/{genre_id}` | Admin | Detach genre |
| POST | `/books/{id}/book-types` | Admin | Attach book type |
| DELETE | `/books/{id}/book-types/{book_type_id}` | Admin | Detach book type |
| POST | `/books/{id}/tones` | Admin | Attach tone |
| DELETE | `/books/{id}/tones/{tone_id}` | Admin | Detach tone |
| GET | `/books/authors` | — | List all authors |

### Ratings & Reviews — `/books`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/books/{id}/rating` | Required | Get own rating |
| PUT | `/books/{id}/rating` | Required | Upsert rating `{rating: 1-5, review_text?}` |
| DELETE | `/books/{id}/rating` | Required | Delete own rating |
| GET | `/books/{id}/reviews` | — | All reviews for a book |

### Reading Status & Shelf — `/books`, `/shelf`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/books/{id}/reading-status` | Required | Get own status |
| PUT | `/books/{id}/reading-status` | Required | Upsert `{status: 'want_to_read'|'currently_reading'|'read'}` |
| DELETE | `/books/{id}/reading-status` | Required | Remove status |
| GET | `/shelf/my` | Required | Full shelf grouped by status |

### Dislikes — `/books`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/books/{id}/dislike` | Required | Check if disliked |
| PUT | `/books/{id}/dislike` | Required | Mark as disliked |
| DELETE | `/books/{id}/dislike` | Required | Remove dislike |

### Personal Tags — `/books`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/books/{id}/my-tags` | Required | Get own trope/archetype tags for a book |
| POST | `/books/{id}/my-tags/tropes` | Required | Add trope tag `{trope_id, weight}` |
| DELETE | `/books/{id}/my-tags/tropes/{trope_id}` | Required | Remove trope tag |
| POST | `/books/{id}/my-tags/archetypes` | Required | Add archetype tag `{archetype_id, importance}` |
| DELETE | `/books/{id}/my-tags/archetypes/{archetype_id}` | Required | Remove archetype tag |

### Search — `/search`
| Method | Path | Description |
|---|---|---|
| GET | `/search?q=...&limit=10&alpha=0.7` | Vibe/semantic search. `alpha` (0.0-1.0): 1.0 = pure genome (structural), 0.0 = pure description (vibe). Requires genome embedding. Supports same filters as `/books`. |
| POST | `/search/hybrid` | Hybrid search via Reciprocal Rank Fusion combining PostgreSQL full-text (lexical) and BGE-base description semantic similarity. Body: `{q, top_n, alpha, min_score, ...filters}`. Works for all books. Returns `{book, score, match_type, lex_rank, sem_rank}`. |

### Recommendations — `/recommendations`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/recommendations/for-you?limit=10` | Required | Personalized recs based on rating/shelf history |
| GET | `/recommendations/{book_id}/similar?limit=5` | — | Books similar to a given book |

### Reference Data
| Method | Path | Auth | Description |
|---|---|---|---|
| GET/POST/DELETE | `/tropes` | Admin (write) | Tropes CRUD; `/tropes/{id}/books` shows tagged books |
| GET | `/tropes/categories` | — | All trope categories |
| GET/POST/DELETE | `/archetypes` | Admin (write) | Archetypes CRUD; `/archetypes/{id}/books` shows books |
| GET/POST/DELETE | `/genres` | Admin (write) | Genres CRUD |
| GET/POST/DELETE | `/book-types` | Admin (write) | Book Types CRUD |
| GET/POST/DELETE | `/tones` | Admin (write) | Tones CRUD |
| GET/POST/PUT/DELETE | `/series` | — | Series CRUD |

### Users — `/users`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | Required | Current user profile (includes preferences) |
| PUT | `/users/me` | Required | Update profile `{name?, preferences?}` |
| GET | `/users/me/tags` | Required | All personal tags grouped by book |
| GET | `/users/search?q=` | Required | Search public users by name or email |
| GET | `/users/me/following` | Required | Users the caller follows |
| GET | `/users/me/followers` | Required | Users who follow the caller |
| POST | `/users/me/following/{user_id}` | Required | Follow a user |
| DELETE | `/users/me/following/{user_id}` | Required | Unfollow a user |
| GET | `/users/me/following/{user_id}/status` | Required | Check follow status |
| GET | `/users/me/feed?limit=30` | Required | Activity feed (shelf + ratings from followed users) |
| GET | `/users/{user_id}/profile` | Required | Public profile (403 if private and not following) |
| GET | `/users/{user_id}/shelf` | Required | User's shelf as `ShelfEntry[]` (403 if private) |

### Admin — `/admin`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/embed-status` | Admin | Counts by embedding status (done/pending/failed) |
| POST | `/admin/embed-all` | Admin | Queue all pending/failed books for embedding; crashes mark remaining books failed |
| GET | `/admin/vector-coverage` | Admin | `{total, both, description_only, neither}` embedding stream breakdown |
| POST | `/admin/fetch-covers` | Admin | Batch-fetch missing cover URLs |

---

## Embedding Architecture

### Three Embedding Streams

**Genome stream** (384-dim, `BAAI/bge-small-en-v1.5`):
- Encodes structured literary metadata into a single text string
- Includes: tropes with strength labels ("dominant"≥0.8, "strong"≥0.6, "moderate"≥0.4, "subtle"<0.4), archetypes with importance labels, genres, tones, pacing, title, author
- Deliberately **excludes** free-text description to keep signal clean
- Only computed when book has ≥ 3 canonical tropes (`TROPE_THRESHOLD = 3`)
- Stored in `books.genome_embedding`

**Description stream** (768-dim, `BAAI/bge-base-en-v1.5`):
- Encodes only the free-text book description
- Captures narrative vibe and prose semantics
- Embedded for **all books** regardless of trope count; sets `embedding_status = "done"`
- Stored in `books.description_embedding`; `NULL` if no description

**Review stream** (768-dim, `BAAI/bge-base-en-v1.5`):
- Encodes aggregated user review text
- Stored in `books.review_embedding`; `NULL` until reviews are embedded

### Search Blending

```
score = alpha * genome_score + (1 - alpha) * description_score
```

- Default `alpha=0.7` (70% structure, 30% vibe)
- If a book has no description, genome score is used alone regardless of alpha
- Queries use BGE asymmetric instruction prefix for both streams
- pgvector HNSW index with `hnsw.ef_search = 40`

### Personalized Recommendations

1. Collect user's books: ratings ≥4 + all shelf entries
2. Aggregate their tropes/archetypes (avg weight / avg importance)
3. Build a genome text from aggregated preferences
4. Embed in genome space → cosine search
5. Exclude books already rated or on shelf
6. Return with explanation (shared tropes/archetypes)

### Tagging Threshold & Embedding Lifecycle

`embedding_status = "done"` now means **description is embedded** — the minimum level for hybrid and keyword search. Genome is a bonus, gated at ≥ 3 tropes.

| Phase | Trigger | State |
|---|---|---|
| **Ingestion** | `POST /books` (Title, Author, ISBN, Description) | `embedding_status = pending`, both embeddings NULL |
| **Description embedded** | Embedding job runs | `embedding_status = done`, `description_embedding` populated |
| **Genome gated** | Trope count reaches `TROPE_THRESHOLD = 3` | `genome_embedding` also populated — book appears in vibe search, Similar Books, For You |

Key rules:
- Description embedding always runs; genome additionally requires ≥ 3 tropes.
- If a trope is removed and count drops below 3, only `genome_embedding` is cleared; `embedding_status` stays `done`.
- Admin **Embed All** queues all books with `status != "done"` — no trope-count gate.
- Background task crash recovery: if the batch crashes, remaining `pending` books are marked `failed` via bulk UPDATE.

Each book tracks `embedding_status`:
- `pending` — description not yet embedded
- `done` — description embedded (may or may not have genome)
- `failed` — embedding job threw an error

---

## Data Ingestion (Open Library Scraper)

The `backend/webscraper/` package fetches book metadata from the [Open Library API](https://openlibrary.org/developers/api) and saves it as JSONL files for later import into the database.

### What it collects

For each subject, the scraper calls:
1. `GET /search.json?subject={subject}&limit=100&page=N` — paginated work list
2. `GET /works/{id}.json` — full description per work (concurrent, up to 5 in parallel)

Fields saved per book: `ol_work_key`, `title`, `authors`, `isbn`, `isbn13`, `publication_year`, `publisher`, `page_count`, `language`, `subjects`, `cover_url`, `description`, `edition_count`.

### Built-in subjects (20)

`fantasy`, `mystery`, `romance`, `science fiction`, `thriller`, `historical fiction`, `horror`, `young adult`, `biography`, `self-help`, `classics`, `literary fiction`, `adventure`, `crime`, `philosophy`, `psychology`, `humor`, `poetry`, `graphic novels`, `short stories`

### Run

```bash
cd backend

# Scrape all 20 subjects, 500 books each (~10 000 books total, ~5 min)
uv run python -m webscraper.run

# Scrape a subset
uv run python -m webscraper.run --subjects fantasy mystery --books-per-subject 100

# Resume an interrupted run
uv run python -m webscraper.run --resume
```

Output lands in `backend/webscraper/output/`:
- `books_<subject>.jsonl` — one JSON object per line
- `progress.json` — checkpoint for `--resume`
- `summary.json` — written on completion
- `scrape.log` — full run log

> The `output/` directory is gitignored. Run the scraper locally before importing into the database.

---

## Docker Deployment

The project ships with a `docker-compose.yml` at the repo root that builds and runs both the backend and frontend.

### Prerequisites
- Docker with Compose v2 (`docker compose version`)
- A filled-in `backend/.env` (copy from `backend/.env.example`)
- Supabase credentials exported as shell variables (or in a root-level `.env` file)

### One-time setup

```bash
# 1 — backend secrets
cp backend/.env.example backend/.env
# edit backend/.env with your Supabase + DB credentials

# 2 — frontend build-time vars (baked into the JS bundle)
export VITE_SUPABASE_URL=https://<ref>.supabase.co
export VITE_SUPABASE_ANON_KEY=<anon-key>
# or add them to a root .env file (gitignored)
```

### Run

```bash
docker compose up --build
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Notes
- **FastEmbed models** (~570 MB) are downloaded on first startup and cached in a named Docker volume (`fastembed_cache`). Subsequent starts are instant.
- The `backend` service has a healthcheck that waits up to 120 s for the models to finish loading before the `frontend` container starts routing to it.
- The frontend nginx proxies `/api/*` → `http://backend:8000`, so the browser only ever talks to port 80.
- Set `ENVIRONMENT=production` and `CORS_ORIGINS=["https://yourdomain.com"]` in `backend/.env` for a hardened CORS policy.

---

## End-to-End Testing

The `e2e/` directory contains a Playwright test suite covering public, authenticated user, and admin flows.

### Setup

```bash
cd e2e
npm install

# Create credentials file (gitignored)
cp .env.example .env
# Fill in TEST_EMAIL, ADMIN_EMAIL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
```

No passwords are needed — `global-setup.ts` authenticates via Supabase **magic links** using the service role key.

### Run

```bash
cd e2e

# All 57 tests (requires .env with credentials)
npm test

# Public tests only — no credentials needed, 14 tests
npx playwright test --project=public

# Admin tests only
npx playwright test --project=admin

# Single file
npx playwright test 11-tagging-threshold.spec.ts --project=admin

# Interactive UI mode
npx playwright test --ui
```

The dev server (`npm run dev` in `frontend/`) and backend (`uv run fastapi dev app/main.py` in `backend/`) must both be running before executing the tests.

---

## Local Development Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL with `pgvector` extension (or a Supabase project)

### Backend

```bash
cd backend

# Configure environment (first time only)
cp .env.example .env
# Edit .env with your Supabase credentials and DATABASE_URL

# Run migrations
uv run alembic upgrade head

# Start dev server
uv run fastapi dev app/main.py
# Runs at http://localhost:8000
# Auto-docs at http://localhost:8000/docs
```

> `uv` manages the virtualenv automatically — no manual activation needed.

### Frontend

```bash
cd frontend

npm install

# Create environment file with Supabase config
# The Supabase URL/anon key are in src/lib/supabase.ts

npm run dev
# Runs at http://localhost:5173
# Proxies /api → http://localhost:8000 (configured in vite.config.ts)
```

### Useful Backend Commands

```bash
# Run linter/formatter
uv run ruff check .
uv run ruff format .

# Create a new migration
uv run alembic revision --autogenerate -m "description of change"

# Apply migrations
uv run alembic upgrade head

# Roll back one migration
uv run alembic downgrade -1

# Embed all books (script)
uv run python scripts/embed_all_books.py

# Import pre-tagged books from tagged_books.json
uv run python scripts/import_tagged_books.py --no-embed

# Seed database
uv run python scripts/seed.py
```

### Useful Frontend Commands

```bash
npm run dev       # Dev server with HMR
npm run build     # Production build → dist/
npm run lint      # ESLint
npm run preview   # Preview production build locally
```

---

## Environment Variables

### Backend (`.env`)

```env
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
SECRET_KEY=change-me-in-production
ENVIRONMENT=development
```

> `SYNC_DATABASE_URL` is a computed property in `config.py` — it replaces `asyncpg` with `psycopg` for Alembic's synchronous migration runner. Do not set it manually.

### Frontend

Supabase credentials are currently hardcoded in `src/lib/supabase.ts`. For production, move these to `.env.local` as Vite `VITE_*` variables.

---

## Key Implementation Notes

### SQLAlchemy Async — Eager Loading Required

All relationships accessed in async route handlers **must** use explicit `selectinload()` or `joinedload()`. SQLAlchemy async does not support lazy loading (raises `MissingGreenlet`). See `feedback_async_sqlalchemy.md` in memory.

### React Router — Data Router Required

`App.tsx` uses `createBrowserRouter` + `RouterProvider` (React Router v7 data router), **not** the legacy `<BrowserRouter>`. This is required for `useBlocker` (navigation guard in AddBook). Do not revert to `<BrowserRouter>` — it breaks the dirty-form navigation guard.

### AuthContext — Loading Flag

`AuthContext.tsx` holds `loading = true` until both the Supabase session AND the `AppUser` profile are resolved. This prevents `ProtectedRoute` from seeing a transient `isAdmin = false` and firing a spurious redirect to `/unauthorized`. The `onAuthStateChange` listener skips its first event via `initializedRef` to avoid double-fetching.

### Admin CRUD — Auth Token Required

`api.genres.create/delete`, `api.tones.create/delete`, `api.bookTypes.create/delete`, and `api.archetypes.create/delete` all require an explicit `token` parameter (pass `session!.access_token` from `useAuth()`). They call `authedFetch()` internally. Do not use the generic unauthenticated `post()` / `del()` helpers for any admin write operation.

### Embedding Race Condition Guard

`_embed_in_background` (in `books.py`) checks the trope count **both before and after** calling `embed_book()`. The post-embed check ensures that if a `detach_trope` races with the background task and drops count below threshold during embedding, the `'done'` status is immediately reverted to `'pending'`. Similarly, `detach_trope` resets status whenever `embedding_status != 'pending'` (not just on `'done'`).

### Migrations

The migration chain is linear (no branches). The latest migration (`j4k5l6m7n8o9`) drops the now-unused `embedding_jobs` and `recommendation_events` tables — embedding status is now tracked directly on the `books` table via `embedding_status` column, and job tracking is handled inline in the FastAPI background task system.

### Authentication Flow

1. User signs in via Supabase Auth (frontend uses Supabase JS SDK)
2. Supabase issues a JWT
3. Frontend sends JWT as `Authorization: Bearer <token>` on every API request
4. FastAPI validates the JWT signature against the Supabase secret
5. `get_current_user()` fetches/creates the corresponding `AppUser` row in the local DB

### Background Tasks

Embedding and cover-fetching run as FastAPI `BackgroundTask` objects — they execute after the response is sent, in the same process event loop. For production load, replace with a proper task queue (Celery + Redis, or RQ).

---

## Migration History Summary

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
| +pacing | pacing column (1-5) |
| +description | description column |
| +supabase_auth | Migrated user_id to UUID for Supabase Auth |
| +series | Series model, series_id/series_position on books |
| +user_tags | UserBookTrope, UserBookArchetype models |
| +indexes | Added performance indexes |
| +constraints | Added check constraints on weights/importance |
| +cascades | Added ON DELETE CASCADE |
| +embed_status | Renamed/consolidated embedding status field |
| j4k5l6m7n8o9 | **Drop embedding_jobs and recommendation_events** (replaced by inline status) |
| k5l6m7n8o9p0 | **Add preferences JSONB to app_users** (blocked content lists, profile_public) |
| l6m7n8o9p0q1 | **Add user_follows table** (follower_id, followee_id, created_at; composite PK + indexes) |
| n8o9p0q1r2s3 | **Add search_vector tsvector GENERATED column** to books (lexical full-text for hybrid search) |
| o9p0q1r2s3t4 | **Add page_count, language columns** to books; add review_embedding vector(768) |
