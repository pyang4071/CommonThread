"""
Import tagged books from webscraper/output/tagged_books.json into CommonThread.

For each entry:
  - If a book with matching ISBN or title+author already exists: apply its tags.
  - If no match: create the book then apply tags.

Tags applied: genres, book_types, tones, tropes (with weight), archetypes (with importance),
pacing. Unknown tag names (not in the DB) are warned and skipped — no new taxonomy
entries are created by this script.

After all books are processed, every tagged book is re-embedded in one batch call so
genome vectors reflect the new tropes. Pass --no-embed to skip this step.

Usage:
    cd backend
    uv run python scripts/import_tagged_books.py
    uv run python scripts/import_tagged_books.py --dry-run
    uv run python scripts/import_tagged_books.py --limit 50
    uv run python scripts/import_tagged_books.py --no-embed
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database.engine import AsyncSessionLocal
from app.models.archetype import Archetype
from app.models.author import Author
from app.models.book import Book
from app.models.book_book_type import book_book_types
from app.models.book_genre import book_genres
from app.models.book_tone import book_tones
from app.models.book_trope import BookTrope
from app.models.book_type import BookType
from app.models.character_dna import CharacterDNA
from app.models.genre import Genre
from app.models.tone import Tone
from app.models.trope import Trope
from app.crud.author import get_or_create as get_or_create_author
from app.services.embedding import embed_books_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TAGGED_BOOKS_PATH = Path(__file__).parent.parent / "webscraper" / "output" / "tagged_books.json"
TROPE_THRESHOLD = 3


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

async def _load_lookup(db, model, id_col: str, name_col: str = "name") -> dict[str, int]:
    """Load all rows of a model into a {name_lower: id} dict."""
    rows = (await db.execute(select(model))).scalars().all()
    return {getattr(r, name_col).lower(): getattr(r, id_col) for r in rows}


# ---------------------------------------------------------------------------
# Per-book tag application (all inserts idempotent via on_conflict_do_nothing)
# ---------------------------------------------------------------------------

async def _apply_tags(
    db,
    book_id: int,
    entry: dict,
    genre_map: dict[str, int],
    book_type_map: dict[str, int],
    tone_map: dict[str, int],
    trope_map: dict[str, int],
    archetype_map: dict[str, int],
) -> dict[str, int]:
    """Apply all tags from an entry to book_id. Returns counts of what was applied/skipped."""
    counts = {"genres": 0, "book_types": 0, "tones": 0, "tropes": 0, "archetypes": 0,
              "skipped_tropes": 0, "skipped_archetypes": 0}

    for name in entry.get("genres") or []:
        gid = genre_map.get(name.lower())
        if gid:
            await db.execute(
                pg_insert(book_genres).values(book_id=book_id, genre_id=gid)
                .on_conflict_do_nothing()
            )
            counts["genres"] += 1

    for name in entry.get("book_types") or []:
        btid = book_type_map.get(name.lower())
        if btid:
            await db.execute(
                pg_insert(book_book_types).values(book_id=book_id, book_type_id=btid)
                .on_conflict_do_nothing()
            )
            counts["book_types"] += 1

    for name in entry.get("tones") or []:
        tid = tone_map.get(name.lower())
        if tid:
            await db.execute(
                pg_insert(book_tones).values(book_id=book_id, tone_id=tid)
                .on_conflict_do_nothing()
            )
            counts["tones"] += 1

    for t in entry.get("tropes") or []:
        trid = trope_map.get(t["name"].lower())
        if trid is None:
            logger.warning("  Unknown trope '%s' — skipping", t["name"])
            counts["skipped_tropes"] += 1
            continue
        existing = await db.get(BookTrope, (book_id, trid))
        if existing:
            existing.weight = t["weight"]
        else:
            db.add(BookTrope(book_id=book_id, trope_id=trid, weight=t["weight"]))
        counts["tropes"] += 1

    for a in entry.get("archetypes") or []:
        aid = archetype_map.get(a["name"].lower())
        if aid is None:
            logger.warning("  Unknown archetype '%s' — skipping", a["name"])
            counts["skipped_archetypes"] += 1
            continue
        existing = await db.get(CharacterDNA, (book_id, aid))
        if existing:
            existing.importance = a["importance"]
        else:
            db.add(CharacterDNA(book_id=book_id, archetype_id=aid, importance=a["importance"]))
        counts["archetypes"] += 1

    return counts


# ---------------------------------------------------------------------------
# Main import logic
# ---------------------------------------------------------------------------

async def run_import(limit: int | None, dry_run: bool, embed: bool) -> None:
    data: list[dict] = json.loads(TAGGED_BOOKS_PATH.read_text())
    if limit:
        data = data[:limit]

    logger.info("Loaded %d entries from tagged_books.json", len(data))

    stats = {
        "matched": 0, "created": 0, "skipped": 0,
        "total_tropes": 0, "total_archetypes": 0,
        "skipped_tropes": 0, "skipped_archetypes": 0,
        "tagged_book_ids": [],
    }

    async with AsyncSessionLocal() as db:
        # Load all taxonomy lookups once
        genre_map = await _load_lookup(db, Genre, "genre_id")
        book_type_map = await _load_lookup(db, BookType, "book_type_id")
        tone_map = await _load_lookup(db, Tone, "tone_id")
        trope_map = await _load_lookup(db, Trope, "trope_id")
        archetype_map = await _load_lookup(db, Archetype, "archetype_id")

        logger.info(
            "Lookups: %d genres, %d book_types, %d tones, %d tropes, %d archetypes",
            len(genre_map), len(book_type_map), len(tone_map),
            len(trope_map), len(archetype_map),
        )

        for entry in data:
            title = (entry.get("title") or "").strip()
            author_name = (entry.get("author") or "").strip()
            isbn = (entry.get("isbn") or "").strip() or None

            if not title or not author_name:
                logger.warning("Skipping entry with missing title/author: %s", entry)
                stats["skipped"] += 1
                continue

            # 1. Try ISBN match
            book: Book | None = None
            if isbn:
                row = await db.execute(
                    select(Book).where(Book.isbn == isbn, Book.deleted_at.is_(None))
                )
                book = row.scalar_one_or_none()

            # 2. Try title+author match
            if book is None:
                row = await db.execute(
                    select(Book)
                    .join(Author, Book.author_id == Author.author_id)
                    .where(func.lower(Book.title) == title.lower())
                    .where(func.lower(Author.name) == author_name.lower())
                    .where(Book.deleted_at.is_(None))
                    .limit(1)
                )
                book = row.scalar_one_or_none()

            if book is not None:
                stats["matched"] += 1
                action = "matched"
            else:
                # 3. Create new book
                if dry_run:
                    logger.info("[DRY RUN] Would create: '%s' by %s", title, author_name)
                    stats["created"] += 1
                    continue

                pub_date: date | None = None
                if entry.get("publication_year"):
                    try:
                        pub_date = date(entry["publication_year"], 1, 1)
                    except ValueError:
                        pass

                author = await get_or_create_author(db, author_name)
                book = Book(
                    title=title,
                    author_id=author.author_id,
                    isbn=isbn,
                    publication_date=pub_date,
                    description=entry.get("description"),
                    cover_url=entry.get("cover_url"),
                    pacing=entry.get("pacing"),
                )
                db.add(book)
                await db.flush()
                stats["created"] += 1
                action = "created"

            if dry_run and action == "matched":
                trope_count = len(entry.get("tropes") or [])
                logger.info("[DRY RUN] Would tag: '%s' by %s (%d tropes)", title, author_name, trope_count)
                stats["total_tropes"] += trope_count
                continue

            # 4. Fill in missing fields for matched books
            changed = False
            if book.description is None and entry.get("description"):
                book.description = entry["description"]
                changed = True
            if book.cover_url is None and entry.get("cover_url"):
                book.cover_url = entry["cover_url"]
                changed = True
            if book.pacing is None and entry.get("pacing") is not None:
                book.pacing = entry["pacing"]
                changed = True

            # 5. Apply tags
            counts = await _apply_tags(
                db, book.book_id, entry,
                genre_map, book_type_map, tone_map, trope_map, archetype_map,
            )

            stats["total_tropes"] += counts["tropes"]
            stats["total_archetypes"] += counts["archetypes"]
            stats["skipped_tropes"] += counts["skipped_tropes"]
            stats["skipped_archetypes"] += counts["skipped_archetypes"]
            stats["tagged_book_ids"].append(book.book_id)

            # 6. Mark for re-embedding (genome needs updating with new tropes)
            book.embedding_status = "pending"

            await db.commit()
            logger.info(
                "%s '%s': %d tropes, %d archetypes, %d genres, %d tones, %d book_types",
                action, title,
                counts["tropes"], counts["archetypes"],
                counts["genres"], counts["tones"], counts["book_types"],
            )

        # 7. Batch embed all tagged books
        if embed and not dry_run and stats["tagged_book_ids"]:
            # Only embed books that now have enough tropes for genome, but embed
            # description for all. embed_books_batch handles the per-book threshold.
            eligible = (
                await db.execute(
                    select(Book.book_id)
                    .where(Book.book_id.in_(stats["tagged_book_ids"]))
                    .where(Book.embedding_status == "pending")
                )
            ).scalars().all()

            if eligible:
                logger.info("Embedding %d books...", len(eligible))
                await embed_books_batch(list(eligible), db)
                logger.info("Embedding complete.")

    logger.info(
        "\nDone%s:\n"
        "  matched=%d  created=%d  skipped=%d\n"
        "  tropes applied=%d (skipped=%d)\n"
        "  archetypes applied=%d (skipped=%d)",
        "  [DRY RUN — no writes]" if dry_run else "",
        stats["matched"], stats["created"], stats["skipped"],
        stats["total_tropes"], stats["skipped_tropes"],
        stats["total_archetypes"], stats["skipped_archetypes"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import tagged books from tagged_books.json into CommonThread DB"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and count without writing to DB.")
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="Process only the first N entries.")
    parser.add_argument("--no-embed", action="store_true",
                        help="Skip embedding after import (run admin Embed All later).")
    args = parser.parse_args()

    asyncio.run(run_import(
        limit=args.limit,
        dry_run=args.dry_run,
        embed=not args.no_embed,
    ))


if __name__ == "__main__":
    main()
