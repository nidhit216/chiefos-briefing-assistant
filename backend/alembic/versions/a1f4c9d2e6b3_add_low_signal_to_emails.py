"""add low_signal to emails

Revision ID: a1f4c9d2e6b3
Revises: 4b6d1f8a9c52
Create Date: 2026-06-25 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1f4c9d2e6b3'
down_revision: Union[str, None] = '4b6d1f8a9c52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('emails', sa.Column('low_signal', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('emails', 'low_signal')
