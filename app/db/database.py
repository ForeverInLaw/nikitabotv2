"""
Database connection and session management.
Handles async database operations with SQLAlchemy.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from config.settings import settings
from .models import Base

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# Create async session factory
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db() -> None:
    """Initialize database and create tables."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an asynchronous database session.
    This function is an async context manager.
    """
    # Use the factory to create an AsyncSession instance.
    # The 'async with session_instance:' block will manage its lifecycle
    # (begin, commit/rollback, close).
    session_instance: AsyncSession = async_session()
    async with session_instance as managed_session:
        try:
            # Yield the session that is managed by the inner 'async with'.
            # Code in user_service.py will use this 'managed_session'.
            yield managed_session
        except Exception as e:
            # This will catch errors from the code block where 'get_session' is used
            # (e.g., from user_service.py).
            # The 'managed_session' (via 'async with session_instance as managed_session:')
            # should have already handled its own rollback if the error
            # occurred during database operations on it.
            logger.error(f"Error within get_session's yielded block: {e}", exc_info=True) # Added exc_info
            raise
        # 'finally' block to explicitly close 'managed_session' is not needed here,
        # as the 'async with session_instance as managed_session:' statement handles it.





