"""drop language column from books

Revision ID: s3t4u5v6w7x8
Revises: r2s3t4u5v6w7
Create Date: 2026-05-08

"""
from alembic import op
import sqlalchemy as sa

revision = "s3t4u5v6w7x8"
down_revision = "r2s3t4u5v6w7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_books_language", table_name="books")
    op.drop_column("books", "language")


def downgrade() -> None:
    op.add_column("books", sa.Column("language", sa.String(length=8), nullable=True))
    op.create_index("ix_books_language", "books", ["language"])
