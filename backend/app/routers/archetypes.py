import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.auth import require_admin
from app.database import get_db
from app.database.engine import AsyncSessionLocal
from app.models.book import Book
from app.models.character_dna import CharacterDNA
from app.models.user import AppUser
from app.schemas.archetype import ArchetypeCreate, ArchetypeRead, ArchetypeUpdate
from app.schemas.book import BookRead
from app.services.embedding import embed_book
from sqlalchemy import select

router = APIRouter(prefix="/archetypes", tags=["archetypes"])


@router.get("/", response_model=list[ArchetypeRead])
async def list_archetypes(
    skip: int = 0, limit: int = 500, db: AsyncSession = Depends(get_db)
):
    return await crud.archetype.list_archetypes(db, skip=skip, limit=limit)


class BookWithImportance(BookRead):
    importance: int


@router.get("/{archetype_id}/books", response_model=list[BookWithImportance])
async def books_for_archetype(archetype_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Book, CharacterDNA.importance)
        .join(CharacterDNA, Book.book_id == CharacterDNA.book_id)
        .where(CharacterDNA.archetype_id == archetype_id)
        .order_by(CharacterDNA.importance.desc())
    )
    rows = result.all()
    return [
        BookWithImportance(**BookRead.model_validate(row.Book).model_dump(), importance=row.importance)
        for row in rows
    ]


@router.post("/", response_model=ArchetypeRead, status_code=201)
async def create_archetype(data: ArchetypeCreate, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    return await crud.archetype.create_archetype(db, data)


@router.get("/{archetype_id}", response_model=ArchetypeRead)
async def get_archetype(archetype_id: int, db: AsyncSession = Depends(get_db)):
    archetype = await crud.archetype.get_archetype(db, archetype_id)
    if not archetype:
        raise HTTPException(status_code=404, detail="Archetype not found")
    return archetype


@router.put("/{archetype_id}", response_model=ArchetypeRead)
async def update_archetype(
    archetype_id: int, data: ArchetypeUpdate, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)
):
    archetype = await crud.archetype.get_archetype(db, archetype_id)
    if not archetype:
        raise HTTPException(status_code=404, detail="Archetype not found")
    return await crud.archetype.update_archetype(db, archetype, data)


async def _reembed(book_ids: list[int]) -> None:
    for book_id in book_ids:
        async with AsyncSessionLocal() as db:
            await embed_book(book_id, db)


@router.delete("/{archetype_id}", status_code=204)
async def delete_archetype(archetype_id: int, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    archetype = await crud.archetype.get_archetype(db, archetype_id)
    if not archetype:
        raise HTTPException(status_code=404, detail="Archetype not found")
    affected = await crud.archetype.get_affected_book_ids(db, archetype_id)
    await crud.archetype.delete_archetype(db, archetype)
    if affected:
        asyncio.get_event_loop().create_task(_reembed(affected))
