# CommonThread — Master Plan

---

## Completed Phases

| Phase | What | Status |
|---|---|---|
| Phase 1 — Recommendation Engine | Three-stream embedding (genome/description/review), Open Library import, crowd promotion scaffolding, description fallback in recommendations | ✅ Complete |
| Phase 2 — Hybrid Search | `search_vector` tsvector column, RRF hybrid search (`POST /search/hybrid`), unified search bar in `Books.tsx` | ✅ Complete |
| Phase 3 — Crowd Promotion | Median weight, dominant-anchor rule, ratchet semantics, ON CONFLICT atomic upsert, archetype parity, `is_crowd_promoted` badge in UI, review batch embed, embed-all description backfill, genome-eligible admin stat | ✅ Complete |
| Phase 4 — Audit Fixes | Review stream wired into recommendation scoring (20% Similar Books, 15% For You), page count filter UI, `/health` model status panel in Admin, `onboarding_completed` column dropped | ✅ Complete |

---

# Phase 5 — Bug Fixes, Polish & Tests

## Bugs

| # | Bug | Fix |
|---|---|---|
| 1 | **Page count filter ignored in hybrid search** — `runHybridSearch` in `Books.tsx` doesn't pass `pageCountMin`/`pageCountMax`; `HybridSearchRequest` body and backend route have no `page_count_min`/`page_count_max` fields | Add fields to `HybridSearchRequest` (backend schema + `hybrid_search` CRUD), client `HybridSearchRequest` type, and pass from `runHybridSearch` |
| 2 | **Page count filter ignored in semantic search** — `GET /search` route has no `page_count_min`/`page_count_max` query params | Add params to `semantic_search` route; apply `WHERE` clauses before the pgvector order; pass from client semantic call |

## Features

| # | Feature | Work |
|---|---|---|
| 3 | **Review coverage in Vector Coverage panel** — admin shows genome/description breakdown but not how many books have `review_embedding` | Add `review_embedded: int` to `VectorCoverageResult` schema and query; add a stat card in `Admin.tsx` |
| 4 | **Confirm modal on Trope/Archetype delete** — direct delete on click; Genres/BookTypes/Tones all use `ConfirmModal`; trope/archetype deletes trigger re-embeds on all associated books | Add `ConfirmModal` flow to `Tropes.tsx` and `Archetypes.tsx` matching the Genres pattern |
| 5 | **Railway/Vercel deployment guide** — README documents Docker Compose only | Add deployment section: Railway backend (Dockerfile, env vars, CORS), Vercel frontend (`vercel.json` SPA rewrite + API proxy, `VITE_*` vars) |

## Testing

| # | Item | Work |
|---|---|---|
| 6 | **E2E tests for Phase 3/4 features** | New spec covering: crowd-tagged badge visible after N user tags; page count filter narrows results; admin health panel shows model status |
| 7 | **Backend unit tests** | Tests for recommendation scoring (review blend), hybrid search page count filter, crowd archetype promotion |

---

## Progress Checklist

- [ ] Bug 1 — page count in hybrid search (backend schema + CRUD + client + Books.tsx)
- [ ] Bug 2 — page count in semantic search (backend route + client)
- [ ] Feature 3 — review coverage stat in admin panel
- [ ] Feature 4 — confirm modal on trope/archetype delete
- [ ] Feature 5 — Railway/Vercel deployment guide in README
- [ ] Test 6 — E2E specs for Phase 3/4
- [ ] Test 7 — backend unit tests for new scoring + search logic
