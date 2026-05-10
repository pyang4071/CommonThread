# CommonThread — Final Write-up
## ECE 464: Databases

---

## 1. Mission

Most book recommendation systems treat books as items to be co-purchased or co-clicked. CommonThread treats them as structured literary objects — defined by the tropes they execute and the character archetypes they deploy — and matches readers to books based on story structure rather than what other people happened to buy.

The core problem: a reader who loved *The Name of the Wind* for its "Mentor/Protégé" dynamic and "Chosen One Reframed" trope has no good way to find books that share that specific DNA. Genre tags ("Fantasy") are too broad. Collaborative filtering finds what similar readers bought, not what shares the story structure they actually responded to.

CommonThread builds a genome for each book — a weighted vector of tropes and archetypes — and uses that genome to power similarity search, personalized recommendations, and a hybrid keyword + semantic search bar. Readers can also tag books themselves, and when enough readers agree, their tags are promoted to canonical and reshape the data for everyone.

---

## 2. Schema

The full column-by-column schema is in [schema.md](schema.md). Summary below.

### Core tables (4)

| Table | Purpose |
|---|---|
| `app_users` | Registered users. Links to Supabase Auth by UUID. Stores display name, admin flag, content blocklist (JSONB), and privacy setting. |
| `books` | Central table. Every book edition — metadata, pacing, three embedding columns, soft-delete, tsvector for full-text search. |
| `authors` | Simple lookup; created automatically on book import. |
| `series` | Groups books into a series; books reference series via nullable FK. |

### Taxonomy tables (5)

`tropes`, `archetypes`, `genres`, `book_types`, `tones` — the controlled vocabulary used to annotate books. Tropes carry a `category` field (used for diversity re-ranking). All are admin-managed; tropes and archetypes additionally receive crowd-sourced tags from readers.

### Book association tables (5)

| Table | Extra columns |
|---|---|
| `book_tropes` | `weight` (0.0–1.0), `is_crowd_promoted` |
| `character_dna` | `importance` (1–10), `is_crowd_promoted` |
| `book_genres` | none |
| `book_book_types` | none |
| `book_tones` | none |

### User interaction tables (6)

`reading_statuses`, `book_ratings` (with `review_text`), `book_dislikes`, `user_book_tropes`, `user_book_archetypes`, `user_follows`

**Total: 20 tables.** The target range was 10–15. The extra tables come from the user-tagging system — `user_book_tropes` and `user_book_archetypes` are separate from the canonical association tables (`book_tropes`, `character_dna`) so that reader opinions never directly overwrite admin-curated data.

### Indexing strategy

| Index | Why |
|---|---|
| `ix_books_title`, `ix_books_author_id` | Book list queries always filter/sort by title or join to authors |
| `ix_authors_name` | Lexical search ORs in `author.name ILIKE ?`; without this the OR would force a seq scan |
| `ix_tropes_category` | Diversity re-ranking groups candidates by dominant trope category |
| `ix_book_tropes_trope_id`, `ix_character_dna_archetype_id` | Association lookups are always by the FK side (trope/archetype → books), not the PK side |
| `ix_book_ratings_book_id` | "All ratings for this book" runs on every BookDetail load |
| HNSW index on `genome_embedding`, `description_embedding` | pgvector ANN; used by For You, Similar Books, and the semantic leg of hybrid search |
| GENERATED `search_vector` TSVECTOR | Postgres maintains this automatically; `@@` operator uses the GIN index that backs it |

---

## 3. Architecture

```
Browser (React 19 + TypeScript + Vite)
        │  HTTPS
        ▼
  Vercel (static hosting)
        │  API calls  Authorization: Bearer <JWT>
        ▼
  Railway (FastAPI + Python 3.12)
        │
        ├── SQLAlchemy 2.0 async (asyncpg driver)
        │        │
        │        ▼
        │   Supabase Postgres
        │   ├── pgvector extension (genome 384d, description 768d, review 768d)
        │   └── GENERATED tsvector column (hybrid search)
        │
        ├── FastEmbed (BAAI/bge-small + bge-base, runs in-process)
        │   loaded at startup via run_in_executor; pre-warmed before first request
        │
        └── Supabase Auth
            JWT issued to browser → validated in FastAPI on every request
            New users auto-upserted into app_users on first API call
```

### External services

- **Supabase Auth** — email/password login, JWT issuance. FastAPI validates the JWT against the Supabase secret; `get_current_user()` upserts the `app_users` row on every authenticated request so new users get their DB profile automatically.
- **Open Library API** — used by the background cover-fetch service to probe for cover images by ISBN, and by the webscraper to populate the initial book catalog (`/search.json` for paginated subject search, `/works/{id}.json` for descriptions).

