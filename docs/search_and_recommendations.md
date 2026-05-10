# Search & Recommendations — Deep Dive

---

## Search

The search bar uses **hybrid search exclusively** (`POST /search/hybrid`). The alpha slider that appears below the search bar when you type controls the lexical/semantic blend *within* that single hybrid call — higher alpha weights keyword matching more, lower alpha weights semantic description similarity more.

### Hybrid Search

When you type a query, two completely independent legs run sequentially against the database and their ranked results are merged.

**Lexical leg** — PostgreSQL full-text search against a `TSVECTOR GENERATED` column on the `books` table. Postgres maintains this column automatically from the title and description. The query also ORs in an `ILIKE` on the author name, since author names aren't included in the tsvector. Results are ranked by `ts_rank_cd` (a built-in Postgres ranking function that considers term frequency and proximity):

```python
tsq = func.plainto_tsquery("english", query)
stmt = (
    select(Book.book_id, func.ts_rank_cd(Book.search_vector, tsq).label("lex_score"))
    .where(Book.search_vector.op("@@")(tsq) | Author.name.ilike(f"%{query}%"))
    .order_by("lex_score DESC")
    .limit(100)
)
```

**Semantic leg** — encodes the query with BGE-base (768-dim) and runs cosine distance against `description_embedding` via pgvector. This works for any prose query — "cozy mystery with slow-burn romance" returns books whose descriptions embed near that query even if none of those exact words appear:

```python
query_vec = await _run(query, _get_description_model)
stmt = (
    select(Book.book_id, Book.description_embedding.cosine_distance(query_vec).label("distance"))
    .where(Book.description_embedding.is_not(None))
    .order_by("distance")
    .limit(100)
)
```

**Merging — Reciprocal Rank Fusion**

Both legs return an ordered list of book IDs. RRF converts those ranks into scores and combines them:

```
rrf(rank, k=60) = 1 / (60 + rank)
score = alpha × rrf(lex_rank) + (1 − alpha) × rrf(sem_rank)
```

The `k=60` constant softens rank-1 dominance — the difference between rank 1 and rank 2 matters less than the difference between rank 61 and rank 62. The alpha slider in the UI (default 0.5) controls the blend: higher alpha weights lexical more, lower weights semantic more. Books that appear in both legs get an agreement bonus; books in only one leg still appear if their score clears a `min_score = 0.003` floor.

The result includes a `match_type` field — `"both"`, `"lexical"`, or `"semantic"` — and books matched semantically get a "matched by vibe" badge in the UI.

---

## Recommendation System

### Similar Books (`/recommendations/{book_id}/similar`)

This is the simpler of the two. Given a source book:

**Step 1 — ANN candidate fetch**: The genome embedding is used as the primary search vector when available, falling back to description if not. The ANN returns up to `limit × 4` candidates with their cosine distances.

**Step 2 — Sparse feature scoring**: A second similarity score is computed using the actual trope weights and archetype importance values as sparse feature vectors. For each candidate, the dot product of the source book's trope weight vector and the candidate's trope weight vector (normalized) gives a structural similarity score that is exact — not approximate like the ANN. This rewards books that share the same specific tropes at similar intensities, not just books that land nearby in the embedding space.

**Step 3 — Embedding score blend (genome + description)**: When the source book has both a genome and a description embedding, both cosines are blended into the embedding score weighted by trope count:
```
genome_weight = min(trope_count / 8, 1.0)
embedding_score = genome_weight × genome_cosine + (1 − genome_weight) × description_cosine
```
A 3-trope book is 37% genome / 63% description; an 8+ trope book is 100% genome. This means sparse books lean on prose similarity more, while fully-tagged books lean on structural similarity more. If description is the primary stream (no genome), the blending step is skipped.

**Step 4 — Three-stream blend**:
```
base_score = 0.5 × embedding_score + 0.5 × sparse_score
```
If both the source book and the candidate have a `review_embedding`, the score shifts to:
```
final_score = 0.80 × base_score + 0.20 × review_cosine
```
This means books that readers *describe similarly* get a small boost on top of structural similarity.

**Step 5** — The source book is excluded from its own results, and the top-N (up to 100) are returned with an explanation listing shared tropes and archetypes. BookDetail shows the top 6 with a "See all →" link to `/books/:id/similar` for the full list.

---

### For You (`/recommendations/for-you`)

This is the full pipeline — eight steps.

**Step 1 — Build the exclude set**

Three queries run in parallel to collect every book ID the user should never see again:
- All rated books (any rating)
- All books marked "read"
- All disliked books

These are unioned into `exclude_ids`.

**Step 2 — Find seed books**

The preference vector is built from books the user has rated ≥ 4 stars. If there are none, it falls back to books on the want-to-read or currently-reading shelf. If there's nothing there either, the endpoint returns empty.

**Step 3 — Build the preference vector**

The genome embeddings of all seed books are mean-pooled into a single 384-dim vector. This is the "taste centroid" — a point in genome space representing what the user tends to like structurally.

On top of that, the user's personal tags (tropes and archetypes they've added to books via the tagging feature) are aggregated and embedded into a separate taste vector, then blended in at 30%:

```
preference = 0.7 × mean_pool(liked_genome_embeddings)
           + 0.3 × embed_user_taste(taste_tropes, taste_archetypes)
```

This means power users who actively tag books get a preference vector that reflects their explicit literary opinions, not just which books they clicked stars on.

If none of the seed books have genome embeddings, the system falls back to mean-pooling their description embeddings instead (768-dim, separate vector space).

A separate review preference vector is also built by mean-pooling `review_embedding` for the seed books — used later in step 7.

**Step 4 — ANN candidate fetch**

pgvector cosine distance search against the preference vector, over-fetching at `limit × 5` candidates to leave room for the filtering steps that follow. Already-read/rated/disliked books are excluded in the SQL query itself.

**Step 5 — Dislike penalty**

The genome embeddings of all disliked books are loaded and unit-normalized. For every candidate, the maximum cosine similarity to any disliked book is computed via matrix multiply. Any candidate with max similarity ≥ 0.82 is dropped entirely — it's too close to something the user explicitly rejected. This means a dislike suppresses not just that one book but the entire neighbourhood of structurally similar books.

**Step 6 — Diversity re-ranking**

Without this step, the top 10 results could all be books with the same dominant trope category (e.g. ten epic fantasies). The re-ranker loads each candidate's tropes, identifies the dominant category, and caps how many books from the same category can appear in the final results.

**Step 7 — Review re-scoring**

For candidates that have a `review_embedding`, a final score blend is applied:

```
final_score = 0.85 × embedding_score + 0.15 × review_cosine(candidate, review_preference)
```

Books without a review embedding are unaffected — their embedding score is used as-is. This rewards books that readers describe in ways consistent with how the user's liked books are described.

**Step 8 — Collaborative filtering**

Up to one third of the final results can come from a collaborative signal: other users with similar taste profiles (measured by genome cosine similarity of their own preference vectors) who have highly rated books the current user hasn't seen. This adds serendipity — books that don't score highest on pure similarity but are consistently loved by readers with similar taste.

The final results are returned with explanations: which tropes and archetypes the recommended book shares with the user's history, and whether the source was `"embedding"` or `"collaborative"`. The Home page shows the top 10 with a "See all →" link to `/for-you` which fetches up to 50.
