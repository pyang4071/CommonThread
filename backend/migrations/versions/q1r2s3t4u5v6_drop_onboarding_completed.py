"""drop app_users.onboarding_completed (unused column)

Revision ID: q1r2s3t4u5v6
Revises: p0q1r2s3t4u5
Create Date: 2026-04-20
"""
from alembic import op

revision = "q1r2s3t4u5v6"
down_revision = "p0q1r2s3t4u5"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("app_users", "onboarding_completed")


def downgrade():
    import sqlalchemy as sa
    op.add_column(
        "app_users",
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default="false"),
    )
