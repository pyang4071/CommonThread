import uuid
from datetime import datetime, timezone, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reading_status import ReadingStatus

VALID_STATUSES = frozenset({"want_to_read", "currently_reading", "read"})


async def get_status(db: AsyncSession, user_id: uuid.UUID, book_id: int) -> ReadingStatus | None:
    result = await db.execute(
        select(ReadingStatus).where(
            ReadingStatus.user_id == user_id,
            ReadingStatus.book_id == book_id,
        )
    )
    return result.scalar_one_or_none()


async def upsert_status(
    db: AsyncSession, user_id: uuid.UUID, book_id: int, status: str
) -> ReadingStatus:
    entry = await get_status(db, user_id, book_id)
    now = datetime.now(UTC).replace(tzinfo=None)
    if entry:
        entry.status = status
        entry.updated_at = now
    else:
        entry = ReadingStatus(user_id=user_id, book_id=book_id, status=status, updated_at=now)
        db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def delete_status(db: AsyncSession, user_id: uuid.UUID, book_id: int) -> bool:
    entry = await get_status(db, user_id, book_id)
    if not entry:
        return False
    await db.delete(entry)
    await db.commit()
    return True


async def list_my_shelf(db: AsyncSession, user_id: uuid.UUID) -> list[ReadingStatus]:
    result = await db.execute(
        select(ReadingStatus)
        .where(ReadingStatus.user_id == user_id)
        .order_by(ReadingStatus.updated_at.desc())
    )
    return list(result.scalars().all())
