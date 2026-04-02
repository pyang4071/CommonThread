import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.auth import get_optional_user
from app.database import get_db
from app.database.engine import AsyncSessionLocal
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
from app.services.embedding import embed_book

router = APIRouter(prefix="/books", tags=["books"])
logger = logging.getLogger(__name__)


async def _embed_in_background(book_id: int, max_attempts: int = 3) -> None:
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
            await asyncio.sleep(2 ** attempt)  # 1 s, 2 s between retries

    # All attempts exhausted — mark as failed so the admin queue can re-try later
    async with AsyncSessionLocal() as db:
        book = await db.get(Book, book_id)
        if book:
            book.embedding_status = "failed"
            await db.commit()


async def _fetch_cover_in_background(book_id: int, isbn: str | None, title: str, author: str) -> None:
    url = await fetch_cover_url(isbn, title, author)
    if not url:
        return
    async with AsyncSessionLocal() as db:
        book = await db.get(Book, book_id)
        if book and not book.cover_url:
            book.cover_url = url
            await db.commit()


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
    shelf_status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser | None = Depends(get_optional_user),
):
    return await crud.book.list_books(
        db, skip=skip, limit=limit, search=search,
        categories=categories or None,
        genre_ids=genre_ids or None,
        book_type_ids=book_type_ids or None,
        pacing=pacing,
        tone_ids=tone_ids or None,
        exclude_trope_ids=exclude_trope_ids or None,
        exclude_archetype_ids=exclude_archetype_ids or None,
        shelf_status=shelf_status,
        user_id=current_user.user_id if current_user else None,
    )


@router.post("/", response_model=BookRead, status_code=201)
async def create_book(data: BookCreate, db: AsyncSession = Depends(get_db)):
    book = await crud.book.create_book(db, data)
    asyncio.create_task(_embed_in_background(book.book_id))
    asyncio.create_task(_fetch_cover_in_background(book.book_id, book.isbn, book.title, book.author.name))
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
    asyncio.create_task(_embed_in_background(book_id))
    return updated


@router.get("/{book_id}/series", response_model=list[BookRead])
async def get_series(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await crud.book.get_book(db, book_id)
    if not book or not book.series_name:
        return []
    return await crud.book.get_books_in_series(db, book.series_name)


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
    asyncio.create_task(_embed_in_background(book_id))


@router.delete("/{book_id}/tropes/{trope_id}", status_code=204)
async def detach_trope(book_id: int, trope_id: int, db: AsyncSession = Depends(get_db)):
    removed = await crud.book.detach_trope(db, book_id, trope_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Book-trope association not found")
    asyncio.create_task(_embed_in_background(book_id))


@router.post("/{book_id}/archetypes", status_code=204)
async def attach_archetype(
    book_id: int, data: CharacterDNAAttach, db: AsyncSession = Depends(get_db)
):
    book = await crud.book.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await crud.book.attach_archetype(db, book_id, data)
    asyncio.create_task(_embed_in_background(book_id))


@router.delete("/{book_id}/archetypes/{archetype_id}", status_code=204)
async def detach_archetype(book_id: int, archetype_id: int, db: AsyncSession = Depends(get_db)):
    removed = await crud.book.detach_archetype(db, book_id, archetype_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Book-archetype association not found")
    asyncio.create_task(_embed_in_background(book_id))


@router.post("/{book_id}/genres", status_code=204)
async def attach_genre(
    book_id: int, data: BookGenreAttach, db: AsyncSession = Depends(get_db)
):
    book = await crud.book.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await crud.book.attach_genre(db, book_id, data)
    asyncio.create_task(_embed_in_background(book_id))


@router.delete("/{book_id}/genres/{genre_id}", status_code=204)
async def detach_genre(book_id: int, genre_id: int, db: AsyncSession = Depends(get_db)):
    removed = await crud.book.detach_genre(db, book_id, genre_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Book-genre association not found")
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
    asyncio.create_task(_embed_in_background(book_id))


@router.delete("/{book_id}/tones/{tone_id}", status_code=204)
async def detach_tone(book_id: int, tone_id: int, db: AsyncSession = Depends(get_db)):
    removed = await crud.book.detach_tone(db, book_id, tone_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Book-tone association not found")
    asyncio.create_task(_embed_in_background(book_id))
