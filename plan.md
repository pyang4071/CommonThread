# CommonThread — Master Plan

This document is the single source of truth for all planned and completed work on CommonThread's recommendation and search systems.

---

## Status Overview

### Phase 1 — Recommendation Engine ✅ Complete

| Step | What | Status |
|---|---|---|
| 1 | DB migration (`review_embedding`, `is_crowd_promoted`) | ✅ done |
| 2 | `embed_description_only` + `embed_reviews_for_book` | ✅ done |
| 3 | Trigger description embed at book creation | ✅ done |
| 4a | `import_books.py` — Open Library catalog import | ✅ done |
| 5 | Description fallback in recommendations | ✅ done |
| 4b | Goodreads enricher — shelf + review bootstrap | ✅ done |
| 6 | Crowdsourcing promotion / demotion | ✅ done |
| 7 | Frontend source labels | ✅ done |

### Phase 2 — Hybrid Search ⬜ Pending

| Step | What | Status |
|---|---|---|
| H1 | DB migration — `search_vector` tsvector column + GIN index | ⬜ pending |
| H2 | `crud/search.py` — `hybrid_search()` with RRF | ⬜ pending |
| H3 | `POST /search/hybrid` endpoint | ⬜ pending |
| H4 | Frontend — unified search bar replaces keyword + vibe panels | ⬜ pending |

---

---

# Phase 1 — Recommendation Engine

## The Problem

The genome embedding — the system's core differentiator — requires admin-tagged tropes. Without them:
- Books stay at `embedding_status = pending` forever
- For You returns `[]` if the user's liked books have no genome embeddings
- Similar Books falls back to near-random ordering
- Imported Open Library books never enter the recommendation pool

## The Three-Stream Embedding Model

Each book has up to three independent embedding streams. Each fires on its own trigger — no stream blocks another.

```
Stream 1 — Genome (384-dim, BAAI/bge-small-en-v1.5)
  Trigger : ≥ 3 canonical tropes attached to the book
  Source  : admin tagging OR crowdsourced from user tags
  Quality : highest — structured literary signal (tropes, archetypes, genres, tones)

Stream 2 — Description (768-dim, BAAI/bge-base-en-v1.5)
  Trigger : book creation, if description exists
  Source  : Open Library description field (~90% of imported books have one)
  Quality : moderate — prose/vibe signal

Stream 3 — Review Aggregate (768-dim, BAAI/bge-base-en-v1.5)
  Trigger : any rating with review_text is posted or updated
  Source  : all review texts for a book, concatenated with " | "
  Quality : grows over time — user-generated narrative signal
```

Streams 2 and 3 share the same model and dimension (BGE-base, 768-dim), so no second model download is needed.

At recommendation time the streams are searched **independently** — not blended. The genome path is used when available; the description path is the fallback. Blending vectors of different dimensions would require a learned projection that does not exist.

## The Crowdsourcing Loop

User tags in `user_book_tropes` affect only that user's personal taste vector. The promotion mechanism closes the gap to canonical `book_tropes` (which drives genome embeddings):

```
User reads book
  → tags a personal trope (user_book_tropes)
    → promotion check runs after every upsert:
        IF ≥ 3 distinct users tagged the same (book_id, trope_id)
        AND avg weight across those tags ≥ 0.4
        AND no admin-set tag already exists for this (book_id, trope_id)
          → write to book_tropes with is_crowd_promoted=True and avg weight
          → if canonical trope count now ≥ 3: trigger genome embed
```

On tag removal: if support drops below threshold, the crowd-promoted row is deleted from `book_tropes`. If canonical trope count then falls below `TROPE_THRESHOLD`, `genome_embedding` is cleared and `embedding_status` reset to `pending`. Admin-set tags (`is_crowd_promoted=False`) are never auto-removed.

## Data Ingestion

### Open Library (`scripts/import_books.py`)
Reads scraped JSONL files from `webscraper/output/books_*.jsonl`. For each book: deduplicates by ISBN, creates author + book + genres (via 50-entry subject→genre lookup dict), triggers description embed. Result: **6,048 books** imported across 20 genres.

