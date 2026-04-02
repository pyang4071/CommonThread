from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book_trope import BookTrope
from app.models.trope import Trope
from app.schemas.trope import TropeCreate, TropeUpdate


async def list_categories(db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(Trope.category).distinct().order_by(Trope.category)
    )
    return list(result.scalars().all())


async def get_trope(db: AsyncSession, trope_id: int) -> Trope | None:
    return await db.get(Trope, trope_id)


async def list_tropes(
    db: AsyncSession, skip: int = 0, limit: int = 20, category: str | None = None
) -> list[Trope]:
    stmt = select(Trope).offset(skip).limit(limit)
    if category:
        stmt = stmt.where(Trope.category == category)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_tropes_by_category(db: AsyncSession, category: str) -> list[Trope]:
    result = await db.execute(select(Trope).where(Trope.category == category))
    return list(result.scalars().all())


async def create_trope(db: AsyncSession, data: TropeCreate) -> Trope:
    trope = Trope(**data.model_dump())
    db.add(trope)
    await db.commit()
    await db.refresh(trope)
    return trope


async def update_trope(db: AsyncSession, trope: Trope, data: TropeUpdate) -> Trope:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(trope, field, value)
    await db.commit()
    await db.refresh(trope)
    return trope


async def get_affected_book_ids(db: AsyncSession, trope_id: int) -> list[int]:
    result = await db.execute(
        select(BookTrope.book_id).where(BookTrope.trope_id == trope_id)
    )
    return list(result.scalars().all())


async def delete_trope(db: AsyncSession, trope: Trope) -> None:
    await db.delete(trope)
    await db.commit()
