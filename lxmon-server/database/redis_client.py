"""
Redis client for caching and command queue management.
"""

import redis.asyncio as redis
import json
import logging
from typing import Any, Optional
from core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client wrapper for lxmon operations."""

    def __init__(self):
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis."""
        try:
            self.client = redis.from_url(settings.REDIS_URL)
            await self.client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def ping(self) -> bool:
        """Ping Redis to check connection."""
        if not self.client:
            await self.connect()
        return await self.client.ping()

    async def set_cache(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set cache value with expiration."""
        if not self.client:
            await self.connect()

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return await self.client.setex(key, expire, value)
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False

    async def get_cache(self, key: str) -> Optional[Any]:
        """Get cache value."""
        if not self.client:
            await self.connect()

        try:
            value = await self.client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value.decode('utf-8')
            return None
        except Exception as e:
            logger.error(f"Error getting cache: {e}")
            return None

    async def delete_cache(self, key: str) -> bool:
        """Delete cache key."""
        if not self.client:
            await self.connect()

        try:
            return await self.client.delete(key) > 0
        except Exception as e:
            logger.error(f"Error deleting cache: {e}")
            return False

    async def push_command(self, server_id: int, command: dict) -> bool:
        """Push command to server's command queue."""
        if not self.client:
            await self.connect()

        queue_key = f"commands:{server_id}"
        try:
            return await self.client.lpush(queue_key, json.dumps(command)) > 0
        except Exception as e:
            logger.error(f"Error pushing command: {e}")
            return False

    async def pop_command(self, server_id: int) -> Optional[dict]:
        """Pop command from server's command queue."""
        if not self.client:
            await self.connect()

        queue_key = f"commands:{server_id}"
        try:
            result = await self.client.rpop(queue_key)
            if result:
                return json.loads(result)
            return None
        except Exception as e:
            logger.error(f"Error popping command: {e}")
            return None

    async def get_info(self) -> dict:
        """Get Redis server information."""
        if not self.client:
            await self.connect()

        try:
            info = await self.client.info()
            return info
        except Exception as e:
            logger.error(f"Error getting Redis info: {e}")
            return {}

# Global Redis client instance
redis_client = RedisClient()
