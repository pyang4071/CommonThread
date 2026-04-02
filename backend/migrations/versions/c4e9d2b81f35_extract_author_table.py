"""extract author into own table, FK from books

Revision ID: c4e9d2b81f35
Revises: 7d7215e6c989
Create Date: 2026-03-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4e9d2b81f35'
down_revision: Union[str, None] = '7d7215e6c989'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create authors table
    op.create_table(
        "authors",
        sa.Column("author_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
    )
    op.create_index("ix_authors_name", "authors", ["name"])

    # 2. Cluster by name for efficient author-based lookups
    op.execute("CLUSTER authors USING ix_authors_name")

    # 3. Migrate existing author strings into the authors table
    op.execute("""
        INSERT INTO authors (name)
        SELECT DISTINCT author FROM books ORDER BY author
    """)

    # 4. Add nullable author_id column to books
    op.add_column("books", sa.Column("author_id", sa.Integer(), nullable=True))

    # 5. Populate author_id from the new authors table
    op.execute("""
        UPDATE books
        SET author_id = authors.author_id
        FROM authors
        WHERE books.author = authors.name
    """)

    # 6. Make author_id NOT NULL and add FK
    op.alter_column("books", "author_id", nullable=False)
    op.create_foreign_key(
        "fk_books_author_id", "books", "authors", ["author_id"], ["author_id"]
    )

    # 7. Drop the old author string column and its index
    op.drop_index("ix_books_author", table_name="books")
    op.drop_column("books", "author")


def downgrade() -> None:
    op.add_column("books", sa.Column("author", sa.String(), nullable=True))
    op.execute("""
        UPDATE books
        SET author = authors.name
        FROM authors
        WHERE books.author_id = authors.author_id
    """)
    op.alter_column("books", "author", nullable=False)
    op.create_index("ix_books_author", "books", ["author"])
    op.drop_constraint("fk_books_author_id", "books", type_="foreignkey")
    op.drop_column("books", "author_id")
    op.drop_index("ix_authors_name", table_name="authors")
    op.drop_table("authors")
