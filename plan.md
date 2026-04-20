# CommonThread — Master Plan

---

## Completed Phases

| Phase | What | Status |
|---|---|---|
| Phase 1 — Recommendation Engine | Three-stream embedding (genome/description/review), Open Library import, crowd promotion scaffolding, description fallback in recommendations | ✅ Complete |
| Phase 2 — Hybrid Search | `search_vector` tsvector column, RRF hybrid search (`POST /search/hybrid`), unified search bar in `Books.tsx` | ✅ Complete |

---

# Phase 3 — Crowd Promotion (Fixes + Extensions)

## Context

The crowd promotion scaffolding was built in Phase 1 but has correctness bugs and is incomplete. This phase fixes the implementation, extends it to archetypes, and resolves two open questions from Phase 1 about embed-all coverage and review re-embed frequency.

---

## Design Decisions (locked)

| Decision | Choice |
|---|---|
| **A — Weight for promoted trope** | **Median** of all user-submitted weights (was: average) |
| **B — Dominant trope rule** | Promotion allowed at median ≥ 0.4 only if the book already has a dominant canonical trope (weight ≥ 0.65). If no dominant exists, the promoted trope must itself have median ≥ 0.65 to serve as anchor. |
| **C — Demotion on user removal** | **Ratchet** — once promoted, stays canonical. Weight recalculates (median) whenever user tags change. Admin-only removal via existing `DELETE /books/{id}/tropes/{trope_id}`. |
| **D — Promotion threshold N** | Env var `CROWD_PROMOTION_THRESHOLD`, default 3. |
| **E — Archetypes** | Same treatment as tropes. Median importance ≥ 5 to promote. No dominant-analogue check. Needs `is_crowd_promoted` migration on `character_dna`. |
| **F — Embed All description backfill** | `POST /admin/embed-all` must also pick up books where `description IS NOT NULL AND description_embedding IS NULL`, regardless of `embedding_status`. Currently those are silently skipped if status is already `'done'`. |
| **G — Review re-embed frequency** | Batch: only re-embed review stream when a book's review count has grown by ≥ 5 since the last review embed. Requires a new `review_embed_count INT DEFAULT 0` column on `books`. |

---

## Bugs in Current Implementation

| # | Bug | Fix |
|---|---|---|
| 1 | **Concurrency race** — two simultaneous upserts at count N-1 both pass the threshold check before either insert commits → IntegrityError on `book_tropes` PK | `INSERT … ON CONFLICT DO UPDATE` via `pg_insert().on_conflict_do_update()` |
| 2 | **`TROPE_THRESHOLD` duplicated** — defined in both `books.py` and `user_tags.py`; will silently diverge if one changes | Move to `config.py`; both files import from `settings` |
| 3 | **Weight never updates after user removal** — when a user removes their tag and count stays above threshold, canonical weight is stale | After any tag removal, recalculate median and update `book_tropes.weight`; trigger re-embed if weight changed |
| 4 | **No re-embed when weight changes on removal** — stale genome stays live | Trigger `_embed_in_background` whenever canonical weight is updated |
| 5 | **`demote_user_trope_if_needed` must be removed** — replaced entirely by ratchet + weight-update pattern | Delete function; replace call site in `remove_user_trope` with `_update_crowd_trope_weight` |
| 6 | **avg → median** | Replace `func.avg()` with Python-side `statistics.median()` on fetched weights |

---

## Promotion Logic (tropes) — Final Design

```
promote_or_update_trope(db, book_id, trope_id):

  existing_canonical = db.get(BookTrope, (book_id, trope_id))

  # Admin tag wins — never overwrite
  if existing_canonical and not existing_canonical.is_crowd_promoted:
    return False

  user_weights = SELECT weight FROM user_book_tropes
                 WHERE book_id=X AND trope_id=Y

  if len(user_weights) < settings.CROWD_PROMOTION_THRESHOLD:
    # Below threshold but ratchet: update weight if crowd row already exists
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

  # Dominant anchor check (decision B)
  has_dominant = EXISTS(
    SELECT 1 FROM book_tropes
    WHERE book_id=X AND trope_id != Y AND weight >= 0.65
  )
  if not has_dominant and median_weight < DOMINANT_WEIGHT_THRESHOLD:  # 0.65
    return False

  # Atomic upsert — resolves concurrency race and admin-wins rule in one statement
  pg_insert(BookTrope).values(
    book_id=book_id, trope_id=trope_id,
    weight=round(median_weight, 4), is_crowd_promoted=True
  ).on_conflict_do_update(
    index_elements=["book_id", "trope_id"],
    set_={"weight": round(median_weight, 4)},
    where=BookTrope.is_crowd_promoted == True  # never clobber admin row
  )

  trigger_re_embed_if_eligible(book_id)
  return True
```

