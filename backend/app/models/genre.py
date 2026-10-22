from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.book import Book


class Genre(Base):
    __tablename__ = "genres"

    genre_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    books: Mapped[list["Book"]] = relationship(
        secondary="book_genres", back_populates="genres"
    )

    __table_args__ = (Index("ix_genres_name", "name"),)
