"""add genres table

Revision ID: d3f8a1c2e4b5
Revises: 5bc1d5cb61b9
Create Date: 2026-03-31 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd3f8a1c2e4b5'
down_revision: Union[str, None] = '5bc1d5cb61b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'genres',
        sa.Column('genre_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.String(), nullable=True),
    )
    op.create_index('ix_genres_name', 'genres', ['name'])

    op.create_table(
        'book_genres',
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.book_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('genre_id', sa.Integer(), sa.ForeignKey('genres.genre_id', ondelete='CASCADE'), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table('book_genres')
    op.drop_index('ix_genres_name', table_name='genres')
    op.drop_table('genres')
