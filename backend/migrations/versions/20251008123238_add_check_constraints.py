"""add check constraints to chat_messages

Revision ID: add_check_constraints
Revises: 1c5507fb4e03
Create Date: 2025-10-08 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers
revision: str = 'add_check_constraints'
down_revision: Union[str, Sequence[str], None] = '1c5507fb4e03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add check constraints to chat_messages."""
    op.execute("""
        ALTER TABLE chat_messages 
        ADD CONSTRAINT check_message_type 
        CHECK (message_type IN ('user', 'assistant', 'system'))
    """)
    
    op.execute("""
        ALTER TABLE chat_messages 
        ADD CONSTRAINT check_content_type 
        CHECK (content_type IN ('text', 'audio'))
    """)


def downgrade() -> None:
    """Remove check constraints from chat_messages."""
    op.execute("ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS check_message_type")
    op.execute("ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS check_content_type")
