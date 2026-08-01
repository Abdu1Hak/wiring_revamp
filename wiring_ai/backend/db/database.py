# database.py
# -----------
# Handles all database connections and queries for the app.
#
# WHAT CHANGED FROM THE SQLITE VERSION:
#   - We now support TWO backends:
#       1. PostgreSQL via asyncpg (when DATABASE_URL is set in .env)
#       2. SQLite via aiosqlite (fallback for local dev without Docker)
#   - All query functions are now "async" — they don't block the server
#     while waiting for the database to respond.
#   - Raw SQL strings are replaced with SQLAlchemy's query builder.

import os
import json
from dotenv import load_dotenv
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .models import components_table, metadata

# Ensure .env inside backend/db/ or backend/ is loaded
db_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(db_dir, ".env"))
load_dotenv()

# ---------------------------------------------------------------------------
# ENGINE SETUP
# ---------------------------------------------------------------------------
# The "engine" manages the connection pool to PostgreSQL via asyncpg.

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is missing in backend/.env. "
        "PostgreSQL configuration is required."
    )

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
print("[DB] Using PostgreSQL (asyncpg)")

# ---------------------------------------------------------------------------
# SESSION FACTORY
# ---------------------------------------------------------------------------
# A "session" is a single unit of work with the database — it holds the
# connection open for a request and automatically releases it when done.
# "expire_on_commit=False" means objects are still readable after a commit.

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ---------------------------------------------------------------------------
# HELPER: Row → Python dict
# ---------------------------------------------------------------------------
def _parse_component(row_dict: dict) -> dict:
    """
    Converts a raw database row into the dict shape the rest of the app expects.

    PostgreSQL with SQLAlchemy already deserializes JSON columns into Python
    objects automatically. SQLite stores JSON as plain text strings, so we
    parse those manually here. The try/except handles both cases safely.
    """
    json_fields = [
        "pins", "power", "constraints", "compatible_boards",
        "tags", "board_pins", "input_voltage_range",
    ]
    for field in json_fields:
        value = row_dict.get(field)
        if isinstance(value, str):
            # SQLite path: value is a JSON string, parse it
            try:
                row_dict[field] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Last-resort fallback for the legacy comma-separated pins format
                if field == "pins":
                    row_dict[field] = value.split(",") if value else []
                else:
                    row_dict[field] = [] if field in (
                        "pins", "constraints", "compatible_boards", "tags", "board_pins"
                    ) else None
        elif value is None:
            # Column was NULL — set sensible empty defaults
            row_dict[field] = [] if field in (
                "pins", "constraints", "compatible_boards", "tags", "board_pins"
            ) else None

    # Normalise booleans (SQLite stores 0/1 integers for booleans)
    for field in ["has_wifi", "has_bluetooth", "_needs_review"]:
        if field in row_dict:
            row_dict[field] = bool(row_dict[field]) if row_dict[field] is not None else False

    return row_dict

# ---------------------------------------------------------------------------
# QUERIES
# ---------------------------------------------------------------------------

async def get_all_components() -> list[dict]:
    """
    Fetches every component from the database, sorted by category then name.
    Called by the GET /api/components endpoint on page load.
    """
    # Build the SELECT query using SQLAlchemy's query builder.
    # Equivalent SQL: SELECT * FROM components ORDER BY category, name
    query = select(components_table).order_by(
        components_table.c.category,
        components_table.c.name,
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(query)
        rows = result.mappings().all()  # returns list of dict-like RowMapping objects

    return [_parse_component(dict(row)) for row in rows]


async def get_components_by_ids(component_ids: list[str]) -> list[dict]:
    """
    Fetches specific components by their IDs.
    Called by the validation pipeline and generate-project endpoint.

    Note: SQLAlchemy's .in_() generates a safe parameterised query:
        SELECT * FROM components WHERE id IN ($1, $2, ...)
    No SQL injection risk.
    """
    if not component_ids:
        return []

    # Deduplicate IDs for the DB query (we re-expand duplicates below)
    unique_ids = list(set(component_ids))

    query = select(components_table).where(
        components_table.c.id.in_(unique_ids)
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(query)
        rows = result.mappings().all()

    # Build a lookup dict so we can re-expand duplicates in the original order.
    # Example: if the user selected ["led_red", "led_red"], we return two copies.
    lookup = {row["id"]: _parse_component(dict(row)) for row in rows}

    return [lookup[cid] for cid in component_ids if cid in lookup]