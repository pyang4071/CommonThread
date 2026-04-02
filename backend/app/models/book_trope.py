from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.trope import Trope


class BookTrope(Base):
    __tablename__ = "book_tropes"

    book_id: Mapped[int] = mapped_column(ForeignKey("books.book_id"), primary_key=True)
    trope_id: Mapped[int] = mapped_column(ForeignKey("tropes.trope_id"), primary_key=True)
    weight: Mapped[float]

    book: Mapped["Book"] = relationship(back_populates="book_tropes")
    trope: Mapped["Trope"] = relationship(back_populates="book_tropes")

    __table_args__ = (
        CheckConstraint("weight >= 0.0 AND weight <= 1.0", name="ck_book_tropes_weight"),
    )
