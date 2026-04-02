"""add review_text to ratings and book_dislikes table

Revision ID: f3a4b5c6d7e8
Revises: d4e5f6a7b8c9
Create Date: 2026-04-02 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('book_ratings', sa.Column('review_text', sa.Text(), nullable=True))

    op.create_table(
        'book_dislikes',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['app_users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['book_id'], ['books.book_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'book_id'),
    )
    op.create_index('ix_book_dislikes_user_id', 'book_dislikes', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_book_dislikes_user_id', table_name='book_dislikes')
    op.drop_table('book_dislikes')
    op.drop_column('book_ratings', 'review_text')
