from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.auth import get_current_user
from app.database import get_db
from app.models.user import AppUser
from app.schemas.user_tags import (
    UserArchetypeAttach,
    UserArchetypeRead,
    UserTagsRead,
    UserTropeAttach,
    UserTropeRead,
)

router = APIRouter(prefix="/books", tags=["user-tags"])


@router.get("/{book_id}/my-tags", response_model=UserTagsRead)
async def get_my_tags(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    book = await crud.book.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    tropes, archetypes = await crud.user_tags.get_user_tags(db, current_user.user_id, book_id)
    return UserTagsRead(
        tropes=[UserTropeRead.model_validate(t) for t in tropes],
        archetypes=[UserArchetypeRead.model_validate(a) for a in archetypes],
    )


@router.post("/{book_id}/my-tags/tropes", response_model=UserTropeRead, status_code=201)
async def add_my_trope(
    book_id: int,
    data: UserTropeAttach,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    book = await crud.book.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    entry = await crud.user_tags.upsert_user_trope(db, current_user.user_id, book_id, data)
    return UserTropeRead.model_validate(entry)


@router.delete("/{book_id}/my-tags/tropes/{trope_id}", status_code=204)
async def remove_my_trope(
    book_id: int,
    trope_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    removed = await crud.user_tags.remove_user_trope(db, current_user.user_id, book_id, trope_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Tag not found")


@router.post("/{book_id}/my-tags/archetypes", response_model=UserArchetypeRead, status_code=201)
async def add_my_archetype(
    book_id: int,
    data: UserArchetypeAttach,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    book = await crud.book.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    entry = await crud.user_tags.upsert_user_archetype(
        db, current_user.user_id, book_id, data
    )
    return UserArchetypeRead.model_validate(entry)


@router.delete("/{book_id}/my-tags/archetypes/{archetype_id}", status_code=204)
async def remove_my_archetype(
    book_id: int,
    archetype_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    removed = await crud.user_tags.remove_user_archetype(
        db, current_user.user_id, book_id, archetype_id
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Tag not found")
