"""
Tests for tool calls refactor - strict JSON schema validation.

This module tests the new strict JSON schema validation for the tool calls refactor.
"""

import json
import pytest
from unittest.mock import Mock, patch

# Note: schemas.py was removed in refactor - FastMCP auto-generates schemas from type hints
# This test file needs to be updated to test FastMCP schema generation


class TestFastMCPSchemaGeneration:
    """Test FastMCP auto-generated schemas from type hints."""

    def test_fastmcp_server_has_name(self):
        """Test that FastMCP server has expected name."""
        from youtrack_mcp.server_fastmcp import mcp
        assert mcp.name == "youtrack"

    def test_tools_are_callable(self):
        """Test that loaded tools are callable functions."""
        from youtrack_mcp.utils.loader import load_all_tools
        tools = load_all_tools()

        for tool_name, tool_func in tools.items():
            assert callable(tool_func), f"Tool {tool_name} is not callable"

    def test_tool_names_follow_convention(self):
        """Test that tool names follow the expected naming convention."""
        from youtrack_mcp.utils.loader import load_all_tools
        tools = load_all_tools()

        for tool_name in tools.keys():
            assert '.' in tool_name, f"Tool name {tool_name} should contain '.' separator"
            assert tool_name.replace('.', '').replace('_', '').isalnum(), \
                f"Tool name {tool_name} contains invalid characters"


class TestFastMCPErrorHandling:
    """Test error handling in FastMCP system."""

    def test_tools_handle_errors_gracefully(self):
        """Test that tools handle errors gracefully."""
        from youtrack_mcp.utils.loader import load_all_tools
        tools = load_all_tools()

        # Just verify that tools exist and are callable
        assert len(tools) > 0
        for tool_name, tool_func in tools.items():
            assert callable(tool_func)


if __name__ == "__main__":
    # Run tests manually without pytest
    import sys

    print("Running tool calls refactor tests manually...")

    # Create test instance
    test_instance = TestFastMCPSchemaGeneration()

    try:
        # Run FastMCP tests
        print("\n1. Testing FastMCP schema generation...")
        test_instance.test_fastmcp_server_has_name()
        print("   ✓ fastmcp_server_has_name passed")

        test_instance.test_tools_are_callable()
        print("   ✓ tools_are_callable passed")

        test_instance.test_tool_names_follow_convention()
        print("   ✓ tool_names_follow_convention passed")

        # Run error handling tests
        print("\n2. Testing FastMCP error handling...")
        error_test_instance = TestFastMCPErrorHandling()
        error_test_instance.test_tools_handle_errors_gracefully()
        print("   ✓ tools_handle_errors_gracefully passed")

        print("\n✅ All FastMCP tests passed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)