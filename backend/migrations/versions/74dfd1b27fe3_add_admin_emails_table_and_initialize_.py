"""Add admin emails table and initialize admin users

Revision ID: 74dfd1b27fe3
Revises: b162ecb20b72
Create Date: 2025-09-18 22:48:13.374047

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74dfd1b27fe3'
down_revision: Union[str, Sequence[str], None] = 'b162ecb20b72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create admin_emails table
    op.create_table(
        'admin_emails',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('email', sa.String(254), nullable=False, unique=True),
        sa.Column('added_by', sa.String(254), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_emails_email'), 'admin_emails', ['email'], unique=True)

    # Insert initial admin emails
    op.execute("""
        INSERT INTO admin_emails (email, added_by, is_active, created_at)
        VALUES
            ('felipe.nascimento@semcon.com', 'system', true, CURRENT_TIMESTAMP),
            ('paulo.pereira@semcon.com', 'system', true, CURRENT_TIMESTAMP)
        ON CONFLICT (email) DO NOTHING
    """)

    # Update existing users to be admins if their email is in the admin list
    op.execute("""
        UPDATE users
        SET is_admin = true
        WHERE email IN (
            'felipe.nascimento@semcon.com',
            'paulo.pereira@semcon.com'
        )
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove admin privileges from users
    op.execute("""
        UPDATE users
        SET is_admin = false
        WHERE email IN (
            SELECT email FROM admin_emails
        )
    """)

    # Drop admin_emails table
    op.drop_index(op.f('ix_admin_emails_email'), table_name='admin_emails')
    op.drop_table('admin_emails')