### Goodreads Enricher (`webscraper/goodreads_enricher.py`)
ISBN-targeted lookup (avoids the broken genre-browse pagination). For each imported book: searches Goodreads by ISBN, scrapes shelf names + review texts, maps shelf names to canonical tropes via a 100+ entry lookup dict, writes to `book_tropes` with `is_crowd_promoted=True`, writes review embedding. Shelf count → weight: `min(1.0, shelf_proportion * 5)`.

**Note on ToS:** Goodreads scraping is acceptable for ECE 464 demo purposes only — not for production deployments.

## Recommendation Fallback Logic

### `get_recommendations_for_user`
```
Try genome path:
  collect genome_embeddings from liked books
  if ≥ 1 exists → build preference vector, search genome space, source="genome"

Else try description path:
  collect description_embeddings from liked books
  if ≥ 1 exists → build preference vector, search description space, source="description"

Else: return []
```

### `get_similar_books`
```
if source book has genome_embedding  → cosine search genome space
elif source book has description_embedding → cosine search description space
else → return []
```

## Open Questions (Phase 1)

- **Promotion threshold calibration:** min 3 users, avg weight ≥ 0.4 are starting values. Revisit with real user data.
- **Review embed trigger frequency:** currently re-embeds on every review upsert. Could batch (e.g. only when review count increases by 5+).
- **`embed_all` admin endpoint:** currently skips books below `TROPE_THRESHOLD`. Should also embed descriptions for books with a description but no `description_embedding` yet (backfill script `scripts/embed_descriptions.py` exists as a one-shot workaround).

---

---

# Phase 2 — Hybrid Search

## The Problem with the Current Setup

Two separate search bars exist today:
- **Keyword search** (`GET /books?search=`) — ILIKE on title/author. Fast, precise on names. Returns nothing for vibe queries.
- **Vibe search** (`GET /search/`) — cosine similarity on genome/description embeddings. Good for themes/moods. Returns garbage for exact title lookups.

Users shouldn't have to know which one to use. A single search bar should handle both.

## Approach: Reciprocal Rank Fusion (RRF)

Each query triggers both a lexical leg and a semantic leg in parallel. Their ranked result lists are combined using RRF, a standard technique for hybrid search that rewards "agreement between signals."

### Why RRF works

```
rrf(rank, k=60) = 1 / (k + rank)
```

For each document in the union of both result sets:
```
combined_score = α × rrf(lex_rank) + (1−α) × rrf(sem_rank)
```

- If a document only appears in the lexical results: `sem_rank` contributes 0
- If a document only appears in the semantic results: `lex_rank` contributes 0
- If it appears in both: scores add — the "agreement bonus"

With `k=60`, `top_n=20`, `α=0.5`:

| Scenario | Score |
|---|---|
| Rank 1 in both | ≈ 0.0164 |
| Rank 1 lexical only | ≈ 0.0082 |
| Rank 1 semantic only | ≈ 0.0082 |
| Rank 10 in both | ≈ 0.0071 × 2 = 0.0143 |
| Rank 10 lexical only | ≈ 0.0071 |

### Does a semantic-only result show up?

**Yes**, as long as its combined score clears `MIN_SCORE`. With `MIN_SCORE = 0.003`:
- Rank 1 semantic-only at α=0.5: score ≈ 0.0082 → **passes**
- Rank 10 semantic-only at α=0.5: score ≈ 0.0036 → **passes**
- Rank 18 semantic-only at α=0.5: score ≈ 0.0026 → **filtered out**

The slider controls α. Sliding toward "semantic" (lower α) raises semantic-only scores relative to lexical-only scores, keeping more vibe results above threshold. Sliding toward "lexical" (higher α) rewards exact matches more and filters weaker semantic results.

## Step H1 — DB Migration: `search_vector` tsvector column

Add a `GENERATED ALWAYS` tsvector column to `books` so lexical ranking uses proper PostgreSQL full-text search (stemming, tf/idf-style ranking) rather than ILIKE.

```sql
ALTER TABLE books
  ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'C')
  ) STORED;

CREATE INDEX ix_books_search_vector ON books USING GIN (search_vector);
```

