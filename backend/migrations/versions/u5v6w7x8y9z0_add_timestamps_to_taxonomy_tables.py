"""add created_at/updated_at to admin-managed taxonomy tables

These tables are only writable by admins, and without timestamps there was no
way to tell whether (or when) an admin session changed them. updated_at is
maintained by a trigger so edits made outside the ORM (e.g. the Supabase SQL
editor) are recorded too. Existing rows get the migration time as created_at.

Revision ID: u5v6w7x8y9z0
Revises: t4u5v6w7x8y9
Create Date: 2026-10-22

"""
import sqlalchemy as sa
from alembic import op

revision = "u5v6w7x8y9z0"
down_revision = "t4u5v6w7x8y9"
branch_labels = None
depends_on = None

TABLES = ["tropes", "genres", "tones", "archetypes", "book_types"]


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = ''
        AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$;
    """)
    for table in TABLES:
        for column in ("created_at", "updated_at"):
            op.add_column(
                table,
                sa.Column(column, sa.DateTime(), server_default=sa.func.now(), nullable=False),
            )
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON public.{table}
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        """)


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON public.{table};")
        op.drop_column(table, "updated_at")
        op.drop_column(table, "created_at")
    op.execute("DROP FUNCTION IF EXISTS public.set_updated_at();")
