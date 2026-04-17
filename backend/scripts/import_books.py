"""
Import scraped Open Library books into the CommonThread database.

Reads all JSONL files from backend/webscraper/output/ and upserts books,
authors, and genre associations into the database. Triggers a description
embedding for each imported book immediately (no trope gate).

Usage:
    cd backend
    uv run python scripts/import_books.py
    uv run python scripts/import_books.py --dry-run       # print stats, no DB writes
    uv run python scripts/import_books.py --limit 100     # import first N books
    uv run python scripts/import_books.py --file books_fantasy.jsonl  # single file
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import date
from pathlib import Path

# Add backend root to path so app.* imports work when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database.engine import AsyncSessionLocal
from app.models.book import Book
from app.models.genre import Genre
from app.crud.author import get_or_create as get_or_create_author
from app.crud.book import attach_genre
from app.schemas.book import BookCreate, BookGenreAttach
from app.services.embedding import embed_description_only
from webscraper.models import ScrapedBook

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "webscraper" / "output"

# ---------------------------------------------------------------------------
# Subject → Genre name mapping
# Covers the 20 built-in Open Library subjects plus common sub-subjects.
# Keys are lowercased for case-insensitive matching.
# ---------------------------------------------------------------------------
SUBJECT_TO_GENRE: dict[str, str] = {
    # Core subjects (match the 20 built-in scraper subjects)
    "fantasy": "Fantasy",
    "mystery": "Mystery",
    "romance": "Romance",
    "science fiction": "Science Fiction",
    "thriller": "Thriller",
    "historical fiction": "Historical Fiction",
    "horror": "Horror",
    "young adult": "Young Adult",
    "biography": "Biography",
    "self-help": "Self-Help",
    "classics": "Classics",
    "literary fiction": "Literary Fiction",
    "adventure": "Adventure",
    "crime": "Crime",
    "philosophy": "Philosophy",
    "psychology": "Psychology",
    "humor": "Humor",
    "poetry": "Poetry",
    "graphic novels": "Graphic Novel",
    "short stories": "Short Stories",
    # Common Open Library subject variants
    "detective and mystery stories": "Mystery",
    "detective stories": "Mystery",
    "mystery and detective stories": "Mystery",
    "crime fiction": "Crime",
    "spy stories": "Thriller",
    "suspense": "Thriller",
    "psychological fiction": "Thriller",
    "science fiction, american": "Science Fiction",
    "science fiction, english": "Science Fiction",
    "dystopian fiction": "Science Fiction",
    "space opera": "Science Fiction",
    "cyberpunk": "Science Fiction",
    "fantasy fiction": "Fantasy",
    "epic fantasy": "Fantasy",
    "urban fantasy": "Fantasy",
    "dark fantasy": "Fantasy",
    "paranormal fiction": "Fantasy",
    "vampires": "Horror",
    "ghost stories": "Horror",
    "horror tales": "Horror",
    "romance fiction": "Romance",
    "love stories": "Romance",
    "historical romance": "Romance",
    "regency romance": "Romance",
    "young adult fiction": "Young Adult",
    "teen fiction": "Young Adult",
    "coming of age": "Young Adult",
    "autobiographies": "Biography",
    "memoirs": "Biography",
    "biography & autobiography": "Biography",
    "personal memoirs": "Biography",
    "self help": "Self-Help",
    "personal development": "Self-Help",
    "motivational literature": "Self-Help",
    "classic literature": "Classics",
    "english literature": "Classics",
    "american literature": "Literary Fiction",
    "literary collections": "Literary Fiction",
    "action and adventure": "Adventure",
    "sea stories": "Adventure",
    "war stories": "Adventure",
    "philosophical literature": "Philosophy",
    "ethics": "Philosophy",
    "psychology and mental health": "Psychology",
    "psychiatry": "Psychology",
    "comic books, strips, etc.": "Graphic Novel",
    "comics": "Graphic Novel",
    "manga": "Graphic Novel",
    "humorous fiction": "Humor",
    "satire": "Humor",
    "humorous stories": "Humor",
    "poetry collections": "Poetry",
    "short fiction": "Short Stories",
    "anthologies": "Short Stories",
}


def map_subjects_to_genres(subjects: list[str]) -> list[str]:
    """
    Map a list of raw Open Library subject strings to canonical genre names.
    Returns a deduplicated list of matched genre names.
    """
    matched: set[str] = set()
    for subject in subjects:
        normalized = subject.lower().strip()
        if normalized in SUBJECT_TO_GENRE:
            matched.add(SUBJECT_TO_GENRE[normalized])
    return sorted(matched)


async def get_or_create_genre(db, name: str) -> Genre:
    result = await db.execute(select(Genre).where(Genre.name == name))
    genre = result.scalar_one_or_none()
    if genre is None:
        genre = Genre(name=name)
        db.add(genre)
        await db.flush()  # get genre_id without full commit
    return genre


async def import_book(db, scraped: ScrapedBook, dry_run: bool = False) -> bool:
    """
    Import a single ScrapedBook into the DB. Returns True if a new book was
    created, False if it was skipped (duplicate ISBN or no importable data).
    """
    # Require at least a title and one author
    if not scraped.title or not scraped.authors:
        return False

    # Prefer ISBN-13 over ISBN-10; skip if neither present
    isbn = scraped.isbn13 or scraped.isbn
    if not isbn:
        return False

    # Duplicate check by ISBN
    existing = await db.execute(select(Book).where(Book.isbn == isbn))
    if existing.scalar_one_or_none() is not None:
        return False

    if dry_run:
        return True

    # Resolve publication date (year only → Jan 1)
    pub_date: date | None = None
    if scraped.publication_year:
        try:
            pub_date = date(scraped.publication_year, 1, 1)
        except ValueError:
            pass

    # Create the book via the existing CRUD helper
    author_name = scraped.authors[0]
    data = BookCreate(
        title=scraped.title,
        author=author_name,
        isbn=isbn,
        publication_date=pub_date,
        description=scraped.description,
    )
    author = await get_or_create_author(db, author_name)
    from app.crud.series import get_or_create as get_or_create_series  # noqa: F401 (unused here)
    book = Book(
        title=data.title,
        author_id=author.author_id,
        isbn=data.isbn,
        publication_date=data.publication_date,
        description=data.description,
        cover_url=scraped.cover_url,
    )
    db.add(book)
    await db.flush()  # get book_id

    # Attach genres derived from subjects
    genre_names = map_subjects_to_genres(scraped.subjects)
    for genre_name in genre_names:
        genre = await get_or_create_genre(db, genre_name)
        await attach_genre(db, book.book_id, BookGenreAttach(genre_id=genre.genre_id))

    await db.commit()
    return True


async def run_import(
    files: list[Path],
    limit: int | None,
    dry_run: bool,
    embed: bool,
) -> None:
    total_seen = 0
    total_imported = 0
    total_skipped = 0
    total_embedded = 0

    async with AsyncSessionLocal() as db:
        for jsonl_path in files:
            logger.info("Reading %s", jsonl_path.name)
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                        scraped = ScrapedBook.model_validate(raw)
                    except Exception as exc:
                        logger.warning("Skipping malformed record: %s", exc)
                        total_skipped += 1
                        continue

                    total_seen += 1
                    if limit and total_imported >= limit:
                        break

                    created = await import_book(db, scraped, dry_run=dry_run)
                    if created:
                        total_imported += 1
                        if not dry_run and embed and scraped.description:
                            # Fetch the newly created book_id from DB
                            isbn = scraped.isbn13 or scraped.isbn
                            result = await db.execute(
                                select(Book.book_id).where(Book.isbn == isbn)
                            )
                            book_id = result.scalar_one_or_none()
                            if book_id:
                                await embed_description_only(book_id, db)
                                total_embedded += 1
                    else:
                        total_skipped += 1

                if limit and total_imported >= limit:
                    logger.info("Reached limit of %d, stopping.", limit)
                    break

    logger.info(
        "Done. seen=%d  imported=%d  skipped=%d  embedded=%d%s",
        total_seen,
        total_imported,
        total_skipped,
        total_embedded,
        "  [DRY RUN — no writes]" if dry_run else "",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Open Library JSONL into CommonThread DB")
    parser.add_argument(
        "--file",
        metavar="FILENAME",
        help="Single JSONL file to import (relative to webscraper/output/). "
             "Default: all books_*.jsonl files.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Stop after importing N books.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and count records without writing to the DB.",
    )
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="Skip description embedding after import (faster; embed later via admin Embed All).",
    )
    args = parser.parse_args()

    if args.file:
        files = [OUTPUT_DIR / args.file]
        if not files[0].exists():
            logger.error("File not found: %s", files[0])
            sys.exit(1)
    else:
        files = sorted(OUTPUT_DIR.glob("books_*.jsonl"))
        if not files:
            logger.error(
                "No books_*.jsonl files found in %s. Run the scraper first:\n"
                "  uv run python -m webscraper.run",
                OUTPUT_DIR,
            )
            sys.exit(1)

    logger.info("Found %d JSONL file(s) to import", len(files))
    asyncio.run(
        run_import(
            files=files,
            limit=args.limit,
            dry_run=args.dry_run,
            embed=not args.no_embed,
        )
    )


if __name__ == "__main__":
    main()
