import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, or_, and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.database.engine import AsyncSessionLocal
from app.models.book import Book
from app.models.book_trope import BookTrope
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


class VectorCoverageResult(BaseModel):
    total: int
    both: int           # genome + description
    description_only: int
    neither: int
    genome_eligible: int  # books with >= 3 canonical tropes (could have genome embedding)
    review_embedded: int  # books with a review_embedding populated


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


@router.get("/vector-coverage", response_model=VectorCoverageResult)
async def vector_coverage(db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    """
    Count books by which embedding streams are populated.
    Excludes soft-deleted books.
    """
    eligible_book_ids = (
        select(BookTrope.book_id)
        .group_by(BookTrope.book_id)
        .having(func.count(BookTrope.trope_id) >= 3)
    )
    row = (await db.execute(
        select(
            func.count(1).label("total"),
            func.count(1).filter(
                Book.genome_embedding.is_not(None),
                Book.description_embedding.is_not(None),
            ).label("both"),
            func.count(1).filter(
                Book.genome_embedding.is_(None),
                Book.description_embedding.is_not(None),
            ).label("description_only"),
            func.count(1).filter(
                Book.genome_embedding.is_(None),
                Book.description_embedding.is_(None),
            ).label("neither"),
            func.count(1).filter(
                Book.book_id.in_(eligible_book_ids),
            ).label("genome_eligible"),
            func.count(1).filter(
                Book.review_embedding.is_not(None),
            ).label("review_embedded"),
        ).where(Book.deleted_at.is_(None))
    )).one()
    return VectorCoverageResult(
        total=row.total,
        both=row.both,
        description_only=row.description_only,
        neither=row.neither,
        genome_eligible=row.genome_eligible,
        review_embedded=row.review_embedded,
    )


@router.post("/embed-all", response_model=EmbedAllResult)
async def embed_all(db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    """
    Kick off a single background task that batch-embeds every book whose
    status is not 'done' (both pending and failed).
    Description is embedded for all books; genome is only embedded for books
    with >= 3 tropes (checked per-book inside embed_books_batch).
    Returns the number of books queued.
    """
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
    book_ids = list(result.scalars().all())
    if not book_ids:
        return EmbedAllResult(queued=0)

    async def _run_batch_background() -> None:
        try:
            async with AsyncSessionLocal() as session:
                await embed_books_batch(book_ids, session)
        except Exception:
            logger.exception(
                "embed-all background task crashed before completing; "
                "marking %d remaining pending books as failed",
                len(book_ids),
            )
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Book)
                    .where(Book.book_id.in_(book_ids))
                    .where(Book.embedding_status == "pending")
                    .values(embedding_status="failed")
                )
                await session.commit()

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