### Data pipeline

1. **Scrape** — `backend/webscraper/` async HTTP scraper hits Open Library and writes JSONL. ~14,000 books scraped across 20 subjects; 9,220 remain in JSONL files not yet tagged.
2. **Tag** — Books are sent in batches to an LLM with the taxonomy reference. Trope/archetype/genre/tone tags are written back as JSON and reviewed.
3. **Import** — `scripts/import_tagged_books.py` loads tagged JSON into Postgres idempotently; deduplicates by title+author. 1,240 duplicate editions were soft-deleted during cleanup, leaving ~5,772 active books.
4. **Embed** — Admin "Embed All" queues all pending books. The FastAPI background task encodes each book's description (all books) and genome (books with ≥ 3 tropes) and writes the vectors back to `books`. 648 books are fully tagged with tropes/archetypes and have genome embeddings.
5. **Serve** — pgvector ANN queries run at request time for search and recommendations.

---

## 4. Key Queries

### Query 1 — Hybrid search (RRF)

Two legs run sequentially against the same async session:

**Lexical leg** — full-text search on the generated `search_vector` column, with an author name `ILIKE` OR (author names are not in the tsvector):

```python
tsq = func.plainto_tsquery("english", query)
stmt = (
    select(Book.book_id, func.ts_rank_cd(Book.search_vector, tsq).label("lex_score"))
    .join(Author, Book.author_id == Author.author_id)
    .where(Book.deleted_at.is_(None))
    .where(Book.search_vector.op("@@")(tsq) | Author.name.ilike(f"%{query}%"))
    .order_by(text("lex_score DESC"))
    .limit(top_n)
)
```

`ts_rank_cd` weights title matches (weight A) higher than description matches (weight C) because the tsvector column uses `setweight`.

**Semantic leg** — BGE-base cosine distance against `description_embedding`:

```python
query_vec = await _run(query, _get_description_model)
stmt = (
    select(Book.book_id, Book.description_embedding.cosine_distance(query_vec).label("distance"))
    .where(Book.deleted_at.is_(None))
    .where(Book.description_embedding.is_not(None))
    .order_by(text("distance"))
    .limit(top_n)
)
```

**Merge** — Reciprocal Rank Fusion over the union of both result sets:

```python
RRF_K = 60
score = alpha * (1 / (RRF_K + lex_rank)) + (1 - alpha) * (1 / (RRF_K + sem_rank))
```

`k=60` softens rank-1 dominance. Books in both legs get an agreement bonus. Results below `min_score = 0.003` are dropped. The alpha slider in the UI shifts the blend; default is 0.5 (equal weight).

**Why sequential, not parallel?** A single `AsyncSession` cannot run two concurrent operations — SQLAlchemy raises `InvalidRequestError`. Separate sessions would work but add connection overhead for a latency difference that is negligible given indexed queries.

---

### Query 2 — For You preference vector

The recommendation engine builds a taste centroid by mean-pooling the genome embeddings of books the user rated ≥ 4 stars, then blending in a taste vector derived from the user's own tags:

```python
# Mean-pool genome embeddings of high-rated books
preference = np.mean(genome_embeddings, axis=0)   # shape: (384,)

# Blend personal tag vector at 30%
taste_tropes, taste_archetypes = await get_aggregated_taste(db, user_id)
if taste_tropes or taste_archetypes:
    taste_vec = await embed_user_taste(taste_tropes, taste_archetypes)
    preference = 0.7 * preference + 0.3 * np.array(taste_vec)
```

The blended vector is then used as the query vector for a pgvector ANN search over `genome_embedding`, over-fetching by 5× to leave room for dislike filtering and diversity re-ranking downstream.

The dislike penalty computes max cosine similarity between each candidate and every disliked book's genome embedding via matrix multiply, and drops candidates with similarity ≥ 0.82 — suppressing not just the disliked book itself but its entire structural neighbourhood.

---

### Query 3 — Crowd promotion atomic upsert

When a trope crosses the threshold, an `INSERT ... ON CONFLICT DO UPDATE WHERE is_crowd_promoted = TRUE` ensures that concurrent promotions never race to overwrite an admin-set row:

```python
stmt = (
    pg_insert(BookTrope)
    .values(book_id=book_id, trope_id=trope_id, weight=med_weight, is_crowd_promoted=True)
    .on_conflict_do_update(
        index_elements=["book_id", "trope_id"],
        set_={"weight": med_weight},
        where=BookTrope.__table__.c.is_crowd_promoted.is_(True),
    )
)
```

The `WHERE` clause on the conflict target means: only update the row if it is already crowd-promoted. If the row is admin-set (`is_crowd_promoted = FALSE`), the conflict clause silently does nothing — the admin value is preserved without an explicit check in application code.

