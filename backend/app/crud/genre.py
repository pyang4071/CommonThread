from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.genre import Genre
from app.schemas.genre import GenreCreate, GenreUpdate


async def list_genres(db: AsyncSession) -> list[Genre]:
    result = await db.execute(select(Genre).order_by(Genre.name))
    return list(result.scalars().all())


async def get_genre(db: AsyncSession, genre_id: int) -> Genre | None:
    return await db.get(Genre, genre_id)


async def create_genre(db: AsyncSession, data: GenreCreate) -> Genre:
    genre = Genre(**data.model_dump())
    db.add(genre)
    await db.commit()
    await db.refresh(genre)
    return genre


async def update_genre(db: AsyncSession, genre: Genre, data: GenreUpdate) -> Genre:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(genre, field, value)
    await db.commit()
    await db.refresh(genre)
    return genre


async def delete_genre(db: AsyncSession, genre: Genre) -> None:
    await db.delete(genre)
    await db.commit()
