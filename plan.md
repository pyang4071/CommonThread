# CommonThread — Recommendation Engine Plan

This document describes the planned improvements to the recommendation system, addressing the core problem that narrative DNA data (tropes/archetypes) is hard to obtain at scale.

---

## Current Phase

**Active: Step 1 — DB Migration**

| Step | Status |
|---|---|
| 1 — DB migration (`review_embedding`, `is_crowd_promoted`) | ✅ done |
| 2 — `embed_description_only` + `embed_reviews_for_book` | ✅ done |
| 3 — Trigger description embed at book creation | ✅ done |
| 4a — `import_books.py` Open Library import | ✅ done |
| 5 — Description fallback in recommendations | ✅ done |
| 4b — Goodreads enricher | ✅ done |
| 6 — Crowdsourcing promotion / demotion | ✅ done |
| 7 — Frontend source labels | ✅ done |

---

## The Problem

The genome embedding — the system's core differentiator — requires admin-tagged tropes. Without them:
- Books stay at `embedding_status = pending` forever
- For You returns `[]` if the user's liked books have no genome embeddings
- Similar Books falls back to near-random ordering
- Imported Open Library books never enter the recommendation pool

---

## The Three-Stream Model

Each book has up to three independent embedding streams. Each fires on its own trigger — no stream blocks another.

```
Stream 1 — Genome (384-dim, BAAI/bge-small-en-v1.5)
  Trigger : ≥ 3 canonical tropes attached to the book
  Source  : admin tagging OR crowdsourced from user tags (see below)
  Quality : highest — structured literary signal (tropes, archetypes, genres, tones)

Stream 2 — Description (768-dim, BAAI/bge-base-en-v1.5)
  Trigger : book creation, if description exists
  Source  : Open Library description field (covers ~90% of imported books)
  Quality : moderate — prose/vibe signal

Stream 3 — Review Aggregate (768-dim, BAAI/bge-base-en-v1.5)
  Trigger : any rating with review_text is posted or updated
  Source  : all review texts for a book concatenated with " | "
  Quality : grows over time — user-generated narrative signal
```

Streams 2 and 3 share the same model (BGE-base) and dimension, so no second model download is needed.

At recommendation time the streams are searched **independently** — not blended into a single vector. The genome path is used when available; the description path is the fallback. Blending vectors of different dimensions would require a learned projection that does not exist here.

---

## The Crowdsourcing Loop

The key insight: user tags in `user_book_tropes` currently only affect that user's personal taste vector. They never touch `book_tropes` (the canonical table that drives genome embeddings). This plan adds a promotion mechanism to close that gap.

```
User reads book
  → tags a personal trope (user_book_tropes)
    → promotion check runs after every upsert:
        IF ≥ 3 distinct users tagged the same (book_id, trope_id)
        AND avg weight across those tags ≥ 0.4
        AND no admin-set tag already exists for this (book_id, trope_id)
          → write to book_tropes with crowd-sourced avg weight
          → if canonical trope count now ≥ 3: trigger genome embed
```

On tag removal: if a crowd-promoted trope loses enough support (distinct users drops below threshold), remove it from `book_tropes` (only crowd-promoted rows; admin rows are never auto-removed).

This means the genome pool grows organically as users engage — without any admin work.

---

## What Needs to Be Built

### Step 1 — DB Migration

Add one column:

```sql
ALTER TABLE books ADD COLUMN review_embedding vector(768);
```

Also add a `is_crowd_promoted` boolean (default false) to `book_tropes` so the system can distinguish admin-set tags from crowd-promoted ones (admin tags are never auto-removed on demotion).

```sql
ALTER TABLE book_tropes ADD COLUMN is_crowd_promoted BOOLEAN NOT NULL DEFAULT FALSE;
```

---

### Step 2 — `services/embedding.py`

**`embed_description_only(book_id, db)`**
Embeds only the description stream for a book and writes to `books.description_embedding`. No trope gate. No-op if the book has no description. Does not touch `genome_embedding` or `embedding_status`.

**`embed_reviews_for_book(book_id, db)`**
Fetches all `book_ratings.review_text` where `review_text IS NOT NULL` for the given book. Concatenates them separated by `" | "`. Embeds with the description model (already loaded). Writes to `books.review_embedding`. No-op if no reviews with text exist.

---

### Step 3 — `routers/books.py`

**On `POST /books` (book creation):**
Add a new background task `_embed_description_in_background(book_id)` that calls `embed_description_only`. Fires immediately on creation, regardless of trope count. The existing `_embed_in_background` (genome) is unchanged.

