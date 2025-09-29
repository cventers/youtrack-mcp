"""Unified cache manager with multiple backend support."""

import asyncio
from enum import Enum
from typing import Any, Dict, List, Optional

from .backends.base import CacheBackend
from .backends.memory import MemoryCacheBackend
from .backends.sqlite import SQLiteCacheBackend


class CacheStrategy(str, Enum):
    """Cache strategy enumeration."""

    OFF = "off"
    MEMORY = "memory"
    SQLITE = "sqlite"
    SQLITE_HYBRID = "sqlite_hybrid"
    REDIS = "redis"


class UnifiedCacheManager:
    """Unified cache manager with multiple backend support."""

    def __init__(
        self,
        strategy: CacheStrategy = CacheStrategy.SQLITE_HYBRID,
        memory_config: Optional[Dict] = None,
        sqlite_config: Optional[Dict] = None,
        redis_config: Optional[Dict] = None,
    ):
        """Initialize unified cache manager.

        Args:
            strategy: Caching strategy to use
            memory_config: Configuration for memory backend
            sqlite_config: Configuration for SQLite backend
            redis_config: Configuration for Redis backend
        """
        self.strategy = strategy
        self.backends: List[CacheBackend] = []

        # Initialize backends based on strategy
        if strategy == CacheStrategy.OFF:
            # No caching
            pass
        elif strategy == CacheStrategy.MEMORY:
            # Memory only
            self.memory = MemoryCacheBackend(**(memory_config or {}))
            self.backends = [self.memory]
        elif strategy == CacheStrategy.SQLITE:
            # SQLite only
            # Extract optimization settings from config
            sqlite_cfg = sqlite_config or {}
            optimization_mode = sqlite_cfg.pop("optimization_mode", "balanced")
            self.sqlite = SQLiteCacheBackend(
                optimization_mode=optimization_mode,
                **sqlite_cfg
            )
            self.backends = [self.sqlite]
        elif strategy == CacheStrategy.SQLITE_HYBRID:
            # Memory (L1) + SQLite (L2)
            self.memory = MemoryCacheBackend(**(memory_config or {}))
            # Extract optimization settings from config
            sqlite_cfg = sqlite_config or {}
            optimization_mode = sqlite_cfg.pop("optimization_mode", "balanced")
            self.sqlite = SQLiteCacheBackend(
                optimization_mode=optimization_mode,
                **sqlite_cfg
            )
            self.backends = [self.memory, self.sqlite]
        elif strategy == CacheStrategy.REDIS:
            # Redis only
            try:
                from .backends.redis import RedisCacheBackend

                self.redis = RedisCacheBackend(**(redis_config or {}))
                self.backends = [self.redis]
            except ImportError:
                raise ImportError(
                    "Redis backend requires 'redis' package. " "Install with: uv add 'redis[hiredis]'"
                )

    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get value from cache, checking each backend in order.

        For hybrid strategies, if a value is found in a slower backend,
        it's backfilled to faster backends for future access.

        Args:
            key: Cache key
            namespace: Cache namespace

        Returns:
            Cached value or None if not found
        """
        if self.strategy == CacheStrategy.OFF:
            return None

        for i, backend in enumerate(self.backends):
            value = await backend.get(key, namespace)
            if value is not None:
                # Backfill to faster caches for hybrid strategies
                if self.strategy == CacheStrategy.SQLITE_HYBRID and i > 0:
                    # Found in slower cache, populate faster ones
                    for j in range(i):
                        await self.backends[j].set(key, value, namespace=namespace)
                return value
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default",
        backends: Optional[List[str]] = None,
    ) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            namespace: Cache namespace
            backends: Optional list of specific backends to use
        """
        if self.strategy == CacheStrategy.OFF:
            return

        tasks = []
        for backend in self.backends:
            # If specific backends requested, filter
            if backends:
                backend_name = backend.__class__.__name__.lower()
                if not any(b in backend_name for b in backends):
                    continue
            tasks.append(backend.set(key, value, ttl, namespace))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete key from all backends.

        Args:
            key: Cache key
            namespace: Cache namespace

        Returns:
            True if deleted from at least one backend
        """
        if self.strategy == CacheStrategy.OFF:
            return False

        results = await asyncio.gather(
            *[backend.delete(key, namespace) for backend in self.backends],
            return_exceptions=True,
        )
        # Return True if any backend successfully deleted
        return any(r is True for r in results if not isinstance(r, Exception))

    async def clear(self, namespace: Optional[str] = None) -> int:
        """Clear cache across all backends.

        Args:
            namespace: Optional namespace to clear

        Returns:
            Total number of entries cleared
        """
        if self.strategy == CacheStrategy.OFF:
            return 0

        results = await asyncio.gather(
            *[backend.clear(namespace) for backend in self.backends],
            return_exceptions=True,
        )
        # Sum up all successful clears
        return sum(r for r in results if isinstance(r, int))

    async def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists in any backend.

        Args:
            key: Cache key
            namespace: Cache namespace

        Returns:
            True if key exists in any backend
        """
        if self.strategy == CacheStrategy.OFF:
            return False

        for backend in self.backends:
            if await backend.exists(key, namespace):
                return True
        return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics from all backends.

        Returns:
            Dictionary with cache statistics
        """
        if self.strategy == CacheStrategy.OFF:
            return {"strategy": "off", "caching_disabled": True}

        stats = {"strategy": self.strategy.value, "backends": {}}
        for backend in self.backends:
            backend_name = backend.__class__.__name__.replace("CacheBackend", "").lower()
            try:
                stats["backends"][backend_name] = await backend.get_stats()
            except Exception as e:
                stats["backends"][backend_name] = {"error": str(e)}
        return stats

    async def cleanup_expired(self) -> Dict[str, int]:
        """Cleanup expired entries from all backends.

        Returns:
            Dictionary mapping backend names to number of entries cleaned
        """
        if self.strategy == CacheStrategy.OFF:
            return {}

        results = {}
        for backend in self.backends:
            backend_name = backend.__class__.__name__.replace("CacheBackend", "").lower()
            try:
                results[backend_name] = await backend.cleanup_expired()
            except Exception as e:
                results[backend_name] = -1  # Indicate error
        return results

    async def close(self):
        """Close all backend connections."""
        for backend in self.backends:
            if hasattr(backend, "close"):
                await backend.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()