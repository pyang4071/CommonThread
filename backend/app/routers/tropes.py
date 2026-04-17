import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.auth import require_admin
from app.database import get_db
from app.database.engine import AsyncSessionLocal
from app.models.book import Book
from app.models.book_trope import BookTrope
from app.models.user import AppUser
from app.schemas.book import BookRead
from app.schemas.trope import TropeCreate, TropeRead, TropeUpdate
from app.services.embedding import embed_book
from sqlalchemy import select

router = APIRouter(prefix="/tropes", tags=["tropes"])


@router.get("/categories", response_model=list[str])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await crud.trope.list_categories(db)


@router.get("/", response_model=list[TropeRead])
async def list_tropes(
    skip: int = 0,
    limit: int = 500,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await crud.trope.list_tropes(db, skip=skip, limit=limit, category=category)


class BookWithWeight(BookRead):
    weight: float


@router.get("/{trope_id}/books", response_model=list[BookWithWeight])
async def books_for_trope(trope_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Book, BookTrope.weight)
        .join(BookTrope, Book.book_id == BookTrope.book_id)
        .where(BookTrope.trope_id == trope_id)
        .order_by(BookTrope.weight.desc())
    )
    rows = result.all()
    return [
        BookWithWeight(**BookRead.model_validate(row.Book).model_dump(), weight=row.weight)
        for row in rows
    ]


@router.post("/", response_model=TropeRead, status_code=201)
async def create_trope(data: TropeCreate, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    return await crud.trope.create_trope(db, data)


@router.get("/by-category/{category}", response_model=list[TropeRead])
async def tropes_by_category(category: str, db: AsyncSession = Depends(get_db)):
    return await crud.trope.list_tropes_by_category(db, category)


@router.get("/{trope_id}", response_model=TropeRead)
async def get_trope(trope_id: int, db: AsyncSession = Depends(get_db)):
    trope = await crud.trope.get_trope(db, trope_id)
    if not trope:
        raise HTTPException(status_code=404, detail="Trope not found")
    return trope


@router.put("/{trope_id}", response_model=TropeRead)
async def update_trope(trope_id: int, data: TropeUpdate, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    trope = await crud.trope.get_trope(db, trope_id)
    if not trope:
        raise HTTPException(status_code=404, detail="Trope not found")
    return await crud.trope.update_trope(db, trope, data)


async def _reembed(book_ids: list[int]) -> None:
    for book_id in book_ids:
        async with AsyncSessionLocal() as db:
            await embed_book(book_id, db)


@router.delete("/{trope_id}", status_code=204)
async def delete_trope(trope_id: int, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    trope = await crud.trope.get_trope(db, trope_id)
    if not trope:
        raise HTTPException(status_code=404, detail="Trope not found")
    affected = await crud.trope.get_affected_book_ids(db, trope_id)
    await crud.trope.delete_trope(db, trope)
    if affected:
        asyncio.get_event_loop().create_task(_reembed(affected))