Weight breakdown:
- `A` (highest) — title
- `C` — description
- Author name is in a separate table; joined at query time and scored separately

The GIN index makes `@@` queries fast even at scale. For 6k books this is instant; for 100k+ books this is still sub-10ms.

**What changes:** one new Alembic migration (`n8o9p0q1r2s3_add_search_vector.py`).

## Step H2 — `crud/search.py`: `hybrid_search()`

New file. Core function signature:

```python
async def hybrid_search(
    db: AsyncSession,
    query: str,
    *,
    top_n: int = 20,          # candidates from each leg
    alpha: float = 0.5,       # weight on lexical; 1−alpha on semantic
    min_score: float = 0.003, # RRF combined score threshold
    final_n: int = 20,        # results returned after combining
    # shared filters (same as existing search)
    genre_ids: list[int] = [],
    book_type_ids: list[int] = [],
    tone_ids: list[int] = [],
    pacing: int | None = None,
    categories: list[str] = [],
    exclude_trope_ids: list[int] = [],
    exclude_archetype_ids: list[int] = [],
    exclude_genre_ids: list[int] = [],
    exclude_book_type_ids: list[int] = [],
    exclude_tone_ids: list[int] = [],
) -> list[HybridResult]:
```

### Lexical leg

```sql
SELECT book_id,
       ts_rank_cd(search_vector, query) AS lex_score
FROM books
JOIN app_authors ON books.author_id = app_authors.author_id
WHERE (
  search_vector @@ plainto_tsquery('english', :q)
  OR lower(app_authors.name) LIKE lower('%' || :q || '%')
)
-- + shared filter subqueries (same as existing)
ORDER BY lex_score DESC
LIMIT :top_n
```

The `OR author LIKE` clause ensures author name queries still work (author is not in `search_vector`).

### Semantic leg

Embed the query with `_get_description_model` (BGE-base, 768-dim). Cosine search on `description_embedding`.

**Important:** the existing `GET /search/` endpoint only searches `genome_embedding IS NOT NULL` — a small pool of admin-tagged books. The hybrid semantic leg deliberately searches `description_embedding IS NOT NULL` instead, which covers the full ~6k imported catalog. This is a meaningful improvement in coverage, not a bug.

```sql
SELECT book_id,
       description_embedding <=> :query_vec AS distance
FROM books
WHERE description_embedding IS NOT NULL
-- + shared filters
ORDER BY distance
LIMIT :top_n
```

### RRF combination

```python
K = 60

# Build rank maps from each leg
lex_ranks  = {row.book_id: i+1 for i, row in enumerate(lex_rows)}
sem_ranks  = {row.book_id: i+1 for i, row in enumerate(sem_rows)}

# Union
all_ids = set(lex_ranks) | set(sem_ranks)

scored = []
for book_id in all_ids:
    lex_rrf = 1.0 / (K + lex_ranks[book_id]) if book_id in lex_ranks else 0.0
    sem_rrf = 1.0 / (K + sem_ranks[book_id]) if book_id in sem_ranks else 0.0
    score   = alpha * lex_rrf + (1 - alpha) * sem_rrf

    if score < min_score:
        continue

    match_type = (
        "both"     if book_id in lex_ranks and book_id in sem_ranks else
        "lexical"  if book_id in lex_ranks else
        "semantic"
    )
    scored.append((book_id, score, match_type))

scored.sort(key=lambda x: x[1], reverse=True)
top = scored[:final_n]
```

After ranking: fetch full `Book` objects for the surviving `book_id`s in one query with `selectinload(Book.author)` (required — lazy loading raises `MissingGreenlet` in async context), attach `avg_rating`, return `list[HybridResult]`.

### `HybridResult` schema

```python
class HybridResult(BaseModel):
    book: BookRead
    score: float
    match_type: Literal["both", "lexical", "semantic"]
    lex_rank: int | None   # rank in lexical leg, None if not present
    sem_rank: int | None   # rank in semantic leg, None if not present
```

## Step H3 — `POST /search/hybrid` endpoint

