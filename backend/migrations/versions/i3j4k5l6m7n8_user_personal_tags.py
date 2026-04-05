"""add user_book_tropes and user_book_archetypes for per-user personal tags

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-04-04 01:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'i3j4k5l6m7n8'
down_revision: Union[str, None] = 'h2i3j4k5l6m7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_book_tropes',
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('app_users.user_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.book_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('trope_id', sa.Integer(), sa.ForeignKey('tropes.trope_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('weight >= 0.0 AND weight <= 1.0', name='ck_user_book_tropes_weight'),
    )
    op.create_index('ix_user_book_tropes_user_id', 'user_book_tropes', ['user_id'])

    op.create_table(
        'user_book_archetypes',
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('app_users.user_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.book_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('archetype_id', sa.Integer(), sa.ForeignKey('archetypes.archetype_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('importance', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('importance >= 1 AND importance <= 10', name='ck_user_book_archetypes_importance'),
    )
    op.create_index('ix_user_book_archetypes_user_id', 'user_book_archetypes', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_user_book_archetypes_user_id', table_name='user_book_archetypes')
    op.drop_table('user_book_archetypes')
    op.drop_index('ix_user_book_tropes_user_id', table_name='user_book_tropes')
    op.drop_table('user_book_tropes')
