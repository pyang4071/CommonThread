from sqlalchemy import Column, ForeignKey, Table

from app.database.base import Base

book_book_types = Table(
    "book_book_types",
    Base.metadata,
    Column("book_id", ForeignKey("books.book_id", ondelete="CASCADE"), primary_key=True),
    Column("book_type_id", ForeignKey("book_types.book_type_id", ondelete="CASCADE"), primary_key=True),
)
