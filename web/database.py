import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

"""
Async database configuration and session management.

Provides:
- Async SQLAlchemy engine
- Session factory for DB interactions
- Base ORM model class
- FastAPI dependency for request-scoped DB sessions

CONCEPT: This module centralizes all database setup so that:
- Connection handling is consistent across the app
- Sessions are properly scoped and cleaned up
- Models share a common metadata registry
"""

# -------------------------------------------------------------------
# Database configuration
# -------------------------------------------------------------------
# DATABASE_URL can be set via environment variable.
# Falls back to a local Postgres instance for development.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_sdlc"
)

# -------------------------------------------------------------------
# Async SQLAlchemy engine
# -------------------------------------------------------------------
# Creates the core database engine used for all connections.
# echo=True logs all SQL queries (useful for debugging, disable in production).
engine = create_async_engine(DATABASE_URL, echo=True)

# -------------------------------------------------------------------
# Async session maker
# -------------------------------------------------------------------
# Factory for creating async database sessions.
# expire_on_commit=False ensures ORM objects remain usable after commit
# (avoids needing to re-fetch them).
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# -------------------------------------------------------------------
# Base class for all ORM models
# -------------------------------------------------------------------
class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    CONCEPT: Every model should inherit from this class so that:
    - SQLAlchemy can track table metadata
    - Tables can be created via Base.metadata.create_all()
    """
    pass

# -------------------------------------------------------------------
# Dependency: Get DB session
# -------------------------------------------------------------------
async def get_db() -> AsyncSession:
    """
    Provide a request-scoped async database session.

    Designed to be used with FastAPI dependency injection:
        db: AsyncSession = Depends(get_db)

    CONCEPT: Ensures proper session lifecycle management:
    - A new session is created per request
    - The session is automatically closed after use
    - Prevents connection leaks

    Yields:
        AsyncSession: Active database session.
    """
    # Create a new async session
    async with AsyncSessionLocal() as session:
        try:
            # Provide session to the request handler
            yield session
        finally:
            # Ensure the session is always closed
            await session.close()