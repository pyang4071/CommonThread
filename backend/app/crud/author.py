from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.author import Author


async def get_by_name(db: AsyncSession, name: str) -> Author | None:
    result = await db.execute(select(Author).where(Author.name == name))
    return result.scalar_one_or_none()


async def get_or_create(db: AsyncSession, name: str) -> Author:
    author = await get_by_name(db, name)
    if not author:
        author = Author(name=name)
        db.add(author)
        await db.flush()  # get author_id without committing
    return author


async def list_authors(db: AsyncSession) -> list[Author]:
    result = await db.execute(select(Author).order_by(Author.name))
    return list(result.scalars().all())
