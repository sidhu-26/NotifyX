"""
Core Redis client — singleton connection with utility helpers.
Used as the base for future rate limiting and queue operations.
"""

import redis
import os
from dotenv import load_dotenv

load_dotenv()

# Singleton Redis connection
_redis_client = None


def get_redis_client() -> redis.Redis:
    """Get or create a Redis connection singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            decode_responses=True,
        )
    return _redis_client


def increment_key(key: str, ttl: int = 60) -> int:
    """
    Increment a key and set expiry if it's new.
    Returns the new count. Useful for rate limiting.
    """
    client = get_redis_client()
    count = client.incr(key)
    if count == 1:
        client.expire(key, ttl)
    return count


def set_key(key: str, value: str, ttl: int = 300) -> bool:
    """Set a key with expiry. Returns True on success."""
    client = get_redis_client()
    return client.setex(key, ttl, value)


def get_key(key: str) -> str | None:
    """Get a key's value. Returns None if key doesn't exist."""
    client = get_redis_client()
    return client.get(key)


def delete_key(key: str) -> bool:
    """Delete a key. Returns True if key existed."""
    client = get_redis_client()
    return bool(client.delete(key))
