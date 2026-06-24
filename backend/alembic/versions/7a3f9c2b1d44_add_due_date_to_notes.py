"""add_due_date_to_notes

Revision ID: 7a3f9c2b1d44
Revises: 3c8f2a4d7e91
Create Date: 2026-06-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a3f9c2b1d44'
down_revision: Union[str, None] = '3c8f2a4d7e91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('notes', sa.Column('due_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('notes', 'due_date')
