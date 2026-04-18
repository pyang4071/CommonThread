import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.auth import get_optional_user
from app.database import get_db
from app.database.engine import AsyncSessionLocal
from app.models.book_rating import BookRating
from app.models.book_trope import BookTrope
from app.schemas.author import AuthorRead
from app.schemas.book import (
    BookCreate,
    BookGenreAttach,
    BookRead,
    BookReadDetail,
    BookToneAttach,
    BookTropeAttach,
    BookTypeAttach,
    BookUpdate,
    CharacterDNAAttach,
)
from app.models.book import Book
from app.models.user import AppUser
from app.services.covers import fetch_cover_url
from app.services.embedding import embed_book, embed_description_only, embed_reviews_for_book

router = APIRouter(prefix="/books", tags=["books"])
logger = logging.getLogger(__name__)

# Minimum number of canonical tropes required before genome embedding is triggered.
TROPE_THRESHOLD = 3


async def _embed_in_background(book_id: int, max_attempts: int = 3) -> None:
    for attempt in range(max_attempts):
        async with AsyncSessionLocal() as db:
            try:
                # Pre-guard: abort if tropes dropped below threshold while we were waiting
                count = await _trope_count(db, book_id)
                if count < TROPE_THRESHOLD:
                    return
                await embed_book(book_id, db)
                # Post-guard: if a detach raced with us and count is now below threshold,
                # undo the 'done' status so the badge shows correctly.
                count_after = await _trope_count(db, book_id)
                if count_after < TROPE_THRESHOLD:
                    book_obj = await db.get(Book, book_id)
                    if book_obj:
                        book_obj.embedding_status = "pending"
                        book_obj.genome_embedding = None
                        await db.commit()
                return
            except Exception:
                logger.exception(
                    "Failed to embed book %d (attempt %d/%d)", book_id, attempt + 1, max_attempts
                )
        if attempt < max_attempts - 1:
            await asyncio.sleep(2 ** attempt)  # 1 s, 2 s between retries

    # All attempts exhausted — mark as failed so the admin queue can re-try later
    async with AsyncSessionLocal() as db:
        book = await db.get(Book, book_id)
        if book:
            book.embedding_status = "failed"
            await db.commit()


async def _embed_description_in_background(book_id: int) -> None:
    """Embed the description stream for a book. Fires at creation, no trope gate."""
    async with AsyncSessionLocal() as db:
        try:
            await embed_description_only(book_id, db)
        except Exception:
            logger.exception("Failed to embed description for book %d", book_id)


async def _embed_reviews_in_background(book_id: int) -> None:
    """Re-aggregate and re-embed all review texts for a book."""
    async with AsyncSessionLocal() as db:
        try:
            await embed_reviews_for_book(book_id, db)
        except Exception:
            logger.exception("Failed to embed reviews for book %d", book_id)


async def _fetch_cover_in_background(book_id: int, isbn: str | None, title: str, author: str) -> None:
    url = await fetch_cover_url(isbn, title, author)
    if not url:
        return
    async with AsyncSessionLocal() as db:
        book = await db.get(Book, book_id)
        if book and not book.cover_url:
            book.cover_url = url
            await db.commit()


async def _trope_count(db: AsyncSession, book_id: int) -> int:
    """Return the number of canonical tropes currently attached to the book."""
    result = await db.execute(
        select(func.count()).select_from(BookTrope).where(BookTrope.book_id == book_id)
    )
    return result.scalar_one()


@router.get("/authors", response_model=list[AuthorRead])
async def list_authors(db: AsyncSession = Depends(get_db)):
    return await crud.author.list_authors(db)


@router.get("/", response_model=list[BookRead])
async def list_books(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    categories: list[str] = Query(default=[]),
    genre_ids: list[int] = Query(default=[]),
    book_type_ids: list[int] = Query(default=[]),
    pacing: int | None = None,
    tone_ids: list[int] = Query(default=[]),
    exclude_trope_ids: list[int] = Query(default=[]),
    exclude_archetype_ids: list[int] = Query(default=[]),
    exclude_genre_ids: list[int] = Query(default=[]),
    exclude_book_type_ids: list[int] = Query(default=[]),
    exclude_tone_ids: list[int] = Query(default=[]),
    shelf_status: str | None = None,
    page_count_min: int | None = None,
    page_count_max: int | None = None,
    language: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser | None = Depends(get_optional_user),
):
    books = await crud.book.list_books(
        db, skip=skip, limit=limit, search=search,
        categories=categories or None,
        genre_ids=genre_ids or None,
        book_type_ids=book_type_ids or None,
        pacing=pacing,
        tone_ids=tone_ids or None,
        exclude_trope_ids=exclude_trope_ids or None,
        exclude_archetype_ids=exclude_archetype_ids or None,
        exclude_genre_ids=exclude_genre_ids or None,
        exclude_book_type_ids=exclude_book_type_ids or None,
        exclude_tone_ids=exclude_tone_ids or None,
        shelf_status=shelf_status,
        user_id=current_user.user_id if current_user else None,
        page_count_min=page_count_min,
        page_count_max=page_count_max,
        language=language,
    )
    book_ids = [b.book_id for b in books]
    avg_map: dict[int, float] = {}
    if book_ids:
        avg_q = await db.execute(
            select(BookRating.book_id, func.avg(BookRating.rating).label("avg_rating"))
            .where(BookRating.book_id.in_(book_ids))
            .group_by(BookRating.book_id)
        )
        avg_map = {r.book_id: round(float(r.avg_rating), 2) for r in avg_q}
    out = []
    for book in books:
        book_read = BookRead.model_validate(book)
        book_read.avg_rating = avg_map.get(book.book_id)
        out.append(book_read)
    return out


