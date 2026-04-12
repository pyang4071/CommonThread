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

### [TEMPLATE] Supabase JWT — `app_users` row not created for new auth users

**Context**: New user signs up via Supabase Auth and makes their first authenticated API call.

**Error**: `404 Not Found` or `None` returned from `get_current_user()` for a user that exists in Supabase Auth but has no row in the local `app_users` table.

**Root Cause**: Supabase Auth and the local `app_users` table are separate. Supabase Auth manages credentials; the application manages profile data. A new Supabase Auth user has no corresponding `app_users` row until one is created.

**Fix**: `app/auth.py`'s `get_current_user()` function does an upsert — if no `app_users` row exists for the JWT's `sub` (user UUID), it creates one with the email from the token claims.

**Prevention**: Always treat `get_current_user()` as an upsert, not a pure lookup. If you rewrite auth logic, preserve the auto-creation behavior or new users will get 404s on their first request.

---
