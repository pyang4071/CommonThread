"""enable row level security on all public tables

Supabase exposes the public schema to the anon/authenticated roles through the
Data API (/rest/v1, /graphql/v1). With RLS on and no policies, those roles see
nothing; the backend connects as the table owner and bypasses RLS. RLS was
previously enabled only in the Supabase dashboard, so a database rebuilt from
migrations would have been readable and writable with the public anon key.

Revision ID: t4u5v6w7x8y9
Revises: s3t4u5v6w7x8
Create Date: 2026-10-22

"""
from alembic import op

revision = "t4u5v6w7x8y9"
down_revision = "s3t4u5v6w7x8"
branch_labels = None
depends_on = None

# Every public table at this revision. A later migration that creates a table
# must enable RLS on it and list it in its own RLS_TABLES —
# tests/test_rls_coverage.py fails otherwise.
RLS_TABLES = [
    "alembic_version",
    "app_users",
    "archetypes",
    "authors",
    "book_book_types",
    "book_dislikes",
    "book_genres",
    "book_ratings",
    "book_tones",
    "book_tropes",
    "book_types",
    "books",
    "character_dna",
    "genres",
    "reading_statuses",
    "series",
    "tones",
    "tropes",
    "user_book_archetypes",
    "user_book_tropes",
    "user_follows",
]


def upgrade() -> None:
    for table in RLS_TABLES:
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    # Intentionally a no-op: disabling RLS would expose every table to the anon key.
    pass
