import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dislike import BookDislike


async def get_dislike(db: AsyncSession, user_id: uuid.UUID, book_id: int) -> BookDislike | None:
    result = await db.execute(
        select(BookDislike).where(
            BookDislike.user_id == user_id, BookDislike.book_id == book_id
        )
    )
    return result.scalar_one_or_none()


async def set_dislike(db: AsyncSession, user_id: uuid.UUID, book_id: int) -> BookDislike:
    existing = await get_dislike(db, user_id, book_id)
    if existing:
        return existing
    dislike = BookDislike(user_id=user_id, book_id=book_id)
    db.add(dislike)
    await db.commit()
    await db.refresh(dislike)
    return dislike


async def remove_dislike(db: AsyncSession, user_id: uuid.UUID, book_id: int) -> bool:
    existing = await get_dislike(db, user_id, book_id)
    if not existing:
        return False
    await db.delete(existing)
    await db.commit()
    return True


async def get_user_disliked_ids(db: AsyncSession, user_id: uuid.UUID) -> list[int]:
    result = await db.execute(
        select(BookDislike.book_id).where(BookDislike.user_id == user_id)
    )
    return list(result.scalars().all())
