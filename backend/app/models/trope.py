from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, func
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
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    book_tropes: Mapped[list["BookTrope"]] = relationship(back_populates="trope")

    __table_args__ = (Index("ix_tropes_category", "category"),)
