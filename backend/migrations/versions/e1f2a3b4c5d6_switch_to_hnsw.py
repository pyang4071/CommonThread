"""switch embedding indexes from ivfflat to hnsw

Revision ID: e1f2a3b4c5d6
Revises: d5e7a9c1f3b2
Create Date: 2026-04-02 00:00:00.000000

IVFFlat with lists=10 and probes=10 scans every cluster (no benefit over a
sequential scan).  HNSW requires no training data, has better recall at all
dataset sizes, and degrades gracefully as the catalog grows.

Tuning used:
  m=16, ef_construction=64  — pgvector defaults, good up to ~100k rows.
  ef_search=40 set at query time via SET LOCAL.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd5e7a9c1f3b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_books_genome_embedding")
    op.execute("DROP INDEX IF EXISTS ix_books_description_embedding")

    op.execute(
        "CREATE INDEX ix_books_genome_embedding ON books "
        "USING hnsw (genome_embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX ix_books_description_embedding ON books "
        "USING hnsw (description_embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_books_genome_embedding")
    op.execute("DROP INDEX IF EXISTS ix_books_description_embedding")

    op.execute(
        "CREATE INDEX ix_books_genome_embedding ON books "
        "USING ivfflat (genome_embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute(
        "CREATE INDEX ix_books_description_embedding ON books "
        "USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 100)"
    )
