"""recommendation engine schema

Revision ID: m7n8o9p0q1r2
Revises: l6m7n8o9p0q1
Create Date: 2026-04-17

Two schema additions required for the recommendation engine improvements:

1. books.review_embedding vector(768)
   Stores the aggregate embedding of all review texts for a book.
   Same model and dimension as description_embedding (BAAI/bge-base-en-v1.5).
   NULL until at least one review with text exists. Re-embedded on every
   review upsert via _embed_reviews_in_background background task.

2. book_tropes.is_crowd_promoted boolean NOT NULL DEFAULT FALSE
   Distinguishes admin-set trope associations from ones promoted automatically
   when ≥ 3 users independently tag the same trope on a book.
   Admin rows (is_crowd_promoted = False) are never auto-removed.
   Crowd-promoted rows may be demoted if user support drops below threshold.
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = 'm7n8o9p0q1r2'
down_revision = 'l6m7n8o9p0q1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add review aggregate embedding stream to books
    op.add_column(
        'books',
        sa.Column('review_embedding', Vector(768), nullable=True),
    )

    # Add crowd-promotion flag to book_tropes
    op.add_column(
        'book_tropes',
        sa.Column(
            'is_crowd_promoted',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('FALSE'),
        ),
    )


def downgrade() -> None:
    op.drop_column('book_tropes', 'is_crowd_promoted')
    op.drop_column('books', 'review_embedding')
