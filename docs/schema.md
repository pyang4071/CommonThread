# CommonThread — Database Schema

Every table in the CommonThread database, with a description of each column and its role. For how these tables feed into search and recommendations, see [search_and_recommendations.md](search_and_recommendations.md). For API endpoints that read/write these tables, see [features.md](features.md).

---

## Table of Contents

1. [Core tables](#core-tables)
   - [app_users](#app_users)
   - [books](#books)
   - [authors](#authors)
   - [series](#series)
2. [Taxonomy tables](#taxonomy-tables)
   - [tropes](#tropes)
   - [archetypes](#archetypes)
   - [genres](#genres)
   - [book_types](#book_types)
   - [tones](#tones)
3. [Book association tables](#book-association-tables)
   - [book_tropes](#book_tropes)
   - [character_dna](#character_dna)
   - [book_genres / book_book_types / book_tones](#book_genres--book_book_types--book_tones)
4. [User interaction tables](#user-interaction-tables)
   - [reading_statuses](#reading_statuses)
   - [book_ratings](#book_ratings)
   - [book_dislikes](#book_dislikes)
   - [user_book_tropes](#user_book_tropes)
   - [user_book_archetypes](#user_book_archetypes)
   - [user_follows](#user_follows)

---

## Core tables

### `app_users`

Stores every registered user. Separate from Supabase Auth — the `user_id` is the UUID issued by Supabase and the two records are linked by it, but profile data lives here.

| Column | Type | Notes |
|---|---|---|
| `user_id` | UUID PK | Matches the `sub` claim in the Supabase JWT. Auto-created on first authenticated request via upsert in `get_current_user()`. |
| `name` | VARCHAR | Display name. Nullable — users who have never set a name show their email in the UI instead. |
| `email` | VARCHAR | Unique. Pulled from the JWT claims on upsert; never directly editable. |
| `is_admin` | BOOLEAN | Default `false`. Admin users can create/edit/delete books and reference data. Set manually in the DB. |
| `preferences` | JSONB | User content preferences and privacy settings. Schema: `{ blocked_genre_ids: int[], blocked_book_type_ids: int[], blocked_tone_ids: int[], profile_public: bool }`. `blocked_*` lists are applied server-side when listing books. `profile_public` gates shelf/profile visibility to non-followers. |
| `created_at` | TIMESTAMP | Auto-set on insert. |

---

### `books`

The central table. Each row is a single book edition (not a work — if the same title was imported with different ISBNs, duplicates may exist; dedup is applied at import time by title+author).

| Column | Type | Notes |
|---|---|---|
| `book_id` | INT PK | Auto-incrementing surrogate key. |
| `title` | VARCHAR | Required. Indexed (`ix_books_title`) for fast autocomplete and sorting. |
| `author_id` | INT FK → `authors` | Required. Indexed (`ix_books_author_id`). |
| `isbn` | VARCHAR | Unique, nullable. ISBN-13 preferred when both are available. Used as the primary key for OpenLibrary cover probing. |
| `publication_date` | DATE | Nullable. |
| `description` | TEXT | Free-text synopsis. Nullable — books without a description cannot have a `description_embedding`. |
| `pacing` | INT 1–5 | Nullable. `1` = Very Slow, `5` = Very Fast. Included in the genome text string and shown as a chip in the UI. |
| `page_count` | INT | Nullable. Filterable on the Books page (min/max range). |
| `cover_url` | VARCHAR | Nullable. Set by the background cover-fetch service. Points to an OpenLibrary image URL. |
| `search_vector` | TSVECTOR | **Generated column** — maintained automatically by Postgres. Computed as `setweight(to_tsvector('english', title), 'A') \|\| setweight(to_tsvector('english', description), 'C')`. Title terms are weighted A (highest); description terms weighted C. Used by the lexical leg of hybrid search. Deferred — not loaded unless explicitly queried. |
| `genome_embedding` | vector(384) | Structural embedding from `BAAI/bge-small-en-v1.5`. Encodes tropes, archetypes, genres, tones, pacing, title, author as a formatted text string. `NULL` until the book has ≥ 3 canonical tropes. Used by Similar Books, For You, and the dislike penalty. |
| `description_embedding` | vector(768) | Prose embedding from `BAAI/bge-base-en-v1.5`. Encodes the description text only. `NULL` if description is missing. Used by the semantic leg of hybrid search. |
| `review_embedding` | vector(768) | Aggregated review text embedding from `BAAI/bge-base-en-v1.5`. `NULL` until at least one review has been embedded. Used to re-score recommendations based on how readers describe the book. |
| `embedding_status` | VARCHAR | `pending` \| `done` \| `failed`. `done` means the description is embedded (minimum searchability). Genome is separately gated on trope count. A book can be `done` with `genome_embedding = NULL` if it has fewer than 3 tropes. |
| `review_embed_count` | INT | Count of reviews included in the last review embedding run. Re-embedding only triggers when the current review count exceeds this by `REVIEW_EMBED_BATCH_SIZE` (5). Prevents re-embedding on every new review. |
| `series_id` | INT FK → `series` | Nullable. `SET NULL` on series delete so the book is not deleted with it. Indexed (`ix_books_series_id`). |
| `series_position` | INT | Nullable. Ordinal position within the series (1-indexed by convention). |
| `created_at` | TIMESTAMP | Auto-set on insert. |
| `updated_at` | TIMESTAMP | Auto-updated on every write. |
| `deleted_at` | TIMESTAMP | Nullable. Soft-delete — when set, the book is excluded from all queries via `WHERE deleted_at IS NULL`. |

---

### `authors`

Simple lookup table. Authors are created automatically when a book is imported/added; they are not managed independently.

| Column | Type | Notes |
|---|---|---|
| `author_id` | INT PK | Auto-incrementing. |
| `name` | VARCHAR | Indexed (`ix_authors_name`). Used in the lexical search leg via `ILIKE` (author names are not in the tsvector). Also shown in autocomplete on AddBook. |
| `bio` | TEXT | Nullable. Not currently displayed in the UI. |

---

### `series`

Groups books that belong to the same series. A book may belong to at most one series.

| Column | Type | Notes |
|---|---|---|
| `series_id` | INT PK | Auto-incrementing. |
| `name` | VARCHAR | Unique. |
| `description` | TEXT | Nullable. Not currently displayed in the UI. |

---

## Taxonomy tables

These tables define the controlled vocabulary used to tag books. All are admin-managed (create/edit/delete via the admin UI), with the exception of tropes and archetypes which also receive user tags via the crowd-promotion system.

### `tropes`

Narrative devices or story beats (e.g. "Enemies to Lovers", "Chosen One", "Locked Room Mystery"). Tropes are the primary structural signal — the genome embedding is built from them.

| Column | Type | Notes |
|---|---|---|
| `trope_id` | INT PK | Auto-incrementing. |
| `name` | VARCHAR | Unique. |
| `description` | TEXT | Nullable. Displayed on the TropeDetail page. |
| `category` | VARCHAR | Groups tropes into broad categories (e.g. "Romance", "Conflict", "Setting"). Indexed (`ix_tropes_category`). Used for diversity re-ranking in For You recommendations — the system caps how many books from the same dominant trope category appear in results. |

---

### `archetypes`

Character role patterns (e.g. "The Reluctant Hero", "The Mentor", "The Trickster"). Complement tropes by describing who is in the story rather than what happens.

| Column | Type | Notes |
|---|---|---|
| `archetype_id` | INT PK | Auto-incrementing. |
| `name` | VARCHAR | Unique. |
| `description` | TEXT | Nullable. Displayed on the ArchetypeDetail page. |

---

### `genres`

Broad genre labels (e.g. "Fantasy", "Mystery", "Romance"). A book can have multiple genres. Used as a filter on the Books page and in the content blocklist.

| Column | Type | Notes |
|---|---|---|
| `genre_id` | INT PK | Auto-incrementing. |
| `name` | VARCHAR | Unique, indexed (`ix_genres_name`). |
| `description` | TEXT | Nullable. |

---

### `book_types`

Format/format-adjacent labels (e.g. "Novel", "Novella", "Graphic Novel", "Short Story Collection"). Separate from genre because the same genre can appear across many book types.

| Column | Type | Notes |
|---|---|---|
| `book_type_id` | INT PK | Auto-incrementing. |
| `name` | VARCHAR | Unique, indexed. |
| `description` | TEXT | Nullable. |

---

### `tones`

Mood/atmosphere labels (e.g. "Dark", "Cozy", "Witty", "Gritty"). Included in the genome text string. A book can have multiple tones.

| Column | Type | Notes |
|---|---|---|
| `tone_id` | INT PK | Auto-incrementing. |
| `name` | VARCHAR | Unique. |

---

## Book association tables

Junction tables linking books to their taxonomy tags.

### `book_tropes`

Links a book to its canonical tropes with a weight indicating how central each trope is to the story.

| Column | Type | Notes |
|---|---|---|
| `book_id` | INT PK, FK → `books` | Composite primary key. |
| `trope_id` | INT PK, FK → `tropes` | Indexed (`ix_book_tropes_trope_id`). |
| `weight` | FLOAT 0.0–1.0 | How structurally important this trope is. DB check constraint enforces the range. Tiers: Flavor (0.10), Supporting (0.45), Major (0.65), Dominant (0.85), Structural (1.0). At least one trope per book must be Major (≥ 0.65) if any tropes are added — enforced in the frontend. Used as a feature vector for sparse similarity scoring in Similar Books. |
| `is_crowd_promoted` | BOOLEAN | `false` for admin-set entries, `true` for entries that were crowd-promoted from user tags. Crowd-promoted entries are never overwritten by the promotion system (atomic upsert with `WHERE is_crowd_promoted = true`). Only admins can delete a crowd-promoted entry. |

---

### `character_dna`

Links a book to its canonical archetypes with an importance score indicating how central each character is.

| Column | Type | Notes |
|---|---|---|
| `book_id` | INT PK, FK → `books` | Composite primary key. |
| `archetype_id` | INT PK, FK → `archetypes` | Indexed (`ix_character_dna_archetype_id`). |
| `importance` | INT 1–10 | Role centrality. DB check constraint enforces the range. Tiers: Background (1–2), Supporting (3–4), Secondary (5–6), Major (7–8), Central (9–10). Used in the genome text string and sparse similarity scoring. |
| `is_crowd_promoted` | BOOLEAN | Same semantics as `book_tropes.is_crowd_promoted`. |

---

### `book_genres` / `book_book_types` / `book_tones`

Simple junction tables with no extra columns — just `(book_id, taxonomy_id)` composite PKs. They exist to support the many-to-many relationship between books and each taxonomy dimension.

These associations trigger a genome re-embed when added or removed (if the book has ≥ 3 tropes), since genres and tones appear in the genome text string.

---

## User interaction tables

Records of user actions on books and other users.

### `reading_statuses`

Tracks where a user is in their reading journey with a book. Only one status per user per book at a time (composite PK).

| Column | Type | Notes |
|---|---|---|
| `user_id` | UUID PK, FK → `app_users` | CASCADE delete — status removed when user is deleted. |
| `book_id` | INT PK, FK → `books` | CASCADE delete. |
| `status` | VARCHAR | `want_to_read` \| `currently_reading` \| `read`. Enforced by the frontend and API; no DB check constraint. |
| `created_at` | TIMESTAMP | When the status was first set. |
| `updated_at` | TIMESTAMP | When the status was last changed (e.g. progressed from `want_to_read` to `currently_reading`). |

---

### `book_ratings`

Stores a user's star rating and optional review text for a book. One rating per user per book (unique constraint).

| Column | Type | Notes |
|---|---|---|
| `rating_id` | INT PK | Surrogate key — the business key is the unique constraint on `(user_id, book_id)`. |
| `user_id` | UUID FK → `app_users` | CASCADE delete. |
| `book_id` | INT FK → `books` | CASCADE delete. Indexed (`ix_book_ratings_book_id`) for fast "all ratings for book" queries. |
| `rating` | INT 1–5 | DB check constraint enforces the range. Ratings ≥ 4 are used as seed books for the For You preference vector. |
| `review_text` | TEXT | Nullable. Max 1000 chars (enforced frontend only). When present, triggers a review re-embed after every 5 new reviews (`REVIEW_EMBED_BATCH_SIZE`). |
| `created_at` | TIMESTAMP | When the rating was first submitted. |
| `updated_at` | TIMESTAMP | When the rating was last edited (upsert semantics). |

---

### `book_dislikes`

Records explicit dislikes. Disliked books are excluded from all recommendations and feed events. Their genome embeddings are used to define a suppression zone — books with cosine similarity ≥ 0.82 to any disliked book are also filtered out.

| Column | Type | Notes |
|---|---|---|
| `user_id` | UUID PK, FK → `app_users` | CASCADE delete. Composite PK with `book_id`. |
| `book_id` | INT PK, FK → `books` | CASCADE delete. |
| `created_at` | TIMESTAMP | When the dislike was recorded. |

---

### `user_book_tropes`

Personal trope tags added by users on the BookDetail page. Separate from canonical `book_tropes` — these represent individual reader opinions. When enough users tag the same trope, it is crowd-promoted to canonical.

| Column | Type | Notes |
|---|---|---|
| `user_id` | UUID PK, FK → `app_users` | Composite PK. CASCADE delete. |
| `book_id` | INT PK, FK → `books` | Composite PK. CASCADE delete. |
| `trope_id` | INT PK, FK → `tropes` | Composite PK. CASCADE delete. |
| `weight` | FLOAT 0.0–1.0 | The user's assessment of this trope's importance. DB check constraint enforces the range. When enough users tag the same trope, the **median** weight across all taggers is used as the canonical `book_tropes.weight`. |
| `created_at` | TIMESTAMP | When the tag was added. |

---

### `user_book_archetypes`

Personal archetype tags. Same crowd-promotion mechanics as `user_book_tropes`.

| Column | Type | Notes |
|---|---|---|
| `user_id` | UUID PK, FK → `app_users` | Composite PK. CASCADE delete. |
| `book_id` | INT PK, FK → `books` | Composite PK. CASCADE delete. |
| `archetype_id` | INT PK, FK → `archetypes` | Composite PK. CASCADE delete. |
| `importance` | INT 1–10 | The user's assessment of the archetype's centrality. Median importance across taggers is used at promotion time. DB check constraint enforces the range. |
| `created_at` | TIMESTAMP | When the tag was added. |

---

### `user_follows`

Directed follow relationships between users. Powers the activity feed.

| Column | Type | Notes |
|---|---|---|
| `follower_id` | UUID PK, FK → `app_users` | The user who clicked Follow. Composite PK. CASCADE delete. |
| `followee_id` | UUID PK, FK → `app_users` | The user being followed. CASCADE delete. |
| `created_at` | TIMESTAMP | When the follow was created. |

The composite PK on `(follower_id, followee_id)` is backed by a unique constraint (`uq_user_follows`) — the two are redundant in Postgres but the explicit unique constraint makes the intent clear.

---

## Constraints summary

| Table | Constraint | Rule |
|---|---|---|
| `app_users` | UNIQUE `email` | One account per email address |
| `books` | UNIQUE `isbn` | No two books share an ISBN |
| `book_ratings` | UNIQUE `(user_id, book_id)` | One rating per user per book |
| `book_tropes` | CHECK `weight` | `0.0 ≤ weight ≤ 1.0` |
| `character_dna` | CHECK `importance` | `1 ≤ importance ≤ 10` |
| `book_ratings` | CHECK `rating` | `1 ≤ rating ≤ 5` |
| `user_book_tropes` | CHECK `weight` | `0.0 ≤ weight ≤ 1.0` |
| `user_book_archetypes` | CHECK `importance` | `1 ≤ importance ≤ 10` |
| `user_follows` | UNIQUE `(follower_id, followee_id)` | Can't follow the same user twice |
| All user interaction tables | CASCADE DELETE | Rows removed when the referenced user or book is deleted |
