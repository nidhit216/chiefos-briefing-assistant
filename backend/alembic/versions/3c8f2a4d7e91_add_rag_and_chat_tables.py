"""add rag and chat tables

Revision ID: 3c8f2a4d7e91
Revises: 01b5868ea647
Create Date: 2026-06-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '3c8f2a4d7e91'
down_revision: Union[str, None] = '01b5868ea647'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Document embeddings table
    op.create_table('document_embeddings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.Uuid(), nullable=False),
        sa.Column('content_text', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(384), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_embeddings_user_id'), 'document_embeddings', ['user_id'], unique=False)
    op.create_index(op.f('ix_document_embeddings_source_type'), 'document_embeddings', ['source_type'], unique=False)
    op.create_index(op.f('ix_document_embeddings_source_id'), 'document_embeddings', ['source_id'], unique=False)

    # Chat messages table
    op.create_table('chat_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_user_id'), 'chat_messages', ['user_id'], unique=False)
    op.create_index(op.f('ix_chat_messages_session_id'), 'chat_messages', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_chat_messages_session_id'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_user_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index(op.f('ix_document_embeddings_source_id'), table_name='document_embeddings')
    op.drop_index(op.f('ix_document_embeddings_source_type'), table_name='document_embeddings')
    op.drop_index(op.f('ix_document_embeddings_user_id'), table_name='document_embeddings')
    op.drop_table('document_embeddings')
    op.execute("DROP EXTENSION IF EXISTS vector")
