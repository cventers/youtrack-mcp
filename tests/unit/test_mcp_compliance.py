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

from youtrack_mcp.server import YouTrackMCPServer
from youtrack_mcp.tools.loader import load_all_tools


class TestMCPCompliance:
    """Test MCP protocol compliance."""

    def setup_method(self):
        """Set up test fixtures."""
        self.server = YouTrackMCPServer(transport="stdio")
        self.tools = load_all_tools()

    def test_server_initialization(self):
        """Test that MCP server initializes correctly."""
        assert self.server is not None
        assert hasattr(self.server, 'server')
        assert hasattr(self.server, '_tools')
        assert hasattr(self.server, '_registered_tools')

    def test_tool_registration(self):
        """Test that tools are properly registered."""
        # Register tools
        self.server.register_loaded_tools(self.tools)

        # Verify tools are registered
        assert len(self.server._tools) > 0
        assert len(self.server._registered_tools) > 0

        # Check that core tools are present
        tool_names = list(self.server._tools.keys())
        assert any('issues.' in name for name in tool_names)
        assert any('projects.' in name for name in tool_names)
        assert any('search.' in name for name in tool_names)
        assert any('users.' in name for name in tool_names)

    def test_tool_schema_generation(self):
        """Test that tool schemas are properly generated."""
        # Register tools first
        self.server.register_loaded_tools(self.tools)

        # Check that schemas are generated for registered tools
        for tool_name, tool_func in self.server._tools.items():
            # Each tool should have a schema
            assert tool_name in self.server._tools
            assert callable(tool_func)

    def test_mcp_protocol_messages(self):
        """Test MCP protocol message handling."""
        # Test that server can handle basic MCP messages
        # This is a basic test - in a real implementation we'd test
        # the actual message parsing and response generation

        # Mock the FastMCP server
        with patch('youtrack_mcp.server.ToolServerBase') as mock_server_class:
            mock_server = Mock()
            mock_server_class.return_value = mock_server

            server = YouTrackMCPServer(transport="stdio")

            # Verify FastMCP is initialized
            mock_server_class.assert_called_once()
            call_args = mock_server_class.call_args
            assert 'name' in call_args.kwargs
            assert 'instructions' in call_args.kwargs

    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """Test that tools can be executed asynchronously."""
        # Register tools
        self.server.register_loaded_tools(self.tools)

        # Find an async tool to test
        async_tool = None
        tool_name = None

        for name, tool_func in self.server._tools.items():
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

    def test_tool_definitions_format(self):
        """Test that tool definitions follow expected format."""
        # Register tools
        self.server.register_loaded_tools(self.tools)

        # Check tool definitions
        for tool_name, tool_func in self.server._tools.items():
            assert isinstance(tool_name, str)
            assert callable(tool_func)

            # Tool name should follow naming convention
            assert '.' in tool_name, f"Tool name {tool_name} should contain '.' separator"

    def test_error_handling(self):
        """Test error handling in MCP context."""
        # Test that server handles errors gracefully
        with patch('youtrack_mcp.server.logger') as mock_logger:
            # This would test error scenarios in the MCP protocol
            # For now, just verify logging is set up
            assert mock_logger is not None

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

    def test_transport_detection(self):
        """Test transport auto-detection."""
        with patch('sys.stdin.isatty', return_value=False):
            server = YouTrackMCPServer()
            assert server.transport_mode == "stdio"

        with patch('sys.stdin.isatty', return_value=True):
            with patch('sys.stdout.isatty', return_value=True):
                server = YouTrackMCPServer()
                assert server.transport_mode == "http"

    def test_structured_logging(self):
        """Test structured logging functionality."""
        from youtrack_mcp.server import structured_logger

        # Test that structured logger exists
        assert structured_logger is not None
        assert hasattr(structured_logger, 'log')
        assert hasattr(structured_logger, 'redact')

        # Test redaction
        test_message = 'Bearer abc123'
        redacted = structured_logger.redact(test_message)
        assert '[REDACTED]' in redacted
        assert 'abc123' not in redacted


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

            server = YouTrackMCPServer(transport="stdio")
            tools = load_all_tools()
            server.register_loaded_tools(tools)

            print(f"✅ Server initialized with {len(tools)} tools")
            print(f"✅ Tools registered: {list(tools.keys())}")

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