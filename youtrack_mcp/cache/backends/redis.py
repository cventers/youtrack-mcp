"""Redis-based distributed cache backend."""

import json
from typing import Any, Dict, Optional

from .base import CacheBackend

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisCacheBackend(CacheBackend):
    """Redis-based distributed cache backend."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 300,
        key_prefix: str = "youtrack_mcp",
    ):
        """Initialize Redis cache backend.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (if required)
            default_ttl: Default TTL in seconds
            key_prefix: Prefix for all keys to avoid collisions
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis support requires 'redis' package. " "Install with: uv add 'redis[hiredis]'"
            )

        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.client = redis.Redis(
            host=host, port=port, db=db, password=password, decode_responses=True
        )
        self.stats = {"operations": 0}

    def _make_key(self, key: str, namespace: str) -> str:
        """Create namespaced Redis key."""
        return f"{self.key_prefix}:{namespace}:{key}"

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value)

    def _deserialize(self, value_json: str) -> Any:
        """Deserialize JSON string to value."""
        return json.loads(value_json)

    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Retrieve value from Redis."""
        redis_key = self._make_key(key, namespace)
        value = await self.client.get(redis_key)
        self.stats["operations"] += 1
        if value:
            return self._deserialize(value)
        return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = "default"
    ) -> None:
        """Store value in Redis with TTL."""
        redis_key = self._make_key(key, namespace)
        value_json = self._serialize(value)
        ttl = ttl or self.default_ttl
        await self.client.setex(redis_key, ttl, value_json)
        self.stats["operations"] += 1

    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete key from Redis."""
        redis_key = self._make_key(key, namespace)
        deleted = await self.client.delete(redis_key)
        self.stats["operations"] += 1
        return deleted > 0

    async def clear(self, namespace: Optional[str] = None) -> int:
        """Clear cache by namespace or all."""
        pattern = f"{self.key_prefix}:{namespace}:*" if namespace else f"{self.key_prefix}:*"
        keys = []
        # Use SCAN for better performance with large key sets
        async for key in self.client.scan_iter(match=pattern):
            keys.append(key)

        count = 0
        if keys:
            # Delete in batches for better performance
            batch_size = 100
            for i in range(0, len(keys), batch_size):
                batch = keys[i : i + batch_size]
                count += await self.client.delete(*batch)

        self.stats["operations"] += 1
        return count

    async def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists."""
        redis_key = self._make_key(key, namespace)
        exists = await self.client.exists(redis_key)
        self.stats["operations"] += 1
        return exists > 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get basic Redis stats."""
        try:
            info = await self.client.info("stats")
            memory_info = await self.client.info("memory")
            keyspace_info = await self.client.info("keyspace")

            # Count keys with our prefix
            our_keys = 0
            async for _ in self.client.scan_iter(match=f"{self.key_prefix}:*", count=1000):
                our_keys += 1

            return {
                "connected": True,
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_connections_received": info.get("total_connections_received", 0),
                "used_memory_human": memory_info.get("used_memory_human", "unknown"),
                "our_keys": our_keys,
                "operations": self.stats["operations"],
                "key_prefix": self.key_prefix,
                "default_ttl": self.default_ttl,
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "operations": self.stats["operations"],
            }

    async def cleanup_expired(self) -> int:
        """Redis handles expiration automatically."""
        # Redis automatically removes expired keys, so this is a no-op
        # We could force expiration check by accessing all keys, but that's expensive
        return 0

    async def close(self):
        """Close Redis connection."""
        await self.client.close()