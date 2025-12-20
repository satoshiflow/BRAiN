"""
Database connection management with connection pooling.

Provides:
- Async SQLAlchemy engine with optimized connection pooling
- Session factory for database operations
- Health check utilities
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncSession,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.pool import NullPool, QueuePool

from .config import get_settings

settings = get_settings()

# Production-ready connection pool configuration
engine: AsyncEngine = create_async_engine(
    settings.db_url,
    echo=False,  # Set to True for SQL query logging in development
    future=True,
    # Connection Pool Settings
    poolclass=QueuePool,  # Use QueuePool for production (default)
    pool_size=20,  # Number of persistent connections
    max_overflow=10,  # Additional connections when pool is full
    pool_timeout=30,  # Wait time for connection from pool (seconds)
    pool_recycle=3600,  # Recycle connections after 1 hour (prevents stale connections)
    pool_pre_ping=True,  # Test connection before using (prevents broken connections)
    # Connection Settings
    connect_args={
        "server_settings": {
            "application_name": "brain_core",  # Shows in pg_stat_activity
        },
        "command_timeout": 60,  # Query timeout (seconds)
        "timeout": 10,  # Connection timeout (seconds)
    },
    # Additional Settings
    echo_pool=False,  # Set to True to log pool events
    hide_parameters=True,  # Hide sensitive data in logs
)

# Session factory with optimized settings
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy-loading after commit
    autoflush=False,  # Manual control of flush timing
    autocommit=False,  # Explicit transaction management
)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Get an async database session.

    Usage:
        async with get_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()

    The session is automatically committed and closed.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> bool:
    """
    Check database connectivity and health.

    Returns:
        True if database is healthy, False otherwise

    Example:
        if await check_db_health():
            print("Database is healthy")
    """
    try:
        async with get_session() as session:
            # Simple query to test connection
            result = await session.execute(text("SELECT 1"))
            row = result.scalar()
            return row == 1
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False


async def get_pool_status() -> dict:
    """
    Get current connection pool status.

    Returns:
        Dictionary with pool statistics

    Example:
        status = await get_pool_status()
        print(f"Pool size: {status['pool_size']}")
    """
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.size() - pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total_connections": pool.size() + pool.overflow(),
    }


async def close_db_connections():
    """
    Close all database connections gracefully.

    Should be called on application shutdown.

    Example:
        @app.on_event("shutdown")
        async def shutdown():
            await close_db_connections()
    """
    await engine.dispose()


# For testing: Use NullPool to avoid connection pooling issues
def create_test_engine(database_url: str) -> AsyncEngine:
    """
    Create an async engine for testing (no connection pooling).

    Args:
        database_url: Database connection URL

    Returns:
        AsyncEngine instance with NullPool

    Example:
        test_engine = create_test_engine("postgresql+asyncpg://...")
    """
    return create_async_engine(
        database_url,
        echo=True,  # Log queries in tests
        poolclass=NullPool,  # No pooling for tests
        future=True,
    )
