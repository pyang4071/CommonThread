from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.series import Series
from app.schemas.series import SeriesCreate


async def get_by_id(db: AsyncSession, series_id: int) -> Series | None:
    return await db.get(Series, series_id)


async def get_by_name(db: AsyncSession, name: str) -> Series | None:
    result = await db.execute(select(Series).where(Series.name == name))
    return result.scalar_one_or_none()


async def get_or_create(db: AsyncSession, name: str) -> Series:
    series = await get_by_name(db, name)
    if not series:
        series = Series(name=name)
        db.add(series)
        await db.flush()
    return series


async def list_series(db: AsyncSession) -> list[Series]:
    result = await db.execute(select(Series).order_by(Series.name))
    return list(result.scalars().all())


async def create_series(db: AsyncSession, data: SeriesCreate) -> Series:
    series = Series(name=data.name, description=data.description)
    db.add(series)
    await db.commit()
    await db.refresh(series)
    return series


async def update_series(db: AsyncSession, series: Series, data: SeriesCreate) -> Series:
    series.name = data.name
    series.description = data.description
    await db.commit()
    await db.refresh(series)
    return series


async def delete_series(db: AsyncSession, series: Series) -> None:
    await db.delete(series)
    await db.commit()
