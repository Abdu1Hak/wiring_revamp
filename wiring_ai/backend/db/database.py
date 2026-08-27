# database.py
# -----------
# Handles all database connections, sessions, and asynchronous queries for the application.
#
# DATABASE CONFIGURATION:
#   - Primary & Only Backend: PostgreSQL via asyncpg driver (configured via DATABASE_URL).
#   - All query functions are async to ensure non-blocking I/O during database transactions.
#   - Database queries utilize SQLAlchemy's query builder (select, in_) for type safety
#     and parameterization against SQL injection.

from qdrant_client.conversions.common_types import PointsSelector
import os
import json
from dotenv import load_dotenv
# common query builders
from sqlalchemy import select, text, func, or_
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from .models import components_table, metadata

# ---------------------------------------------------------------------------
# ENVIRONMENT CONFIGURATION
# ---------------------------------------------------------------------------
# Load environment variables from backend/db/.env or backend/.env if available.
db_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(db_dir, ".env"))
load_dotenv()

# ---------------------------------------------------------------------------
# ENGINE SETUP
# ---------------------------------------------------------------------------
# The engine establishes and manages the connection pool to PostgreSQL via asyncpg.
# pool_pre_ping=True checks connection health before issuing queries.

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
# AsyncSessionLocal creates asynchronous database sessions for unit-of-work interactions.
# - bind=engine connects the session factory to the configured PostgreSQL engine.
# - expire_on_commit=False keeps model attribute state available post-commit without requiring re-fetches.

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

# ---------------------------------------------------------------------------
# HELPER: Row Parsing & Sanitization
# in databases, some values arent exactly the same as True or False, or numbers 
# so they need to be standardized so the app can read them as python compatible
# ---------------------------------------------------------------------------
def _parse_component(row_dict: dict) -> dict:
    """
    Converts a database row dictionary into the structured format required by the application.

    - Deserializes JSON fields if they are returned as string representations or guarantees list defaults if NULL.
    - Standardizes boolean values for component flag attributes.
    """
    json_fields = [
        "pins", "interface", "power", "constraints", "compatible_boards",
        "tags", "board_pins", "input_voltage_range",
    ]
    for field in json_fields:
        value = row_dict.get(field)
        if isinstance(value, str):
            # Parse JSON string values if necessary
            try:
                row_dict[field] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Fallback for legacy comma-separated values in pins field
                if field == "pins":
                    row_dict[field] = value.split(",") if value else []
                else:
                    row_dict[field] = [] if field in (
                        "pins", "constraints", "compatible_boards", "tags", "board_pins"
                    ) else None
        elif value is None:
            # Set default empty collections or None for missing/NULL columns
            row_dict[field] = [] if field in (
                "pins", "constraints", "compatible_boards", "tags", "board_pins"
            ) else None

    # Ensure boolean flags strictly evaluate to Python booleans
    for field in ["has_wifi", "has_bluetooth", "_needs_review"]:
        if field in row_dict:
            row_dict[field] = bool(row_dict[field]) if row_dict[field] is not None else False

    # Normalize interface if missing
    if not row_dict.get("interface") or not isinstance(row_dict["interface"], dict):
        pins = row_dict.get("pins") or []
        cat = row_dict.get("category", "")
        has_sda = any("SDA" in p.get("name", "").upper() for p in pins if isinstance(p, dict))
        has_scl = any("SCL" in p.get("name", "").upper() for p in pins if isinstance(p, dict))
        
        if has_sda and has_scl:
            protocol = "i2c"
        elif cat == "passive":
            protocol = "passive"
        elif any(k in row_dict.get("name", "").lower() for k in ["motor", "pump"]):
            protocol = "sub_peripheral"
        else:
            protocol = "gpio"

        row_dict["interface"] = {
            "protocol": protocol,
            "i2c_address": None
        }

    return row_dict

# ---------------------------------------------------------------------------
# DATABASE QUERIES
# ---------------------------------------------------------------------------

async def get_all_components() -> list[dict]:
    """
    Fetches all components from the PostgreSQL database, sorted alphabetically by category and name.
    
    Returns:
        list[dict]: A list of formatted component dictionaries.
    """
    # query is a variable that stores SQLAlchemy instructions on how to initially order the rows
    # it selects the database table and orders it by category first then name. 
    query = select(components_table).order_by(
        components_table.c.category,
        components_table.c.name,
    )
    

    # Execute query asynchronously within a managed session context
    async with AsyncSessionLocal() as session:
        result = await session.execute(query)
        rows = result.mappings().all()  # Map database records to key-value row mappings

    # Convert each database record through the parsing helper
    return [_parse_component(dict(row)) for row in rows]


