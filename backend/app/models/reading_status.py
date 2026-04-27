import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.book import Book


class ReadingStatus(Base):
    __tablename__ = "reading_statuses"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_users.user_id", ondelete="CASCADE"), primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.book_id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    book: Mapped["Book"] = relationship(lazy="joined")
