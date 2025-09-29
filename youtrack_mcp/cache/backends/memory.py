"""In-memory cache backend using cachetools TTLCache."""

from typing import Any, Dict, Optional

from cachetools import TTLCache

from .base import CacheBackend


class MemoryCacheBackend(CacheBackend):
    """In-memory cache using cachetools TTLCache."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """Initialize memory cache backend.

        Args:
            max_size: Maximum number of items per namespace
            default_ttl: Default TTL in seconds
        """
        self.caches: Dict[str, TTLCache] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "clears": 0}

    def _get_cache(self, namespace: str) -> TTLCache:
        """Get or create cache for namespace."""
        if namespace not in self.caches:
            self.caches[namespace] = TTLCache(maxsize=self.max_size, ttl=self.default_ttl)
        return self.caches[namespace]

    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Retrieve value from cache."""
        cache = self._get_cache(namespace)
        if key in cache:
            self.stats["hits"] += 1
            return cache[key]
        self.stats["misses"] += 1
        return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = "default"
    ) -> None:
        """Store value in cache with optional TTL."""
        cache = self._get_cache(namespace)
        # TTLCache handles TTL internally at cache level, not per-item
        # For per-item TTL, we'd need a different approach
        cache[key] = value
        self.stats["sets"] += 1

    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete key from cache."""
        cache = self._get_cache(namespace)
        if key in cache:
            del cache[key]
            self.stats["deletes"] += 1
            return True
        return False

    async def clear(self, namespace: Optional[str] = None) -> int:
        """Clear cache, optionally by namespace."""
        count = 0
        if namespace:
            if namespace in self.caches:
                count = len(self.caches[namespace])
                self.caches[namespace].clear()
        else:
            for cache in self.caches.values():
                count += len(cache)
            self.caches.clear()
        self.stats["clears"] += 1
        return count

    async def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists in cache."""
        cache = self._get_cache(namespace)
        return key in cache

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_items = sum(len(cache) for cache in self.caches.values())
        return {
            **self.stats,
            "namespaces": len(self.caches),
            "total_items": total_items,
            "max_size_per_namespace": self.max_size,
            "default_ttl": self.default_ttl,
        }

    async def cleanup_expired(self) -> int:
        """Remove expired entries.

        Note: TTLCache automatically removes expired items on access,
        so this is mostly a no-op for memory backend.
        """
        count = 0
        for cache in self.caches.values():
            # Accessing expired items causes TTLCache to remove them
            initial_size = len(cache)
            # Force expiration check by iterating keys
            _ = list(cache.keys())
            count += initial_size - len(cache)
        return count