async def get_components_by_ids(component_ids: list[str]) -> list[dict]:
    """
    Fetches specific components by their unique IDs from the PostgreSQL database.
    Used by validation pipelines and project generation endpoints.

    Args:
        component_ids (list[str]): List of component identifier strings to retrieve.

    Returns:
        list[dict]: List of formatted component dictionaries in the requested order (preserving duplicate requests).
    """
    if not component_ids:
        return []

    # Extract unique IDs to minimize query payload size
    unique_ids = list(set(component_ids))

    # Construct parameterized IN clause query to prevent SQL injection vulnerabilities
    # SQL Equivalent: SELECT * FROM components WHERE id IN ($1, $2, ...)
    query = select(components_table).where(
        components_table.c.id.in_(unique_ids)
    )

    # Execute asynchronous database query
    async with AsyncSessionLocal() as session:
        result = await session.execute(query)
        rows = result.mappings().all()

    # Map retrieved database rows by ID for fast lookup and duplicate preservation
    lookup = {row["id"]: _parse_component(dict(row)) for row in rows}

    # Reconstruct result array preserving the original requested component_ids order and duplicates
    return [lookup[cid] for cid in component_ids if cid in lookup]


async def get_component_by_name(component_name: str) -> dict | None:
    """
    Fetches a single component by its name or ID (case-insensitive) from the PostgreSQL database.

    Args:
        component_name (str): Component name or ID string (e.g., "Arduino Uno" or "arduino_uno").

    Returns:
        dict | None: Formatted component dictionary if found, otherwise None.
    """
    if not component_name:
        return None

    norm = component_name.strip().lower()
    id_variant = norm.replace(" ", "_")

    query = select(components_table).where(
        or_(
            func.lower(components_table.c.name) == norm,
            func.lower(components_table.c.id) == norm,
            func.lower(components_table.c.id) == id_variant,
        )
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(query)
        row = result.mappings().first()
        if row:
            return _parse_component(dict(row))
        return None


async def delete_component_by_id(component_id:str) -> bool: 
    """
    Delete a component from the postgreSQL database and purges its vector chunks from the Qdrant VectorDB 
    """ 

    if not component_id: 
        return False 
    
    norm_id = component_id.strip().lower() 

    # 1. delete from postgreSQL 
    async with AsyncSessionLocal() as session: 
        result = await session.execute(
            text("DELETE FROM components WHERE LOWER(id) = LOWER(:id) OR LOWER(name) = LOWER(:id)"),
            {"id": norm_id}
        )
        await session.commit()
        # pyrefly: ignore [missing-attribute]
        deleted_count = result.rowcount or 0 


    # 2. delete vectors from qdrant 
    try: 
        q_host = os.getenv("QDRANT_HOST", "localhost")
        q_port = int(os.getenv("QDRANT_PORT", "6333"))
        q_key = os.getenv("QDRANT_API_KEY", None)

        qdrant = QdrantClient(host=q_host, port=q_port, api_key=q_key, https=False, timeout=10)
        qdrant.delete(
            collection_name="datasheets",
            points_selector=Filter(
                must=[FieldCondition(
                    key="component_id",
                    match=MatchValue(value=norm_id)
                )]
            )
        )
    except Exception as e: 
        print(f"[DB DELETE]: Warning: Could not purge Qdrant points for {norm_id}: {e}")
    print("Deleted Rows", deleted_count)
    return deleted_count > 0 


async def update_component_name(component_id: str, new_name: str) -> dict | None:
    """
    Updates the display name of a component in the PostgreSQL database.
    """
    if not component_id or not new_name or not new_name.strip():
        return None

    norm_id = component_id.strip()
    clean_name = new_name.strip()

    async with AsyncSessionLocal() as session:
        query = (
            components_table.update()
            .where(
                or_(
                    func.lower(components_table.c.id) == norm_id.lower(),
                    components_table.c.id == norm_id,
                )
            )
            .values(name=clean_name)
            .returning(components_table)
        )
        result = await session.execute(query)
        await session.commit()
        row = result.mappings().first()
        if row:
            return _parse_component(dict(row))
        return None


async def update_component_metadata(component_id: str, update_data: dict) -> dict | None:
    """
    Updates component metadata fields (name, power, interface) in the PostgreSQL database.
    
    Args:
        component_id (str): Component ID or name to update
        update_data (dict): Dictionary with fields to update (name, power, interface, etc.)
    
    Returns:
        dict | None: Updated component dictionary if successful, None otherwise
    """
    if not component_id or not update_data:
        return None

    norm_id = component_id.strip()
    
    # Convert power/interface dicts to JSON if needed
    values_to_update = {}
    for key, value in update_data.items():
        if key in ["power", "interface"]:
            # Merge with existing data (don't overwrite completely)
            values_to_update[key] = value
        else:
            values_to_update[key] = value

    async with AsyncSessionLocal() as session:
        query = (
            components_table.update()
            .where(
                or_(
                    func.lower(components_table.c.id) == norm_id.lower(),
                    components_table.c.id == norm_id,
                )
            )
            .values(**values_to_update)
            .returning(components_table)
        )
        result = await session.execute(query)
        await session.commit()
        row = result.mappings().first()
        if row:
            return _parse_component(dict(row))
        return None
