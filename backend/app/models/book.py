from datetime import date, datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.author import Author
    from app.models.book_trope import BookTrope
    from app.models.book_type import BookType
    from app.models.character_dna import CharacterDNA
    from app.models.genre import Genre
    from app.models.series import Series
    from app.models.tone import Tone


class Book(Base):
    __tablename__ = "books"

    book_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.author_id"))
    isbn: Mapped[str | None] = mapped_column(unique=True)
    publication_date: Mapped[date | None]
    description: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    pacing: Mapped[int | None] = mapped_column(nullable=True)
    cover_url: Mapped[str | None] = mapped_column(nullable=True)
    genome_embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    description_embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    embedding_status: Mapped[str] = mapped_column(default="pending", server_default="pending")
    series_id: Mapped[int | None] = mapped_column(
        ForeignKey("series.series_id", ondelete="SET NULL"), nullable=True
    )
    series_position: Mapped[int | None] = mapped_column(nullable=True)

    author: Mapped["Author"] = relationship(back_populates="books", lazy="joined")
    series: Mapped["Series | None"] = relationship(back_populates="books", lazy="joined")
    book_tropes: Mapped[list["BookTrope"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    character_dna: Mapped[list["CharacterDNA"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    genres: Mapped[list["Genre"]] = relationship(
        secondary="book_genres", back_populates="books", lazy="raise"
    )
    book_types: Mapped[list["BookType"]] = relationship(
        secondary="book_book_types", back_populates="books", lazy="raise"
    )
    tones: Mapped[list["Tone"]] = relationship(
        secondary="book_tones", back_populates="books", lazy="raise"
    )

    __table_args__ = (Index("ix_books_title", "title"),)
