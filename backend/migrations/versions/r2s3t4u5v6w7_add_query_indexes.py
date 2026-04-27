"""add missing query indexes for book lookups and related tables

Revision ID: r2s3t4u5v6w7
Revises: q1r2s3t4u5v6
Create Date: 2026-04-26

Adds indexes that were missing on FK and secondary-direction filter columns:

- books.author_id         FK used in the author-name search subquery
                           (list_books keyword search joins authors → filters books)
- books.series_id         FK used in get_books_in_series and recommendations
                           series-gate query
- book_tropes.trope_id    composite PK is (book_id, trope_id); trope-side lookups
                           (category filter in list_books, TropeDetail page) need this
- character_dna.archetype_id  same pattern as book_tropes
- book_ratings.book_id    unique constraint is (user_id, book_id) with user_id
                           leading; avg-rating aggregation in list_books queries
                           by book_id alone and cannot use that index
"""

from alembic import op

revision = "r2s3t4u5v6w7"
down_revision = "q1r2s3t4u5v6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_books_author_id", "books", ["author_id"])
    op.create_index("ix_books_series_id", "books", ["series_id"])
    op.create_index("ix_book_tropes_trope_id", "book_tropes", ["trope_id"])
    op.create_index("ix_character_dna_archetype_id", "character_dna", ["archetype_id"])
    op.create_index("ix_book_ratings_book_id", "book_ratings", ["book_id"])


def downgrade() -> None:
    op.drop_index("ix_book_ratings_book_id", table_name="book_ratings")
    op.drop_index("ix_character_dna_archetype_id", table_name="character_dna")
    op.drop_index("ix_book_tropes_trope_id", table_name="book_tropes")
    op.drop_index("ix_books_series_id", table_name="books")
    op.drop_index("ix_books_author_id", table_name="books")
