# ==============================================================================
# REDIS CACHING CLIENT LAYER (redis_client.py)
# ==============================================================================
# WHAT IS REDIS CACHING?
# Redis is an ultra-fast, in-memory Key-Value database (runs in RAM).
# While PostgreSQL stores data on DISK (takes 10-50ms to read), Redis stores data
# in RAM (takes < 2ms to read).
#
# HOW DOES THE REDIS CACHE EXCHANGE WORK IN WIRING AI?
# 1. READ (get_cached_data): FastAPI checks Redis first before doing heavy work.
#    - If Redis has the key ("CACHE HIT"), FastAPI returns data in < 2ms!
# 2. WRITE (set_cached_data): When Celery or FastAPI computes a heavy result, it 
#    saves the JSON data into Redis with a TTL (Time-To-Live, e.g. 3600 seconds).
# 3. EXPIRATION (TTL): Redis automatically deletes old cache keys after 1 hour 
#    so memory stays clean.
# ==============================================================================

import os
import json
import logging
from typing import Any, Optional, cast
from dotenv import load_dotenv
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Load environment configuration
db_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(db_dir, "db", ".env"))
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://:redis_password@localhost:6379/0")
DEFAULT_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # Default 1 hour (3600s)

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Returns an async Redis client singleton connection pool.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
    return _redis_client


async def close_redis_client() -> None:
    """
    Closes the Redis connection pool cleanly.
    """
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


async def ping_redis() -> bool:
    """
    Health check helper to verify Redis connectivity.
    """
    try:
        client = get_redis_client()
        result = await cast(Any, client.ping())
        return bool(result)
    except Exception as e:
        logger.warning(f"[Redis] Health check ping failed: {e}")
        return False


async def get_cached_data(key: str) -> Optional[Any]:
    """
    Retrieves and JSON-deserializes cached data by key.
    Returns None if key does not exist or Redis is offline.
    """
    try:
        client = get_redis_client()
        cached_value = await client.get(key)
        if cached_value:
            logger.info(f"[Redis Cache HIT] Key: '{key}'")
            return json.loads(cached_value)
        logger.info(f"[Redis Cache MISS] Key: '{key}'")
        return None
    except Exception as e:
        logger.error(f"[Redis] Error reading cache key '{key}': {e}")
        return None


async def set_cached_data(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    JSON-serializes and stores data in Redis with an optional TTL in seconds.
    Defaults to REDIS_CACHE_TTL (3600s).
    """
    try:
        client = get_redis_client()
        expire_time = ttl if ttl is not None else DEFAULT_CACHE_TTL
        serialized_value = json.dumps(value)
        await client.set(name=key, value=serialized_value, ex=expire_time)
        logger.info(f"[Redis Cache SET] Key: '{key}' (TTL: {expire_time}s)")
        return True
    except Exception as e:
        logger.error(f"[Redis] Error setting cache key '{key}': {e}")
        return False


async def delete_cached_data(key: str) -> bool:
    """
    Removes a cached key from Redis.
    """
    try:
        client = get_redis_client()
        await client.delete(key)
        logger.info(f"[Redis Cache DELETE] Key: '{key}'")
        return True
    except Exception as e:
        logger.error(f"[Redis] Error deleting cache key '{key}': {e}")
        return False


async def clear_cache_pattern(pattern: str = "wiring_ai:*") -> int:
    """
    Deletes all keys matching a specific pattern.
    Useful for invalidating temporal datasheet caches.
    """
    try:
        client = get_redis_client()
        keys = await client.keys(pattern)
        if keys:
            deleted_count = await client.delete(*keys)
            logger.info(f"[Redis Cache CLEAR] Pattern '{pattern}' cleared {deleted_count} keys.")
            return deleted_count
        return 0
    except Exception as e:
        logger.error(f"[Redis] Error clearing cache pattern '{pattern}': {e}")
        return 0
