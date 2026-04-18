"""
Batch-embed description_embedding for all books that have a description
but no description_embedding yet.

This is a one-shot catch-up script for books imported via import_books.py
with --no-embed. New books created through the API get their description
embedded automatically at creation time; this script fills the backlog.

Usage:
    cd backend
    uv run python scripts/embed_descriptions.py
    uv run python scripts/embed_descriptions.py --limit 500
    uv run python scripts/embed_descriptions.py --batch-size 64
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database.engine import AsyncSessionLocal
from app.models.book import Book
from app.services.embedding import _get_description_model, _run_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def run(limit: int | None, batch_size: int) -> None:
    async with AsyncSessionLocal() as db:
        q = (
            select(Book.book_id, Book.description)
            .where(Book.description.is_not(None))
            .where(Book.description != "")
            .where(Book.description_embedding.is_(None))
        )
        if limit:
            q = q.limit(limit)
        rows = (await db.execute(q)).all()

    total = len(rows)
    logger.info("Found %d books needing description embeddings", total)
    if total == 0:
        return

    done = 0
    failed = 0

    for i in range(0, total, batch_size):
        chunk = rows[i : i + batch_size]
        ids = [r.book_id for r in chunk]
        texts = [r.description for r in chunk]

        try:
            vecs = await _run_batch(texts, _get_description_model)
        except Exception:
            logger.exception("Batch %d failed — skipping", i // batch_size)
            failed += len(chunk)
            continue

        async with AsyncSessionLocal() as db:
            for book_id, vec in zip(ids, vecs):
                book = await db.get(Book, book_id)
                if book:
                    book.description_embedding = vec
            await db.commit()

        done += len(chunk)
        logger.info("  %d / %d embedded", done, total)

    logger.info("Done. embedded=%d  failed=%d", done, failed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-embed book descriptions.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    asyncio.run(run(limit=args.limit, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