New endpoint in `routers/search.py`:

```python
class HybridSearchRequest(BaseModel):
    q: str
    top_n: int = 20
    alpha: float = 0.5
    min_score: float = 0.003
    # filter fields (mirrors existing GET /books params)
    genre_ids: list[int] = []
    book_type_ids: list[int] = []
    tone_ids: list[int] = []
    pacing: int | None = None
    categories: list[str] = []
    exclude_trope_ids: list[int] = []
    exclude_archetype_ids: list[int] = []
    exclude_genre_ids: list[int] = []
    exclude_book_type_ids: list[int] = []
    exclude_tone_ids: list[int] = []

@router.post("/hybrid", response_model=list[HybridResult])
async def hybrid_search_endpoint(body: HybridSearchRequest, db: AsyncSession = Depends(get_db)):
    ...
```

**Note:** POST is used (not GET) because the request body carries filter arrays that would be unwieldy as query params, and because this endpoint triggers model inference (not idempotent in a caching sense).

The existing `GET /search/` semantic endpoint is kept for backward compatibility.

## Step H4 — Frontend: unified search bar

### What changes in `Books.tsx`

- Remove the "Vibe Search" panel (the `vibeOpen` state, the `semanticResults` state, the example prompts, the alpha slider inside the panel, the separate result grid)
- The main search input now triggers hybrid search on every keystroke (debounced 300ms)
- A compact alpha slider lives **beside the search bar** (always visible when the input has a value, hidden when empty)
- Results replace the regular book grid; no separate vibe result section
- When the query is empty, the page falls back to the regular `GET /books` browse (filters only, no search). Hybrid results are cleared **immediately** when the input is emptied — do not wait for the browse fetch to complete before removing them.

### Alpha slider placement

```
[  Search by title, author, or vibe…  ] [━━●━━━] [Filters ▼] [Clear]
                                         ↑
                          "Lexical ←→ Semantic"
                          small label, only shown when query is non-empty
```

Slider range: 0 (pure semantic) → 1 (pure lexical). Default: 0.5. Persisted in session state so it survives navigation.

### Result card changes

Each card shows a small `match_type` label:
- `"both"` → no label (strongest signal)
- `"semantic"` → muted chip "matched by vibe"
- `"lexical"` → no label (exact match needs no explanation)

Score is shown as a percentage only in vibe-heavy results (when `match_type === "semantic"` and score < 0.012) to give users a sense of confidence.

### API client addition

The hybrid endpoint does **not** require auth — blocked content IDs are sent explicitly in the request body by the frontend (sourced from `profile.preferences`). Use a plain `fetch`, not `authedFetch`.

```typescript
hybrid: (body: HybridSearchRequest) =>
  fetch(`${BASE}/search/hybrid`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(r => r.json() as Promise<HybridResult[]>)
```

## Files Affected (Phase 2)

| File | Change |
|---|---|
| New Alembic migration | `search_vector tsvector GENERATED ALWAYS` + GIN index on `books` |
| `backend/app/crud/search.py` | New — `hybrid_search()`, `HybridResult` |
| `backend/app/routers/search.py` | Add `POST /search/hybrid`; keep existing `GET /search/` |
| `frontend/src/api/client.ts` | Add `api.search.hybrid(...)`, `HybridResult` type |
| `frontend/src/pages/Books.tsx` | Remove vibe panel; wire search input to hybrid; add inline alpha slider |

## Constants (tunable)

| Constant | Value | Where |
|---|---|---|
| `RRF_K` | 60 | `crud/search.py` |
| `DEFAULT_TOP_N` | 20 | `crud/search.py` |
| `DEFAULT_MIN_SCORE` | 0.003 | `crud/search.py` |
| `DEFAULT_ALPHA` | 0.5 | frontend session state |
| Debounce delay | 300ms | `Books.tsx` |

## Build Order (Phase 2)

| Step | Dependency |
|---|---|
| H1 — migration | None — do first |
| H2 — `hybrid_search()` CRUD | H1 (needs `search_vector` column) |
| H3 — endpoint | H2 |
| H4 — frontend | H3 |

---

