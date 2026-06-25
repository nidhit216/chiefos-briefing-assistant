"""add google token expiry to users

Revision ID: 4b6d1f8a9c52
Revises: ef1aa15c8ec1
Create Date: 2026-06-24 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b6d1f8a9c52'
down_revision: Union[str, None] = 'ef1aa15c8ec1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('google_token_expiry', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'google_token_expiry')
