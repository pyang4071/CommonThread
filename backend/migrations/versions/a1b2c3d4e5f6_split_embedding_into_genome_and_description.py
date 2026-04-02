"""split embedding into genome_embedding (384) and description_embedding (768)

Revision ID: a1b2c3d4e5f6
Revises: f2b4c6d8e0a1
Create Date: 2026-03-31 15:00:00.000000

genome_embedding  — 384-dim, bge-small-en-v1.5, structured labels only (tropes/archetypes/genres)
description_embedding — 768-dim, bge-base-en-v1.5, prose description text only
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f2b4c6d8e0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old mixed-signal index
    op.execute("DROP INDEX IF EXISTS ix_books_embedding")

    # Rename embedding → description_embedding (still Vector(768))
    op.alter_column("books", "embedding", new_column_name="description_embedding")

    # Null it out — the old vectors mixed genome+description and are no longer valid
    op.execute("UPDATE books SET description_embedding = NULL")

    # Add genome_embedding column (384 dims, bge-small)
    op.add_column("books", sa.Column("genome_embedding", Vector(384), nullable=True))

    # Create separate ivfflat indexes for each stream
    op.execute(
        "CREATE INDEX ix_books_description_embedding ON books "
        "USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 10)"
    )
    op.execute(
        "CREATE INDEX ix_books_genome_embedding ON books "
        "USING ivfflat (genome_embedding vector_cosine_ops) WITH (lists = 10)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_books_description_embedding")
    op.execute("DROP INDEX IF EXISTS ix_books_genome_embedding")
    op.drop_column("books", "genome_embedding")
    op.alter_column("books", "description_embedding", new_column_name="embedding")
    op.execute("UPDATE books SET embedding = NULL")
    op.execute(
        "CREATE INDEX ix_books_embedding ON books "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)"
    )
