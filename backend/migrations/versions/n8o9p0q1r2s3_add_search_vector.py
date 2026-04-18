"""add search_vector tsvector column to books

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2026-04-17

Adds a GENERATED ALWAYS tsvector column to `books` for full-text search,
and a GIN index on that column. This powers the lexical leg of hybrid search.

The column is weighted:
  - title       → weight A (highest)
  - description → weight C

Author name lives in app_authors and is joined at query time.
"""
from alembic import op

revision = "n8o9p0q1r2s3"
down_revision = "m7n8o9p0q1r2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE books
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'C')
        ) STORED
    """)
    op.execute("""
        CREATE INDEX ix_books_search_vector
        ON books USING GIN (search_vector)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_books_search_vector")
    op.execute("ALTER TABLE books DROP COLUMN IF EXISTS search_vector")
