"""Abstract base class for cache backends."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Retrieve value from cache."""
        pass

    @abstractmethod
    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = "default"
    ) -> None:
        """Store value in cache with optional TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete key from cache."""
        pass

    @abstractmethod
    async def clear(self, namespace: Optional[str] = None) -> int:
        """Clear cache, optionally by namespace."""
        pass

    @abstractmethod
    async def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        pass