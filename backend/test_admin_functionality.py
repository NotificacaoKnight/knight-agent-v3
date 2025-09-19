"""
Test script to verify admin functionality
"""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.user import User
from app.models.admin import AdminEmail
from app.core.config import settings
from app.core.admin_config import admin_service

async def test_admin_functionality():
    """Test admin functionality"""

    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )

    # Create async session
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as db:
        print("\n=== Testing Admin Functionality ===\n")

        # 1. Check admin emails in database
        print("1. Checking admin_emails table...")
        stmt = select(AdminEmail)
        result = await db.execute(stmt)
        admin_emails = result.scalars().all()

        print(f"Found {len(admin_emails)} admin emails:")
        for admin in admin_emails:
            print(f"  - {admin.email} (active={admin.is_active}, added_by={admin.added_by})")

        # 2. Check users with admin status
        print("\n2. Checking users with is_admin=True...")
        stmt = select(User).where(User.is_admin == True)
        result = await db.execute(stmt)
        admin_users = result.scalars().all()

        print(f"Found {len(admin_users)} admin users:")
        for user in admin_users:
            print(f"  - {user.email} (name={user.display_name})")

        # 3. Test admin service
        print("\n3. Testing admin service...")

        # Test is_admin_email
        test_email = "felipe.nascimento@semcon.com"
        is_admin = await admin_service.is_admin_email(test_email, db)
        print(f"  - Is {test_email} admin? {is_admin}")

        # Get all admin emails
        all_admins = await admin_service.get_admin_emails(db)
        print(f"  - All admin emails: {all_admins}")

        # Get admin count
        count = await admin_service.get_admin_count(db)
        print(f"  - Total admin count: {count}")

        print("\n=== Admin Functionality Test Complete ===")

        # 4. Check if felipe.nascimento@semcon.com user exists and has admin
        print("\n4. Checking felipe.nascimento@semcon.com user...")
        stmt = select(User).where(User.email == "felipe.nascimento@semcon.com")
        result = await db.execute(stmt)
        felipe_user = result.scalar_one_or_none()

        if felipe_user:
            print(f"  User found:")
            print(f"    - Email: {felipe_user.email}")
            print(f"    - Name: {felipe_user.display_name}")
            print(f"    - Is Admin: {felipe_user.is_admin}")
            print(f"    - Is Active: {felipe_user.is_active}")

            if not felipe_user.is_admin:
                print("\n  ⚠️ WARNING: User is not marked as admin!")
                print("  Updating user to admin...")
                felipe_user.is_admin = True
                await db.commit()
                print("  ✅ User updated to admin")
        else:
            print("  ❌ User not found - will be created and marked as admin on first login")

if __name__ == "__main__":
    asyncio.run(test_admin_functionality())