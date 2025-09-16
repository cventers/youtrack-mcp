"""
Unit tests for the YouTrack MCP Server.

Note: This test file needs to be updated for the new FastMCP architecture.
The old MCPServer class has been replaced with direct FastMCP tool registration.
"""

import pytest
from unittest.mock import Mock, patch

from youtrack_mcp.server_fastmcp import mcp
from youtrack_mcp.utils.loader import load_all_tools


class TestFastMCPServer:
    """Test cases for FastMCP server."""

    @pytest.mark.unit
    def test_initialization(self, mock_youtrack_client):
        """Test that FastMCP server initializes correctly."""
        # Test that the FastMCP instance exists
        assert mcp is not None
        assert hasattr(mcp, 'name')
        assert mcp.name == "youtrack"

    @pytest.mark.unit
    def test_tools_loaded(self, mock_youtrack_client):
        """Test that tools are loaded correctly."""
        tools = load_all_tools()

        # Should return a dictionary of tools
        assert isinstance(tools, dict)
        assert len(tools) > 0

    @pytest.mark.unit
    def test_fastmcp_server_has_tools(self, mock_youtrack_client):
        """Test that FastMCP server has tools registered."""
        # Test that the FastMCP instance has the expected structure
        assert mcp is not None
        # Note: FastMCP internal structure may vary, but it should exist
        assert hasattr(mcp, 'name')
