import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import AppUser


class BookRating(Base):
    __tablename__ = "book_ratings"

    rating_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_users.user_id", ondelete="CASCADE"))
    book_id: Mapped[int] = mapped_column(ForeignKey("books.book_id", ondelete="CASCADE"))
    rating: Mapped[int]
    review_text: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    user: Mapped["AppUser"] = relationship()
    book: Mapped["Book"] = relationship()

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_book_ratings_rating"),
        UniqueConstraint("user_id", "book_id", name="uq_book_ratings_user_book"),
    )
