from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.crud import dislike as crud_dislike
from app.database import get_db
from app.models.user import AppUser

router = APIRouter(prefix="/books", tags=["dislikes"])


class DislikeStatus(BaseModel):
    disliked: bool


@router.get("/{book_id}/dislike", response_model=DislikeStatus)
async def get_dislike_status(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    existing = await crud_dislike.get_dislike(db, current_user.user_id, book_id)
    return DislikeStatus(disliked=existing is not None)


@router.put("/{book_id}/dislike", status_code=204)
async def set_dislike(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    await crud_dislike.set_dislike(db, current_user.user_id, book_id)


@router.delete("/{book_id}/dislike", status_code=204)
async def remove_dislike(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    removed = await crud_dislike.remove_dislike(db, current_user.user_id, book_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Dislike not found")
