"""add book_types table

Revision ID: e7c4b2a9f1d3
Revises: d3f8a1c2e4b5
Create Date: 2026-03-31 13:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e7c4b2a9f1d3'
down_revision: Union[str, None] = 'd3f8a1c2e4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'book_types',
        sa.Column('book_type_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.String(), nullable=True),
    )
    op.create_index('ix_book_types_name', 'book_types', ['name'])

    op.create_table(
        'book_book_types',
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.book_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('book_type_id', sa.Integer(), sa.ForeignKey('book_types.book_type_id', ondelete='CASCADE'), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table('book_book_types')
    op.drop_index('ix_book_types_name', table_name='book_types')
    op.drop_table('book_types')
