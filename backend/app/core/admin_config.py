"""
Administrator configuration and management
"""
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.admin import AdminEmail
from app.models.user import User

logger = logging.getLogger(__name__)

# Initial admin emails (will be synced to database)
INITIAL_ADMIN_EMAILS = [
    'felipe.nascimento@semcon.com',
    'paulo.pereira@semcon.com'
]


class AdminService:
    """Service for managing administrator privileges"""

    async def is_admin_email(self, email: str, db: AsyncSession) -> bool:
        """
        Check if an email has admin privileges

        Args:
            email: Email to check
            db: Database session

        Returns:
            True if email is admin, False otherwise
        """
        if not email:
            return False

        email = email.lower().strip()

        # Check in database
        stmt = select(AdminEmail).where(
            AdminEmail.email == email,
            AdminEmail.is_active == True
        )
        result = await db.execute(stmt)
        admin_email = result.scalar_one_or_none()

        return admin_email is not None

    async def get_admin_emails(self, db: AsyncSession) -> List[str]:
        """
        Get all active admin emails

        Args:
            db: Database session

        Returns:
            List of admin email addresses
        """
        stmt = select(AdminEmail).where(AdminEmail.is_active == True)
        result = await db.execute(stmt)
        admin_emails = result.scalars().all()

        return [admin.email for admin in admin_emails]

    async def add_admin_email(
        self,
        email: str,
        added_by: str,
        db: AsyncSession
    ) -> bool:
        """
        Add a new admin email

        Args:
            email: Email to add as admin
            added_by: Email of admin who is adding this
            db: Database session

        Returns:
            True if added successfully, False if already exists
        """
        email = email.lower().strip()

        # Check if already exists
        if await self.is_admin_email(email, db):
            return False

        # Add new admin email
        admin_email = AdminEmail(
            email=email,
            added_by=added_by,
            is_active=True
        )
        db.add(admin_email)

        # Update user if they exist
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.is_admin = True
            logger.info(f"Updated existing user {email} to admin")

        await db.commit()
        logger.info(f"Added admin email: {email} (by {added_by})")
        return True

    async def remove_admin_email(
        self,
        email: str,
        removed_by: str,
        db: AsyncSession
    ) -> bool:
        """
        Remove admin privileges from an email

        Args:
            email: Email to remove admin from
            removed_by: Email of admin who is removing this
            db: Database session

        Returns:
            True if removed successfully
        """
        email = email.lower().strip()

        # Prevent removing the last admin
        admin_count = await self.get_admin_count(db)
        if admin_count <= 1:
            logger.warning(f"Cannot remove last admin: {email}")
            return False

        # Prevent self-removal
        if email == removed_by.lower():
            logger.warning(f"Admin cannot remove themselves: {email}")
            return False

        # Remove from database
        stmt = delete(AdminEmail).where(AdminEmail.email == email)
        result = await db.execute(stmt)

        # Update user if they exist
        user_stmt = select(User).where(User.email == email)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if user:
            user.is_admin = False
            logger.info(f"Removed admin privileges from user {email}")

        await db.commit()
        logger.info(f"Removed admin email: {email} (by {removed_by})")
        return result.rowcount > 0

    async def get_admin_count(self, db: AsyncSession) -> int:
        """
        Get count of active admin emails

        Args:
            db: Database session

        Returns:
            Number of active admins
        """
        stmt = select(AdminEmail).where(AdminEmail.is_active == True)
        result = await db.execute(stmt)
        admins = result.scalars().all()
        return len(admins)

    async def sync_initial_admins(self, db: AsyncSession):
        """
        Sync initial admin emails to database
        This is called during startup to ensure initial admins exist

        Args:
            db: Database session
        """
        for email in INITIAL_ADMIN_EMAILS:
            email = email.lower().strip()

            # Check if already exists
            stmt = select(AdminEmail).where(AdminEmail.email == email)
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                admin_email = AdminEmail(
                    email=email,
                    added_by="system",
                    is_active=True
                )
                db.add(admin_email)
                logger.info(f"Added initial admin email: {email}")

        await db.commit()

    async def update_user_admin_status(
        self,
        email: str,
        db: AsyncSession
    ) -> bool:
        """
        Update a user's admin status based on admin email list

        Args:
            email: User email to check and update
            db: Database session

        Returns:
            True if user is admin, False otherwise
        """
        is_admin = await self.is_admin_email(email, db)

        # Update user if exists
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user and user.is_admin != is_admin:
            user.is_admin = is_admin
            await db.commit()
            logger.info(f"Updated user {email} admin status to {is_admin}")

        return is_admin


# Singleton instance
admin_service = AdminService()