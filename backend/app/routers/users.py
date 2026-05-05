import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.auth import get_current_user
from app.database.engine import get_db
from app.models.user import AppUser
from app.schemas.book import BookRead
from app.crud import reading_status as crud_status
from app.schemas.reading_status import ShelfEntry
from app.schemas.user import FeedEntry, FollowStatus, UserPublicProfile, UserRead, UserUpdate
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


# ── Social / Follow endpoints ─────────────────────────────────────────────────

@router.get("/search", response_model=list[UserPublicProfile])
async def search_users(
    q: str = Query(min_length=1),
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search for other users by name or email."""
    return await crud.follow.search_users(db, q, current_user.user_id)


@router.get("/me/following", response_model=list[UserPublicProfile])
async def get_following(
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.follow.get_following(db, current_user.user_id)


@router.get("/me/followers", response_model=list[UserPublicProfile])
async def get_followers(
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.follow.get_followers(db, current_user.user_id)


@router.post("/me/following/{user_id}", response_model=FollowStatus, status_code=200)
async def follow_user(
    user_id: uuid.UUID,
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    target = await crud.user.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await crud.follow.follow(db, current_user.user_id, user_id)
    return FollowStatus(following=True)


@router.delete("/me/following/{user_id}", response_model=FollowStatus, status_code=200)
async def unfollow_user(
    user_id: uuid.UUID,
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await crud.follow.unfollow(db, current_user.user_id, user_id)
    return FollowStatus(following=False)


@router.get("/me/following/{user_id}/status", response_model=FollowStatus)
async def follow_status(
    user_id: uuid.UUID,
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    following = await crud.follow.is_following(db, current_user.user_id, user_id)
    return FollowStatus(following=following)


@router.get("/me/feed", response_model=list[FeedEntry])
async def get_feed(
    limit: int = Query(default=30, le=100),
    before: datetime | None = Query(default=None),
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Activity feed of books recently read/rated by followed users.

    Pass `before` (ISO datetime of the last entry) to load the next page.
    """
    return await crud.follow.get_feed(db, current_user.user_id, limit, before)


@router.get("/{user_id}/profile", response_model=UserPublicProfile)
async def get_user_profile(
    user_id: uuid.UUID,
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await crud.user.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    prefs = target.preferences or {}
    if not prefs.get("profile_public", True):
        # Only visible to followers
        is_following = await crud.follow.is_following(db, current_user.user_id, user_id)
        if not is_following and current_user.user_id != user_id:
            raise HTTPException(status_code=403, detail="This profile is private")
    return UserPublicProfile.model_validate(target)


@router.get("/{user_id}/shelf", response_model=list[ShelfEntry])
async def get_user_shelf(
    user_id: uuid.UUID,
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """View another user's shelf (public profiles only, or own shelf)."""
    if user_id != current_user.user_id:
        target = await crud.user.get_by_id(db, user_id)
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        prefs = target.preferences or {}
        if not prefs.get("profile_public", True):
            following = await crud.follow.is_following(db, current_user.user_id, user_id)
            if not following:
                raise HTTPException(status_code=403, detail="This profile is private")
    statuses = await crud_status.list_my_shelf(db, user_id)
    return [
        ShelfEntry(book=s.book, status=s.status, created_at=s.created_at, updated_at=s.updated_at)
        for s in statuses
    ]