---

## 5. Complexity Component

### Three-stream embedding

CommonThread encodes each book three independent ways:

| Stream | Model | Dim | Input |
|---|---|---|---|
| Genome | `BAAI/bge-small-en-v1.5` | 384 | Structured literary metadata — trope names with weights, archetype names with importance, genres, tones, pacing, title, author. No description. |
| Description | `BAAI/bge-base-en-v1.5` | 768 | Raw free-text description only. Captures prose vibe. |
| Review | `BAAI/bge-base-en-v1.5` | 768 | Aggregated review text from users. Re-embedded when review count grows by ≥ 5. |

The genome intentionally excludes the description. This means the genome vector encodes *what kind of story* this is, while the description vector encodes *how the author writes*. They operate in entirely different semantic spaces and are never mixed — each is queried independently with its own ANN index.

The genome text format is a structured string that tells the embedding model which features to weight:

```
"The Name of the Wind" by Patrick Rothfuss.
Tropes: 'Chosen One Reframed' (0.85, dominant trope); 'Mentor/Protégé' (0.65, major trope).
Character archetypes: 'The Prodigy' (9/10 importance); 'The Mentor' (7/10 importance).
Genres: Fantasy.
Tone: Epic, Lyrical.
Pacing: 2/5.
```

The recommendation scoring blends all three streams. For Similar Books, the embedding score itself is first computed as a trope-count-weighted blend of genome and description cosines:

```
genome_weight   = min(trope_count / 8, 1.0)
embedding_score = genome_weight × genome_cosine + (1 − genome_weight) × description_cosine
```

This means a 3-trope book leans 63% on description similarity and 37% on genome, while a fully-tagged book relies entirely on genome. The embedding score and sparse dot product are then combined:

```
base_score  = 0.5 × embedding_score + 0.5 × sparse_dot_product
final_score = 0.80 × base_score + 0.20 × review_cosine   (when review_embedding exists)
```

The sparse dot product is computed from the raw weight/importance values stored in `book_tropes` and `character_dna` — an exact (non-approximate) similarity that rewards books sharing the same specific tropes at similar intensities, not just books that happen to be nearby in vector space.

### Crowd promotion system

The promotion system converts individual reader opinions into canonical book metadata. When ≥ 3 users tag the same `(book, trope)` pair, the system:

1. Computes the median weight across all taggers
2. Checks that median ≥ 0.4 (minimum signal strength)
3. Checks the dominant anchor rule: if no canonical trope has weight ≥ 0.65 yet, the promoted trope must itself be dominant — preventing a book from entering the genome with only weak-signal tropes
4. Atomically upserts into `book_tropes` with `WHERE is_crowd_promoted = TRUE` to protect admin rows
5. Triggers a genome re-embed so the new trope immediately affects recommendations

The ratchet: once a trope is promoted, it is never automatically removed. The weight recalculates on every user tag add/remove, but the canonical row persists even if all user tags are eventually removed. Only an admin can delete it.

---

## 6. The Journey

### What was harder than expected

**Async SQLAlchemy** — SQLAlchemy 2.0 async is strict in ways the documentation undersells. Every relationship accessed in a route handler must be declared in the query with `selectinload()` or `joinedload()`. Implicit lazy loading raises `MissingGreenlet` at runtime, not at compile time, so these bugs only surface under specific access patterns. The pattern `selectinload(Book.book_tropes).selectinload(BookTrope.trope)` became a constant refrain.

**AsyncSession concurrency** — the natural instinct was to run the two hybrid search legs in parallel with `asyncio.gather`. This immediately raised `InvalidRequestError: concurrent operations are not permitted`. A single SQLAlchemy async session is not safe to use across concurrent coroutines — the legs had to run sequentially.

**The trope threshold** — the embedding contract evolved mid-project. Originally `embedding_status = "done"` meant both genome and description were embedded. When ~7,000 imported books sat at `pending` forever because they had no tropes, it became clear that description embedding must be independent of the trope gate. Splitting the contract (`done` = description embedded, genome additionally gated on ≥ 3 tropes) required updating the embedding service, the admin embed-all query, the BookDetail badge logic, and six test assertions.

**Goodreads pagination** — the original scraper used Playwright against Goodreads shelf pages with `?page=N`. Pages 2 through N all returned the same 50 books as page 1 — Goodreads had migrated to a React SPA where the page parameter is handled client-side and ignored server-side. Switching to the Open Library REST API (which paginates correctly) was the right call and reduced scrape time from hours to minutes.

