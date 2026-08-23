"""add is_admin to app_users

Revision ID: c1d2e3f4a5b6
Revises: a9b8c7d6e5f4
Create Date: 2026-04-02 12:00:00.000000

Default is false. If SEED_ADMIN_EMAIL is set in the environment, that user
is promoted to admin.
"""
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'a9b8c7d6e5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'app_users',
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
    )
    admin_email = os.environ.get("SEED_ADMIN_EMAIL")
    if admin_email:
        op.execute(
            sa.text("UPDATE app_users SET is_admin = true WHERE email = :email")
            .bindparams(email=admin_email)
        )


def downgrade() -> None:
    op.drop_column('app_users', 'is_admin')