---

# Phase 3 — Crowd Promotion (Fixes + Archetype Extension)

## Context

The crowd promotion scaffolding was built in Phase 1 (Step 6) but has correctness bugs and is missing archetype support. This phase fixes the existing implementation and extends it symmetrically to archetypes.

## Design Decisions (locked)

| Decision | Choice |
|---|---|
| **A — Weight for promoted trope** | **Median** of all user-submitted weights (was: average) |
| **B — Dominant trope rule** | Promotion allowed at median ≥ 0.4 only if the book already has a dominant canonical trope (weight ≥ 0.65). If no dominant exists, the promoted trope must itself have median ≥ 0.65 to serve as anchor. |
| **C — Demotion on user removal** | **Ratchet** — once promoted, stays canonical forever. Weight recalculates (median) whenever user tags change. Admin-only removal via existing `DELETE /books/{id}/tropes/{trope_id}`. |
| **D — Promotion threshold N** | Read from env var `CROWD_PROMOTION_THRESHOLD`, default 3. |
| **E — Archetypes** | Same treatment. Median importance. No dominant-analogue check; require median importance ≥ 5. `is_crowd_promoted` column needs migration on `character_dna`. |

## Bugs in Current Implementation

| # | Bug | Fix |
|---|---|---|
| 1 | **Concurrency race** — two simultaneous upserts at count N-1 both pass the threshold check before either insert commits → IntegrityError on `book_tropes` PK | `INSERT … ON CONFLICT DO UPDATE` via `pg_insert().on_conflict_do_update()` |
| 2 | **`TROPE_THRESHOLD` duplicated** — defined in both `books.py` and `user_tags.py`, will silently diverge | Move to `config.py`; both files import from `settings` |
| 3 | **Weight never updates downward** — when a user removes their tag and count stays above threshold, the canonical weight is stale (still uses old avg) | After any tag removal, recalculate median from remaining user tags and update `book_tropes.weight` if changed; trigger re-embed if above threshold |
| 4 | **No re-embed on weight change after removal** — the weight update path in bug #3 doesn't exist yet, so genome is stale after a user removes a high-weight tag | Trigger re-embed whenever the canonical weight changes (same `_embed_in_background` call) |
| 5 | **Demotion code removed** — `demote_user_trope_if_needed` is replaced by the ratchet + weight-update pattern | Delete `demote_user_trope_if_needed`; replace call site in `remove_user_trope` with new `_update_crowd_weight` helper |
| 6 | **avg → median** | Replace `func.avg()` with Python-side `statistics.median()` on fetched weights |

## Promotion Logic (tropes) — Final Design

```
promote_or_update_trope(db, book_id, trope_id):

  existing_canonical = db.get(BookTrope, (book_id, trope_id))

  # Admin tag wins — never overwrite weight
  if existing_canonical and not existing_canonical.is_crowd_promoted:
    return False

  # Fetch all user weights for this (book, trope)
  user_weights = SELECT weight FROM user_book_tropes
                 WHERE book_id=X AND trope_id=Y

  if len(user_weights) < settings.CROWD_PROMOTION_THRESHOLD:
    # Below threshold — if a crowd-promoted row exists, update its weight only
    # (ratchet: don't delete it)
    if existing_canonical and existing_canonical.is_crowd_promoted:
      new_median = median(user_weights) if user_weights else existing_canonical.weight
      if new_median != existing_canonical.weight:
        existing_canonical.weight = new_median
        db.commit()
        trigger_re_embed_if_eligible(book_id)
    return False

  median_weight = median(user_weights)

  if median_weight < MIN_MEDIAN_WEIGHT:  # 0.4
    return False

  # Dominant anchor check (B)
  has_dominant = EXISTS(
    SELECT 1 FROM book_tropes
    WHERE book_id=X AND trope_id != Y AND weight >= 0.65
  )
  if not has_dominant and median_weight < DOMINANT_WEIGHT_THRESHOLD:  # 0.65
    return False

  # Upsert — ON CONFLICT handles race condition
  pg_insert(BookTrope).values(
    book_id=book_id, trope_id=trope_id,
    weight=round(median_weight, 4), is_crowd_promoted=True
  ).on_conflict_do_update(
    index_elements=["book_id", "trope_id"],
    set_={"weight": round(median_weight, 4)},
    where=BookTrope.is_crowd_promoted == True   # never clobber admin row
  )

  trigger_re_embed_if_eligible(book_id)
  return True
```

