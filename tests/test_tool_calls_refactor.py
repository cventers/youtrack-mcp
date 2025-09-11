"""
Tests for tool calls refactor - strict schemas and legacy compatibility.

This module tests the new strict JSON schema validation and legacy router
functionality for the tool calls refactor.
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
from youtrack_mcp.legacy_router import (
    LegacyParameterProcessor,
    LegacyRouter,
    should_enable_legacy_router,
    MCP_PARAM_REPAIR
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


class TestLegacyParameterProcessor:
    """Test legacy parameter processing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = LegacyParameterProcessor()

    def test_process_legacy_call_simple_kwargs(self):
        """Test processing simple keyword arguments."""
        result = self.processor.process_legacy_call(
            "issues.get",
            (),
            {"issue_id": "DEMO-123"}
        )

        assert result == {"issue_id": "DEMO-123"}

    def test_process_legacy_call_positional_args(self):
        """Test processing positional arguments."""
        result = self.processor.process_legacy_call(
            "issues.get",
            ("DEMO-123",),
            {}
        )

        assert result == {"issue_id": "DEMO-123"}

    def test_process_legacy_call_args_parameter_json(self):
        """Test processing args parameter with JSON string."""
        result = self.processor.process_legacy_call(
            "issues.get",
            (),
            {"args": '{"issue_id": "DEMO-123"}'}
        )

        assert result == {"issue_id": "DEMO-123"}

    def test_process_legacy_call_args_parameter_key_value(self):
        """Test processing args parameter with key=value string."""
        result = self.processor.process_legacy_call(
            "issues.get",
            (),
            {"args": 'issue_id="DEMO-123"'}
        )

        assert result == {"issue_id": "DEMO-123"}

    def test_process_legacy_call_kwargs_parameter_json(self):
        """Test processing kwargs parameter with JSON string."""
        result = self.processor.process_legacy_call(
            "issues.create",
            (),
            {"kwargs": '{"project": "DEMO", "summary": "Test"}'}
        )

        assert result == {"project": "DEMO", "summary": "Test"}

    def test_process_legacy_call_type_conversion(self):
        """Test automatic type conversion."""
        result = self.processor.process_legacy_call(
            "search.query",
            (),
            {"query": "test", "limit": "10"}
        )

        assert result == {"query": "test", "limit": 10}

    def test_process_legacy_call_boolean_conversion(self):
        """Test boolean string conversion."""
        result = self.processor.process_legacy_call(
            "search.autosearch",
            (),
            {"natural_language_query": "test", "strict_mode": "true"}
        )

        assert result == {"natural_language_query": "test", "strict_mode": True}

    def test_process_legacy_call_parameter_mapping(self):
        """Test parameter name mapping."""
        result = self.processor.process_legacy_call(
            "issues.create",
            (),
            {"project_id": "DEMO", "summary": "Test"}
        )

        assert result == {"project": "DEMO", "summary": "Test"}

    def test_process_legacy_call_deprecation_warning(self):
        """Test that deprecation warning is logged once per tool."""
        with patch('youtrack_mcp.legacy_router.logger') as mock_logger:
            # First call should log warning
            self.processor.process_legacy_call("issues.get", (), {"issue_id": "DEMO-123"})
            mock_logger.warning.assert_called_once()

            # Reset mock
            mock_logger.reset_mock()

            # Second call should not log warning (already warned)
            self.processor.process_legacy_call("issues.get", (), {"issue_id": "DEMO-456"})
            mock_logger.warning.assert_not_called()


class TestLegacyRouter:
    """Test legacy router functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_strict_server = Mock()
        self.router = LegacyRouter(self.mock_strict_server)

    def test_route_legacy_tool_call_simple(self):
        """Test routing simple legacy call."""
        self.mock_strict_server._tools = {"issues.get": Mock(return_value="result")}

        result = self.router.route_legacy_tool_call(
            "issues.get",
            (),
            {"issue_id": "DEMO-123"}
        )

        # Should call the mock strict server
        assert result is not None

    def test_route_legacy_tool_call_with_args_param(self):
        """Test routing legacy call with args parameter."""
        self.mock_strict_server._tools = {"issues.get": Mock(return_value="result")}

        result = self.router.route_legacy_tool_call(
            "issues.get",
            (),
            {"args": '{"issue_id": "DEMO-123"}'}
        )

        assert result is not None


class TestEnvironmentFlags:
    """Test environment flag handling."""

    def test_should_enable_legacy_router_default(self):
        """Test legacy router disabled by default."""
        with patch.dict('os.environ', {}, clear=True):
            assert should_enable_legacy_router() is False

    def test_should_enable_legacy_router_true(self):
        """Test legacy router enabled when flag is set."""
        with patch.dict('os.environ', {MCP_PARAM_REPAIR: 'true'}):
            assert should_enable_legacy_router() is True

    def test_should_enable_legacy_router_various_values(self):
        """Test legacy router with various flag values."""
        test_cases = [
            ('1', True),
            ('yes', True),
            ('True', True),
            ('TRUE', True),
            ('false', False),
            ('0', False),
            ('no', False),
            ('random', False)
        ]

        for value, expected in test_cases:
            with patch.dict('os.environ', {MCP_PARAM_REPAIR: value}):
                assert should_enable_legacy_router() == expected


class TestMigrationScenarios:
    """Test common migration scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = LegacyParameterProcessor()

    def test_migrate_issues_get_positional(self):
        """Test migrating issues.get with positional args."""
        # Old: issues.get("DEMO-123")
        result = self.processor.process_legacy_call(
            "issues.get",
            ("DEMO-123",),
            {}
        )

        expected = {"issue_id": "DEMO-123"}
        assert result == expected

    def test_migrate_issues_create_kwargs(self):
        """Test migrating issues.create with kwargs."""
        # Old: issues.create(project="DEMO", summary="Bug")
        result = self.processor.process_legacy_call(
            "issues.create",
            (),
            {"project": "DEMO", "summary": "Bug"}
        )

        expected = {"project": "DEMO", "summary": "Bug"}
        assert result == expected

    def test_migrate_search_query_mixed(self):
        """Test migrating search.query with mixed parameters."""
        # Old: search.query("project: DEMO", limit="5")
        result = self.processor.process_legacy_call(
            "search.query",
            ("project: DEMO",),
            {"limit": "5"}
        )

        expected = {"query": "project: DEMO", "limit": 5}
        assert result == expected

    def test_migrate_complex_custom_fields(self):
        """Test migrating complex custom fields."""
        # Old: issues.create(project="DEMO", summary="Bug", custom_fields='{"Type": "Bug"}')
        result = self.processor.process_legacy_call(
            "issues.create",
            (),
            {
                "project": "DEMO",
                "summary": "Bug",
                "custom_fields": '{"Type": "Bug", "Priority": "High"}'
            }
        )

        expected = {
            "project": "DEMO",
            "summary": "Bug",
            "custom_fields": {"Type": "Bug", "Priority": "High"}
        }
        assert result == expected


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

    def test_legacy_processing_error_recovery(self):
        """Test that legacy processing handles errors gracefully."""
        processor = LegacyParameterProcessor()

        # Test with malformed JSON
        result = processor.process_legacy_call(
            "issues.get",
            (),
            {"args": '{"issue_id": "DEMO-123", invalid_json}'}
        )

        # Should still produce valid result
        assert "issue_id" in result or "arg_value" in result


if __name__ == "__main__":
    pytest.main([__file__])