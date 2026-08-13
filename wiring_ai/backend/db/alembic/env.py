# Alembic runs this file every time you run an "alembic" command.
# Its job is to:
#   1. Connect to the database
#   2. Tell Alembic which tables/metadata to track
#   3. Run migrations in the right mode (online = live DB, offline = generate SQL)

import os
import sys
from dotenv import load_dotenv
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# ---------------------------------------------------------------------------
# Make sure Python can find our backend modules (models.py, etc.)
# when alembic is run from the backend/ directory.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(db_dir, ".env"))
load_dotenv()  # reads DATABASE_URL from .env

# Import our table definitions so Alembic can diff them against the real DB
from db.models import metadata

# ---------------------------------------------------------------------------
# Standard Alembic boilerplate — reads logging config from alembic.ini
# ---------------------------------------------------------------------------
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic about our table definitions.
# "autogenerate" (alembic revision --autogenerate) uses this to detect changes.
target_metadata = metadata

# ---------------------------------------------------------------------------
# DB URL resolution:
#   1. Read DATABASE_URL from environment (set by .env)
#   2. Fall back to the URL in alembic.ini if not set
# ---------------------------------------------------------------------------
def get_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        # If DATABASE_URL isn't set, read from alembic.ini as fallback.
        # NOTE: Alembic migrations only run against a real Postgres DB.
        #       SQLite migration support is not implemented here intentionally —
        #       the app handles its own SQLite schema via seed_components.py.
        url = config.get_main_option("sqlalchemy.url")
    return url


# ---------------------------------------------------------------------------
# OFFLINE mode: generates migration SQL without connecting to the DB.
# Useful for reviewing what SQL will be executed before running it.
# Run with: alembic upgrade head --sql
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# ONLINE mode: connects to the real DB and runs migrations live.
# This is the mode used by: alembic upgrade head
# ---------------------------------------------------------------------------
async def run_async_migrations() -> None:
    """Creates an async engine and runs migrations within it."""
    url = get_url()
    # NullPool means no connection pooling — each migration step gets its own
    # fresh connection. This is the recommended setting for Alembic.
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection):
    """Synchronous migration runner — called by SQLAlchemy's run_sync helper."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Entry point for online mode — runs the async migration via asyncio."""
    import asyncio
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Alembic calls this file as a script — choose the right mode.
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
