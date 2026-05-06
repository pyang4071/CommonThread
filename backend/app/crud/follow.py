"""CRUD helpers for the user_follows social graph."""

import uuid
from datetime import datetime

from sqlalchemy import desc, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.book_rating import BookRating
from app.models.reading_status import ReadingStatus
from app.models.user import AppUser
from app.models.user_follow import UserFollow
from app.schemas.user import FeedEntry, UserPublicProfile


def _is_public(model: type[AppUser] = AppUser):
    """SQLAlchemy clause: preferences->profile_public is true or absent (default public).

    Uses string comparison instead of CAST to avoid a PostgreSQL error when the
    stored value is JSON null (which ->> serialises as the literal string 'null',
    not a SQL NULL, and cannot be cast to boolean).
    """
    return func.coalesce(
        model.preferences["profile_public"].as_string() != "false",
        true(),
    )


async def follow(db: AsyncSession, follower_id: uuid.UUID, followee_id: uuid.UUID) -> None:
    """Create a follow relationship.  No-ops if it already exists."""
    existing = await db.get(UserFollow, (follower_id, followee_id))
    if existing:
        return
    db.add(UserFollow(follower_id=follower_id, followee_id=followee_id))
    await db.commit()


async def unfollow(db: AsyncSession, follower_id: uuid.UUID, followee_id: uuid.UUID) -> None:
    """Remove a follow relationship if it exists."""
    existing = await db.get(UserFollow, (follower_id, followee_id))
    if existing:
        await db.delete(existing)
        await db.commit()


async def is_following(db: AsyncSession, follower_id: uuid.UUID, followee_id: uuid.UUID) -> bool:
    return await db.get(UserFollow, (follower_id, followee_id)) is not None


async def get_following(db: AsyncSession, user_id: uuid.UUID) -> list[AppUser]:
    """Return AppUser objects that *user_id* follows."""
    result = await db.execute(
        select(AppUser)
        .join(UserFollow, UserFollow.followee_id == AppUser.user_id)
        .where(UserFollow.follower_id == user_id)
        .order_by(AppUser.name)
    )
    return list(result.scalars().all())


async def get_followers(db: AsyncSession, user_id: uuid.UUID) -> list[AppUser]:
    """Return AppUser objects who follow *user_id*."""
    result = await db.execute(
        select(AppUser)
        .join(UserFollow, UserFollow.follower_id == AppUser.user_id)
        .where(UserFollow.followee_id == user_id)
        .order_by(AppUser.name)
    )
    return list(result.scalars().all())


async def search_users(db: AsyncSession, query: str, requesting_user_id: uuid.UUID) -> list[AppUser]:
    """Search for public-profile users by name or email (excludes the caller)."""
    like = f"%{query.lower()}%"
    result = await db.execute(
        select(AppUser)
        .where(
            AppUser.user_id != requesting_user_id,
            _is_public(),
            (AppUser.name.ilike(like)) | (AppUser.email.ilike(like)),
        )
        .limit(20)
    )
    return list(result.scalars().all())


async def get_feed(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 30,
    before: datetime | None = None,
) -> list[FeedEntry]:
    """Pull-model activity feed: recent shelf + rating events from followed users.

    Cursor-based pagination: pass `before` (the occurred_at of the last entry
    from the previous page) to fetch the next page of older events.
    """
    shelf_filters = [UserFollow.follower_id == user_id]
    if before is not None:
        shelf_filters.append(ReadingStatus.updated_at < before)

    shelf_rows = await db.execute(
        select(ReadingStatus, AppUser, Book)
        .join(AppUser, AppUser.user_id == ReadingStatus.user_id)
        .join(Book, Book.book_id == ReadingStatus.book_id)
        .join(UserFollow, UserFollow.followee_id == ReadingStatus.user_id)
        .where(*shelf_filters)
        .order_by(desc(ReadingStatus.updated_at))
        .limit(limit)
    )

    entries: list[FeedEntry] = []
    for rs, user, book in shelf_rows:
        entries.append(
            FeedEntry(
                user=UserPublicProfile.model_validate(user),
                book_id=book.book_id,
                book_title=book.title,
                book_cover_url=book.cover_url,
                event_type=rs.status,
                rating=None,
                occurred_at=rs.updated_at.replace(tzinfo=None),
            )
        )

    rating_filters = [UserFollow.follower_id == user_id]
    if before is not None:
        rating_filters.append(BookRating.updated_at < before)

    rating_rows = await db.execute(
        select(BookRating, AppUser, Book)
        .join(AppUser, AppUser.user_id == BookRating.user_id)
        .join(Book, Book.book_id == BookRating.book_id)
        .join(UserFollow, UserFollow.followee_id == BookRating.user_id)
        .where(*rating_filters)
        .order_by(desc(BookRating.updated_at))
        .limit(limit)
    )

    for rating, user, book in rating_rows:
        has_review = bool(rating.review_text and rating.review_text.strip())
        entries.append(
            FeedEntry(
                user=UserPublicProfile.model_validate(user),
                book_id=book.book_id,
                book_title=book.title,
                book_cover_url=book.cover_url,
                event_type="review" if has_review else "rating",
                rating=rating.rating,
                review_text=rating.review_text if has_review else None,
                occurred_at=rating.updated_at.replace(tzinfo=None),
            )
        )

    entries.sort(key=lambda e: e.occurred_at, reverse=True)
    return entries[:limit]


async def get_user_shelf(db: AsyncSession, target_user_id: uuid.UUID) -> list[ReadingStatus]:
    """Return another user's shelf (caller must already have checked visibility)."""
    result = await db.execute(
        select(ReadingStatus)
        .where(ReadingStatus.user_id == target_user_id)
        .order_by(desc(ReadingStatus.updated_at))
    )
    return list(result.scalars().all())
