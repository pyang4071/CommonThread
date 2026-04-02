from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book_type import BookType
from app.schemas.book_type import BookTypeCreate, BookTypeUpdate


async def list_book_types(db: AsyncSession) -> list[BookType]:
    result = await db.execute(select(BookType).order_by(BookType.name))
    return list(result.scalars().all())


async def get_book_type(db: AsyncSession, book_type_id: int) -> BookType | None:
    return await db.get(BookType, book_type_id)


async def create_book_type(db: AsyncSession, data: BookTypeCreate) -> BookType:
    book_type = BookType(**data.model_dump())
    db.add(book_type)
    await db.commit()
    await db.refresh(book_type)
    return book_type


async def update_book_type(db: AsyncSession, book_type: BookType, data: BookTypeUpdate) -> BookType:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(book_type, field, value)
    await db.commit()
    await db.refresh(book_type)
    return book_type


async def delete_book_type(db: AsyncSession, book_type: BookType) -> None:
    await db.delete(book_type)
    await db.commit()