**AuthContext race condition** — admin users landing directly on `/admin` were briefly redirected to `/unauthorized`. The auth context set `loading = false` after `getSession()` resolved, before the `api.users.me()` profile fetch (which carries the `is_admin` flag) completed. `ProtectedRoute` saw `isAdmin = false` in that window and fired the redirect. The fix: hold `loading = true` until both the session and the profile are known.

### What was easier than expected

**pgvector** — the extension integrates cleanly with SQLAlchemy via the `pgvector.sqlalchemy` package. Declaring `Vector(384)` as a column type and calling `.cosine_distance()` as an ORM expression felt natural. The HNSW index setup was straightforward.

**Supabase Auth** — JWT validation in FastAPI is a `python-jose` one-liner once you have the secret. The upsert pattern for auto-creating `app_users` rows made onboarding invisible.

**React Router v7 data router** — migrating from `<BrowserRouter>` to `createBrowserRouter` was a one-time cost (and required because `useBlocker` only works with data routers), but the structure it enforces — a `RootLayout` wrapping all routes — turned out to be cleaner than the old approach.

### AI-assisted development

The entire codebase was built with AI assistance. This changed the work in a few specific ways:

- **Boilerplate disappeared.** Pydantic schemas, SQLAlchemy model declarations, FastAPI route handlers — things that are structurally repetitive but still require getting right — took seconds rather than minutes.
- **The bottleneck shifted to system design.** The hard decisions — how to split the embedding contract, how to structure crowd promotion atomicity, when to use JSONB vs normalized tables — were still genuinely difficult and required understanding the tradeoffs. AI didn't resolve those; it executed them once decided.
- **Error log became essential.** Because the AI doesn't carry context between sessions, writing down the root cause and fix for each non-obvious bug (the error log in `docs/error_log.md`) meant the same mistake didn't repeat across sessions. The log grew to 30 entries.
- **Verification matters more.** Generated code works most of the time and fails in subtle ways the rest of the time. Running `npm run build` (not just `vite dev`) and reading actual query plans rather than trusting that a query "looks right" caught several silent bugs.

---

## 7. Scaling

Current state: ~5,772 books in DB (648 fully tagged with genome embeddings), single Railway instance, single Supabase Postgres.

### Bottleneck 1 — Embedding inference (in-process)

FastEmbed runs in the same process as FastAPI. At scale, embedding a query (semantic search leg) blocks an event loop thread via `run_in_executor`. Under load, this saturates the thread pool.

**Fix:** Move embedding to a dedicated service (Triton Inference Server or a small FastAPI sidecar with GPU). The main API becomes a thin orchestrator that calls the embedding service and runs Postgres queries — no ML in the request path.

### Bottleneck 2 — pgvector ANN at scale

HNSW ANN search is fast for thousands of books but degrades as the table grows. At 1M books, a single Postgres instance may not keep the index in memory.

**Fix:** Dedicated vector database (Qdrant, Weaviate, or Pinecone). Store book IDs and vectors there; keep metadata in Postgres. The ANN query returns IDs; a follow-up Postgres query fetches the full book rows. This separates the vector workload from the relational workload.

### Bottleneck 3 — Background embedding (in-process FastAPI background tasks)

Embedding runs as a `BackgroundTask` in the FastAPI event loop. At scale, a flood of book creates or tag changes would queue up and starve the event loop.

**Fix:** Move to a proper task queue — Celery + Redis or Temporal. Embedding jobs become durable, retryable, and rate-limited. The API acknowledges the request immediately and the job completes asynchronously.

### Bottleneck 4 — Crowd promotion on every tag write

Currently, every user tag add/remove triggers a promotion check synchronously inside the API handler. At scale, with many concurrent taggers on a popular book, this creates contention on the `book_tropes` row.

**Fix:** Debounce promotion checks via the task queue. Write the user tag immediately, enqueue a promotion-check job with a short delay. Multiple near-simultaneous tags collapse into a single promotion evaluation.

### Bottleneck 5 — Single Postgres write path

All writes go to one Supabase Postgres instance. User interactions (ratings, shelf updates, dislikes, tags) at 1M users would saturate a single writer.

**Fix:** Read replicas for all recommendation and search queries (already read-heavy). Partition user interaction tables by `user_id` hash to distribute write load. For the activity feed, consider a dedicated time-series store (TimescaleDB) since the feed is append-only and queried by recency.

### Summary

| Scale | Architecture |
|---|---|
| Now (~5K books, ~100 users) | Single FastAPI + Supabase Postgres + in-process embeddings |
| 10K users | Read replicas, background task queue (Celery), embedding service separated |
| 100K users | Dedicated vector DB, Postgres connection pooling (PgBouncer), CDN for cover images |
| 1M users | Horizontally scaled API pods, sharded user interaction tables, vector DB cluster, streaming feed (Kafka), separate recommendation precompute job |
