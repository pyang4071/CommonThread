# CommonThread — Error Log

This file records errors encountered during development, their root causes, and how they were resolved, so future agents or developers do not repeat the same debugging cycles.

---

## Format

Each entry follows this structure:

```
### [DATE] Error title
**Context**: Where/when the error appeared
**Error**: The exact error message or symptom
**Root Cause**: Why it happened
**Fix**: What was changed to resolve it
**Prevention**: How to avoid this in the future
```

---

## Errors

### 2026-04-05 — `embedding_jobs` / `recommendation_events` tables dropped from models but still existed in DB

**Context**: Migration `j4k5l6m7n8o9` was written after `EmbeddingJob` and `RecommendationEvent` models were removed from `app/models/`.

**Error**: Alembic autogenerate would try to drop the tables on the next `--autogenerate` run; existing DB had stale tables not reflected in ORM.

**Root Cause**: The models were deleted from `app/models/__init__.py` and the individual files (`embedding_job.py`, `recommendation_event.py`) were deleted, but no migration was written to drop the tables from the database.

**Fix**: Wrote migration `j4k5l6m7n8o9` with explicit `op.drop_table('embedding_jobs')` and `op.drop_table('recommendation_events')` in `upgrade()`, and re-creation DDL in `downgrade()`.

**Prevention**: Whenever an ORM model file is deleted, always write a corresponding Alembic migration to drop the underlying table. Never rely solely on `--autogenerate` to detect deleted models — it only works if the model was imported into `env.py`'s metadata scope at the time the model existed.

---

### [TEMPLATE] MissingGreenlet error on relationship access in async routes

**Context**: Any async route handler that accesses an ORM relationship that was not eagerly loaded.

**Error**:
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here.
Was IO attempted in an unexpected place?
```

**Root Cause**: SQLAlchemy async mode does not support implicit lazy loading. When a relationship attribute is accessed outside of an `await`-able context (i.e., after the async session has been used to fetch the parent object), SQLAlchemy tries to fire a lazy SELECT but cannot do so without an event loop greenlet.

**Fix**: Add `selectinload()` or `joinedload()` to the initial query for every relationship that will be accessed in the response serialization.

Example:
```python
# WRONG — triggers lazy load
result = await db.execute(select(Book).where(Book.book_id == book_id))
book = result.scalar_one()
print(book.book_tropes)  # MissingGreenlet here

# CORRECT — explicit eager load
from sqlalchemy.orm import selectinload
result = await db.execute(
    select(Book)
    .options(selectinload(Book.book_tropes).selectinload(BookTrope.trope))
    .where(Book.book_id == book_id)
)
book = result.scalar_one()
print(book.book_tropes)  # safe
```

**Prevention**: Always use `selectinload()` for collections and `joinedload()` for single relationships when using SQLAlchemy async. Never access a relationship attribute on an ORM object fetched in an async session without having loaded it eagerly in the query.

---

### [TEMPLATE] Alembic `SYNC_DATABASE_URL` — do not set manually

**Context**: Running `alembic upgrade head` after setting environment variables.

**Error**: Connection refused or driver mismatch if `DATABASE_URL` still uses `asyncpg` driver during Alembic migrations.

**Root Cause**: Alembic's migration runner is synchronous. The `DATABASE_URL` in `.env` uses the `postgresql+asyncpg://` scheme, which is incompatible with the synchronous `env.py`.

**Fix**: `app/config.py` exposes a `SYNC_DATABASE_URL` computed property that replaces `asyncpg` with `psycopg`. Alembic's `env.py` uses `settings.SYNC_DATABASE_URL` automatically.

**Prevention**: Never set `SYNC_DATABASE_URL` as an environment variable. It is computed from `DATABASE_URL` — just set `DATABASE_URL` correctly and let `config.py` derive the sync variant.

---

### [TEMPLATE] pgvector HNSW index not used — queries fall back to sequential scan

**Context**: Semantic search queries returning slowly; `EXPLAIN ANALYZE` shows `Seq Scan`.

**Error**: No error thrown, but performance degrades severely at scale. pgvector only uses the HNSW index for approximate nearest neighbor queries when `hnsw.ef_search` is set.

**Root Cause**: pgvector requires `SET hnsw.ef_search = N` to be executed in the session before running a vector similarity query, otherwise it defaults to exact search (sequential scan).

**Fix**: The search router (`app/routers/search.py`) executes `await db.execute(text("SET hnsw.ef_search = 40"))` before issuing the vector similarity query.

**Prevention**: Always set `hnsw.ef_search` in the same DB session before any `<=>` cosine distance query when using HNSW-indexed columns.

---

### [TEMPLATE] FastEmbed models download at first use — cold start hang

**Context**: First request to any endpoint that triggers embedding (book create, search, recommendations) hangs for several minutes.

**Error**: No error — just a very long response time on first use. FastEmbed downloads `BAAI/bge-small-en-v1.5` (~130 MB) and `BAAI/bge-base-en-v1.5` (~440 MB) to `~/.cache/fastembed/` on first invocation.

**Root Cause**: FastEmbed lazily initializes and downloads models on first use. In production this would manifest as a cold-start timeout.

**Fix (dev)**: Accept the one-time download. Models are cached after first use.

**Fix (prod)**: `app/main.py` lifespan handler now pre-warms both models via `run_in_executor` before `yield`. The Docker volume `fastembed_cache` persists the cache across container restarts. The `/health` endpoint reports `"genome": "ready"` / `"description": "ready"` once models are loaded.

**Prevention**: Document expected first-run behavior. The `/health` healthcheck in `docker-compose.yml` uses a 120 s `start_period` to allow for first-run model download.

---

### [TEMPLATE] Alembic configparser rejects % in DATABASE_URL

