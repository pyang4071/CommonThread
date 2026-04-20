"""add character_dna.is_crowd_promoted and books.review_embed_count

Revision ID: p0q1r2s3t4u5
Revises: o9p0q1r2s3t4
Create Date: 2026-04-20
"""
from alembic import op
import sqlalchemy as sa

revision = "p0q1r2s3t4u5"
down_revision = "o9p0q1r2s3t4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "character_dna",
        sa.Column("is_crowd_promoted", sa.Boolean(), nullable=False, server_default="FALSE"),
    )
    op.add_column(
        "books",
        sa.Column("review_embed_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("books", "review_embed_count")
    op.drop_column("character_dna", "is_crowd_promoted")
