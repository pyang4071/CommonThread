from typing import TYPE_CHECKING

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.book_trope import BookTrope


class Trope(Base):
    __tablename__ = "tropes"

    trope_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]
    category: Mapped[str]

    book_tropes: Mapped[list["BookTrope"]] = relationship(back_populates="trope")

    __table_args__ = (Index("ix_tropes_category", "category"),)
