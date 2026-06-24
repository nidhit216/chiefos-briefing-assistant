"""add brief_tasks table

Revision ID: 5c3a7d9e2f10
Revises: 2f7b8e1c4a90
Create Date: 2026-06-24 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c3a7d9e2f10'
down_revision: Union[str, None] = '2f7b8e1c4a90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('brief_tasks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('task', sa.Text(), nullable=False),
        sa.Column('date_label', sa.String(length=50), nullable=True),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_brief_tasks_user_id'), 'brief_tasks', ['user_id'], unique=False)
    op.create_index('ix_brief_tasks_user_id_category', 'brief_tasks', ['user_id', 'category'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_brief_tasks_user_id_category', table_name='brief_tasks')
    op.drop_index(op.f('ix_brief_tasks_user_id'), table_name='brief_tasks')
    op.drop_table('brief_tasks')
