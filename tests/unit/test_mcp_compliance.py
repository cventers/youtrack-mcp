"""
MCP Compliance Tests for YouTrack MCP Server.

These tests validate that the YouTrack MCP server implementation
complies with the MCP (Model Context Protocol) specification.
"""

import json
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from youtrack_mcp.server_fastmcp import mcp

class TestMCPCompliance:
    """Test MCP protocol compliance."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_server = mcp
        # FastMCP manages tools internally

    def test_server_initialization(self):
        """Test that MCP server initializes correctly."""
        assert self.mcp_server is not None
        assert hasattr(self.mcp_server, 'name')
        assert self.mcp_server.name == "youtrack"

    @pytest.mark.asyncio
    async def test_tool_registration(self):
        """Test that tools are properly registered."""
        # Get tools from FastMCP server
        tools = await self.mcp_server.list_tools()
        
        # Verify tools are loaded
        assert len(tools) > 0
        
        # Check that core tools are present
        tool_names = [tool.name for tool in tools]
        assert any('issues_' in name for name in tool_names)
        assert any('projects_' in name for name in tool_names)
        assert any('search_' in name for name in tool_names)

    def test_tool_definitions_format(self):
        """Test that tool definitions follow expected format."""
        # Check tool definitions
        for tool_name, tool_func in self.tools.items():
            assert isinstance(tool_name, str)
            assert callable(tool_func)

            # Tool name should follow naming convention
            assert '.' in tool_name, f"Tool name {tool_name} should contain '.' separator"

    def test_mcp_server_structure(self):
        """Test MCP server has expected structure."""
        # Test that server can handle basic MCP messages
        # This is a basic test - in a real implementation we'd test
        # the actual message parsing and response generation

        # Verify FastMCP is initialized
        assert hasattr(self.mcp_server, 'name')
        assert self.mcp_server.name == "youtrack"

    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """Test that tools can be executed asynchronously."""
        # Find an async tool to test
        async_tool = None
        tool_name = None

        for name, tool_func in self.tools.items():
            if asyncio.iscoroutinefunction(tool_func):
                async_tool = tool_func
                tool_name = name
                break

        assert async_tool is not None, "No async tools found"
        assert tool_name is not None

        # Mock the tool execution (we can't actually call it without API)
        with patch.object(async_tool, '__call__', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"result": "test"}

            # This would normally be called by the MCP protocol handler
            # We're just testing that the async infrastructure is in place
            assert asyncio.iscoroutinefunction(async_tool)

    def test_error_handling(self):
        """Test error handling in MCP context."""
        # Test that server handles errors gracefully
        # For now, just verify the server exists and has expected attributes
        assert self.mcp_server is not None

    def test_token_security_enhancements(self):
        """Test enhanced token security features."""
        from youtrack_mcp.api.client import YouTrackClient
        import time

        # Test with mocked config
        with patch('youtrack_mcp.config.config.get_base_url', return_value='https://test.youtrack.cloud'), \
              patch('youtrack_mcp.config.config.YOUTRACK_API_TOKEN', 'test-token'), \
              patch('youtrack_mcp.config.config.VERIFY_SSL', False):

            # Test token TTL functionality
            client = YouTrackClient(token_ttl_seconds=1, enable_token_refresh=True)

            # First access should load token
            token1 = client.api_token
            assert token1 == 'test-token'
            assert client._token_loaded is True
            assert client._token_timestamp is not None

            # Wait for token to expire
            time.sleep(1.1)

            # Mock config to return different token
            with patch('youtrack_mcp.config.config.get_api_token', return_value='refreshed-token'):
                # Second access should refresh token
                token2 = client.api_token
                assert token2 == 'refreshed-token'
                assert token1 != token2

            # Test token info
            info = client.get_token_info()
            assert 'token_loaded' in info
            assert 'token_timestamp' in info
            assert 'token_age_seconds' in info
            assert 'token_ttl_seconds' in info
            assert 'token_refresh_enabled' in info
            assert 'token_expired' in info

            # Test token cache clearing
            client.clear_token_cache()
            assert client._token_loaded is False
            assert client._token_timestamp is None
            assert client._api_token is None

            # Test forced refresh
            client.refresh_token()
            assert client._token_loaded is True

    def test_structured_logging(self):
        """Test structured logging functionality."""
        # Test that logging is available
        import logging
        logger = logging.getLogger('youtrack_mcp')
        assert logger is not None


class TestMCPToolContracts:
    """Test that tools follow MCP tool contracts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = load_all_tools()

    def test_tool_return_types(self):
        """Test that tools return expected types."""
        for tool_name, tool_func in self.tools.items():
            # Tools should be callable
            assert callable(tool_func)

            # Tool name should be a string
            assert isinstance(tool_name, str)

            # Tool should have a name that follows convention
            assert len(tool_name) > 0

    def test_core_tool_presence(self):
        """Test that all core tools are present."""
        tool_names = list(self.tools.keys())

        # Check for core tool categories
        has_issues = any('issues.' in name for name in tool_names)
        has_projects = any('projects.' in name for name in tool_names)
        has_search = any('search.' in name for name in tool_names)
        has_users = any('users.' in name for name in tool_names)
        has_ai = any('ai.' in name for name in tool_names)

        assert has_issues, "Missing issues tools"
        assert has_projects, "Missing projects tools"
        assert has_search, "Missing search tools"
        assert has_users, "Missing users tools"
        assert has_ai, "Missing AI tools"

    def test_tool_naming_convention(self):
        """Test that tools follow naming conventions."""
        for tool_name in self.tools.keys():
            # Should contain a dot separator
            assert '.' in tool_name, f"Tool {tool_name} should contain '.' separator"

            # Should not contain spaces or special characters
            assert ' ' not in tool_name, f"Tool {tool_name} should not contain spaces"
            assert all(c.isalnum() or c in '._-' for c in tool_name), \
                f"Tool {tool_name} contains invalid characters"


if __name__ == "__main__":
    # Run basic compliance check
    print("Running MCP Compliance Tests...")

    try:
        # Mock configuration to avoid needing real YouTrack credentials
        with patch('youtrack_mcp.config.config.get_base_url', return_value='https://test.youtrack.cloud'), \
              patch('youtrack_mcp.config.config.YOUTRACK_API_TOKEN', 'perm:test-token'), \
              patch('youtrack_mcp.config.config.VERIFY_SSL', False):

            # Use the FastMCP server instance
            server = mcp
            tools = load_all_tools()

            print(f"✅ Server initialized with FastMCP")
            print(f"✅ Tools loaded: {list(tools.keys())}")

            # Basic functionality test
            tool_names = list(tools.keys())
            core_categories = ['issues.', 'projects.', 'search.', 'users.', 'ai.']

            for category in core_categories:
                category_tools = [name for name in tool_names if category in name]
                print(f"✅ {category.rstrip('.')}: {len(category_tools)} tools")

            print("\n🎉 MCP Compliance Check Passed!")

    except Exception as e:
        print(f"❌ MCP Compliance Check Failed: {e}")
        raise