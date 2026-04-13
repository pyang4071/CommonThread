"""add user preferences

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-04-12

Adds a JSONB preferences column to app_users.
Stores account-level content blacklist:
  { blocked_genre_ids, blocked_book_type_ids, blocked_tone_ids }
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'k5l6m7n8o9p0'
down_revision = 'j4k5l6m7n8o9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'app_users',
        sa.Column('preferences', JSONB, nullable=False, server_default='{}'),
    )


def downgrade() -> None:
    op.drop_column('app_users', 'preferences')
