from typing import TYPE_CHECKING

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.book import Book


class Author(Base):
    __tablename__ = "authors"

    author_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    bio: Mapped[str | None] = mapped_column(nullable=True)

    books: Mapped[list["Book"]] = relationship(back_populates="author")

    __table_args__ = (Index("ix_authors_name", "name"),)
