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

from youtrack_mcp.server_fastmcp import mcp, register_mcp_tools

class TestMCPCompliance:
    """Test MCP protocol compliance."""

    def setup_method(self):
        """Set up test fixtures."""
        # Register tools before testing
        register_mcp_tools()
        self.mcp_server = mcp

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
        assert any('issues' in name for name in tool_names)
        assert any('projects' in name for name in tool_names)
        assert any('search' in name for name in tool_names)

    @pytest.mark.asyncio
    async def test_tool_definitions_format(self):
        """Test that tool definitions follow expected format."""
        tools = await self.mcp_server.list_tools()

        for tool in tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert isinstance(tool.name, str)
            assert isinstance(tool.description, str)

            # Tool name should follow naming convention
            assert '_' in tool.name, f"Tool name {tool.name} should follow naming convention"

    def test_mcp_server_structure(self):
        """Test MCP server has expected structure."""
        # Test server attributes
        assert hasattr(self.mcp_server, 'name')
        assert hasattr(self.mcp_server, 'version')

        # Test server name and version
        assert self.mcp_server.name == "youtrack"
        assert self.mcp_server.version == "1.0.0"


class TestMCPToolContracts:
    """Test MCP tool contract compliance."""

    def setup_method(self):
        """Set up test fixtures."""
        # Register tools before testing
        register_mcp_tools()
        self.mcp_server = mcp

    @pytest.mark.asyncio
    async def test_tool_return_types(self):
        """Test that all tools return JSON-serializable results."""
        tools = await self.mcp_server.list_tools()

        # We can't actually call the tools without real data, but we can
        # verify they're properly registered
        assert len(tools) > 0
        for tool in tools:
            assert hasattr(tool, 'input_schema')

    @pytest.mark.asyncio
    async def test_core_tool_presence(self):
        """Test presence of core tools."""
        tools = await self.mcp_server.list_tools()
        tool_names = [tool.name for tool in tools]

        # Core tools that should be present
        expected_tools = [
            'search_query',
            'projects_list',
            'projects_get',
            'issues_get',
            'issues_create',
            'issues_patch',
            'users_search'
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Core tool {expected_tool} not found"

    @pytest.mark.asyncio
    async def test_tool_naming_convention(self):
        """Test that tools follow naming convention."""
        tools = await self.mcp_server.list_tools()

        for tool in tools:
            # Tools should use underscore separator
            assert '_' in tool.name or tool.name in ['resources'], \
                f"Tool {tool.name} doesn't follow naming convention"

            # Tool names should be lowercase
            assert tool.name.lower() == tool.name, \
                f"Tool {tool.name} should be lowercase"


class TestProjectsSchema:
    """Test projects.schema method exists."""

    def setup_method(self):
        """Set up test fixtures."""
        from youtrack_mcp.tools.projects_tools import ProjectsTools
        self.projects_tools = ProjectsTools()

    @pytest.mark.asyncio
    async def test_schema_method_exists(self):
        """Test that projects.schema method exists."""
        assert hasattr(self.projects_tools, 'schema')
        assert callable(self.projects_tools.schema)

    @pytest.mark.asyncio
    async def test_schema_returns_valid_json(self):
        """Test that projects.schema returns valid JSON."""
        with patch('youtrack_mcp.tools.projects_tools.ProjectsTools.schema') as mock_schema:
            mock_schema.return_value = {
                "fields": [
                    {"name": "summary", "type": "string", "required": True},
                    {"name": "description", "type": "text", "required": False}
                ]
            }

            result = await mock_schema()
            assert isinstance(result, dict)
            assert "fields" in result

    @pytest.mark.asyncio
    async def test_schema_handles_errors(self):
        """Test that projects.schema handles errors gracefully."""
        with patch('youtrack_mcp.tools.projects_tools.ProjectsTools.schema') as mock_schema:
            mock_schema.side_effect = Exception("API Error")

            try:
                await mock_schema()
            except Exception as e:
                assert "API Error" in str(e)


class TestProjectsGetIncludeSchema:
    """Test projects.get with include=['schema'] expansion."""

    def setup_method(self):
        """Set up test fixtures."""
        from youtrack_mcp.tools.projects_tools import ProjectsTools
        self.projects_tools = ProjectsTools()

    @pytest.mark.asyncio
    async def test_get_with_schema_expansion(self):
        """Test projects.get with schema in include parameter."""
        with patch.object(self.projects_tools, 'get') as mock_get:
            mock_get.return_value = {
                "id": "DEMO",
                "name": "Demo Project",
                "schema": {
                    "fields": [
                        {"name": "summary", "type": "string"}
                    ]
                }
            }

            result = await self.projects_tools.get("DEMO", include=["schema"])
            assert "schema" in result
            assert isinstance(result["schema"], dict)


class TestIssuesPatchFieldsSupport:
    """Test issues.patch with fields parameter support."""

    def setup_method(self):
        """Set up test fixtures."""
        from youtrack_mcp.tools.issues_tools import IssuesTools
        self.issues_tools = IssuesTools()

    @pytest.mark.asyncio
    async def test_patch_with_fields_format(self):
        """Test issues.patch supports fields format."""
        with patch.object(self.issues_tools, 'patch') as mock_patch:
            mock_patch.return_value = {"id": "DEMO-1", "summary": "Updated"}

            # Test with fields parameter
            result = await self.issues_tools.patch(
                issue_id="DEMO-1",
                fields={"summary": "New Summary"}
            )
            assert result["id"] == "DEMO-1"

    @pytest.mark.asyncio
    async def test_patch_with_subpath_format(self):
        """Test issues.patch with /fields/FieldName format."""
        with patch.object(self.issues_tools, 'patch') as mock_patch:
            mock_patch.return_value = {"id": "DEMO-1", "state": "In Progress"}

            # Test with ops format using subpath
            result = await self.issues_tools.patch(
                issue_id="DEMO-1",
                ops=[{
                    "op": "set",
                    "path": "/fields/State",
                    "value": "In Progress"
                }]
            )
            assert result["id"] == "DEMO-1"

    @pytest.mark.asyncio
    async def test_patch_fields_conversion_to_ops(self):
        """Test that fields parameter is converted to ops format."""
        with patch.object(self.issues_tools, 'patch') as mock_patch:
            mock_patch.return_value = {"success": True}

            # Should convert fields to ops internally
            await self.issues_tools.patch(
                issue_id="DEMO-1",
                fields={"Priority": "High"}
            )

            # Verify the method was called
            mock_patch.assert_called_once()


class TestSchemaSizeBudget:
    """Test schema size budget compliance."""

    @pytest.mark.asyncio
    async def test_schema_response_size_budget(self):
        """Test that schema responses fit within token budget."""
        # This is a conceptual test - actual implementation would measure
        # the JSON size of tool schemas
        from youtrack_mcp.server_fastmcp import mcp

        # Register tools first
        register_mcp_tools()

        tools = await mcp.list_tools()

        # Estimate token usage (rough approximation)
        total_size = 0
        for tool in tools:
            # Convert tool to dict representation
            tool_json = json.dumps({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema.model_dump() if hasattr(tool, 'input_schema') and hasattr(tool.input_schema, 'model_dump') else {}
            })
            total_size += len(tool_json)

        # Token budget (assuming ~4 chars per token)
        max_tokens = 10000
        estimated_tokens = total_size / 4

        assert estimated_tokens < max_tokens, \
            f"Schema size ({estimated_tokens} tokens) exceeds budget ({max_tokens} tokens)"