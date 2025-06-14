"""
MCP Protocol Compliance Tests for YouTrack MCP Server.

Tests the server's compliance with the Model Context Protocol specification.
"""
import pytest
import asyncio
import json
import uuid
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# Import MCP components
from mcp.server.fastmcp import FastMCP
from mcp.types import Tool, TextContent

# Import YouTrack MCP server components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.config import config
from main import mcp


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance for YouTrack MCP server."""
    
    @pytest.fixture
    def mock_youtrack_client(self):
        """Mock YouTrack client for testing."""
        client = AsyncMock(spec=YouTrackClient)
        
        # Mock typical API responses
        client.get.return_value = {
            "id": "TEST-123",
            "summary": "Test Issue",
            "description": "Test Description",
            "created": 1640995200000,  # 2022-01-01
            "updated": 1640995200000,
            "project": {"id": "0-0", "name": "Test Project", "shortName": "TEST"},
            "reporter": {"id": "0-1", "login": "reporter", "name": "Reporter User"},
            "customFields": []
        }
        
        client.post.return_value = {
            "id": "TEST-124",
            "summary": "Created Issue"
        }
        
        return client
    
    @pytest.fixture
    def mcp_server(self, mock_youtrack_client):
        """Create MCP server instance for testing."""
        # Mock the global client
        with patch('main.youtrack_client', mock_youtrack_client):
            yield mcp
    
    def test_mcp_server_initialization(self):
        """Test that MCP server initializes correctly."""
        assert isinstance(mcp, FastMCP)
        assert mcp.name == "YouTrack MCP"
    
    def test_tools_registration(self, mcp_server):
        """Test that all required tools are registered."""
        expected_tools = [
            "get_issue",
            "get_issue_raw", 
            "create_issue",
            "search_issues",
            "advanced_search",
            "filter_issues",
            "search_with_custom_fields",
            "add_comment",
            "update_issue",
            "link_issues",
            "remove_link",
            "create_dependency",
            "get_issue_links",
            "get_available_link_types",
            "create_project",
            "update_project",
            "get_project_issues",
            "get_custom_fields",
            "get_project_by_name",
            "get_projects",
            "get_project",
            "get_user",
            "get_user_groups",
            "get_current_user",
            "search_users",
            "get_user_by_login"
        ]
        
        registered_tools = list(mcp_server.tools.keys())
        
        for tool_name in expected_tools:
            assert tool_name in registered_tools, f"Tool {tool_name} is not registered"
    
    @pytest.mark.asyncio
    async def test_tool_execution_basic(self, mcp_server, mock_youtrack_client):
        """Test basic tool execution through MCP interface."""
        # Test get_issue tool
        tool_func = mcp_server.tools["get_issue"]
        
        with patch('main.youtrack_client', mock_youtrack_client):
            result = await tool_func.func(issue_id="TEST-123")
        
        assert isinstance(result, dict)
        assert "id" in result
        assert result["id"] == "TEST-123"
    
    @pytest.mark.asyncio
    async def test_tool_parameter_validation(self, mcp_server):
        """Test tool parameter validation."""
        tool_func = mcp_server.tools["get_issue"]
        
        # Test with missing required parameter
        with pytest.raises(TypeError):
            await tool_func.func()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_server):
        """Test proper error handling in tools."""
        tool_func = mcp_server.tools["get_issue"]
        
        # Mock client to raise an exception
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("API Error")
        
        with patch('main.youtrack_client', mock_client):
            result = await tool_func.func(issue_id="INVALID-123")
        
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_tool_metadata_compliance(self, mcp_server):
        """Test that tools have proper metadata for MCP compliance."""
        for tool_name, tool_func in mcp_server.tools.items():
            # Check that tool function exists
            assert callable(tool_func.func), f"Tool {tool_name} is not callable"
            
            # Check that tool has docstring
            assert tool_func.func.__doc__ is not None, f"Tool {tool_name} lacks documentation"
            
            # Check that tool has proper signature
            import inspect
            sig = inspect.signature(tool_func.func)
            
            # All tools should have type hints
            for param_name, param in sig.parameters.items():
                assert param.annotation != inspect.Parameter.empty, \
                    f"Tool {tool_name} parameter {param_name} lacks type annotation"


class TestMCPToolSchemas:
    """Test MCP tool schema generation and validation."""
    
    @pytest.fixture
    def mcp_server(self):
        """Get MCP server for schema testing."""
        return mcp
    
    def test_tool_schema_generation(self, mcp_server):
        """Test that tools can generate valid MCP schemas."""
        for tool_name, tool_func in mcp_server.tools.items():
            import inspect
            
            sig = inspect.signature(tool_func.func)
            doc = tool_func.func.__doc__ or "No description available"
            
            # Generate MCP-compatible schema
            properties = {}
            required = []
            
            for param_name, param in sig.parameters.items():
                param_type = "string"  # Default type
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == bool:
                        param_type = "boolean"
                    elif param.annotation == float:
                        param_type = "number"
                
                properties[param_name] = {"type": param_type}
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)
            
            schema = {
                "name": tool_name,
                "description": doc.strip(),
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
            
            # Validate schema structure
            assert "name" in schema
            assert "description" in schema
            assert "inputSchema" in schema
            assert schema["inputSchema"]["type"] == "object"
            assert "properties" in schema["inputSchema"]
            assert "required" in schema["inputSchema"]
    
    def test_tool_parameter_types(self, mcp_server):
        """Test tool parameter type consistency."""
        for tool_name, tool_func in mcp_server.tools.items():
            import inspect
            sig = inspect.signature(tool_func.func)
            
            for param_name, param in sig.parameters.items():
                # Ensure all parameters have proper type annotations
                assert param.annotation != inspect.Parameter.empty, \
                    f"Parameter {param_name} in tool {tool_name} lacks type annotation"
                
                # Check for supported MCP types
                if param.annotation not in [str, int, bool, float, dict, list]:
                    # Check if it's a typing type (like Optional, Dict, List)
                    import typing
                    origin = getattr(param.annotation, '__origin__', None)
                    assert origin in [typing.Union, dict, list, type(None)], \
                        f"Unsupported parameter type {param.annotation} in {tool_name}.{param_name}"


class TestMCPResponseFormats:
    """Test MCP response format compliance."""
    
    @pytest.mark.asyncio
    async def test_tool_response_formats(self):
        """Test that tools return properly formatted responses."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "id": "TEST-123",
            "summary": "Test Issue"
        }
        
        with patch('main.youtrack_client', mock_client):
            # Import a tool function directly
            from main import get_issue
            result = await get_issue("TEST-123")
        
        # Should return a dictionary that can be serialized to JSON
        assert isinstance(result, (dict, list, str, int, float, bool, type(None)))
        
        # Test JSON serializability
        try:
            json.dumps(result)
        except (TypeError, ValueError) as e:
            pytest.fail(f"Tool response is not JSON serializable: {e}")
    
    @pytest.mark.asyncio
    async def test_error_response_format(self):
        """Test that error responses are properly formatted."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Test error")
        
        with patch('main.youtrack_client', mock_client):
            from main import get_issue
            result = await get_issue("INVALID-123")
        
        assert isinstance(result, dict)
        assert "error" in result
        assert isinstance(result["error"], str)


class TestMCPIntegration:
    """Test MCP integration scenarios."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with patch.object(config, 'YOUTRACK_API_TOKEN', 'test-token'):
            with patch.object(config, 'YOUTRACK_URL', 'https://test.youtrack.cloud'):
                yield config
    
    @pytest.mark.asyncio
    async def test_tool_chaining(self, mock_config):
        """Test chaining multiple tool calls together."""
        mock_client = AsyncMock()
        
        # Mock create_project response
        mock_client.post.return_value = {
            "id": "0-1",
            "name": "Test Project",
            "shortName": "TEST"
        }
        
        # Mock create_issue response
        mock_client.post.return_value = {
            "id": "TEST-1",
            "summary": "Test Issue",
            "project": {"shortName": "TEST"}
        }
        
        with patch('main.youtrack_client', mock_client):
            from main import create_project, create_issue
            
            # First create a project
            project_result = await create_project("TEST", "Test Project")
            assert "id" in project_result
            
            # Then create an issue in that project  
            issue_result = await create_issue("TEST", "Test Issue")
            assert "id" in issue_result
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, mock_config):
        """Test concurrent execution of multiple tools."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {"id": "TEST-123", "summary": "Test"}
        
        with patch('main.youtrack_client', mock_client):
            from main import get_issue, search_issues
            
            # Execute multiple tools concurrently
            tasks = [
                get_issue("TEST-123"),
                search_issues("test query"),
                get_issue("TEST-124")
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should complete without exceptions
            for result in results:
                assert not isinstance(result, Exception)
                assert isinstance(result, (dict, list))


class TestMCPConfiguration:
    """Test MCP server configuration compliance."""
    
    def test_server_name_compliance(self):
        """Test server name follows MCP conventions."""
        assert isinstance(mcp.name, str)
        assert len(mcp.name) > 0
        assert mcp.name == "YouTrack MCP"
    
    def test_tool_registration_compliance(self):
        """Test tool registration follows MCP patterns."""
        # Should have at least one tool
        assert len(mcp.tools) > 0
        
        # All tools should be properly registered
        for tool_name, tool_func in mcp.tools.items():
            assert isinstance(tool_name, str)
            assert len(tool_name) > 0
            assert callable(tool_func.func)


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])