from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.auth import get_current_user
from app.database.engine import get_db
from app.models.user import AppUser
from app.schemas.book import BookRead
from app.schemas.user import UserRead, UserUpdate
from app.schemas.user_tags import UserArchetypeRead, UserTropeRead

router = APIRouter(prefix="/users", tags=["users"])


class BookTagsEntry(BaseModel):
    book: BookRead
    tropes: list[UserTropeRead] = []
    archetypes: list[UserArchetypeRead] = []

    model_config = {"from_attributes": True}


@router.get("/me", response_model=UserRead)
async def get_me(current_user: AppUser = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate,
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.user.update(db, current_user, data)


@router.get("/me/tags", response_model=list[BookTagsEntry])
async def get_my_tags(
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await crud.user_tags.get_all_tags_by_book(db, current_user.user_id)
    return [
        BookTagsEntry(
            book=BookRead.model_validate(row["book"]),
            tropes=[UserTropeRead.model_validate(t) for t in row["tropes"]],
            archetypes=[UserArchetypeRead.model_validate(a) for a in row["archetypes"]],
        )
        for row in rows
    ]