**Context**: Running `uv run alembic upgrade head` after setting a database password containing special characters (e.g. `@` percent-encoded as `%40`).

**Error**:
```
ValueError: invalid interpolation syntax in '...DayDream4071%40...' at position 63
```

**Root Cause**: Alembic's `env.py` calls `config.set_main_option("sqlalchemy.url", ...)` which feeds the URL into Python's `configparser`. ConfigParser uses `%` as an interpolation prefix, so `%40` is treated as a malformed interpolation expression rather than a literal string.

**Fix**: Escape `%` as `%%` before passing to `set_main_option`. The actual engine (`create_async_engine`) reads from `settings.DATABASE_URL` directly and is unaffected:
```python
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))
```

**Prevention**: Any time a DATABASE_URL contains percent-encoded characters (common with special-character passwords), apply this escape. The `%%` is only needed for configparser — SQLAlchemy's engine accepts the original `%40` form correctly.

---

### [TEMPLATE] React context must wrap all consumers — ToastProvider placement

**Context**: Adding `ToastProvider` to `App.tsx` when `ReadingStatusButton` (used inside many pages) calls `useToast()`.

**Error**:
```
Error: useToast must be used within ToastProvider
```

**Root Cause**: `ToastProvider` was initially placed inside `AuthProvider`, but `AuthProvider` renders the `<Header>` which contains nav links — and some components that call `useToast()` may render before the inner provider is mounted if the tree is ordered incorrectly.

**Fix**: Place `ToastProvider` as the outermost wrapper in `App.tsx`, outside `AuthProvider`, so every component in the tree can call `useToast()` regardless of auth state.

**Prevention**: Toast/notification context should always be at the root of the provider tree. Rule of thumb: providers that have no dependencies go outermost; providers that depend on auth state go inside `AuthProvider`.

---

### [TEMPLATE] Cover fetch — no retry on transient network errors

**Context**: Background cover fetching after book create/update, or admin `/fetch-covers`.

**Error**: Silent failure — `fetch_cover_url` catches `httpx.HTTPError` on the first attempt and returns `None`, leaving `cover_url` as `NULL` even when OpenLibrary would have succeeded on a retry.

**Root Cause**: Original implementation had no retry loop; a single timeout or transient 5xx silently returned `None`.

**Fix**: `covers.py` now lets `httpx.HTTPError` propagate from `_probe_isbn` / `_search_cover` and retries up to 3 times with exponential back-off (1 s, 2 s) at the `fetch_cover_url` level. "No cover found" (404 / empty search results) is still a silent `None` — only actual network/HTTP errors are retried.

**Prevention**: When wrapping external HTTP calls that touch a CDN or third-party API, always retry on `httpx.TransportError` / 5xx at the service layer, not the caller.

---

### 2026-04-13 — `useRef` missing from BookDetail.tsx import

**Context**: `BookDetail.tsx` uses `useRef` extensively (tropeTagRef, tropeTagListRef, archetypeTagRef, archetypeTagListRef) but the React import only listed `useEffect, useState`.

**Error**: TypeScript would report `useRef` is not defined; the project likely compiled due to global type inference or lenient tsconfig, but it's a latent type error.

**Root Cause**: `useRef` was added to the component body when the typeahead inputs were implemented but was not added to the destructured import from `'react'`.

**Fix**: Added `useRef` to the import: `import { useEffect, useRef, useState } from 'react'`.

**Prevention**: When adding new hooks to a component, always update the import statement at the top of the file in the same diff. TypeScript strict mode (`"strict": true` in tsconfig) would surface this immediately.

---

### [TEMPLATE] Supabase JWT — `app_users` row not created for new auth users

**Context**: New user signs up via Supabase Auth and makes their first authenticated API call.

**Error**: `404 Not Found` or `None` returned from `get_current_user()` for a user that exists in Supabase Auth but has no row in the local `app_users` table.

**Root Cause**: Supabase Auth and the local `app_users` table are separate. Supabase Auth manages credentials; the application manages profile data. A new Supabase Auth user has no corresponding `app_users` row until one is created.

**Fix**: `app/auth.py`'s `get_current_user()` function does an upsert — if no `app_users` row exists for the JWT's `sub` (user UUID), it creates one with the email from the token claims.

**Prevention**: Always treat `get_current_user()` as an upsert, not a pure lookup. If you rewrite auth logic, preserve the auto-creation behavior or new users will get 404s on their first request.

---

### 2026-04-13 — Silent `.catch(() => {})` swallowing load errors with no user feedback

**Context**: Home.tsx, MyTags.tsx, Friends.tsx — initial data load effects.

**Error**: No error shown to user when shelf, recommendations, tags, following list, or activity feed failed to load. The page silently rendered as empty.

**Root Cause**: All initial data loads used `.catch(() => {})` — exceptions were swallowed with no toast or inline error.

**Fix**: Added `useToast` to Home.tsx and wired `.catch()` callbacks to `toast.error(...)` in all three files. MyTags and Friends already imported `useToast`; Home.tsx needed the import added.

**Prevention**: Never use `.catch(() => {})` on user-visible data loads. At minimum, call `toast.error(...)` in the catch so the user knows a load failed.

---

### 2026-04-13 — ProtectedRoute admin redirect sent non-admin users to /404 instead of /unauthorized

**Context**: `frontend/src/components/ProtectedRoute.tsx` line 14.

**Error**: Non-admin users hitting admin-only routes (Genres, Book Types, Tones, Edit Book) were redirected to the 404 page instead of a meaningful 403 page.

**Root Cause**: `<Navigate to="/404" replace />` was hardcoded. No `/unauthorized` page existed.

