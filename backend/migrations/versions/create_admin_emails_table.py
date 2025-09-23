"""Create admin_emails table

Revision ID: create_admin_emails
Revises: bbac859eac4d
Create Date: 2025-09-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'create_admin_emails'
down_revision: Union[str, Sequence[str], None] = 'bbac859eac4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create admin_emails table"""
    op.create_table(
        'admin_emails',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('added_by', sa.String(length=254), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_emails_email'), 'admin_emails', ['email'], unique=True)
    op.create_index(op.f('ix_admin_emails_id'), 'admin_emails', ['id'], unique=False)


def downgrade() -> None:
    """Drop admin_emails table"""
    op.drop_index(op.f('ix_admin_emails_id'), table_name='admin_emails')
    op.drop_index(op.f('ix_admin_emails_email'), table_name='admin_emails')
    op.drop_table('admin_emails')