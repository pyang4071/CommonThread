import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.archetype import Archetype


class UserBookArchetype(Base):
    __tablename__ = "user_book_archetypes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_users.user_id", ondelete="CASCADE"), primary_key=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.book_id", ondelete="CASCADE"), primary_key=True
    )
    archetype_id: Mapped[int] = mapped_column(
        ForeignKey("archetypes.archetype_id", ondelete="CASCADE"), primary_key=True
    )
    importance: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    archetype: Mapped["Archetype"] = relationship(lazy="joined")

    __table_args__ = (
        CheckConstraint(
            "importance >= 1 AND importance <= 10", name="ck_user_book_archetypes_importance"
        ),
    )
