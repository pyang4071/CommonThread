"""initial schema

Revision ID: e09714bacac6
Revises: 
Create Date: 2026-03-30 14:47:53.255175

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e09714bacac6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("book_id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("isbn", sa.String(), nullable=True, unique=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_books_author", "books", ["author"])
    op.create_index("ix_books_title", "books", ["title"])

    op.create_table(
        "tropes",
        sa.Column("trope_id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
    )
    op.create_index("ix_tropes_category", "tropes", ["category"])

    op.create_table(
        "archetypes",
        sa.Column("archetype_id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.String(), nullable=True),
    )

    op.create_table(
        "book_tropes",
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.book_id"), primary_key=True),
        sa.Column("trope_id", sa.Integer(), sa.ForeignKey("tropes.trope_id"), primary_key=True),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.CheckConstraint("weight >= 0.0 AND weight <= 1.0", name="ck_book_tropes_weight"),
    )

    op.create_table(
        "character_dna",
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.book_id"), primary_key=True),
        sa.Column(
            "archetype_id",
            sa.Integer(),
            sa.ForeignKey("archetypes.archetype_id"),
            primary_key=True,
        ),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "importance >= 1 AND importance <= 10", name="ck_character_dna_importance"
        ),
    )


def downgrade() -> None:
    op.drop_table("character_dna")
    op.drop_table("book_tropes")
    op.drop_table("archetypes")
    op.drop_table("tropes")
    op.drop_index("ix_books_title", "books")
    op.drop_index("ix_books_author", "books")
    op.drop_table("books")
