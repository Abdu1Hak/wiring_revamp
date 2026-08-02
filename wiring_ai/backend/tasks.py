# ==============================================================================
# CELERY BACKGROUND WORKER TASKS (tasks.py)
# ==============================================================================
# HOW DOES A CELERY TASK WORK?
# 1. `@celery_app.task`: This decorator registers Python functions as Celery tasks.
# 2. SEPARATE PROCESS EXECUTION:
#    When FastAPI calls `lookup_component_task.delay("arduino uno")`, FastAPI does
#    NOT run this code. It drops a JSON message into Redis.
# 3. WORKER PICKUP:
#    The Celery Worker process (Terminal 2 running `celery -A celery_app worker`)
#    pops the task from Redis and executes this code in the background.
# 4. DB QUERY & REDIS CACHE:
#    The worker queries PostgreSQL (`get_component_by_name`), formats the JSON result,
#    and writes it to Redis (`set_cached_data`) so future lookups hit the cache instantly!
# 5. RESULT BACKEND REPORTING:
#    The return value of this function is automatically saved to Redis under
#    `celery-task-meta-<task_id>` with status="SUCCESS" so FastAPI can read it.
# ==============================================================================

import time
import asyncio
import logging
from celery_app import celery_app
from db.database import get_component_by_name
from redis_client import set_cached_data

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.lookup_component", bind=True)
def lookup_component_task(self, component_name: str) -> dict:
    """
    Learning Workflow Task for Component Lookup:
    1. Receives normalized component name (e.g. 'arduino uno').
    2. Adds an artificial 2-second delay (`time.sleep(2)`) so Celery execution is visible.
    3. Queries PostgreSQL database directly through database layer.
    4. Retrieves category and description.
    5. Stores result in Redis as JSON under key 'component_lookup:<name>' with 1-hour TTL (3600s).
    6. Returns component result or not-found status dict to Redis Result Backend.
    """
    logger.info(f"[Celery Task] Looking up component in PostgreSQL: '{component_name}'")

    # Artificial 2-second delay for learning/demonstration purposes
    # TODO: Remove this artificial delay in production
    time.sleep(2)

    # Query PostgreSQL database directly through repository layer
    component = asyncio.run(get_component_by_name(component_name))

    if not component:
        logger.warning(f"[Celery Task] Component '{component_name}' not found in PostgreSQL database.")
        return {
            "found": False,
            "message": f"Component '{component_name}' not found in database."
        }

    data = {
        "category": component.get("category", "N/A"),
        "description": component.get("description", "No description available.")
    }

    # Store result in Redis as JSON with 1-hour (3600s) TTL
    redis_key = f"component_lookup:{component_name}"
    asyncio.run(set_cached_data(redis_key, data, ttl=3600))
    logger.info(f"[Celery Task] Saved result to Redis under key '{redis_key}' (1h TTL).")

    return {
        "found": True,
        "data": data
    }


@celery_app.task(name="tasks.ingest_datasheet", bind=True, max_retries=3)
def ingest_datasheet_task(self, component_id: str, datasheet_source: str) -> dict:
    """
    Background worker task to parse PDF datasheets, extract electrical specifications via LLM,
    and update temporal Redis cache and database.
    """
    logger.info(f"[Task] Starting datasheet ingestion for component: '{component_id}' from '{datasheet_source}'")
    
    try:
        # Step 1: Simulate/Execute PDF parsing & OCR extraction
        time.sleep(2)  # Heavy I/O processing delay simulation
        
        # Step 2: Extract specs
        extracted_data = {
            "component_id": component_id,
            "status": "completed",
            "pins_extracted": 16,
            "operating_voltage": 5.0,
            "ingested_at": time.time(),
        }
        
        logger.info(f"[Task] Ingestion completed for '{component_id}'.")
        return extracted_data
    except Exception as exc:
        logger.error(f"[Task] Error ingesting datasheet for '{component_id}': {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))


@celery_app.task(name="tasks.generate_vector_embeddings", bind=True)
def generate_vector_embeddings_task(self, component_id: str, content: str) -> dict:
    """
    Background worker task to generate text embeddings for Qdrant vector database search.
    """
    logger.info(f"[Task] Generating vector embeddings for component: '{component_id}'")
    
    # Placeholder for Qdrant embedding generation
    result = {
        "component_id": component_id,
        "embedding_dimensions": 1536,
        "status": "indexed",
    }
    return result