## Archetype Promotion — Final Design

Mirrors trope logic with:
- Tables: `character_dna` (canonical), `user_book_archetypes` (user tags)
- Field: `importance` (int 1–10) instead of `weight` (float 0–1)
- Threshold: median importance ≥ `MIN_MEDIAN_IMPORTANCE` (5); no dominant-anchor check
- `character_dna.is_crowd_promoted` requires a new migration

## Embed All — Description Backfill (Decision F)

Current query in `POST /admin/embed-all`:
```python
select(Book.book_id).where(Book.embedding_status != "done")
```

Updated query — union of two cases:
```python
select(Book.book_id).where(
    or_(
        Book.embedding_status != "done",
        and_(Book.description.is_not(None), Book.description_embedding.is_(None))
    )
)
```

This catches books where status is `'done'` (genome was embedded at some point) but description was null at the time and has since been filled in, or any other data inconsistency that left description_embedding null.

## Review Re-embed Batching (Decision G)

New `review_embed_count` column on `books` tracks how many reviews were aggregated at the time of the last review embed.

**Trigger check in ratings router** (after a review upsert):
```python
current_count = SELECT COUNT(*) FROM book_ratings
                WHERE book_id=X AND review_text IS NOT NULL

if current_count - book.review_embed_count >= REVIEW_EMBED_BATCH_SIZE:  # 5
    asyncio.create_task(_embed_reviews_in_background(book_id))
```

**After embed completes** (`embed_reviews_for_book`):
```python
book.review_embed_count = current_review_count
await db.commit()
```

`REVIEW_EMBED_BATCH_SIZE = 5` defined as a constant in `config.py`.

---

## Files to Change

| File | Change |
|---|---|
| `backend/app/config.py` | Add `CROWD_PROMOTION_THRESHOLD: int = 3`, `TROPE_THRESHOLD: int = 3` (moved), `REVIEW_EMBED_BATCH_SIZE: int = 5` |
| `backend/app/models/book.py` | Add `review_embed_count: Mapped[int]` column |
| `backend/app/models/character_dna.py` | Add `is_crowd_promoted: Mapped[bool]` column |
| New Alembic migration | Add `character_dna.is_crowd_promoted BOOLEAN NOT NULL DEFAULT FALSE` and `books.review_embed_count INT NOT NULL DEFAULT 0` |
| `backend/app/crud/user_tags.py` | Rewrite trope promotion (median, dominant check, ON CONFLICT, ratchet); add archetype equivalents; delete `demote_user_trope_if_needed` |
| `backend/app/routers/books.py` | Remove local `TROPE_THRESHOLD`; import from `settings` |
| `backend/app/routers/admin.py` | Update `embed_all` query to include description backfill (decision F) |
| `backend/app/routers/ratings.py` | Add review count check before triggering review re-embed (decision G) |
| `backend/app/services/embedding.py` | Update `embed_reviews_for_book` to set `review_embed_count` after embed |
| `backend/.env.example` | Add `CROWD_PROMOTION_THRESHOLD=3` |
| Backend schemas | Confirm `is_crowd_promoted` exposed in `BookTropeRead` and archetype equivalent |
| `frontend/src/pages/BookDetail.tsx` | Crowd-tagged badge on tropes/archetypes where `is_crowd_promoted === true` |

---

## Progress Checklist

- [x] `config.py` — add `CROWD_PROMOTION_THRESHOLD`, move `TROPE_THRESHOLD`, add `REVIEW_EMBED_BATCH_SIZE`
- [x] `book.py` model — add `review_embed_count`
- [x] `character_dna.py` model — add `is_crowd_promoted`
- [x] Migration `p0q1r2s3t4u5` — `character_dna.is_crowd_promoted` + `books.review_embed_count`
- [x] `user_tags.py` — rewrite trope promotion (median, dominant check, ON CONFLICT, ratchet)
- [x] `user_tags.py` — add `_update_crowd_trope_weight` helper; wire into `remove_user_trope`
- [x] `user_tags.py` — add archetype promotion + importance-update helpers; wire in
- [x] `books.py` — remove local `TROPE_THRESHOLD`; import from `settings`
- [x] `admin.py` — update `embed_all` query for description backfill (decision F)
- [x] `ratings.py` — batch check inside `_embed_reviews_in_background` (decision G)
- [x] `embedding.py` — set `review_embed_count` after review embed
- [x] `.env.example` — add `CROWD_PROMOTION_THRESHOLD=3`
- [x] Backend schemas — `is_crowd_promoted` in `BookTropeRead` + `CharacterDNARead`
- [x] Frontend `BookDetail.tsx` — teal crowd-tagged badge on promoted tropes/archetypes
- [x] Tests — `test_crowdsourcing.py` rewritten for ratchet/median/dominant-anchor design
