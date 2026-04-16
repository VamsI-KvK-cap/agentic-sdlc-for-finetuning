import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# -- project imports --
from web.database import DATABASE_URL, Base
import web.executions.models  # noqa: F401  # ensure models are registered

"""
Alembic environment configuration for async migrations.

Handles both:
- Offline migrations (SQL script generation)
- Online migrations (executed against the database)

CONCEPT: Alembic uses this file to:
1. Load database configuration
2. Discover ORM models (via metadata)
3. Execute schema migrations in either offline or online mode
"""

# Alembic config object (from alembic.ini)
config = context.config

# Override DB URL dynamically (useful for env-based configs)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Configure Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata used for autogeneration (detecting schema changes)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in offline mode (no DB connection).

    Generates SQL scripts instead of executing them directly.

    CONCEPT:
    - Useful for CI/CD pipelines or manual review
    - Does not require a live database connection
    """
    url = config.get_main_option("sqlalchemy.url")

    # Configure Alembic context with URL only (no engine)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,  # inline parameters into SQL
        dialect_opts={"paramstyle": "named"},
    )

    # Begin migration transaction and run
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """
    Execute migrations using a provided DB connection.

    CONCEPT:
    - This function is run inside a synchronous context
    - Required because Alembic core is sync, even when using async engine

    Args:
        connection: Active database connection.
    """
    # Bind connection and metadata to Alembic context
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    # Execute migrations within a transaction
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Create async engine and run migrations.

    CONCEPT:
    - Uses SQLAlchemy async engine
    - Bridges async → sync using connection.run_sync()
    - Ensures proper cleanup after execution
    """
    # Create async engine from Alembic config
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # no connection pooling for migrations
    )

    # Establish connection and run migrations
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    # Dispose engine to close all connections
    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in online mode (with DB connection).

    CONCEPT:
    - This is the default mode when running `alembic upgrade`
    - Uses asyncio event loop to execute async migrations
    """
    asyncio.run(run_async_migrations())


# Determine execution mode and run appropriate migration flow
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()