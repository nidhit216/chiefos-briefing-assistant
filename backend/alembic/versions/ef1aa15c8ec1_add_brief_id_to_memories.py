"""add brief_id to memories

Revision ID: ef1aa15c8ec1
Revises: 5c3a7d9e2f10
Create Date: 2026-06-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef1aa15c8ec1'
down_revision: Union[str, None] = '5c3a7d9e2f10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('memories', sa.Column('brief_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_memories_brief_id', 'memories', 'daily_briefs', ['brief_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_memories_brief_id', 'memories', type_='foreignkey')
    op.drop_column('memories', 'brief_id')