**On `PUT /books/{id}/rating` (review upsert):**
Add a new background task `_embed_reviews_in_background(book_id)` that calls `embed_reviews_for_book`. Re-aggregates and re-embeds all reviews for that book every time one is added or updated.

---

### Step 4 — Data Ingestion

Two scrapers, two roles. Run Open Library first to build the catalog, then run the Goodreads enricher to add trope signal and reviews on top.

#### 4a — `scripts/import_books.py` (new script) — Open Library primary catalog

Reads `backend/webscraper/output/books_*.jsonl` and imports books into the DB.

For each scraped book:
1. `get_or_create_author` by name
2. `create_book` — title, isbn, description, publication_date
3. Map `subjects[]` → existing `genres` rows via a static lookup dict (~50 entries, e.g. `"fantasy" → "Fantasy"`, `"detective and mystery stories" → "Mystery"`)
4. `attach_genre` for each matched genre
5. Trigger description embed immediately (no trope gate)
6. Skip duplicates by ISBN (isbn is unique in the schema)

This populates the catalog so that recommendations have something to search against from day one, without requiring any admin tagging.

#### 4b — Goodreads enrichment scraper (new) — shelf + review bootstrap

Open Library gives descriptions and genres. Goodreads gives trope signal and reviews. Rather than scraping Goodreads by genre browse (which is broken — pagination returns the same 50 books every time, see `error_log.md`), the enricher targets books **already imported from Open Library** by ISBN lookup. This sidesteps the pagination problem entirely.

**What Goodreads has that Open Library doesn't:**

| Signal | Open Library | Goodreads |
|---|---|---|
| Descriptions | Good coverage | Good coverage |
| Genres | Weak (raw subject strings) | Strong (user-curated) |
| Trope signal | None | Strong — user shelf names |
| Reviews at import | None | Strong |
| Legal risk | None | Real for production; acceptable for demo |

**Goodreads shelf names as proto-tropes:**
Goodreads users create custom shelves and tag books with them. The most common ones map almost directly to the tropes list:
```
enemies-to-lovers, slow-burn, found-family, chosen-one,
forced-proximity, magic-school, unreliable-narrator,
redemption-arc, dark-academia, fake-dating, ...
```

**Enricher logic** (`webscraper/goodreads_enricher.py`):
1. For each imported book with a known ISBN, search Goodreads (`/search?q={isbn}`) to get the book page URL
2. Scrape the book page for:
   - User shelf names and shelf counts
   - Review texts (top N by helpfulness)
   - Genre tags (user-voted)
3. Map shelf names → tropes via a lookup dict; for each match where shelf count proportion is high enough (e.g. top-3 shelves, or shelf count > 500):
   - Write directly to `book_tropes` with `is_crowd_promoted = True` and weight derived from shelf proportion
4. Write review texts to `book_ratings` (or a separate `scraped_reviews` staging table) to seed `review_embedding` at import time
5. Respect rate limits: 1500 ms delay with jitter; retry on 429/timeout (see existing `error_log.md` patterns)

**Shelf count → weight mapping:**
```
shelf_proportion = shelf_count / total_shelved_count
weight = min(1.0, shelf_proportion * 5)  # scale up; cap at 1.0
```

**Result:** books with strong Goodreads shelf consensus (e.g. "The Hunger Games" with 50k+ "chosen-one" shelves) get genome embeddings at import time. Books with weak or no shelf data fall back to the description stream and wait for CommonThread users to tag them via the crowdsourcing mechanism.

**Note on ToS:** Goodreads prohibits scraping in their Terms of Service. This enricher is acceptable for ECE 464 demonstration purposes but should not be used in a production deployment that serves external users.

---

### Step 5 — `crud/book.py` — recommendation fallback paths

**`get_recommendations_for_user`** (the critical change):

Currently returns `[]` if none of the user's liked books have genome embeddings. New logic:

```
Try genome path:
  collect genome_embeddings from liked books
  if ≥ 1 exists:
    build preference vector, search genome space
    set source = "genome"

Else fall back to description path:
  collect description_embeddings from liked books
  if ≥ 1 exists:
    build preference vector, search description space
    optionally blend review_embedding similarity at 20% weight
    set source = "description"

If neither: return []
```

**`get_similar_books`** (the critical change):

Currently falls back to all books with `emb_scores = 0.0` when the source book has no genome embedding. New logic:

```
if source book has genome_embedding:
  cosine search genome space (existing behavior)
elif source book has description_embedding:
  cosine search description space
  optionally blend review_embedding cosine at 20% when available
else:
  return []
```

