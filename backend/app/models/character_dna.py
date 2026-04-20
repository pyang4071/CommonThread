from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.archetype import Archetype
    from app.models.book import Book


class CharacterDNA(Base):
    __tablename__ = "character_dna"

    book_id: Mapped[int] = mapped_column(ForeignKey("books.book_id"), primary_key=True)
    archetype_id: Mapped[int] = mapped_column(
        ForeignKey("archetypes.archetype_id"), primary_key=True
    )
    importance: Mapped[int]
    is_crowd_promoted: Mapped[bool] = mapped_column(default=False, server_default="FALSE")

    book: Mapped["Book"] = relationship(back_populates="character_dna")
    archetype: Mapped["Archetype"] = relationship(back_populates="character_dna")

    __table_args__ = (
        CheckConstraint(
            "importance >= 1 AND importance <= 10", name="ck_character_dna_importance"
        ),
    )
