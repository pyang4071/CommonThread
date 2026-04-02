import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.book_rating import BookRating


async def get_rating(db: AsyncSession, user_id: uuid.UUID, book_id: int) -> BookRating | None:
    result = await db.execute(
        select(BookRating)
        .where(BookRating.user_id == user_id, BookRating.book_id == book_id)
    )
    return result.scalar_one_or_none()


async def upsert_rating(
    db: AsyncSession,
    user_id: uuid.UUID,
    book_id: int,
    rating: int,
    review_text: str | None = None,
) -> BookRating:
    existing = await get_rating(db, user_id, book_id)
    if existing:
        existing.rating = rating
        if review_text is not None:
            existing.review_text = review_text
    else:
        existing = BookRating(
            user_id=user_id, book_id=book_id, rating=rating, review_text=review_text
        )
        db.add(existing)
    await db.commit()
    await db.refresh(existing)
    return existing


async def delete_rating(db: AsyncSession, user_id: uuid.UUID, book_id: int) -> bool:
    existing = await get_rating(db, user_id, book_id)
    if not existing:
        return False
    await db.delete(existing)
    await db.commit()
    return True


async def list_my_ratings(db: AsyncSession, user_id: uuid.UUID) -> list[BookRating]:
    result = await db.execute(
        select(BookRating).where(BookRating.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_book_reviews(db: AsyncSession, book_id: int) -> list[BookRating]:
    result = await db.execute(
        select(BookRating)
        .where(BookRating.book_id == book_id, BookRating.review_text.is_not(None))
        .options(selectinload(BookRating.user))
        .order_by(BookRating.created_at.desc())
    )
    return list(result.scalars().all())
