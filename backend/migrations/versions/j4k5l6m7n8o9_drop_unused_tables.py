"""drop embedding_jobs and recommendation_events tables

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-04-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'j4k5l6m7n8o9'
down_revision: Union[str, None] = 'i3j4k5l6m7n8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('embedding_jobs')
    op.drop_table('recommendation_events')


def downgrade() -> None:
    op.create_table(
        'recommendation_events',
        sa.Column('event_id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('app_users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.book_id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_rec_events_user_id', 'recommendation_events', ['user_id'])
    op.create_index('ix_rec_events_book_id', 'recommendation_events', ['book_id'])

    op.create_table(
        'embedding_jobs',
        sa.Column('job_id', sa.Integer(), primary_key=True),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.book_id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('status', sa.String(), server_default='queued', nullable=False),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_error', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
