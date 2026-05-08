# Parse Books

## Current Status — 2026-04-18

| Metric | Count |
|---|---|
| Total scraped books (JSONL files) | 10,020 |
| Tagged and **imported into DB** | 648 |
| Skipped (unknown / no data) | 152 |
| **Remaining to process** | **9,220** |

The 648 tagged books are live in the database with tropes, archetypes, genres, tones,
book types, pacing, and genome+description embeddings applied.

`tagging_progress.json` holds the checkpoint. On resume, read it and skip any
`ol_work_key` already in `completed_ol_work_keys` — do **not** re-tag books that
are already done.

---

## After each batch: import to DB

Once you have appended a batch to `tagged_books.json`, run the import script to push
the new entries into the database:

```bash
uv run python scripts/import_tagged_books.py --no-embed
```

Then trigger embedding via the Admin page → **Embed pending & failed books**, or run:

```bash
uv run python -c "
import asyncio, sys; sys.path.insert(0, '.')
from sqlalchemy import select
from app.database.engine import AsyncSessionLocal
from app.models.book import Book
from app.services.embedding import embed_books_batch

async def main():
    async with AsyncSessionLocal() as db:
        ids = (await db.execute(
            select(Book.book_id).where(Book.embedding_status == 'pending')
        )).scalars().all()
        print(f'Embedding {len(ids)} books...')
        result = await embed_books_batch(list(ids), db)
        done = sum(1 for v in result.values() if v == 'done')
        print(f'Done: {done}/{len(ids)}')

asyncio.run(main())
"
```

The import script is idempotent — re-running it on already-imported books is safe.

---

## Goal

Read the scraped book data from `webscraper/output/` and produce a single
`webscraper/output/tagged_books.json` file where every book is annotated
using the CommonThread taxonomy (tropes, archetypes, genres, book types, tones, pacing).

Use your training knowledge of each book. Do not make external tool calls or web
searches to look up book content — rely on the title, author, and description
already present in the scraped data.

---

## Input

Read all JSONL files matching `webscraper/output/books_*.jsonl`.
Each line is a JSON object with these fields (all optional except `title`):

```
ol_work_key         string   Open Library identifier
title               string   Book title
authors             string[] Author name(s)
isbn                string   ISBN-10
isbn13              string   ISBN-13 (prefer this over isbn)
publication_year    int      Year published
description         string   Plot summary / synopsis
subjects            string[] Open Library subject tags (rough genre hints)
cover_url           string   Cover image URL
discovered_via_subject string  Which subject query found this book
```

---

## Taxonomy

The full taxonomy is in `reference_data.md`. Use **only** names from that
file. Do not invent new tropes, archetypes, genres, book types, or tones.

### Trope weights

| Weight | Label | Meaning |
|---|---|---|
| 1.00 | Structural | The story is a deconstruction of or built entirely around this trope |
| 0.85 | Dominant | A primary plot engine, present throughout |
| 0.65 | Major | Significant subplot or recurring theme |
| 0.45 | Supporting | Present and meaningful but not central |
| 0.25 | Minor | A brief arc or secondary character trait |
| 0.10 | Flavor | A single scene or blink-and-miss-it nod |

Assign **5 to 12 tropes** per book, ranked by weight descending.
At least one trope must have weight ≥ 0.65.

### Archetype importance

| Importance | Label | Meaning |
|---|---|---|
| 10 | Central | Defines the character entirely |
| 7 | Significant | Clearly present throughout the story |
| 4 | Supporting | A secondary character quality |
| 1 | Background | A fleeting hint only |

Assign **0 to 8 archetypes** per book.

### Other fields

| Field | Rule |
|---|---|
| `genres` | 1 or more genre names; as many as genuinely apply |
| `book_types` | 1 or more book type names (e.g. `"Novel"` + `"Adult"` + `"Series Starter"`) |
| `tones` | 1 or more tone names; as many as genuinely apply |
| `pacing` | Integer 1–5 (`1` = very slow, `5` = very fast). Omit (null) if unsure |

---

## Output format

Write the result to `webscraper/output/tagged_books.json` as a JSON array.
Each element must follow this exact structure:

```json
{
  "ol_work_key": "/works/OL45804W",
  "title": "Book Title",
  "author": "Author Name",
  "isbn": "978-0-00-000000-0",
  "publication_year": 1997,
  "description": "Original description from the scraped data (copy verbatim).",
  "cover_url": "https://covers.openlibrary.org/...",
  "pacing": 3,
  "genres": ["Fantasy", "Adventure"],
  "book_types": ["Novel", "Adult", "Series Starter"],
  "tones": ["Dark", "Atmospheric", "Hopeful"],
  "tropes": [
    { "name": "Chosen One", "weight": 0.85 },
    { "name": "Found Family", "weight": 0.65 },
    { "name": "Magic System", "weight": 0.45 }
  ],
  "archetypes": [
    { "name": "The Hero", "importance": 9 },
    { "name": "The Mentor", "importance": 7 }
  ]
}
```

Rules:
- `author`: use the first name in the `authors` array; if empty use `"Unknown"`
- `isbn`: prefer `isbn13` from the source; fall back to `isbn`; `null` if neither present
- `description`: copy verbatim from the scraped data; `null` if not present
- `cover_url`: copy verbatim; `null` if not present
- All taxonomy values must match `reference_data.md` exactly (case-sensitive)

---

## Unknown books

If you have no meaningful knowledge of a book (e.g. the title is unrecognisable, the
description is absent, and your training data has nothing on it), **skip it** — do not
guess. Write the skipped book to a separate file:

`webscraper/output/skipped_books.json`

```json
[
  { "ol_work_key": "/works/OL12345W", "title": "...", "reason": "No description and not in training data" }
]
```

---

## Checkpoints

Process books in batches of 50. After each batch of 50:

1. **Append** completed entries to `webscraper/output/tagged_books.json`
   (never overwrite — always append to preserve previously tagged books).
2. **Update** the checkpoint file:

`webscraper/output/tagging_progress.json`

```json
{
  "completed_ol_work_keys": ["/works/OL45804W", "..."],
  "total_tagged": 150,
  "total_skipped": 4,
  "last_batch_completed": "2026-04-14T16:00:00"
}
```

3. **Run the import script** to push the batch to the database (see "After each batch" above).

**After every 200 books (4 batches of 50), stop and wait for the user before continuing.**

On resume, read `tagging_progress.json` and skip any `ol_work_key` already in
`completed_ol_work_keys`. The checkpoint currently has **1250 entries** (1047 tagged +
203 skipped as of 2026-04-19) — start from book 1251.
