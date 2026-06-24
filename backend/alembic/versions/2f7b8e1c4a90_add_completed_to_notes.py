"""add completed to notes

Revision ID: 2f7b8e1c4a90
Revises: 9d1e4f6a2b8c
Create Date: 2026-06-24 11:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f7b8e1c4a90'
down_revision: Union[str, None] = '9d1e4f6a2b8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('notes', sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('notes', 'completed')
