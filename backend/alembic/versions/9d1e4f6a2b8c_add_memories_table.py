"""add memories table

Revision ID: 9d1e4f6a2b8c
Revises: 7a3f9c2b1d44
Create Date: 2026-06-24 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d1e4f6a2b8c'
down_revision: Union[str, None] = '7a3f9c2b1d44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('memories',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memories_user_id'), 'memories', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_memories_user_id'), table_name='memories')
    op.drop_table('memories')
