"""schema improvements: series table, soft deletes, author bio, onboarding flag, embedding jobs, recommendation events

Revision ID: h2i3j4k5l6m7
Revises: g5h6i7j8k9l0
Create Date: 2026-04-04 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'h2i3j4k5l6m7'
down_revision: Union[str, None] = 'g5h6i7j8k9l0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. series table ───────────────────────────────────────────────────────
    op.create_table(
        'series',
        sa.Column('series_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.UniqueConstraint('name', name='uq_series_name'),
    )

    # ── 2. books: add series_id FK, updated_at, deleted_at ───────────────────
    op.add_column('books', sa.Column('series_id', sa.Integer(), nullable=True))
    op.add_column('books', sa.Column(
        'updated_at', sa.DateTime(),
        nullable=False,
        server_default=sa.text('now()'),
    ))
    op.add_column('books', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.create_foreign_key(
        'fk_books_series_id',
        'books', 'series',
        ['series_id'], ['series_id'],
        ondelete='SET NULL',
    )

    # ── 3. backfill series from series_name ───────────────────────────────────
    op.execute("""
        INSERT INTO series (name)
        SELECT DISTINCT series_name
        FROM books
        WHERE series_name IS NOT NULL
        ON CONFLICT (name) DO NOTHING
    """)
    op.execute("""
        UPDATE books
        SET series_id = series.series_id
        FROM series
        WHERE books.series_name = series.name
    """)

    # ── 4. drop series_name column (now redundant) ────────────────────────────
    op.drop_index('ix_books_series_name', table_name='books')
    op.drop_column('books', 'series_name')

    # ── 5. authors: drop unique constraint on name, add bio ──────────────────
    op.drop_constraint('authors_name_key', 'authors', type_='unique')
    op.add_column('authors', sa.Column('bio', sa.Text(), nullable=True))

    # ── 6. app_users: add onboarding_completed ────────────────────────────────
    op.add_column('app_users', sa.Column(
        'onboarding_completed', sa.Boolean(),
        nullable=False,
        server_default=sa.text('false'),
    ))

    # ── 7. embedding_jobs table ───────────────────────────────────────────────
    op.create_table(
        'embedding_jobs',
        sa.Column('job_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.book_id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('status', sa.String(), nullable=False, server_default='queued'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    # ── 8. recommendation_events table ───────────────────────────────────────
    op.create_table(
        'recommendation_events',
        sa.Column('event_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('app_users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.book_id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_rec_events_user_id', 'recommendation_events', ['user_id'])
    op.create_index('ix_rec_events_book_id', 'recommendation_events', ['book_id'])


def downgrade() -> None:
    # ── 8. drop recommendation_events ────────────────────────────────────────
    op.drop_index('ix_rec_events_book_id', table_name='recommendation_events')
    op.drop_index('ix_rec_events_user_id', table_name='recommendation_events')
    op.drop_table('recommendation_events')

    # ── 7. drop embedding_jobs ────────────────────────────────────────────────
    op.drop_table('embedding_jobs')

    # ── 6. remove onboarding_completed ───────────────────────────────────────
    op.drop_column('app_users', 'onboarding_completed')

    # ── 5. restore author unique constraint, drop bio ────────────────────────
    op.drop_column('authors', 'bio')
    op.create_unique_constraint('authors_name_key', 'authors', ['name'])

    # ── 4. restore series_name on books ──────────────────────────────────────
    op.add_column('books', sa.Column('series_name', sa.String(255), nullable=True))
    op.execute("""
        UPDATE books
        SET series_name = series.name
        FROM series
        WHERE books.series_id = series.series_id
    """)
    op.create_index('ix_books_series_name', 'books', ['series_name'])

    # ── 3. remove series_id FK and new book columns ───────────────────────────
    op.drop_constraint('fk_books_series_id', 'books', type_='foreignkey')
    op.drop_column('books', 'deleted_at')
    op.drop_column('books', 'updated_at')
    op.drop_column('books', 'series_id')

    # ── 1. drop series table ──────────────────────────────────────────────────
    op.drop_table('series')
