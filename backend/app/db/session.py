from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

from app.core.config import settings


# The engine manages the connection pool to PostgreSQL.
# 
# Why async? Our FastAPI app is async. If we used a sync engine,
# every DB query would block the event loop — destroying
# the performance benefit of async.
#
# pool_pre_ping=True: before using a connection from the pool,
# test if it's still alive. Prevents "connection closed" errors
# after PostgreSQL restarts or network blips.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,    # Log all SQL in development only
    pool_pre_ping=True,
    pool_size=10,           # Max persistent connections
    max_overflow=20,        # Extra connections allowed under load
)


# Session factory — creates new database sessions
# expire_on_commit=False: after committing, don't expire
# object attributes. Without this, accessing an attribute after
# commit triggers another DB query (the N+1 trap).
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Used like this in a route:
        async def my_route(db: AsyncSession = Depends(get_db)):

    The 'async with' ensures the session is always closed,
    even if an exception occurs — no connection leaks.

    Why yield instead of return? Because FastAPI runs the
    code after yield as cleanup AFTER the response is sent.
    This is dependency injection with automatic cleanup.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()