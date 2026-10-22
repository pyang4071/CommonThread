from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.book import Book


class BookType(Base):
    __tablename__ = "book_types"

    book_type_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    books: Mapped[list["Book"]] = relationship(
        secondary="book_book_types", back_populates="book_types"
    )

    __table_args__ = (Index("ix_book_types_name", "name"),)
