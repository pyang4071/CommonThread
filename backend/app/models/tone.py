from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.book import Book


class Tone(Base):
    __tablename__ = "tones"

    tone_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    books: Mapped[list[Book]] = relationship(secondary="book_tones", back_populates="tones")

    __table_args__ = (UniqueConstraint("name", name="uq_tones_name"),)
