"""
Unit tests for the Tool Reactor refactoring.

Tests the new minimal surface tools and router backward compatibility.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from youtrack_mcp.tools.core_projects import CoreProjectsTools
from youtrack_mcp.tools.core_issues import CoreIssuesTools
from youtrack_mcp.tools.loader import load_all_tools


class TestProjectsSchema:
    """Test the new projects.schema tool."""

    @pytest.fixture
    def projects_tool(self):
        """Create a CoreProjectsTools instance with mocked client."""
        tool = CoreProjectsTools()
        tool.client = MagicMock()
        tool.projects_api = MagicMock()
        return tool

    @pytest.mark.asyncio
    async def test_schema_method_exists(self, projects_tool):
        """Test that the schema method exists and is callable."""
        assert hasattr(projects_tool, 'schema')
        assert callable(projects_tool.schema)

    @pytest.mark.asyncio
    async def test_schema_returns_valid_json(self, projects_tool):
        """Test that schema method returns valid JSON."""
        # Mock the API response
        mock_schemas = {
            "Type": {"type": "enum", "required": True, "allowed_values": ["Bug", "Feature"]},
            "Priority": {"type": "enum", "required": True, "allowed_values": ["High", "Normal"]}
        }
        projects_tool.projects_api.get_all_custom_fields_schemas.return_value = mock_schemas
        projects_tool.projects_api.get_custom_fields.return_value = ["Type", "Priority"]

        result = await projects_tool.schema("TEST_PROJECT")
        result_data = json.loads(result)

        assert "project_id" in result_data
        assert "schemas" in result_data
        assert "required_fields" in result_data
        assert "optional_fields" in result_data
        assert result_data["project_id"] == "TEST_PROJECT"

    @pytest.mark.asyncio
    async def test_schema_handles_errors(self, projects_tool):
        """Test that schema method handles API errors gracefully."""
        projects_tool.projects_api.get_all_custom_fields_schemas.side_effect = Exception("API Error")

        result = await projects_tool.schema("TEST_PROJECT")
        result_data = json.loads(result)

        assert "error" in result_data
        assert "error_type" in result_data


class TestProjectsGetIncludeSchema:
    """Test projects.get with include=["schema"] expansion."""

    @pytest.fixture
    def projects_tool(self):
        """Create a CoreProjectsTools instance with mocked client."""
        tool = CoreProjectsTools()
        tool.client = MagicMock()
        tool.projects_api = MagicMock()
        return tool

    @pytest.mark.asyncio
    async def test_get_with_schema_expansion(self, projects_tool):
        """Test that projects.get includes schema expansion."""
        # Mock project data
        mock_project = {"id": "TEST_PROJECT", "name": "Test Project"}
        projects_tool.projects_api.get_project.return_value = mock_project

        # Mock schema data
        mock_schemas = {
            "Type": {"type": "enum", "required": True, "allowed_values": ["Bug", "Feature"]}
        }
        projects_tool.projects_api.get_all_custom_fields_schemas.return_value = mock_schemas
        projects_tool.projects_api.get_custom_fields.return_value = ["Type"]

        result = await projects_tool.get("TEST_PROJECT", include=["schema"])
        result_data = json.loads(result)

        assert "project" in result_data
        assert "expansions" in result_data
        assert "schema" in result_data["expansions"]
        assert result_data["expansions"]["schema"]["project_id"] == "TEST_PROJECT"


class TestIssuesPatchFieldsSupport:
    """Test issues.patch with /fields/<FieldName> support."""

    @pytest.fixture
    def issues_tool(self):
        """Create a CoreIssuesTools instance with mocked client."""
        tool = CoreIssuesTools()
        tool.client = MagicMock()
        tool.issues_api = MagicMock()
        return tool

    @pytest.mark.asyncio
    async def test_patch_with_fields_format(self, issues_tool):
        """Test issues.patch with friendly fields{} format."""
        # Mock the API response
        mock_issue = {"id": "TEST-123", "summary": "Updated Issue"}
        issues_tool.issues_api.update_issue.return_value = mock_issue
        issues_tool.issues_api.update_issue_custom_fields.return_value = None

        result = await issues_tool.patch(
            issue_id="TEST-123",
            fields={"summary": "New Title", "Type": "Bug", "Priority": "High"}
        )
        result_data = json.loads(result)

        assert result_data["updated"] is True
        assert "regular_fields_updated" in result_data
        assert "custom_fields_updated" in result_data
        assert "summary" in result_data["regular_fields_updated"]
        assert "Type" in result_data["custom_fields_updated"]
        assert "Priority" in result_data["custom_fields_updated"]

    @pytest.mark.asyncio
    async def test_patch_with_subpath_format(self, issues_tool):
        """Test issues.patch with /fields/<FieldName> subpath format."""
        # Mock the API response
        mock_issue = {"id": "TEST-123", "summary": "Updated Issue"}
        issues_tool.issues_api.update_issue.return_value = mock_issue
        issues_tool.issues_api.update_issue_custom_fields.return_value = None

        ops = [
            {"op": "set", "path": "/fields/summary", "value": "New Title"},
            {"op": "set", "path": "/fields/Type", "value": "Bug"}
        ]

        result = await issues_tool.patch(issue_id="TEST-123", ops=ops)
        result_data = json.loads(result)

        assert result_data["updated"] is True
        assert result_data["ops_applied"] == 2

    @pytest.mark.asyncio
    async def test_patch_fields_conversion_to_ops(self, issues_tool):
        """Test that fields{} format is converted to ops format internally."""
        # Mock the API response
        mock_issue = {"id": "TEST-123", "summary": "Updated Issue"}
        issues_tool.issues_api.update_issue.return_value = mock_issue
        issues_tool.issues_api.update_issue_custom_fields.return_value = None

        result = await issues_tool.patch(
            issue_id="TEST-123",
            fields={"summary": "New Title", "Type": "Bug"}
        )

        # Verify that the API was called correctly
        issues_tool.issues_api.update_issue.assert_called_once_with(
            issue_id="TEST-123",
            summary="New Title",
            description=None
        )
        issues_tool.issues_api.update_issue_custom_fields.assert_called_once_with(
            issue_id="TEST-123",
            custom_fields={"Type": "Bug"}
        )





class TestToolLoaderIntegration:
    """Test that the tool loader properly integrates router functionality."""

    def test_load_all_tools_core_only(self):
        """Test that load_all_tools includes only core tools (no legacy)."""
        with patch('youtrack_mcp.tools.core_projects.CoreProjectsTools'), \
             patch('youtrack_mcp.tools.core_issues.CoreIssuesTools'), \
             patch('youtrack_mcp.tools.core_users.CoreUsersTools'), \
             patch('youtrack_mcp.tools.core_search.CoreSearchTools'), \
             patch('youtrack_mcp.tools.core_resources.CoreResourcesTools'), \
             patch('youtrack_mcp.tools.core_ai.CoreAITools'):

            tools = load_all_tools()

            # Check that core tools are present
            assert "projects.schema" in tools
            assert "issues.patch" in tools
            assert "projects.get" in tools
            assert "issues.get" in tools

            # Check that legacy tools are NOT present
            assert "projects.custom_fields" not in tools
            assert "issues.custom_fields.update_custom_fields" not in tools


class TestSchemaSizeBudget:
    """Test that schema responses stay within size budgets."""

    @pytest.fixture
    def projects_tool(self):
        """Create a CoreProjectsTools instance with mocked client."""
        tool = CoreProjectsTools()
        tool.client = MagicMock()
        tool.projects_api = MagicMock()
        return tool

    @pytest.mark.asyncio
    async def test_schema_response_size_budget(self, projects_tool):
        """Test that schema responses stay under 50KB budget."""
        # Create a large schema to test size limits
        large_schema = {}
        for i in range(100):
            large_schema[f"Field{i}"] = {
                "type": "enum",
                "required": i % 2 == 0,
                "allowed_values": [f"Value{j}" for j in range(10)]
            }

        projects_tool.projects_api.get_all_custom_fields_schemas.return_value = large_schema
        projects_tool.projects_api.get_custom_fields.return_value = list(large_schema.keys())

        result = await projects_tool.schema("LARGE_PROJECT")
        result_size_kb = len(result.encode('utf-8')) / 1024

        # Assert size is under 50KB budget
        assert result_size_kb < 50, f"Schema response size {result_size_kb:.2f}KB exceeds 50KB budget"

    @pytest.mark.asyncio
    async def test_schema_field_count_reasonable(self, projects_tool):
        """Test that schema handles reasonable numbers of fields."""
        # Test with a typical project schema
        typical_schema = {
            "Type": {"type": "enum", "required": True, "allowed_values": ["Bug", "Feature", "Task", "Story"]},
            "Priority": {"type": "enum", "required": True, "allowed_values": ["Critical", "High", "Normal", "Low"]},
            "Assignee": {"type": "user", "required": False, "allowed_values": []},
            "Reporter": {"type": "user", "required": True, "allowed_values": []},
            "State": {"type": "state", "required": True, "allowed_values": ["Open", "In Progress", "Review", "Done"]},
            "Description": {"type": "text", "required": False, "allowed_values": []},
            "Story Points": {"type": "integer", "required": False, "allowed_values": []},
            "Due Date": {"type": "date", "required": False, "allowed_values": []}
        }

        projects_tool.projects_api.get_all_custom_fields_schemas.return_value = typical_schema
        projects_tool.projects_api.get_custom_fields.return_value = list(typical_schema.keys())

        result = await projects_tool.schema("TYPICAL_PROJECT")
        result_data = json.loads(result)

        assert len(result_data["schemas"]) == 8
        assert result_data["required_count"] == 4  # Type, Priority, Reporter, State
        assert result_data["total_fields"] == 8</content>
</xai:function_call">Create comprehensive unit tests for the tool reactor refactoring