@router.post("/", response_model=BookRead, status_code=201)
async def create_book(data: BookCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a book with basic metadata. embedding_status starts as 'pending'.
    No genome embedding is triggered here — the book must first reach TROPE_THRESHOLD
    canonical tropes via POST /books/{id}/tropes before embedding fires.
    Cover fetching still runs immediately in the background.
    """
    book = await crud.book.create_book(db, data)
    cover_url = await fetch_cover_url(book.isbn, book.title, book.author.name)
    if cover_url:
        book.cover_url = cover_url
        await db.commit()
        await db.refresh(book)
    asyncio.create_task(_embed_description_in_background(book.book_id))
    return book


@router.get("/{book_id}", response_model=BookReadDetail)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await crud.book.get_book_detail(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.put("/{book_id}", response_model=BookRead)
async def update_book(book_id: int, data: BookUpdate, db: AsyncSession = Depends(get_db)):
    book = await crud.book.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    updated = await crud.book.update_book(db, book, data)
    count = await _trope_count(db, book_id)
    if count >= TROPE_THRESHOLD:
        asyncio.create_task(_embed_in_background(book_id))
    return updated


@router.get("/{book_id}/series", response_model=list[BookRead])
async def get_series(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await crud.book.get_book(db, book_id)
    if not book or not book.series_id:
        return []
    return await crud.book.get_books_in_series(db, book.series_id)


@router.delete("/{book_id}", status_code=204)
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await crud.book.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await crud.book.delete_book(db, book)


@router.post("/{book_id}/tropes", status_code=204)
async def attach_trope(
    book_id: int, data: BookTropeAttach, db: AsyncSession = Depends(get_db)
):
    book = await crud.book.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await crud.book.attach_trope(db, book_id, data)
    count = await _trope_count(db, book_id)
    if count >= TROPE_THRESHOLD:
        asyncio.create_task(_embed_in_background(book_id))


@router.delete("/{book_id}/tropes/{trope_id}", status_code=204)
async def detach_trope(book_id: int, trope_id: int, db: AsyncSession = Depends(get_db)):
    removed = await crud.book.detach_trope(db, book_id, trope_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Book-trope association not found")
    count = await _trope_count(db, book_id)
    if count >= TROPE_THRESHOLD:
        # Still above threshold — re-embed with the updated trope set.
        asyncio.create_task(_embed_in_background(book_id))
    else:
        # Dropped below threshold — invalidate any existing embedding so the book
        # no longer appears in similarity / For You until it is re-tagged.
        # Always reset regardless of current status so that in-flight background
        # embedding tasks don't overwrite with a stale 'done' after detach.
        book_obj = await db.get(Book, book_id)
        if book_obj and book_obj.embedding_status != "pending":
            book_obj.embedding_status = "pending"
            book_obj.genome_embedding = None
            await db.commit()


@router.post("/{book_id}/archetypes", status_code=204)
async def attach_archetype(
    book_id: int, data: CharacterDNAAttach, db: AsyncSession = Depends(get_db)
):
    book = await crud.book.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await crud.book.attach_archetype(db, book_id, data)
    count = await _trope_count(db, book_id)
    if count >= TROPE_THRESHOLD:
        asyncio.create_task(_embed_in_background(book_id))


@router.delete("/{book_id}/archetypes/{archetype_id}", status_code=204)
async def detach_archetype(book_id: int, archetype_id: int, db: AsyncSession = Depends(get_db)):
    removed = await crud.book.detach_archetype(db, book_id, archetype_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Book-archetype association not found")
    count = await _trope_count(db, book_id)
    if count >= TROPE_THRESHOLD:
        asyncio.create_task(_embed_in_background(book_id))


@router.post("/{book_id}/genres", status_code=204)
async def attach_genre(
    book_id: int, data: BookGenreAttach, db: AsyncSession = Depends(get_db)
):
    book = await crud.book.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await crud.book.attach_genre(db, book_id, data)
    count = await _trope_count(db, book_id)
    if count >= TROPE_THRESHOLD:
        asyncio.create_task(_embed_in_background(book_id))


@router.delete("/{book_id}/genres/{genre_id}", status_code=204)
async def detach_genre(book_id: int, genre_id: int, db: AsyncSession = Depends(get_db)):
    removed = await crud.book.detach_genre(db, book_id, genre_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Book-genre association not found")
    count = await _trope_count(db, book_id)
    if count >= TROPE_THRESHOLD:
        asyncio.create_task(_embed_in_background(book_id))


@router.post("/{book_id}/book-types", status_code=204)
async def attach_book_type(
    book_id: int, data: BookTypeAttach, db: AsyncSession = Depends(get_db)
):
    book = await crud.book.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await crud.book.attach_book_type(db, book_id, data)


@router.delete("/{book_id}/book-types/{book_type_id}", status_code=204)
async def detach_book_type(book_id: int, book_type_id: int, db: AsyncSession = Depends(get_db)):
    removed = await crud.book.detach_book_type(db, book_id, book_type_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Book-type association not found")


@router.post("/{book_id}/tones", status_code=204)
async def attach_tone(
    book_id: int, data: BookToneAttach, db: AsyncSession = Depends(get_db)
):
    book = await crud.book.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await crud.book.attach_tone(db, book_id, data)
    count = await _trope_count(db, book_id)
    if count >= TROPE_THRESHOLD:
        asyncio.create_task(_embed_in_background(book_id))


@router.delete("/{book_id}/tones/{tone_id}", status_code=204)
async def detach_tone(book_id: int, tone_id: int, db: AsyncSession = Depends(get_db)):
    removed = await crud.book.detach_tone(db, book_id, tone_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Book-tone association not found")
    count = await _trope_count(db, book_id)
    if count >= TROPE_THRESHOLD:
        asyncio.create_task(_embed_in_background(book_id))
