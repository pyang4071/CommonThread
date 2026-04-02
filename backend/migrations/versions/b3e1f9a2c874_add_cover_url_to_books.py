"""add cover_url to books

Revision ID: b3e1f9a2c874
Revises: a1b2c3d4e5f6
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b3e1f9a2c874'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('books', sa.Column('cover_url', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('books', 'cover_url')
