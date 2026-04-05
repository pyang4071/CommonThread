import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.trope import Trope


class UserBookTrope(Base):
    __tablename__ = "user_book_tropes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_users.user_id", ondelete="CASCADE"), primary_key=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.book_id", ondelete="CASCADE"), primary_key=True
    )
    trope_id: Mapped[int] = mapped_column(
        ForeignKey("tropes.trope_id", ondelete="CASCADE"), primary_key=True
    )
    weight: Mapped[float]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    trope: Mapped["Trope"] = relationship(lazy="joined")

    __table_args__ = (
        CheckConstraint("weight >= 0.0 AND weight <= 1.0", name="ck_user_book_tropes_weight"),
    )
