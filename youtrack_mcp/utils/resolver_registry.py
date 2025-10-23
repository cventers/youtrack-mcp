"""Singleton registry for ID resolver to ensure single instance across tools."""

from typing import Optional
from youtrack_mcp.cache.manager import UnifiedCacheManager
from youtrack_mcp.utils.id_resolver import IDResolver
from youtrack_mcp.logging import get_logger

logger = get_logger(__name__)


class ResolverRegistry:
    """Singleton registry for ID resolver instance.

    This ensures we have a single ID resolver instance shared across all tools,
    preventing duplicate cache managers and improving performance.
    """

    _instance: Optional[IDResolver] = None
    _cache_manager: Optional[UnifiedCacheManager] = None

    @classmethod
    def get_resolver(cls, client=None) -> IDResolver:
        """Get or create the singleton ID resolver instance.

        Args:
            client: Optional YouTrack client to associate with resolver

        Returns:
            The singleton IDResolver instance
        """
        if cls._instance is None:
            logger.info("Creating new ID resolver instance")
            if cls._cache_manager is None:
                cls._cache_manager = UnifiedCacheManager()
            cls._instance = IDResolver(client, cls._cache_manager)
        elif client and cls._instance.client is None:
            logger.info("Setting client reference on existing resolver")
            cls._instance.client = client
        return cls._instance

    @classmethod
    def clear(cls):
        """Clear the singleton instance (mainly for testing)."""
        cls._instance = None
        cls._cache_manager = None
        logger.debug("Cleared resolver registry")


# Global registry instance
resolver_registry = ResolverRegistry()