## Archetype Promotion Logic — Final Design

Mirrors trope logic with these differences:
- Tables: `character_dna` (canonical), `user_book_archetypes` (user tags)
- Field: `importance` (int 1–10) instead of `weight` (float)
- Threshold: median importance ≥ `MIN_MEDIAN_IMPORTANCE` (5)
- No dominant-anchor check
- `character_dna` needs `is_crowd_promoted` column (migration required)

## Files to Change

### 1. `backend/app/config.py`
- Add `CROWD_PROMOTION_THRESHOLD: int = 3`
- Add `TROPE_THRESHOLD: int = 3` (moved from `books.py` and `user_tags.py`)

### 2. `backend/app/models/character_dna.py`
- Add `is_crowd_promoted: Mapped[bool] = mapped_column(default=False, server_default="FALSE")`

### 3. New Alembic migration
- `ALTER TABLE character_dna ADD COLUMN is_crowd_promoted BOOLEAN NOT NULL DEFAULT FALSE`
- File: `p1q2r3s4t5u6_add_crowd_promoted_to_character_dna.py`

### 4. `backend/app/crud/user_tags.py`
- Remove local constants `MIN_USERS_FOR_PROMOTION`, `TROPE_THRESHOLD`; import from `settings`
- Keep `MIN_MEDIAN_WEIGHT_FOR_PROMOTION = 0.4`, `DOMINANT_WEIGHT_THRESHOLD = 0.65`, `MIN_MEDIAN_IMPORTANCE = 5` as module constants
- Replace `promote_user_trope_to_canonical` with updated version (median, dominant check, ON CONFLICT, ratchet weight-update when below threshold)
- Delete `demote_user_trope_if_needed`
- Add `_update_crowd_trope_weight(db, book_id, trope_id)` — called from `remove_user_trope` to recalculate median and re-embed if weight changed
- Add `promote_or_update_archetype(db, book_id, archetype_id)` — mirrors trope logic, median importance ≥ 5
- Add `_update_crowd_archetype_importance(db, book_id, archetype_id)` — mirrors trope weight-update helper
- Wire archetype promotion into `upsert_user_archetype`
- Wire archetype importance-update into `remove_user_archetype`

### 5. `backend/app/routers/books.py`
- Remove local `TROPE_THRESHOLD = 3`; import from `settings`

### 6. `backend/.env.example`
- Add `CROWD_PROMOTION_THRESHOLD=3`

### 7. Backend schema — expose `is_crowd_promoted`
- Verify `BookTropeRead` / archetype equivalent schemas include `is_crowd_promoted`
- Check `BookReadDetail` response includes the flag so frontend can render badge

### 8. `frontend/src/pages/BookDetail.tsx`
- Render a small "crowd-tagged" badge on trope and archetype list items where `is_crowd_promoted === true`

## Progress Checklist

- [ ] `config.py` — add `CROWD_PROMOTION_THRESHOLD`, move `TROPE_THRESHOLD`
- [ ] `character_dna.py` — add `is_crowd_promoted`
- [ ] Migration — `is_crowd_promoted` on `character_dna`
- [ ] `user_tags.py` — rewrite trope promotion (median, dominant check, ON CONFLICT, ratchet)
- [ ] `user_tags.py` — add `_update_crowd_trope_weight` helper; wire into `remove_user_trope`
- [ ] `user_tags.py` — add archetype promotion + weight-update helpers; wire in
- [ ] `books.py` — import `TROPE_THRESHOLD` from settings
- [ ] `.env.example` — add `CROWD_PROMOTION_THRESHOLD=3`
- [ ] Backend schemas — confirm `is_crowd_promoted` exposed in detail responses
- [ ] Frontend `BookDetail.tsx` — crowd-tagged badge
