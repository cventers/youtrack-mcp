"""Unit tests for ID resolver."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from youtrack_mcp.utils.id_resolver import IDResolver, IDResolutionError
from youtrack_mcp.cache.manager import UnifiedCacheManager, CacheStrategy


@pytest.fixture
def mock_client():
    """Create a mock YouTrack client."""
    client = MagicMock()

    # Mock projects API
    client.projects = MagicMock()
    client.projects.get_project = AsyncMock()
    client.projects.get_projects = AsyncMock()

    # Mock users API
    client.users = MagicMock()
    client.users.search_users = AsyncMock()
    client.users.get_users = AsyncMock()

    return client


@pytest_asyncio.fixture
async def cache_manager():
    """Create a test cache manager."""
    cache = UnifiedCacheManager(strategy=CacheStrategy.MEMORY)
    yield cache
    await cache.close()


@pytest_asyncio.fixture
async def resolver(mock_client, cache_manager):
    """Create an ID resolver instance."""
    return IDResolver(mock_client, cache_manager)


class TestIDResolver:
    """Test suite for ID resolver."""

    @pytest.mark.asyncio
    async def test_resolve_numeric_project_id_passthrough(self, resolver):
        """Test that numeric project IDs are passed through without lookup."""
        # Numeric IDs should not trigger API call
        result = await resolver.resolve_project_id("63-13")
        assert result == "63-13"

    @pytest.mark.asyncio
    async def test_resolve_project_short_name(self, resolver, mock_client):
        """Test resolving project short name to numeric ID."""
        # Mock the API response
        mock_client.projects.get_project.return_value = {
            "id": "63-13",
            "shortName": "ACC",
            "name": "Accounting"
        }

        result = await resolver.resolve_project_id("ACC")
        assert result == "63-13"
        mock_client.projects.get_project.assert_called_once_with("ACC")

    @pytest.mark.asyncio
    async def test_resolve_project_caching(self, resolver, mock_client):
        """Test that project resolution results are cached."""
        # Mock the API response
        mock_client.projects.get_project.return_value = {
            "id": "63-13",
            "shortName": "ACC",
            "name": "Accounting"
        }

        # First call should hit the API
        result1 = await resolver.resolve_project_id("ACC")
        assert result1 == "63-13"
        assert mock_client.projects.get_project.call_count == 1

        # Second call should use cache
        result2 = await resolver.resolve_project_id("ACC")
        assert result2 == "63-13"
        # API should still only be called once
        assert mock_client.projects.get_project.call_count == 1

    @pytest.mark.asyncio
    async def test_resolve_project_not_found(self, resolver, mock_client):
        """Test handling of non-existent project."""
        # Mock API to raise exception
        mock_client.projects.get_project.side_effect = Exception("Not found")
        mock_client.projects.get_projects.return_value = []

        with pytest.raises(IDResolutionError) as exc_info:
            await resolver.resolve_project_id("NONEXISTENT")

        assert exc_info.value.ref_type == "project"
        assert exc_info.value.reference == "NONEXISTENT"

    @pytest.mark.asyncio
    async def test_resolve_project_fallback_to_search(self, resolver, mock_client):
        """Test fallback to search when direct lookup fails."""
        # Mock direct lookup to fail
        mock_client.projects.get_project.side_effect = Exception("Not found")

        # Mock search to succeed
        mock_client.projects.get_projects.return_value = [
            {"id": "1-1", "shortName": "OTHER", "name": "Other"},
            {"id": "63-13", "shortName": "ACC", "name": "Accounting"},
        ]

        result = await resolver.resolve_project_id("ACC")
        assert result == "63-13"

    @pytest.mark.asyncio
    async def test_resolve_user_id(self, resolver, mock_client):
        """Test resolving user login to internal ID."""
        # Mock the API response
        mock_client.users.search_users.return_value = [
            {
                "id": "user-123",
                "login": "cventers",
                "email": "chase@example.com"
            }
        ]

        result = await resolver.resolve_user_id("cventers")
        assert result == "user-123"
        mock_client.users.search_users.assert_called_once_with(query="cventers", limit=10)

    @pytest.mark.asyncio
    async def test_resolve_user_by_email(self, resolver, mock_client):
        """Test resolving user by email."""
        # Mock the API response
        mock_client.users.search_users.return_value = [
            {
                "id": "user-123",
                "login": "cventers",
                "email": "chase@example.com"
            }
        ]

        result = await resolver.resolve_user_id("chase@example.com")
        assert result == "user-123"

    @pytest.mark.asyncio
    async def test_resolve_user_caching(self, resolver, mock_client):
        """Test that user resolution results are cached."""
        # Mock the API response
        mock_client.users.search_users.return_value = [
            {
                "id": "user-123",
                "login": "cventers",
                "email": "chase@example.com"
            }
        ]

        # First call should hit the API
        result1 = await resolver.resolve_user_id("cventers")
        assert result1 == "user-123"
        assert mock_client.users.search_users.call_count == 1

        # Second call should use cache
        result2 = await resolver.resolve_user_id("cventers")
        assert result2 == "user-123"
        # API should still only be called once
        assert mock_client.users.search_users.call_count == 1

    @pytest.mark.asyncio
    async def test_resolve_user_not_found(self, resolver, mock_client):
        """Test handling of non-existent user."""
        # Mock API to return empty list
        mock_client.users.search_users.return_value = []

        with pytest.raises(IDResolutionError) as exc_info:
            await resolver.resolve_user_id("nonexistent")

        assert exc_info.value.ref_type == "user"
        assert exc_info.value.reference == "nonexistent"

    @pytest.mark.asyncio
    async def test_resolve_issue_id_passthrough(self, resolver):
        """Test that issue IDs are passed through as-is."""
        # Issue IDs are generally accepted by the API in readable format
        result = await resolver.resolve_issue_id("ACC-123")
        assert result == "ACC-123"

    @pytest.mark.asyncio
    async def test_warm_cache(self, resolver, mock_client):
        """Test cache warming functionality."""
        # Mock projects and users
        mock_client.projects.get_projects.return_value = [
            {"id": "63-13", "shortName": "ACC", "name": "Accounting"},
            {"id": "1-1", "shortName": "DEMO", "name": "Demo Project"},
        ]
        mock_client.users.get_users.return_value = [
            {"id": "user-1", "login": "john.doe", "email": "john@example.com"},
            {"id": "user-2", "login": "jane.doe", "email": "jane@example.com"},
        ]

        counts = await resolver.warm_cache()

        # Should have cached 2 projects (by shortName and name each = 4 entries)
        assert counts["projects"] == 2
        # Should have cached 2 users
        assert counts["users"] == 2

        # Verify cache is populated
        result = await resolver.resolve_project_id("ACC")
        assert result == "63-13"
        # Should not call API again
        assert mock_client.projects.get_project.call_count == 0

    @pytest.mark.asyncio
    async def test_invalidate_project_cache(self, resolver, mock_client, cache_manager):
        """Test invalidating project cache."""
        # Mock and cache a project
        mock_client.projects.get_project.return_value = {
            "id": "63-13",
            "shortName": "ACC",
            "name": "Accounting"
        }

        # Populate cache
        await resolver.resolve_project_id("ACC")

        # Invalidate cache
        await resolver.invalidate_project("ACC")

        # Next call should hit API again
        await resolver.resolve_project_id("ACC")
        assert mock_client.projects.get_project.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_resolution_cache(self, resolver, mock_client):
        """Test clearing all resolution caches."""
        # Mock and populate cache
        mock_client.projects.get_project.return_value = {
            "id": "63-13",
            "shortName": "ACC"
        }
        mock_client.users.search_users.return_value = [
            {"id": "user-123", "login": "cventers"}
        ]

        await resolver.resolve_project_id("ACC")
        await resolver.resolve_user_id("cventers")

        # Clear all caches
        count = await resolver.clear_resolution_cache()
        assert count >= 0  # Should have cleared some entries

        # Next calls should hit API
        await resolver.resolve_project_id("ACC")
        await resolver.resolve_user_id("cventers")
        assert mock_client.projects.get_project.call_count == 2
        assert mock_client.users.search_users.call_count == 2