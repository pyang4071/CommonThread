# Book Tagging Prompt

## Goal

Read the scraped book data from `backend/webscraper/output/` and produce a single
`backend/webscraper/output/tagged_books.json` file where every book is annotated
using the CommonThread taxonomy (tropes, archetypes, genres, book types, tones, pacing).

Use your training knowledge of each book. Do not make external tool calls or web
searches to look up book content — rely on the title, author, and description
already present in the scraped data.

---

## Input

Read all JSONL files matching `backend/webscraper/output/books_*.jsonl`.
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

The full taxonomy is in `backend/reference_data.md`. Use **only** names from that
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

Write the result to `backend/webscraper/output/tagged_books.json` as a JSON array.
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

`backend/webscraper/output/skipped_books.json`

```json
[
  { "ol_work_key": "/works/OL12345W", "title": "...", "reason": "No description and not in training data" }
]
```

---

## Checkpoints

Process books in batches of 50. After each batch, append completed entries to
`tagged_books.json` and write a checkpoint file:

`backend/webscraper/output/tagging_progress.json`

```json
{
  "completed_ol_work_keys": ["/works/OL45804W", "..."],
  "total_tagged": 150,
  "total_skipped": 4,
  "last_batch_completed": "2026-04-14T16:00:00"
}
```

On resume, read `tagging_progress.json` and skip any `ol_work_key` already in
`completed_ol_work_keys`. Append new results to the existing `tagged_books.json`
rather than overwriting it.
