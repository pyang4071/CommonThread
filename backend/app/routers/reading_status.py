from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.crud import reading_status as crud_status
from app.database import get_db
from app.models.user import AppUser
from app.schemas.reading_status import ReadingStatusRead, ReadingStatusUpsert, ShelfEntry

router = APIRouter(prefix="/books", tags=["reading-status"])
shelf_router = APIRouter(prefix="/shelf", tags=["reading-status"])

VALID = {"want_to_read", "currently_reading", "read"}


@router.get("/{book_id}/reading-status", response_model=ReadingStatusRead | None)
async def get_reading_status(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await crud_status.get_status(db, current_user.user_id, book_id)


@router.put("/{book_id}/reading-status", response_model=ReadingStatusRead)
async def upsert_reading_status(
    book_id: int,
    data: ReadingStatusUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    if data.status not in VALID:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(VALID)}")
    return await crud_status.upsert_status(db, current_user.user_id, book_id, data.status)


@router.delete("/{book_id}/reading-status", status_code=204)
async def delete_reading_status(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    removed = await crud_status.delete_status(db, current_user.user_id, book_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Reading status not found")


@shelf_router.get("/my", response_model=list[ShelfEntry])
async def get_my_shelf(
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    entries = await crud_status.list_my_shelf(db, current_user.user_id)
    return [
        ShelfEntry(book=e.book, status=e.status, created_at=e.created_at, updated_at=e.updated_at)
        for e in entries
    ]
