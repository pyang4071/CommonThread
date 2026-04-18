"""add page_count and language to books

Revision ID: o9p0q1r2s3t4
Revises: n8o9p0q1r2s3
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

revision = "o9p0q1r2s3t4"
down_revision = "n8o9p0q1r2s3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("books", sa.Column("page_count", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("language", sa.String(length=8), nullable=True))
    op.create_index("ix_books_language", "books", ["language"])


def downgrade() -> None:
    op.drop_index("ix_books_language", table_name="books")
    op.drop_column("books", "language")
    op.drop_column("books", "page_count")
