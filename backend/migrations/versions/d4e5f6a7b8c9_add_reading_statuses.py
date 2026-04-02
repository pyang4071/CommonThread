"""add reading_statuses table

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-04-02 13:00:00.000000

Tracks per-user reading state for each book.
status values: 'want_to_read' | 'currently_reading' | 'read'
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'reading_statuses',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['app_users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['book_id'], ['books.book_id'], ondelete='CASCADE'),
        sa.CheckConstraint("status IN ('want_to_read', 'currently_reading', 'read')", name='ck_reading_status_value'),
        sa.PrimaryKeyConstraint('user_id', 'book_id'),
    )
    op.create_index('ix_reading_statuses_user_id', 'reading_statuses', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_reading_statuses_user_id', table_name='reading_statuses')
    op.drop_table('reading_statuses')
