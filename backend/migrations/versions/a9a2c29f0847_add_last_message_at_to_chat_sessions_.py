"""add_last_message_at_to_chat_sessions_manual

Revision ID: a9a2c29f0847
Revises: 79b476df49a4
Create Date: 2025-09-24 18:54:08.006027

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9a2c29f0847'
down_revision: Union[str, Sequence[str], None] = '79b476df49a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add last_message_at column to chat_sessions table."""
    # Add last_message_at column
    op.add_column('chat_sessions', sa.Column('last_message_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove last_message_at column from chat_sessions table."""
    # Remove last_message_at column
    op.drop_column('chat_sessions', 'last_message_at')
