"""add document fields

Revision ID: add_document_fields
Revises:
Create Date: 2025-09-23 15:50:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_document_fields'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns if they don't exist
    try:
        op.add_column('documents', sa.Column('created_at', sa.DateTime(), nullable=True))
        op.add_column('documents', sa.Column('processing_started_at', sa.DateTime(), nullable=True))
        op.add_column('documents', sa.Column('processing_completed_at', sa.DateTime(), nullable=True))
        op.add_column('documents', sa.Column('page_count', sa.Integer(), nullable=True))
        op.add_column('documents', sa.Column('chunk_count', sa.Integer(), nullable=True))
        op.add_column('documents', sa.Column('error_message', sa.Text(), nullable=True))
    except Exception as e:
        print(f"Some columns may already exist: {e}")


def downgrade() -> None:
    # Remove the columns
    op.drop_column('documents', 'error_message')
    op.drop_column('documents', 'chunk_count')
    op.drop_column('documents', 'page_count')
    op.drop_column('documents', 'processing_completed_at')
    op.drop_column('documents', 'processing_started_at')
    op.drop_column('documents', 'created_at')