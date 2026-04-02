from sqlalchemy import Column, ForeignKey, Table

from app.database.base import Base

book_tones = Table(
    "book_tones",
    Base.metadata,
    Column("book_id", ForeignKey("books.book_id", ondelete="CASCADE"), primary_key=True),
    Column("tone_id", ForeignKey("tones.tone_id", ondelete="CASCADE"), primary_key=True),
)