**Fix**: Created `frontend/src/pages/Unauthorized.tsx` (403 page, same structure as NotFound). Changed redirect to `<Navigate to="/unauthorized" replace />`. Added `/unauthorized` route in App.tsx. Also fixed `/admin` route to use `<ProtectedRoute adminOnly>` since it was missing the flag.

**Prevention**: Always distinguish 403 (forbidden) from 404 (not found). Keep a dedicated Unauthorized page and redirect there from `adminOnly` route guards.

---

### 2026-04-13 — Playwright strict mode: `getByText(/404|not found/i)` matched two elements on NotFound page

**Context**: `e2e/tests/1-home.spec.ts` — "404 page shown for unknown routes" test.

**Error**:
```
Error: strict mode violation: getByText(/404|not found/i) resolved to 2 elements:
  1) <p class="text-6xl font-bold text-gray-200">404</p>
  2) <h1>Page not found</h1>
```

**Root Cause**: The NotFound page renders both a large decorative `404` number and a `<h1>Page not found</h1>` heading. The regex `/404|not found/i` matched both, violating Playwright's strict mode (single-element assertion).

**Fix**: Added `.first()` to the locator: `page.getByText(/404|not found/i).first()`.

**Prevention**: When using `getByText` with a broad regex on pages that may have repeated text (decorative + semantic), always append `.first()` or use a more specific selector like `getByRole('heading', { name: /page not found/i })`.

---

### 2026-04-13 — Playwright e2e suite: user/admin tests require credentials in e2e/.env

**Context**: Running `npm test` in `e2e/` without a `.env` file configured.

**Error**: All `[user]` project tests fail with `expect(page).toHaveURL('/books')` — the page redirected to `/auth/login` because `globalSetup` wrote an empty `storageState` (no session).

**Root Cause**: The `user` and `admin` Playwright projects use `storageState` files populated by `global-setup.ts`. Without `TEST_EMAIL`/`TEST_PASSWORD` in `e2e/.env`, globalSetup skips login and writes `{ cookies: [], origins: [] }`, so every protected route redirect fires.

**Fix**: Copy `e2e/.env.example` to `e2e/.env` and fill in credentials for a regular user and an admin user before running the full suite:
```bash
cp e2e/.env.example e2e/.env
# Edit e2e/.env with TEST_EMAIL, TEST_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD
npm test          # all projects
npm run test:public   # no credentials needed — 14/14 pass
```

**Prevention**: Always check `e2e/.env` exists before running the full suite in CI. The public project (`npm run test:public`) covers 14 tests and needs no credentials — use it as a smoke test.

---

### 2026-04-18 — Trope threshold blocked 6997 imported books from all search features

**Context**: Admin "Embed All" button; 6997 books imported via Open Library with no tropes.

**Error**: No error thrown, but the admin panel reported "No eligible books to queue — 6997 books are pending but haven't reached the tagging threshold." All 6997 books were invisible in hybrid search and lexical search despite having descriptions.

**Root Cause**: `embedding_status = "done"` was conflated with "both genome AND description are embedded." The trope threshold gate in `embed_all` blocked description embedding for any book with < 3 tropes, leaving them `pending` forever. The semantic leg of hybrid search queries `description_embedding IS NOT NULL`, so these books were fully excluded from search even though their descriptions were available.

**Fix**: Split the embedding contract:
- `embedding_status = "done"` now means *description is embedded* (minimum for searchability)
- Genome is embedded only when `book.book_tropes >= 3` — checked per-book inside `embed_books_batch` and `embed_book` via the loaded `book_tropes` relationship
- `embed_description_only` now sets `embedding_status = "done"` so newly created books mark done after creation-time description embedding
- `embed_all` in admin no longer filters by trope count — it queues all pending/failed books and lets the embedding service decide per-book what to embed
- `detach_trope` (below threshold): clears `genome_embedding` only; no longer resets `embedding_status` to `"pending"`
- BookDetail "needs more tropes" badge condition changed from `embedding_status !== 'done' && tropes.length < 3` to just `tropes.length < 3`

**Prevention**: Never gate description embedding behind structural metadata thresholds. Description and genome are independent streams — a book with no tropes can still be searched by description. Only genome embedding should be gated on trope count.

---

### 2026-04-13 — Tagging threshold: embedding must not fire at book creation

**Context**: `app/routers/books.py` `create_book` endpoint; all trope/archetype/genre/tone attach endpoints.

**Error**: Original implementation triggered `_embed_in_background` immediately on `POST /books`, meaning a book with zero tropes would be embedded with a nearly-empty genome string (`"Title" by Author.` only). That vector has almost no structural signal, producing meaningless similarity and recommendation results.

**Root Cause**: Embedding was fire-and-forget on creation regardless of how much literary metadata the book had. A book with 0 tropes sits in the same embedding space as a fully-tagged book, but its vector is useless for cosine retrieval.

**Fix**: Introduced `TROPE_THRESHOLD = 3` in `books.py` and `admin.py`. Rules:
- `create_book` no longer calls `_embed_in_background` at all.
- Every `attach_trope` counts canonical tropes after insert; triggers embedding only when count ≥ 3.
- Every `detach_trope` that drops count below 3 clears `genome_embedding` and resets `embedding_status = 'pending'`.
- All other attach/detach endpoints (archetype, genre, tone) gate on trope count ≥ 3 before triggering.
- Admin **Embed All** skips books below the threshold.

**Prevention**: Never embed a book that lacks sufficient structured signal. The genome string is meaningless without at least a few tropes. Any future embed-triggering endpoint should call `_trope_count(db, book_id)` and compare against `TROPE_THRESHOLD` before scheduling the task.

---

### 2026-04-13 — AddBook navigation guard missing — unsaved form data silently discarded on navigate

**Context**: `frontend/src/pages/AddBook.tsx` — user clicks browser back or nav link mid-form.

