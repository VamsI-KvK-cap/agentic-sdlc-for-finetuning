import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# -------------------------------------------------------------------
# Database configuration
# -------------------------------------------------------------------
# DATABASE_URL can be set via environment variable, fallback to local Postgres
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_sdlc"
)

# -------------------------------------------------------------------
# Async SQLAlchemy engine
# -------------------------------------------------------------------
# `echo=True` logs all SQL statements (useful for debugging)
engine = create_async_engine(DATABASE_URL, echo=True)

# -------------------------------------------------------------------
# Async session maker
# -------------------------------------------------------------------
# Creates sessions that are used for async DB operations
# expire_on_commit=False prevents automatic expiration of ORM objects after commit
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# -------------------------------------------------------------------
# Base class for all ORM models
# -------------------------------------------------------------------
# All models must inherit from this Base class
# It registers tables and metadata for SQLAlchemy
class Base(DeclarativeBase):
    pass

# -------------------------------------------------------------------
# Dependency function to get a database session
# -------------------------------------------------------------------
# This is used with FastAPI's `Depends(get_db)` in routers
# Provides an async session and ensures it is closed after use
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()