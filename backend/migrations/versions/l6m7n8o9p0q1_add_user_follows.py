"""add user follows

Revision ID: l6m7n8o9p0q1
Revises: k5l6m7n8o9p0
Create Date: 2026-04-12

Creates the user_follows table for the one-directional follow / friends system.
"""

from alembic import op
import sqlalchemy as sa

revision = 'l6m7n8o9p0q1'
down_revision = 'k5l6m7n8o9p0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_follows',
        sa.Column('follower_id', sa.UUID(), nullable=False),
        sa.Column('followee_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['follower_id'], ['app_users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['followee_id'], ['app_users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('follower_id', 'followee_id'),
        sa.UniqueConstraint('follower_id', 'followee_id', name='uq_user_follows'),
    )
    op.create_index('ix_user_follows_followee_id', 'user_follows', ['followee_id'])
    op.create_index('ix_user_follows_follower_id', 'user_follows', ['follower_id'])


def downgrade() -> None:
    op.drop_index('ix_user_follows_followee_id', table_name='user_follows')
    op.drop_index('ix_user_follows_follower_id', table_name='user_follows')
    op.drop_table('user_follows')
