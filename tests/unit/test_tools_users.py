"""
Unit tests for user tools.

Tests users.search and related functionality.
"""

import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from youtrack_mcp.tools.users_tools import UsersTools


class TestUserTools:
    """Test user tools."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_tools = UsersTools()
        # Mock the API client
        self.mock_users_api = Mock()
        self.user_tools.users_api = self.mock_users_api

    def test_init(self):
        """Test initialization."""
        tools = UsersTools()
        assert tools.client is not None
        assert tools.users_api is not None

    def test_close_with_close_method(self):
        """Test closing resources when client has close method."""
        mock_client = Mock()
        mock_client.close = Mock()
        self.user_tools.client = mock_client

        # Mock hasattr to return True for 'close'
        with patch('builtins.hasattr', return_value=True):
            self.user_tools.close() if hasattr(self.user_tools, 'close') else None
            # Should not raise an exception

    def test_close_without_close_method(self):
        """Test closing resources when client lacks close method."""
        mock_client = Mock()
        # Don't add a close method to mock_client
        self.user_tools.client = mock_client

        # Should not raise an exception
        if hasattr(self.user_tools, 'close'):
            self.user_tools.close()

    @pytest.mark.asyncio
    async def test_search_users_success(self):
        """Test successful user search."""
        mock_users = [
            Mock(model_dump=lambda: {"id": "user-1", "login": "alice", "name": "Alice"}),
            Mock(model_dump=lambda: {"id": "user-2", "login": "bob", "name": "Bob"})
        ]
        self.mock_users_api.search_users = AsyncMock(return_value=mock_users)

        result = await self.user_tools.search("alice", limit=5)

        assert result["users"][0]["login"] == "alice"
        assert result["users"][1]["login"] == "bob"
        assert len(result["users"]) == 2
        self.mock_users_api.search_users.assert_called_once_with("alice", 5)

    @pytest.mark.asyncio
    async def test_search_users_with_dict_response(self):
        """Test user search with dict response."""
        mock_users = [
            {"id": "user-3", "login": "charlie", "name": "Charlie"},
            {"id": "user-4", "login": "david", "name": "David"}
        ]
        self.mock_users_api.search_users = AsyncMock(return_value=mock_users)

        result = await self.user_tools.search("char", limit=10)

        assert result["users"][0]["login"] == "charlie"
        assert result["users"][1]["login"] == "david"

    @pytest.mark.asyncio
    async def test_search_users_empty_result(self):
        """Test user search with no results."""
        self.mock_users_api.search_users = AsyncMock(return_value=[])

        result = await self.user_tools.search("nonexistent", limit=5)

        assert result["users"] == []
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_search_users_api_error(self):
        """Test user search with API error."""
        self.mock_users_api.search_users = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await self.user_tools.search("test", limit=5)

        assert "error" in result
        assert "API Error" in str(result["error"])

    @pytest.mark.asyncio
    async def test_search_users_default_limit(self):
        """Test user search with default limit."""
        mock_users = [Mock(model_dump=lambda: {"id": f"user-{i}", "login": f"user{i}", "name": f"User {i}"})
                      for i in range(10)]
        self.mock_users_api.search_users = AsyncMock(return_value=mock_users)

        result = await self.user_tools.search("user")

        assert len(result["users"]) == 10
        self.mock_users_api.search_users.assert_called_once_with("user", 10)

    @pytest.mark.asyncio
    async def test_search_users_special_characters(self):
        """Test user search with special characters."""
        mock_users = [
            Mock(model_dump=lambda: {"id": "user-5", "login": "user@domain", "name": "Special User"})
        ]
        self.mock_users_api.search_users = AsyncMock(return_value=mock_users)

        result = await self.user_tools.search("user@", limit=1)

        assert result["users"][0]["login"] == "user@domain"
        self.mock_users_api.search_users.assert_called_once_with("user@", 1)

    @pytest.mark.asyncio
    async def test_search_users_unicode(self):
        """Test user search with Unicode characters."""
        mock_users = [
            Mock(model_dump=lambda: {"id": "user-6", "login": "user123", "name": "用户"})
        ]
        self.mock_users_api.search_users = AsyncMock(return_value=mock_users)

        result = await self.user_tools.search("用户", limit=5)

        assert result["users"][0]["name"] == "用户"

    @pytest.mark.asyncio
    async def test_search_users_partial_match(self):
        """Test user search with partial match."""
        mock_users = [
            Mock(model_dump=lambda: {"id": "user-7", "login": "administrator", "name": "Admin"}),
            Mock(model_dump=lambda: {"id": "user-8", "login": "admin2", "name": "Admin 2"})
        ]
        self.mock_users_api.search_users = AsyncMock(return_value=mock_users)

        result = await self.user_tools.search("admin", limit=10)

        assert len(result["users"]) == 2
        assert any(u["login"] == "administrator" for u in result["users"])
        assert any(u["login"] == "admin2" for u in result["users"])

    def test_get_tool_definitions(self):
        """Test getting tool definitions."""
        tools = self.user_tools.get_tool_definitions()

        assert "users_search" in tools
        assert tools["users_search"]["description"]
        assert "query" in tools["users_search"]["input_schema"]["properties"]
        assert "limit" in tools["users_search"]["input_schema"]["properties"]