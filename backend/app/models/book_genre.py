from sqlalchemy import Column, ForeignKey, Table

from app.database.base import Base

# Simple association table — no extra columns, so a plain Table is used
# rather than a mapped class. Alembic detects it via Base.metadata.
book_genres = Table(
    "book_genres",
    Base.metadata,
    Column("book_id", ForeignKey("books.book_id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.genre_id", ondelete="CASCADE"), primary_key=True),
)
