"""ID resolver with unified cache integration for YouTrack entities."""

import re
from typing import Dict, Optional

from youtrack_mcp.cache.manager import UnifiedCacheManager
from youtrack_mcp.logging import get_logger

logger = get_logger(__name__)


class IDResolutionError(Exception):
    """Raised when ID resolution fails."""

    def __init__(self, ref_type: str, reference: str):
        self.ref_type = ref_type
        self.reference = reference
        message = f"Could not resolve {ref_type} '{reference}'"
        super().__init__(message)


class IDResolver:
    """Resolves human-friendly IDs to YouTrack internal IDs with caching.

    This resolver handles the translation of human-readable identifiers
    (like project short names, user logins) to YouTrack's internal
    numeric IDs, with intelligent caching to minimize API calls.
    """

    # TTL configuration per entity type (in seconds)
    TTL_CONFIG = {
        "projects": 3600,  # 1 hour - projects rarely change
        "users": 3600,  # 1 hour - users relatively stable
        "issues": 1800,  # 30 minutes - issues more dynamic
        "bundles": 7200,  # 2 hours - bundle elements very stable
        "custom_fields": 3600,  # 1 hour - custom fields stable
    }

    def __init__(self, client, cache_manager: UnifiedCacheManager):
        """Initialize ID resolver.

        Args:
            client: YouTrack API client
            cache_manager: Unified cache manager instance
        """
        self.client = client
        self.cache = cache_manager

        # Regex patterns for ID detection
        self.patterns = {
            "numeric_project": re.compile(r"^\d+-\d+$"),  # e.g., "63-13"
            "readable_issue": re.compile(r"^[A-Z]+-\d+$"),  # e.g., "DEMO-123"
            "user_login": re.compile(r"^[a-z][a-z0-9._-]*$"),  # e.g., "john.doe"
            "email": re.compile(r"^[^@]+@[^@]+\.[^@]+$"),  # Basic email pattern
        }

    async def resolve_project_id(self, project_ref: str) -> str:
        """Resolve project reference to numeric ID.

        Args:
            project_ref: Project short name (e.g., "ACC") or numeric ID

        Returns:
            Numeric project ID (e.g., "63-13")

        Raises:
            ValueError: If project cannot be resolved
        """
        # Check if already numeric
        if self.patterns["numeric_project"].match(project_ref):
            logger.debug("Project reference is already numeric", project_ref=project_ref)
            return project_ref

        # Check cache
        cache_key = f"project:{project_ref}"
        cached_id = await self.cache.get(cache_key, namespace="id_resolution")
        if cached_id:
            logger.debug("Found project ID in cache", project_ref=project_ref, id=cached_id)
            return cached_id

        # Perform API lookup
        logger.info("Resolving project ID via API", project_ref=project_ref)
        try:
            # Try to get project by ID/short name
            project = await self.client.projects.get_project(project_ref)
            if project:
                internal_id = project.get("id")
                # Cache the result
                await self.cache.set(
                    cache_key,
                    internal_id,
                    ttl=self.TTL_CONFIG["projects"],
                    namespace="id_resolution",
                )
                logger.info(
                    "Resolved and cached project ID",
                    project_ref=project_ref,
                    id=internal_id,
                )
                return internal_id
        except Exception as e:
            logger.debug("Direct lookup failed, trying search", error=str(e))

        # If direct lookup fails, try search
        try:
            projects = await self.client.projects.get_projects(limit=100)
            for project in projects:
                if project.get("shortName") == project_ref or project.get("name") == project_ref:
                    internal_id = project.get("id")
                    # Cache the result
                    await self.cache.set(
                        cache_key,
                        internal_id,
                        ttl=self.TTL_CONFIG["projects"],
                        namespace="id_resolution",
                    )
                    logger.info(
                        "Resolved project ID via search",
                        project_ref=project_ref,
                        id=internal_id,
                    )
                    return internal_id

            raise IDResolutionError("project", project_ref)
        except Exception as e:
            logger.error("Failed to resolve project ID", project_ref=project_ref, error=str(e))
            raise IDResolutionError("project", project_ref)

    async def resolve_user_id(self, user_ref: str) -> str:
        """Resolve user reference to internal ID.

        Args:
            user_ref: User login, email, or ID

        Returns:
            Internal user ID

        Raises:
            ValueError: If user cannot be resolved
        """
        # Check cache
        cache_key = f"user:{user_ref}"
        cached_id = await self.cache.get(cache_key, namespace="id_resolution")
        if cached_id:
            logger.debug("Found user ID in cache", user_ref=user_ref, id=cached_id)
            return cached_id

        # Search for user
        logger.info("Resolving user ID via API", user_ref=user_ref)
        try:
            users = await self.client.users.search_users(query=user_ref, limit=10)
            for user in users:
                if (
                    user.get("login") == user_ref
                    or user.get("email") == user_ref
                    or user.get("id") == user_ref
                ):
                    internal_id = user.get("id")
                    # Cache the result
                    await self.cache.set(
                        cache_key,
                        internal_id,
                        ttl=self.TTL_CONFIG["users"],
                        namespace="id_resolution",
                    )
                    logger.info("Resolved and cached user ID", user_ref=user_ref, id=internal_id)
                    return internal_id

            raise IDResolutionError("user", user_ref)
        except Exception as e:
            logger.error("Failed to resolve user ID", user_ref=user_ref, error=str(e))
            raise IDResolutionError("user", user_ref)

    async def resolve_issue_id(self, issue_ref: str) -> str:
        """Resolve issue reference to internal ID.

        Args:
            issue_ref: Issue readable ID (e.g., "DEMO-123")

        Returns:
            Internal issue ID

        Note:
            For issues, we often just return the readable ID as-is
            since YouTrack APIs accept both formats.
        """
        # YouTrack APIs generally accept readable IDs directly
        # But we can cache issue metadata if needed
        return issue_ref

    async def resolve_custom_field_id(self, field_ref: str, project_id: Optional[str] = None) -> str:
        """Resolve custom field reference to internal ID.

        Args:
            field_ref: Field name or ID
            project_id: Optional project context

        Returns:
            Internal field ID

        Raises:
            ValueError: If field cannot be resolved
        """
        # Check cache
        cache_key = f"field:{field_ref}:{project_id or 'global'}"
        cached_id = await self.cache.get(cache_key, namespace="id_resolution")
        if cached_id:
            logger.debug("Found field ID in cache", field_ref=field_ref, id=cached_id)
            return cached_id

        # For now, return as-is (implementation depends on available API)
        # This is a placeholder for future enhancement
        return field_ref

    async def warm_cache(self) -> Dict[str, int]:
        """Pre-populate cache with common data.

        Returns:
            Dictionary with counts of cached items by type
        """
        counts = {"projects": 0, "users": 0, "custom_fields": 0}

        logger.info("Starting cache warm-up")

        # Warm project cache
        try:
            projects = await self.client.projects.get_projects(limit=100)
            for project in projects:
                cache_key = f"project:{project['shortName']}"
                await self.cache.set(
                    cache_key,
                    project["id"],
                    ttl=self.TTL_CONFIG["projects"],
                    namespace="id_resolution",
                )
                counts["projects"] += 1
                # Also cache by name
                if project.get("name"):
                    cache_key = f"project:{project['name']}"
                    await self.cache.set(
                        cache_key,
                        project["id"],
                        ttl=self.TTL_CONFIG["projects"],
                        namespace="id_resolution",
                    )
        except Exception as e:
            logger.error("Failed to warm project cache", error=str(e))

        # Warm user cache (top active users)
        try:
            users = await self.client.users.get_users(limit=50)
            for user in users:
                cache_key = f"user:{user['login']}"
                await self.cache.set(
                    cache_key,
                    user["id"],
                    ttl=self.TTL_CONFIG["users"],
                    namespace="id_resolution",
                )
                counts["users"] += 1
                # Also cache by email if available
                if user.get("email"):
                    cache_key = f"user:{user['email']}"
                    await self.cache.set(
                        cache_key,
                        user["id"],
                        ttl=self.TTL_CONFIG["users"],
                        namespace="id_resolution",
                    )
        except Exception as e:
            logger.error("Failed to warm user cache", error=str(e))

        logger.info(
            "Cache warm-up completed",
            projects=counts["projects"],
            users=counts["users"],
        )
        return counts

    async def invalidate_project(self, project_ref: str):
        """Invalidate cached project ID.

        Args:
            project_ref: Project reference to invalidate
        """
        cache_key = f"project:{project_ref}"
        await self.cache.delete(cache_key, namespace="id_resolution")
        logger.debug("Invalidated project cache", project_ref=project_ref)

    async def invalidate_user(self, user_ref: str):
        """Invalidate cached user ID.

        Args:
            user_ref: User reference to invalidate
        """
        cache_key = f"user:{user_ref}"
        await self.cache.delete(cache_key, namespace="id_resolution")
        logger.debug("Invalidated user cache", user_ref=user_ref)

    async def clear_resolution_cache(self):
        """Clear all ID resolution caches."""
        count = await self.cache.clear(namespace="id_resolution")
        logger.info("Cleared ID resolution cache", entries_cleared=count)
        return count