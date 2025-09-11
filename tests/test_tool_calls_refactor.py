"""
Tests for tool calls refactor - strict JSON schema validation.

This module tests the new strict JSON schema validation for the tool calls refactor.
"""

import json
import pytest
from unittest.mock import Mock, patch

from youtrack_mcp.schemas import (
    TOOL_SCHEMAS,
    get_tool_schema,
    validate_tool_call,
    ISSUES_GET_SCHEMA,
    ISSUES_CREATE_SCHEMA,
    ISSUES_PATCH_SCHEMA
)


class TestSchemaValidation:
    """Test JSON schema validation for tools."""

    def test_get_tool_schema_valid_tool(self):
        """Test getting schema for valid tool."""
        schema = get_tool_schema("issues.get")
        assert schema == ISSUES_GET_SCHEMA
        assert "tool_name" in schema["properties"]
        assert "arguments" in schema["properties"]

    def test_get_tool_schema_invalid_tool(self):
        """Test getting schema for invalid tool raises ValueError."""
        with pytest.raises(ValueError, match="Unknown tool 'invalid.tool'"):
            get_tool_schema("invalid.tool")

    def test_validate_tool_call_valid(self):
        """Test validation of valid tool call."""
        call = {
            "tool_name": "issues.get",
            "arguments": {
                "issue_id": "DEMO-123",
                "include": ["customFields"]
            }
        }

        # Should not raise exception
        validate_tool_call("issues.get", call["arguments"])

    def test_validate_tool_call_missing_required(self):
        """Test validation fails for missing required parameters."""
        call = {
            "tool_name": "issues.get",
            "arguments": {
                "include": ["customFields"]  # Missing issue_id
            }
        }

        with pytest.raises(ValueError, match="validation failed"):
            validate_tool_call("issues.get", call["arguments"])

    def test_validate_tool_call_extra_properties(self):
        """Test validation fails for extra properties when additionalProperties is false."""
        call = {
            "tool_name": "issues.get",
            "arguments": {
                "issue_id": "DEMO-123",
                "extra_param": "not allowed"
            }
        }

        with pytest.raises(ValueError, match="validation failed"):
            validate_tool_call("issues.get", call["arguments"])

    def test_issues_create_schema_validation(self):
        """Test issues.create schema validation."""
        # Valid call
        valid_call = {
            "tool_name": "issues.create",
            "arguments": {
                "project": "DEMO",
                "summary": "Test issue"
            }
        }
        validate_tool_call("issues.create", valid_call["arguments"])

        # Invalid call - missing required
        invalid_call = {
            "tool_name": "issues.create",
            "arguments": {
                "project": "DEMO"
                # Missing summary
            }
        }
        with pytest.raises(ValueError):
            validate_tool_call("issues.create", invalid_call["arguments"])

    def test_issues_patch_schema_validation(self):
        """Test issues.patch schema with oneOf validation."""
        # Valid call with fields
        valid_fields_call = {
            "tool_name": "issues.patch",
            "arguments": {
                "issue_id": "DEMO-123",
                "fields": {
                    "summary": "New title"
                }
            }
        }
        validate_tool_call("issues.patch", valid_fields_call["arguments"])

        # Valid call with ops
        valid_ops_call = {
            "tool_name": "issues.patch",
            "arguments": {
                "issue_id": "DEMO-123",
                "ops": [
                    {"op": "replace", "path": "/fields/summary", "value": "New title"}
                ]
            }
        }
        validate_tool_call("issues.patch", valid_ops_call["arguments"])

        # Invalid call - both fields and ops
        invalid_call = {
            "tool_name": "issues.patch",
            "arguments": {
                "issue_id": "DEMO-123",
                "fields": {"summary": "New title"},
                "ops": [{"op": "replace", "path": "/fields/summary", "value": "New title"}]
            }
        }
        with pytest.raises(ValueError):
            validate_tool_call("issues.patch", invalid_call["arguments"])


class TestErrorHandling:
    """Test error handling in refactored system."""

    def test_schema_validation_error_message(self):
        """Test that schema validation provides helpful error messages."""
        call = {
            "tool_name": "issues.get",
            "arguments": {
                # Missing issue_id
                "include": ["customFields"]
            }
        }

        with pytest.raises(ValueError) as exc_info:
            validate_tool_call("issues.get", call["arguments"])

        error_msg = str(exc_info.value)
        assert "validation failed" in error_msg.lower()


if __name__ == "__main__":
    # Run tests manually without pytest
    import sys

    print("Running tool calls refactor tests manually...")

    # Create test instance
    test_instance = TestSchemaValidation()

    try:
        # Run schema validation tests
        print("\n1. Testing schema validation...")
        test_instance.test_get_tool_schema_valid_tool()
        print("   ✓ get_tool_schema_valid_tool passed")

        test_instance.test_get_tool_schema_invalid_tool()
        print("   ✓ get_tool_schema_invalid_tool passed")

        test_instance.test_validate_tool_call_valid()
        print("   ✓ validate_tool_call_valid passed")

        test_instance.test_validate_tool_call_missing_required()
        print("   ✓ validate_tool_call_missing_required passed")

        test_instance.test_validate_tool_call_extra_properties()
        print("   ✓ validate_tool_call_extra_properties passed")

        test_instance.test_issues_create_schema_validation()
        print("   ✓ issues_create_schema_validation passed")

        test_instance.test_issues_patch_schema_validation()
        print("   ✓ issues_patch_schema_validation passed")

        # Run error handling tests
        print("\n2. Testing error handling...")
        error_test_instance = TestErrorHandling()
        error_test_instance.test_schema_validation_error_message()
        print("   ✓ schema_validation_error_message passed")

        print("\n✅ All tests passed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)