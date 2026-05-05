"""
Embed books missing genome or description embeddings.

Usage (against prod DB):
    DATABASE_URL=<prod-url> uv run python scripts/embed_all_books.py

Targets the same books as POST /admin/embed-all:
  - embedding_status != 'done'
  - has description but no description_embedding
  - genome-eligible (>= 3 tropes) but no genome_embedding
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import and_, func, or_, select

from app.database.engine import AsyncSessionLocal
from app.models.book import Book
from app.models.book_trope import BookTrope
from app.services.embedding import embed_books_batch


async def main() -> None:
    async with AsyncSessionLocal() as db:
        genome_eligible = (
            select(BookTrope.book_id)
            .group_by(BookTrope.book_id)
            .having(func.count(BookTrope.trope_id) >= 3)
        )
        result = await db.execute(
            select(Book.book_id)
            .where(
                or_(
                    Book.embedding_status != "done",
                    and_(Book.description.is_not(None), Book.description_embedding.is_(None)),
                    and_(Book.book_id.in_(genome_eligible), Book.genome_embedding.is_(None)),
                )
            )
            .where(Book.deleted_at.is_(None))
        )
        ids = list(result.scalars().all())

    if not ids:
        print("Nothing to embed.")
        return

    print(f"Embedding {len(ids)} book(s) in batches of 4…")
    async with AsyncSessionLocal() as db:
        statuses = await embed_books_batch(ids, db)

    done = sum(1 for s in statuses.values() if s == "done")
    failed = sum(1 for s in statuses.values() if s == "failed")
    print(f"Done: {done}  Failed: {failed}")


if __name__ == "__main__":
    asyncio.run(main())