---

### Step 6 — `crud/user_tags.py` — crowdsourcing promotion

**New function: `promote_user_tags_to_canonical(db, book_id, trope_id) -> bool`**

```
1. Count distinct users who have tagged (book_id, trope_id) in user_book_tropes
2. Compute avg weight across those tags
3. If count < 3 OR avg_weight < 0.4: return False
4. If a book_tropes row for (book_id, trope_id) already exists
   AND is_crowd_promoted = False: return False  ← admin tag takes precedence
5. Upsert book_tropes(book_id, trope_id, weight=avg_weight, is_crowd_promoted=True)
6. Return True
```

**Demotion: `demote_user_tag_if_needed(db, book_id, trope_id)`**

Called from `remove_user_trope` after a tag is deleted:
```
1. Count remaining distinct users for (book_id, trope_id)
2. If count < 3:
   if book_tropes row exists AND is_crowd_promoted = True:
     delete book_tropes row
     if canonical trope count now < TROPE_THRESHOLD:
       clear genome_embedding, reset embedding_status = 'pending'
```

**`upsert_user_trope` calls promotion after every write:**
```python
promoted = await promote_user_tags_to_canonical(db, book_id, data.trope_id)
if promoted:
    count = await _trope_count(db, book_id)
    if count >= TROPE_THRESHOLD:
        # trigger genome embed (same pattern as attach_trope in books.py)
```

Same pattern applies to `upsert_user_archetype` / `remove_user_archetype` for archetypes.

---

### Step 7 — Frontend

`RecommendationExplanation.source` already exists and flows to the UI. Update the display label in `Home.tsx` (For You cards) and `BookDetail.tsx` (Similar Books cards):

| source | label |
|---|---|
| `"genome"` | *(no label — status quo)* |
| `"description"` | `"Matched by description"` (muted gray) |
| `"collaborative"` | `"Readers like you"` *(already present)* |
| `"review"` | `"Matched by reader reviews"` |

---

## Build Order

Steps are ordered by dependency and impact. Steps 1–5 are the critical path — they make recommendations work for the imported catalog immediately. Steps 6–7 are quality improvements that layer on top.

| Step | What | Why first |
|---|---|---|
| 1 | DB migration | Everything else depends on the schema |
| 2 | `embed_description_only` + `embed_reviews_for_book` | Services before routers |
| 3 | Trigger description embed at book creation | Unblocks new imports |
| 4a | `import_books.py` — Open Library catalog import | Gets books + descriptions into the DB |
| 5 | Description fallback in `get_recommendations_for_user` + `get_similar_books` | Makes recommendations work immediately after 4a |
| 4b | Goodreads enricher — shelf + review bootstrap | Layered on top of existing catalog; seeds genome and review streams |
| 6 | `promote_user_tags_to_canonical` + demotion | Crowdsourced genome growth for books not covered by 4b |
| 7 | Frontend source labels | Polish |

---

## Files Affected

| File | Change |
|---|---|
| New Alembic migration | `review_embedding vector(768)` on `books`; `is_crowd_promoted boolean` on `book_tropes` |
| `backend/app/services/embedding.py` | Add `embed_description_only()`, `embed_reviews_for_book()` |
| `backend/app/routers/books.py` | Trigger description embed on `POST /books`; trigger review embed on `PUT /books/{id}/rating` |
| `backend/app/crud/book.py` | Description fallback in `get_recommendations_for_user` and `get_similar_books` |
| `backend/app/crud/user_tags.py` | Add `promote_user_tags_to_canonical()` and `demote_user_tag_if_needed()` |
| `backend/scripts/import_books.py` | New — Open Library JSONL → DB import with subject-to-genre mapping |
| `backend/webscraper/goodreads_enricher.py` | New — ISBN-targeted Goodreads scraper for shelf names + reviews |
| `frontend/src/pages/Home.tsx` | Source label on For You recommendation cards |
| `frontend/src/pages/BookDetail.tsx` | Source label on Similar Books cards |

---

## Open Questions

- **Promotion threshold calibration:** min 3 users and avg weight ≥ 0.4 are starting values. These should be revisited once real user data exists.
- **Review embed trigger frequency:** re-embedding on every review upsert is simple but potentially wasteful for popular books. Could batch instead (e.g. only re-embed when review count increases by 5+).
- **Description embed on `embed_all`:** the admin Embed All endpoint currently skips books below `TROPE_THRESHOLD`. It should be updated to also embed descriptions for all books that have a description but no `description_embedding` yet.
