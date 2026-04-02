import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.database.engine import AsyncSessionLocal
from app.models.book import Book
from app.models.user import AppUser
from app.services.covers import fetch_cover_url
from app.services.embedding import embed_book, embed_books_batch

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


class EmbedAllResult(BaseModel):
    queued: int


class EmbedStatusResult(BaseModel):
    total: int
    done: int
    pending: int
    failed: int


class FetchCoversResult(BaseModel):
    queued: int


async def _embed_book_safe(book_id: int, max_attempts: int = 3) -> None:
    for attempt in range(max_attempts):
        async with AsyncSessionLocal() as db:
            try:
                await embed_book(book_id, db)
                return
            except Exception:
                logger.exception(
                    "Failed to embed book %d (attempt %d/%d)", book_id, attempt + 1, max_attempts
                )
        if attempt < max_attempts - 1:
            await asyncio.sleep(2 ** attempt)

    async with AsyncSessionLocal() as db:
        book = await db.get(Book, book_id)
        if book:
            book.embedding_status = "failed"
            await db.commit()


async def _fetch_cover_safe(book_id: int, isbn: str | None, title: str, author: str) -> None:
    url = await fetch_cover_url(isbn, title, author)
    if not url:
        return
    async with AsyncSessionLocal() as db:
        book = await db.get(Book, book_id)
        if book and not book.cover_url:
            book.cover_url = url
            await db.commit()


@router.get("/embed-status", response_model=EmbedStatusResult)
async def embed_status(db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    """
    Return a count breakdown of embedding_status across all books.
    """
    rows = await db.execute(
        select(Book.embedding_status, func.count().label("n"))
        .group_by(Book.embedding_status)
    )
    counts = {row.embedding_status: row.n for row in rows}
    total = sum(counts.values())
    return EmbedStatusResult(
        total=total,
        done=counts.get("done", 0),
        pending=counts.get("pending", 0),
        failed=counts.get("failed", 0),
    )


@router.post("/embed-all", response_model=EmbedAllResult)
async def embed_all(db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    """
    Kick off a single background task that batch-embeds every book whose
    status is not 'done' (both pending and failed).
    Books are processed in chunks of 32 — genome and description streams
    run concurrently within each chunk.
    Returns the number of books queued.
    """
    result = await db.execute(
        select(Book.book_id).where(Book.embedding_status != "done")
    )
    book_ids = list(result.scalars().all())
    if not book_ids:
        return EmbedAllResult(queued=0)

    async def _run_batch_background() -> None:
        async with AsyncSessionLocal() as session:
            await embed_books_batch(book_ids, session)

    asyncio.create_task(_run_batch_background())
    return EmbedAllResult(queued=len(book_ids))


@router.post("/fetch-covers", response_model=FetchCoversResult)
async def fetch_covers(db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    """
    Kick off background cover fetching for every book that has no cover_url.
    Returns the number of books queued.
    """
    from sqlalchemy.orm import joinedload
    result = await db.execute(
        select(Book)
        .where(Book.cover_url.is_(None))
        .options(joinedload(Book.author))
    )
    books = list(result.scalars().all())

    for book in books:
        asyncio.create_task(_fetch_cover_safe(book.book_id, book.isbn, book.title, book.author.name))

    return FetchCoversResult(queued=len(books))