**Error**: No confirmation prompt when navigating away from a partially filled AddBook form. All entered data was silently lost.

**Root Cause**: No `useBlocker` or `beforeunload` handler was implemented.

**Fix**: Added `isDirty` computed from non-empty title/author/isbn or any selected trope/archetype. Used `useBlocker(isDirty)` from react-router-dom to intercept in-app navigation, showing a `ConfirmModal`. Added `beforeunload` event listener for browser tab close/refresh. Set `submitted = true` on successful submit so the blocker doesn't fire after form completion.

**Prevention**: Any form with significant user input should guard navigation. Use `useBlocker` for in-app navigation and `beforeunload` for tab close. Always clear the dirty flag after successful submission before calling `navigate()`.

---

### 2026-04-14 — `index.html` title displayed "frontend" instead of "CommonThread"

**Context**: Browser tab, `<title>` tag in `frontend/index.html`.

**Error**: All pages showed "frontend" in the browser tab title — the Vite scaffold default was never updated.

**Root Cause**: `frontend/index.html` was generated by `npm create vite` and the `<title>` tag was never changed from the scaffold value.

**Fix**: Changed `<title>frontend</title>` → `<title>CommonThread</title>` in `frontend/index.html`.

**Prevention**: After any `create vite` scaffold, immediately update `index.html` title, `package.json` name, and `vite.config.ts` project name.

---

### 2026-04-14 — `useBlocker` crash: blank page on AddBook with `<BrowserRouter>`

**Context**: `frontend/src/App.tsx` — after adding `useBlocker(isDirty)` to AddBook.tsx.

**Error**: AddBook rendered a blank white page. Console: `Error: useBlocker() may be used only in the context of a <Router> component` — more precisely, React Router v7 requires a *data router* for `useBlocker`.

**Root Cause**: `App.tsx` used `<BrowserRouter>` + `<Routes>`, which is the legacy "memory router" pattern. React Router v7's `useBlocker` hook only works with data routers created via `createBrowserRouter`.

**Fix**: Migrated `App.tsx` from `<BrowserRouter><Routes>` to `createBrowserRouter([...]) + <RouterProvider>`. Introduced a `RootLayout` component that wraps all routes with `<ToastProvider><AuthProvider><Outlet /></AuthProvider></ToastProvider>`.

**Prevention**: In React Router v7, if you need any data-router feature (`useBlocker`, `useLoaderData`, `useFetcher`, actions), you must use `createBrowserRouter`. Do not mix the component-based `<BrowserRouter>` with v7 data hooks.

---

### 2026-04-14 — Admin CRUD API 401: genres/tones/bookTypes create and delete never sent auth token

**Context**: `frontend/src/api/client.ts` — `api.genres.create()`, `api.genres.delete()`, same for tones and bookTypes.

**Error**: Every attempt to create or delete a genre/tone/book type from the admin UI returned `401 Unauthorized` from the backend.

**Root Cause**: The API client functions for admin CRUD used the generic unauthenticated `post()` / `del()` helpers instead of `authedFetch()`. The backend requires an `Authorization: Bearer <token>` header on all write endpoints, enforced via `require_admin`.

**Fix**: Changed `api.genres.create`, `api.genres.delete`, `api.tones.create`, `api.tones.delete`, `api.bookTypes.create`, `api.bookTypes.delete`, `api.archetypes.create`, and `api.archetypes.delete` to accept a `token: string` parameter and call `authedFetch()`. Updated the corresponding page components (`Genres.tsx`, `Tones.tsx`, `BookTypes.tsx`) to extract `session` from `useAuth()` and pass `session!.access_token`.

**Prevention**: Any API function that calls a backend endpoint gated by `require_admin` or `get_current_user` must pass the bearer token. Audit all admin-only actions in `client.ts` to ensure they use `authedFetch`.

---

### 2026-04-14 — AddBook submit stays on `/books/new`: `useBlocker` intercepts post-submit navigate

**Context**: `frontend/src/pages/AddBook.tsx` — after successful book creation.

**Error**: After form submission, the page stayed at `/books/new` instead of navigating to `/books/{id}`. No navigation occurred.

