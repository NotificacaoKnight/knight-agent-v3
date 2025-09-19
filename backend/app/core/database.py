"""
Database configuration using SQLAlchemy
Supports both async and sync operations
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import Generator, AsyncGenerator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database URL construction is handled in config.py
DATABASE_URL = settings.DATABASE_URL
SYNC_DATABASE_URL = settings.SYNC_DATABASE_URL

# Naming convention for constraints (helps with migrations)
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=naming_convention)

# Create async engine for FastAPI (PostgreSQL with asyncpg)
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Disable SQL query logging for cleaner startup
    future=True,
    pool_size=20,  # Connection pool size
    max_overflow=40,  # Max overflow connections
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections every hour
)

# Sync engine only for Alembic migrations
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync session factory only for Alembic migrations
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base(metadata=metadata)

# Dependency for FastAPI routes
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session dependency for FastAPI
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

# Legacy sync function removed - use get_async_db for FastAPI compatibility
# All routes should use: db: AsyncSession = Depends(get_async_db)

async def init_database():
    """
    Initialize database (create tables if needed)
    Called during app startup
    """
    try:
        # Import all models to ensure they're registered with Base
        # This import is here to avoid circular dependency
        import app.models  # This imports all models via __init__.py

        # For development, we can create tables
        # In production, use Alembic migrations
        if settings.DEBUG:
            async with async_engine.begin() as conn:
                # Check if tables exist first to avoid unnecessary logs
                from sqlalchemy import text
                result = await conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
                table_count = result.scalar()

                if table_count == 0:
                    # Only create tables if none exist
                    logger.info("Creating database tables...")
                    await conn.run_sync(Base.metadata.create_all)
                    logger.info("✅ Database tables created successfully")
                else:
                    logger.info(f"📋 Database already initialized ({table_count} tables found)")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

async def close_database():
    """
    Close database connections
    Called during app shutdown
    """
    await async_engine.dispose()
    logger.info("Database connections closed")

async def check_database_connection() -> bool:
    """
    Check if database is accessible
    Used for health checks
    """
    import asyncio
    try:
        # Add timeout to prevent hanging
        async def db_check():
            async with AsyncSessionLocal() as session:
                # Simple query to test connection
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1

        # 2 second timeout for health check
        return await asyncio.wait_for(db_check(), timeout=2.0)
    except asyncio.TimeoutError:
        logger.warning("Database health check timed out")
        return False
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False