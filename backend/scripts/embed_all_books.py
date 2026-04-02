"""
Embed or re-embed books.

Usage:
    uv run python scripts/embed_all_books.py          # only books missing embeddings
    uv run python scripts/embed_all_books.py --force  # re-embed all books
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database.engine import AsyncSessionLocal
from app.models.book import Book
from app.services.embedding import embed_book


async def main(force: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        stmt = select(Book.book_id) if force else select(Book.book_id).where(Book.embedding.is_(None))
        result = await db.execute(stmt)
        ids = list(result.scalars().all())

    if not ids:
        print("All books already have embeddings. Use --force to re-embed.")
        return

    label = "Re-embedding" if force else "Embedding"
    print(f"{label} {len(ids)} book(s)…")
    for book_id in ids:
        async with AsyncSessionLocal() as db:
            book = await embed_book(book_id, db)
            print(f"  [{book.book_id}] {book.title} — done")

    print("Finished.")


if __name__ == "__main__":
    force = "--force" in sys.argv
    asyncio.run(main(force=force))
