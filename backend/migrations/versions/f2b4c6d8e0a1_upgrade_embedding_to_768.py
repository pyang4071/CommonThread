"""upgrade embedding column to 768 dims (bge-base-en-v1.5)

Revision ID: f2b4c6d8e0a1
Revises: e7c4b2a9f1d3
Create Date: 2026-03-31 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = 'f2b4c6d8e0a1'
down_revision: Union[str, None] = 'e7c4b2a9f1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old index and column, recreate at 768 dims
    # Null out existing embeddings first — they're the wrong dimension
    op.execute("DROP INDEX IF EXISTS ix_books_embedding")
    op.execute("UPDATE books SET embedding = NULL")
    op.alter_column("books", "embedding", type_=Vector(768), nullable=True)
    op.execute(
        "CREATE INDEX ix_books_embedding ON books "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_books_embedding")
    op.execute("UPDATE books SET embedding = NULL")
    op.alter_column("books", "embedding", type_=Vector(384), nullable=True)
    op.execute(
        "CREATE INDEX ix_books_embedding ON books "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)"
    )
