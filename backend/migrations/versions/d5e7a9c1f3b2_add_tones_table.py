"""add tones table

Revision ID: d5e7a9c1f3b2
Revises: c2d4f6a8b0e1
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd5e7a9c1f3b2'
down_revision: Union[str, None] = 'c2d4f6a8b0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tones',
        sa.Column('tone_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.UniqueConstraint('name', name='uq_tones_name'),
    )
    op.create_table(
        'book_tones',
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.book_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('tone_id', sa.Integer(), sa.ForeignKey('tones.tone_id', ondelete='CASCADE'), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table('book_tones')
    op.drop_table('tones')
