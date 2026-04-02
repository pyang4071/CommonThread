from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.character_dna import CharacterDNA


class Archetype(Base):
    __tablename__ = "archetypes"

    archetype_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]

    character_dna: Mapped[list["CharacterDNA"]] = relationship(back_populates="archetype")
