"""add embedding_status column to books

Revision ID: a9b8c7d6e5f4
Revises: e1f2a3b4c5d6
Create Date: 2026-04-02 00:01:00.000000

Values: 'pending' | 'done' | 'failed'
Default is 'pending'.  Books that already have a genome_embedding are
back-filled to 'done' so existing data is not re-embedded unnecessarily.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'books',
        sa.Column(
            'embedding_status',
            sa.String(length=10),
            nullable=False,
            server_default='pending',
        ),
    )
    # Back-fill already-embedded books so the admin queue skips them
    op.execute("UPDATE books SET embedding_status = 'done' WHERE genome_embedding IS NOT NULL")


def downgrade() -> None:
    op.drop_column('books', 'embedding_status')
