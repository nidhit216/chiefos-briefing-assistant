"""add timezone to users

Revision ID: b4e7d1a3f9c5
Revises: a1f4c9d2e6b3
Create Date: 2026-06-27 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4e7d1a3f9c5'
down_revision: Union[str, None] = 'a1f4c9d2e6b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('timezone', sa.String(length=64), server_default='Asia/Kolkata', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('users', 'timezone')
