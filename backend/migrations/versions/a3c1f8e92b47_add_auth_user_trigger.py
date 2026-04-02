"""add trigger to sync auth.users to app_users on signup

Revision ID: a3c1f8e92b47
Revises: e5f3544cbb34
Create Date: 2026-03-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a3c1f8e92b47'
down_revision: Union[str, None] = 'e5f3544cbb34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER SET search_path = public
        AS $$
        BEGIN
            INSERT INTO public.app_users (user_id, email, name)
            VALUES (
                NEW.id,
                NEW.email,
                NEW.raw_user_meta_data->>'name'
            )
            ON CONFLICT (user_id) DO NOTHING;
            RETURN NEW;
        END;
        $$;
    """)

    op.execute("""
        CREATE TRIGGER on_auth_user_created
        AFTER INSERT ON auth.users
        FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;")
    op.execute("DROP FUNCTION IF EXISTS public.handle_new_user();")
