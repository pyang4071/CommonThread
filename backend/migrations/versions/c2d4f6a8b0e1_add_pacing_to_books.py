"""add pacing to books

Revision ID: c2d4f6a8b0e1
Revises: b3e1f9a2c874
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c2d4f6a8b0e1'
down_revision: Union[str, None] = 'b3e1f9a2c874'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('books', sa.Column('pacing', sa.Integer(), nullable=True))
    op.create_check_constraint('ck_books_pacing', 'books', 'pacing >= 1 AND pacing <= 5')


def downgrade() -> None:
    op.drop_constraint('ck_books_pacing', 'books', type_='check')
    op.drop_column('books', 'pacing')