**Root Cause**: `setSubmitted(true)` and `navigate(...)` were called in the same synchronous tick. React batches state updates, so `isDirty` was still `true` during the `navigate()` call (the re-render with `submitted=true` hadn't happened yet). `useBlocker` intercepted the navigation and blocked it silently.

**Fix**: Introduced a `navigateTo: string | null` state variable. On successful submit, call `setSubmitted(true)` and `setNavigateTo('/books/${id}')` together. A `useEffect` watches `navigateTo` and fires `navigate(navigateTo)` after the re-render where `isDirty` becomes `false`. This guarantees the blocker sees `isDirty = false` before the navigation is attempted.

**Prevention**: When using `useBlocker`, never call `navigate()` in the same tick as the state update that clears the dirty flag. Always defer navigation to a `useEffect` that runs after the state flush.

---

### 2026-04-14 — AuthContext race condition: `isAdmin` briefly false → ProtectedRoute redirects admin users to `/unauthorized`

**Context**: `frontend/src/contexts/AuthContext.tsx` — page load with a stored Supabase session.

**Error**: Admin users navigating directly to `/genres`, `/admin`, or any admin-only route were briefly redirected to `/unauthorized` before the page corrected itself — or in some cases were permanently redirected.

**Root Cause**: The initial `getSession()` call set `loading = false` synchronously after receiving the session, before the follow-up `api.users.me()` profile fetch completed. `ProtectedRoute` read `isAdmin` while `profile` was still `null` (fetch in-flight), which evaluated to `false`, firing the redirect.

**Fix**: Moved the profile fetch **inside** the `getSession()` `.then()` callback, before `setLoading(false)`. The `loading` flag now stays `true` until both the session AND the profile are known. `ProtectedRoute` only renders once it has the complete auth state. Added `initializedRef` to skip the first `onAuthStateChange` event (which duplicates `getSession()`).

**Prevention**: Auth context `loading` must remain `true` until ALL required auth state (session + profile/role) has been resolved. Never set `loading = false` in a step that fires a follow-up async fetch whose result guards routing decisions.

---

### 2026-04-14 — Playwright magic-link login: `storageState()` captured 0 items (empty session)

**Context**: `e2e/global-setup.ts` — storing authenticated session after Supabase magic-link login.

**Error**: `storageState()` saved `{ cookies: [], origins: [] }`. All protected-route tests then redirected to `/auth/login` despite the magic-link succeeding.

**Root Cause**: `storageState()` was called immediately after `page.goto(magicLink)` returned, but the Supabase JS SDK processes the `#access_token=...` URL fragment asynchronously via `onAuthStateChange`. By the time the page had navigated, the `sb-*-auth-token` key had not yet been written to `localStorage`.

**Fix**: Added a `page.waitForFunction()` poll after `goto()` that resolves only when `Object.keys(localStorage).some(k => k.startsWith('sb-') && k.endsWith('-auth-token'))` is true (timeout 15 s). Only then is `storageState()` called.

**Prevention**: When persisting Supabase session state in Playwright, always wait for the `sb-*-auth-token` localStorage key before capturing storage state. The magic-link redirect is synchronous; the token write is not.

---

### 2026-04-14 — Playwright strict mode violations in admin tests

**Context**: `e2e/tests/10-admin.spec.ts` and `11-tagging-threshold.spec.ts` — various `getByText()` and `getByRole()` calls.

**Errors** (multiple):
- `getByText(/Recommendations unlock.*3 tropes/i)` matched two elements (heading + sub-label)
- `page.getByText(uniqueName, { exact: false })` matched the genre name + the delete confirmation modal text
- Button name mismatch: test expected `"Embed All"` but actual button text is `"Embed pending & failed books"`; `"Fetch Covers"` vs `"Fetch missing covers"`

**Root Cause**: Playwright strict mode throws when a locator matches more than one element. The tests were written against approximate expected UI text that didn't match the actual rendered strings.

**Fix**:
- Appended `.first()` to ambiguous `getByText()` calls
- Used `{ exact: true }` on genre name lookups
- Updated button name regex to match actual rendered text: `/Embed pending|Embed All/i` and `/Fetch missing|Fetch Covers/i`
- ISBN input selector changed from `input[placeholder*="ISBN" i]` to `input[placeholder*="978" i]` to match the actual placeholder `"978-0-00-000000-0"`

**Prevention**: When writing Playwright tests for text content, use the exact string from the rendered UI or a regex with `.first()`. For button names, inspect the actual DOM — button text is often different from the feature name used in test prose.

---

### 2026-04-14 — `_embed_in_background` race: book stuck at `embedding_status = 'done'` after trope detach below threshold

**Context**: `backend/app/routers/books.py` — `detach_trope` endpoint and `_embed_in_background` task.

**Error**: After removing a trope that dropped the count from 3 to 2 (below `TROPE_THRESHOLD`), the BookDetail page still showed no threshold badge. The book had 2 tropes but `embedding_status = 'done'`, so the condition `embedding_status !== 'done' && tropes.length < 3` evaluated to `false`.

**Root Cause**: `detach_trope` only reset `embedding_status` to `'pending'` if the status was already `'done'`. If the background embedding task was still in-flight when the detach request arrived (status still `'pending'`), the reset was skipped. The background task then completed and set `embedding_status = 'done'`, leaving the book with 2 tropes and `'done'` status — no badge shown.

**Fix** (two-part):
1. **`detach_trope`**: Changed guard from `book_obj.embedding_status == "done"` to `book_obj.embedding_status != "pending"` — always resets unless already pending, catching the `'failed'` case too.
2. **`_embed_in_background`**: Added a **post-embed guard** — after `embed_book()` commits `'done'`, re-checks `_trope_count`. If count has dropped below threshold during embedding, immediately resets `embedding_status = 'pending'` and clears `genome_embedding`.

**Prevention**: Any background task that writes final state to the DB must re-validate business invariants (like trope count ≥ threshold) after its work is done, not just before. Pre-guards prevent wasted work; post-guards prevent stale state commits.

---

### 2026-04-14 — Goodreads scraper: initial selectors incorrect; fixed via live DOM inspection

**Context**: `backend/webscraper/scraper.py` — first test run of the scraper returned `genres=[]`, `page_count=None`, `isbn13=None`, `cover_url=placeholder` for all books.

**Error**: All field extraction for genres, details (pages/format/pub date), ISBN, and cover returned empty/null. Only title, authors, description, series, and ratings populated correctly.

**Root Cause**: Selectors were written based on known legacy Goodreads HTML (`.BookPageMetaSection__genreButton`, `[data-testid="bookDetails"]`, `#details`) — none of which exist in the current React layout. The actual selectors are:
- Genres: `[data-testid="genresList"] a` (not `.BookPageMetaSection__genreButton`)
- Pages/format: `[data-testid="pagesFormat"]` (not `[data-testid="bookDetails"]`)
- Publication date: `[data-testid="publicationInfo"]`
- ISBN + structured metadata: `<script type="application/ld+json">` (schema.org Book object)
- Cover URL: `img.ResponsiveImage` src attribute (or JSON-LD `image` field, preferred)

**Fix**: Rewrote all selector constants and extraction helpers. Now the primary source for isbn, numberOfPages, bookFormat, inLanguage, cover URL, and aggregateRating is the JSON-LD block. DOM selectors handle genres, series, description, shelf tags, and publication info.

**Prevention**: When maintaining the scraper, verify selectors against live pages using `playwright codegen` or a short debug script before assuming selectors are stable. Run `python3 -m webscraper.run --genres fantasy --books-per-genre 3` as a quick smoke test after any Goodreads layout change.

---

### [TEMPLATE] Goodreads scraper — Playwright blocks images/fonts by default, resource type must be checked correctly

**Context**: `backend/webscraper/scraper.py` — `_launch()` method; route interception to speed up scraping.

**Error** (anticipated): If `route.request.resource_type` is checked with `in` against a set but the Playwright API returns a string value not in the set, the abort condition silently falls through and all resources are fetched — slowing scraping significantly.

**Root Cause**: Playwright's `resource_type` values are lowercase strings: `"image"`, `"font"`, `"media"`, `"stylesheet"`, `"script"`, etc. Comparison must be case-sensitive lowercase.

**Fix**: The route handler in `_launch()` explicitly checks `route.request.resource_type in {"image", "font", "media", "stylesheet"}` (all lowercase) and calls `route.abort()` only for those types. All other types continue normally.

**Prevention**: When writing Playwright route interception, always use lowercase resource type strings and test against a literal set. Do not block `"script"` — Goodreads's new React layout requires JavaScript to render the DOM.

---

### [TEMPLATE] Goodreads scraper — `useBlocker` not applicable; Goodreads has dual legacy/React layouts

**Context**: `backend/webscraper/scraper.py` — all selector constants and extraction helpers.

**Error** (anticipated): Selectors written for the legacy Goodreads layout (`#bookTitle`, `#description`) fail silently on the new React-based layout, producing empty ScrapedBook objects (no title, no description, no genres).

**Root Cause**: Goodreads has been migrating pages to a React SPA. The new layout uses `data-testid` attributes (`[data-testid="bookTitle"]`) and class names with generated hashes. Legacy jQuery-era selectors (`#bookTitle`, `#description`) no longer match on migrated pages.

**Fix**: Every extraction helper tries the new-layout selector first and falls back to the legacy selector. Both are defined as module-level constants (`SEL_*_NEW` / `SEL_*_LEGACY`) for easy maintenance.

**Prevention**: When maintaining the scraper, always verify selectors against both layout variants. If Goodreads completes their migration, the legacy fallbacks can be removed. Use `playwright codegen https://www.goodreads.com/book/show/1` to regenerate selectors if the layout changes again.

---

### [TEMPLATE] Goodreads scraper — rate limiting / CAPTCHA

**Context**: `backend/webscraper/scraper.py` — `_throttle()`, `_goto_with_retry()`.

**Error** (anticipated): Goodreads may serve a CAPTCHA page or return HTTP 429 after rapid sequential requests. The scraper will see an empty DOM (no title found) and log a warning, silently skipping the book.

**Root Cause**: Goodreads uses bot detection. Requests without sufficient delay between pages trigger rate-limiting or CAPTCHA challenges.

**Fix**:
- Default delay of 1500 ms with ±30 % jitter (`_throttle()`).
- `_goto_with_retry()` retries up to 3 times with exponential back-off (2 s → 4 s → 8 s) on `TimeoutError`.
- `--no-headless` flag lets you run the browser visibly to manually solve a CAPTCHA, then resume with `--resume`.
- Do not reduce `--delay-ms` below ~1000 ms for large runs.

**Prevention**: Monitor `scrape.log` for clusters of "No title found — skipping" warnings — that is the signal that rate limiting has kicked in. Increase `--delay-ms` or pause the run and resume after a cool-down period.

---

### [TEMPLATE] Goodreads scraper — ISBN not always present; isbn13 preferred

**Context**: `backend/webscraper/scraper.py` — `_extract_details_block()`.

**Error** (anticipated): Many books on Goodreads list only ISBN-13 (or neither). Importing into CommonThread's `books` table with `isbn = NULL` will succeed (column is nullable), but the cover-fetch service in `covers.py` prefers ISBN for the OpenLibrary probe.

**Root Cause**: Goodreads details blocks are inconsistent — some editions list both ISBN-10 and ISBN-13, some only ISBN-13, some only ASIN (Kindle), some neither.

**Fix**: `_extract_details_block()` extracts both when present. `isbn13` is stored in the `ScrapedBook.isbn13` field (preferred). During DB import (future step), pass `isbn13` as the `isbn` field for the `books` table since the schema uses `isbn` as a single nullable unique column.

**Prevention**: When writing the DB import script, prefer `isbn13` over `isbn10`. If neither is present, the book can still be imported — `isbn` is nullable in the schema.

---

### 2026-04-14 — Goodreads shelf pagination broken; switched scraper to Open Library API

**Context**: `backend/webscraper/scraper.py` — `get_book_urls_for_genre()` using `/shelf/show/{genre}?page=N`.

**Error**: Scraper reported completing with far fewer than the target 500 books per genre. Investigation showed that `/shelf/show/{genre}?page=2` and all subsequent page numbers returned the exact same 50 book IDs as page 1. The `new_on_page == 0` guard triggered immediately on page 2, stopping the loop at 50 books.

**Root Cause**: Goodreads migrated to a React SPA. The `?page=N` query parameter on `/shelf/show/` is ignored by the client-side router — all page values render the same fixed set of 50 books. No "Next" pagination button exists in the DOM. Sort parameters (`?sort=num_ratings`, `?sort=avg_rating`, etc.) also all return the same 50 IDs.

**Fix**: Replaced the entire Playwright-based Goodreads scraper with a pure async HTTP scraper against the [Open Library API](https://openlibrary.org/developers/api):
- `GET /search.json?subject={subject}&limit=100&page=N` — paginates correctly, returns 100 new works per page
- `GET /works/{id}.json` — fetches full descriptions concurrently (up to 5 in parallel)
- No browser required — `httpx.AsyncClient` only (already a project dependency)
- 500 books per subject completes in ~2–3 minutes vs. hours with Playwright

**Prevention**: Before building a Playwright scraper for any site, verify that the target URL actually supports server-side pagination by comparing page 1 and page 2 responses. If IDs are identical across pages, the site uses client-side routing and URL-based pagination will not work. Prefer open APIs over scraping when available.

---

### [TEMPLATE] Open Library API — description field has two formats

**Context**: `backend/webscraper/scraper.py` — `_get_description()`.

**Error** (anticipated): Accessing `data["description"]` as a plain string raises `AttributeError` or returns unexpected dict content when the field uses the typed-value format.

**Root Cause**: The Open Library Works API returns `description` in two formats depending on how the data was entered:
1. Plain string: `"description": "This is the synopsis."`
2. Typed value object: `"description": {"type": "/type/text", "value": "This is the synopsis."}`

**Fix**: `_get_description()` checks `isinstance(raw, str)` first, then falls back to `raw.get("value")` for the dict form.

**Prevention**: Always handle both forms when reading any Open Library text field. The same pattern applies to `notes`, `first_sentence`, and other typed-text fields in the Works schema.

---

### 2026-04-17 — `overflow-hidden` on book card clips absolutely-positioned shelf dropdown

**Context**: `frontend/src/pages/Books.tsx` — `ReadingStatusButton` dropdown inside a book card.

**Error**: Clicking the "Add to Shelf" button on the Books page opened a dropdown that was immediately invisible — clipped to the card bounds with no visual feedback.

**Root Cause**: The card `<div>` had `overflow-hidden` set to clip the cover image corners. CSS `overflow-hidden` makes the element the containing block for absolutely-positioned descendants, clipping anything that renders outside the card's bounds. The `ReadingStatusButton` dropdown positioned itself absolutely relative to its trigger but was cropped by the parent's overflow boundary.

**Fix**: Removed `overflow-hidden` from the card `<div>`. Added `rounded-tl-lg rounded-bl-lg` directly to the cover `<img>` and placeholder `<div>` to preserve the rounded corner appearance without creating an overflow boundary.

**Prevention**: Never put `overflow-hidden` on a container that has absolutely-positioned children (dropdowns, tooltips, modals). Apply rounded corners directly to the element that needs them instead.

---

### 2026-04-17 — `Book.search_vector` not mapped on ORM model

**Context**: `backend/app/crud/search.py` — `_lexical_leg()` accessing `Book.search_vector` for full-text search.

**Error**:
```
AttributeError: type object 'Book' has no attribute 'search_vector'
```

**Root Cause**: Migration `n8o9p0q1r2s3` added a `search_vector tsvector GENERATED ALWAYS AS (...)` column to the `books` table in PostgreSQL, but the corresponding `Book` SQLAlchemy ORM model in `app/models/book.py` was never updated to declare the column. The column existed in the DB but was invisible to ORM queries.

**Fix**: Added `search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True, deferred=True)` to `Book`. Used `deferred=True` because the column is large and never needed in non-search contexts. Added `from sqlalchemy.dialects.postgresql import TSVECTOR` to the model imports.

**Prevention**: Whenever a migration adds a column, update the ORM model in the same PR. Generated columns (`GENERATED ALWAYS`) are no different — they must be declared on the model to be usable in ORM expressions like `func.ts_rank_cd(Book.search_vector, tsq)`.

---

### 2026-04-17 — `asyncio.gather` with shared SQLAlchemy async session raises concurrent operation error

**Context**: `backend/app/crud/search.py` — `hybrid_search()` running both search legs in parallel.

**Error**:
```
sqlalchemy.exc.InvalidRequestError: This session is provisioning a new connection;
concurrent operations are not permitted
```

**Root Cause**: `asyncio.gather(_lexical_leg(db, ...), _semantic_leg(db, ...))` ran both coroutines concurrently on the **same** `AsyncSession` object. SQLAlchemy async sessions are not thread-safe and do not support concurrent operations — the session was trying to provision a connection while already in progress.

**Fix**: Changed to sequential execution:
```python
lex_ids = await _lexical_leg(db, query, top_n, filter_kwargs)
sem_ids = await _semantic_leg(db, query, top_n, filter_kwargs)
```

**Prevention**: A single `AsyncSession` instance must be used sequentially — one `await` at a time. To run DB operations truly in parallel, create separate sessions for each task. When in doubt, run sequentially; the latency difference is negligible for queries that hit indexed columns.

---

### 2026-04-17 — `SET LOCAL hnsw.ef_search` silently dropped in Supabase session pooler

**Context**: `backend/app/crud/search.py` — `_semantic_leg()` executing `SET LOCAL hnsw.ef_search = 40` before a vector cosine query.

**Error**: No exception, but `SET LOCAL` had no effect: the HNSW index configuration was not applied, meaning the ANN index behaviour was whatever the server default was.

**Root Cause**: `SET LOCAL` only persists for the duration of the current transaction block. Supabase's session pooler issues each `await db.execute()` as a standalone statement, not inside an explicit `BEGIN`/`COMMIT`. `SET LOCAL` outside a transaction is either a no-op or raises a warning depending on PostgreSQL version.

**Fix**: Removed the `SET LOCAL hnsw.ef_search = 40` statement from `_semantic_leg()`. The HNSW index will use the server default `ef_search`. If tuning is needed in future, it must be done via a `BEGIN` / `SET LOCAL` / query / `COMMIT` block or by setting `hnsw.ef_search` as a session-level parameter in the connection string.

**Prevention**: `SET LOCAL` requires an active transaction. In pooler/serverless DB configurations (Supabase, PgBouncer), avoid `SET LOCAL` unless you explicitly wrap the operation in a transaction via `async with db.begin()`.

---

### 2026-04-17 — Open Library import created duplicate editions of the same work

**Context**: `backend/scripts/import_books.py` — deduplication logic; the DB after a full Open Library import.

**Error**: The Books page showed multiple identical-looking entries for popular works (Pride and Prejudice ×5, Dracula ×3, Coraline ×4, etc.). 1,240 out of 7,012 active books were duplicates.

**Root Cause**: The import script only deduped by ISBN (`Book.isbn == isbn`). Open Library has dozens of distinct ISBNs for the same work (each publisher/edition gets its own ISBN), so every edition was imported as a separate row with a unique ISBN but the same title and author.

**Fix**:
1. **Cleanup**: Soft-deleted the 1,240 duplicates via SQL — for each `(lower(title), author_id)` group, kept the lowest `book_id` and set `deleted_at = now()` on all others. 5,772 books remain.
2. **Prevention**: Added a title+author dedup check in `import_books.py` after the ISBN check. Before inserting, the script now queries `lower(title) + lower(author.name)` against active books and skips if a match exists.

**Prevention**: When importing from any catalog that uses edition-level ISBNs (Open Library, WorldCat, Goodreads), always deduplicate at the work level (`title + author`), not the edition level (`isbn`). Different ISBNs for the same `(title, author)` pair are almost always editions of the same work, not distinct books.

---

### 2026-04-17 — Pre-existing TypeScript errors blocking `npm run build`

**Context**: Discovered during Step 7 (frontend source labels) when verifying the build. None of these errors are in files changed during the recommendation engine work.

**Errors**:
```
src/App.tsx(2,70): error TS6133: 'Route' is declared but its value is never read.
src/App.tsx(2,77): error TS6133: 'Routes' is declared but its value is never read.
src/pages/Archetypes.tsx(25,26): error TS2554: Expected 2 arguments, but got 1.
src/pages/Archetypes.tsx(34,26): error TS2554: Expected 2 arguments, but got 1.
src/pages/Books.tsx(22,10): error TS6133: 'IncludeChip' is declared but its value is never read.
src/pages/Books.tsx(31,10): error TS6133: 'ExcludeChip' is declared but its value is never read.
src/pages/Profile.tsx(294,38): error TS2345: Argument of type '{blocked_genre_ids, blocked_book_type_ids, blocked_tone_ids}'
  is not assignable to 'UserPreferences' — missing required property 'profile_public'.
```

**Root Cause**: Pre-existing issues from prior development cycles. The `Route`/`Routes` imports in `App.tsx` are unused stubs left from the `<BrowserRouter>` → `createBrowserRouter` migration. The `Archetypes.tsx` arity errors suggest a function signature changed but callers weren't updated. `Profile.tsx` is missing `profile_public` in a `UserPreferences` literal.

**Fix needed**:
- `App.tsx`: Remove unused `Route` and `Routes` from the react-router-dom import
- `Archetypes.tsx`: Inspect the failing calls at lines 25 and 34 — likely a component or hook that now requires a second argument
- `Books.tsx`: Remove unused `IncludeChip` and `ExcludeChip` imports
- `Profile.tsx` line 294: Add `profile_public` to the partial `UserPreferences` object literal (use `profile_public: false` as default or pull from existing preferences)

**Prevention**: Run `npm run build` (not just `npm run dev`) in CI or before committing frontend changes. `vite dev` does not surface type errors; `tsc -b` does.

---

### 2026-04-27 — `patch("app.crud.user_tags.settings")` raises AttributeError — settings not at module level

**Context**: `backend/tests/test_crowdsourcing.py` — two tests patching `settings.CROWD_PROMOTION_THRESHOLD`.

**Error**:
```
AttributeError: <module 'app.crud.user_tags'> does not have the attribute 'settings'
```

**Root Cause**: `app/crud/user_tags.py` imports `settings` lazily — `from app.config import settings` is inside each function body, not at module level. `unittest.mock.patch("app.crud.user_tags.settings")` requires the attribute to exist at module level to replace it.

**Fix**: Changed patch target from `"app.crud.user_tags.settings"` to `"app.config.settings"`. Since the lazy import re-fetches `settings` from `app.config` on each function call, patching `app.config.settings` correctly intercepts the lookup. Also added `mock_settings.TROPE_THRESHOLD = 3` alongside the threshold override so the function doesn't fail on unset attributes.

**Prevention**: To patch a name that is lazily imported inside a function (`from module import name` inside the body), always patch the attribute on the **source module** (`"module.name"`), not on the importing module. Module-level imports can be patched on the importer; lazy/local imports must be patched at the source.

---

### 2026-04-27 — `test_does_not_touch_genome_or_status` asserted stale behavior after embedding contract change

**Context**: `backend/tests/test_recommendation_engine.py::TestEmbedDescriptionOnly::test_does_not_touch_genome_or_status`

**Error**:
```
AssertionError: assert 'done' == 'pending'
```

**Root Cause**: The test was written when `embed_description_only` was intended to be a side-effect-free helper that never touched `embedding_status`. After the April 2026 embedding contract split (see "Trope threshold blocked 6997 books" entry), `embed_description_only` was updated to set `embedding_status = "done"` — because `"done"` now means "description is embedded." The test was never updated to reflect this change.

**Fix**: Updated the assertion from `assert mock_book.embedding_status == "pending"` to `assert mock_book.embedding_status == "done"`. Also updated the test docstring and method name to describe the current behavior accurately.

**Prevention**: When the definition of a status field changes (especially one like `embedding_status` whose semantics shifted), grep all tests that assert on that field and update them in the same PR as the behavior change.

---
