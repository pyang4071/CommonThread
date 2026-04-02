"""add series_name and series_position to books

Revision ID: g5h6i7j8k9l0
Revises: f3a4b5c6d7e8
Create Date: 2026-04-02 13:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'g5h6i7j8k9l0'
down_revision: Union[str, None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('books', sa.Column('series_name', sa.String(255), nullable=True))
    op.add_column('books', sa.Column('series_position', sa.Integer(), nullable=True))
    op.create_index('ix_books_series_name', 'books', ['series_name'])


def downgrade() -> None:
    op.drop_index('ix_books_series_name', table_name='books')
    op.drop_column('books', 'series_position')
    op.drop_column('books', 'series_name')
