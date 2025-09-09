"""
Golden tests for core projects GET operations.

Tests the project details with expansions functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch
from youtrack_mcp.tools.core_projects import CoreProjectsTools
from youtrack_mcp.utils import format_json_response


class TestCoreProjectsGet:
    """Test cases for project GET operations."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch('youtrack_mcp.tools.core_projects.YouTrackClient'), \
             patch('youtrack_mcp.tools.core_projects.ProjectsClient'):
            self.tools = CoreProjectsTools()
            self.tools.client = Mock()
            self.tools.projects_api = Mock()

    def _create_mock_project(self, data):
        """Helper to create a mock project object."""
        mock_project = Mock()
        mock_project.model_dump.return_value = data
        mock_project.__dict__ = data
        return mock_project

    def test_get_basic_project(self):
        """Test getting a basic project without expansions."""
        mock_project_data = {
            "id": "0-0",
            "shortName": "DEMO",
            "name": "Demo Project",
            "description": "A demo project for testing",
            "archived": False,
            "created": 1640995200000,
            "updated": 1640995200000
        }

        mock_project = self._create_mock_project(mock_project_data)
        self.tools.projects_api.get_project = Mock(return_value=mock_project)

        result = self.tools.get(project_id="DEMO")

        self.tools.projects_api.get_project.assert_called_once_with("DEMO")

        # Parse the JSON result
        result_data = json.loads(result)
        expected_project = mock_project_data.copy()
        expected_project["created_iso8601"] = "2022-01-01T00:00:00+00:00"
        expected_project["updated_iso8601"] = "2022-01-01T00:00:00+00:00"
        expected = {
            "project": expected_project,
            "expansions": {},
            "expansions_requested": []
        }
        assert result_data == expected

    def test_get_project_with_custom_fields_expansion(self):
        """Test getting a project with custom fields expansion."""
        mock_project_data = {
            "id": "0-0",
            "shortName": "DEMO",
            "name": "Demo Project"
        }

        mock_custom_fields = [
            {"name": "Project Type", "type": "enum"},
            {"name": "Budget", "type": "integer"}
        ]

        mock_project = self._create_mock_project(mock_project_data)
        self.tools.projects_api.get_project = Mock(return_value=mock_project)
        self.tools.projects_api.get_custom_fields = Mock(return_value=mock_custom_fields)

        result = self.tools.get(project_id="DEMO", include=["customFields"])

        self.tools.projects_api.get_project.assert_called_once_with("DEMO")
        self.tools.projects_api.get_custom_fields.assert_called_once_with("DEMO")

        result_data = json.loads(result)
        expected = {
            "project": mock_project_data,
            "expansions": {"customFields": mock_custom_fields},
            "expansions_requested": ["customFields"]
        }
        assert result_data == expected

    def test_get_project_with_issues_expansion(self):
        """Test getting a project with issues expansion."""
        mock_project_data = {
            "id": "0-0",
            "shortName": "DEMO",
            "name": "Demo Project"
        }

        mock_issues = [
            {"id": "DEMO-1", "summary": "First issue"},
            {"id": "DEMO-2", "summary": "Second issue"}
        ]

        mock_project = self._create_mock_project(mock_project_data)
        self.tools.projects_api.get_project = Mock(return_value=mock_project)
        self.tools.projects_api.get_project_issues = Mock(return_value=mock_issues)

        result = self.tools.get(project_id="DEMO", include=["issues"])

        self.tools.projects_api.get_project.assert_called_once_with("DEMO")
        self.tools.projects_api.get_project_issues.assert_called_once_with("DEMO", limit=10)

        result_data = json.loads(result)
        expected = {
            "project": mock_project_data,
            "expansions": {"issues": mock_issues},
            "expansions_requested": ["issues"]
        }
        assert result_data == expected

    def test_get_project_with_multiple_expansions(self):
        """Test getting a project with multiple expansions."""
        mock_project_data = {
            "id": "0-0",
            "shortName": "DEMO",
            "name": "Demo Project"
        }

        mock_custom_fields = [{"name": "Priority", "type": "enum"}]
        mock_issues = [{"id": "DEMO-1", "summary": "Test issue"}]

        mock_project = self._create_mock_project(mock_project_data)
        self.tools.projects_api.get_project = Mock(return_value=mock_project)
        self.tools.projects_api.get_custom_fields = Mock(return_value=mock_custom_fields)
        self.tools.projects_api.get_project_issues = Mock(return_value=mock_issues)

        result = self.tools.get(project_id="DEMO", include=["customFields", "issues"])

        self.tools.projects_api.get_project.assert_called_once_with("DEMO")
        self.tools.projects_api.get_custom_fields.assert_called_once_with("DEMO")
        self.tools.projects_api.get_project_issues.assert_called_once_with("DEMO", limit=10)

        result_data = json.loads(result)
        expected = {
            "project": mock_project_data,
            "expansions": {
                "customFields": mock_custom_fields,
                "issues": mock_issues
            },
            "expansions_requested": ["customFields", "issues"]
        }
        assert result_data == expected

    def test_get_project_with_empty_expansions(self):
        """Test getting a project with empty expansions list."""
        mock_project_data = {
            "id": "0-0",
            "shortName": "DEMO",
            "name": "Demo Project"
        }

        mock_project = self._create_mock_project(mock_project_data)
        self.tools.projects_api.get_project = Mock(return_value=mock_project)

        result = self.tools.get(project_id="DEMO", include=[])

        self.tools.projects_api.get_project.assert_called_once_with("DEMO")

        result_data = json.loads(result)
        expected = {
            "project": mock_project_data,
            "expansions": {},
            "expansions_requested": []
        }
        assert result_data == expected

    def test_get_project_with_none_expansions(self):
        """Test getting a project with None expansions."""
        mock_project_data = {
            "id": "0-0",
            "shortName": "DEMO",
            "name": "Demo Project"
        }

        mock_project = self._create_mock_project(mock_project_data)
        self.tools.projects_api.get_project = Mock(return_value=mock_project)

        result = self.tools.get(project_id="DEMO", include=None)

        self.tools.projects_api.get_project.assert_called_once_with("DEMO")

        result_data = json.loads(result)
        expected = {
            "project": mock_project_data,
            "expansions": {},
            "expansions_requested": []
        }
        assert result_data == expected

    def test_get_project_expansion_error_handling(self):
        """Test error handling when expansions fail."""
        mock_project_data = {
            "id": "0-0",
            "shortName": "DEMO",
            "name": "Demo Project"
        }

        mock_project = self._create_mock_project(mock_project_data)
        self.tools.projects_api.get_project = Mock(return_value=mock_project)
        self.tools.projects_api.get_custom_fields = Mock(side_effect=Exception("Custom fields error"))

        result = self.tools.get(project_id="DEMO", include=["customFields"])

        result_data = json.loads(result)
        expected = {
            "project": mock_project_data,
            "expansions": {"customFields": []},  # Should return empty list on error
            "expansions_requested": ["customFields"]
        }
        assert result_data == expected

    def test_get_project_with_pydantic_model(self):
        """Test getting a project that returns a Pydantic model."""
        class MockProject:
            def __init__(self):
                self.id = "0-0"
                self.shortName = "DEMO"
                self.name = "Demo Project"

            def model_dump(self):
                return {
                    "id": self.id,
                    "shortName": self.shortName,
                    "name": self.name
                }

        mock_project = MockProject()
        self.tools.projects_api.get_project = Mock(return_value=mock_project)

        result = self.tools.get(project_id="DEMO")

        result_data = json.loads(result)
        expected = {
            "project": {"id": "0-0", "shortName": "DEMO", "name": "Demo Project"},
            "expansions": {},
            "expansions_requested": []
        }
        assert result_data == expected

    def test_get_project_with_dict_response(self):
        """Test getting a project that returns a plain dict."""
        class MockProject:
            def __init__(self):
                self.__dict__ = {
                    "id": "0-0",
                    "shortName": "DEMO",
                    "name": "Demo Project"
                }

        mock_project = MockProject()
        self.tools.projects_api.get_project = Mock(return_value=mock_project)

        result = self.tools.get(project_id="DEMO")

        result_data = json.loads(result)
        expected = {
            "project": {"id": "0-0", "shortName": "DEMO", "name": "Demo Project"},
            "expansions": {},
            "expansions_requested": []
        }
        assert result_data == expected

    def test_get_project_api_error(self):
        """Test error handling when project API call fails."""
        self.tools.projects_api.get_project = Mock(side_effect=Exception("Project not found"))

        result = self.tools.get(project_id="NONEXISTENT")

        result_data = json.loads(result)
        assert "error" in result_data
        assert "Project not found" in result_data["error"]
        assert result_data["error_type"] == "Exception"
        assert result_data["project_id"] == "NONEXISTENT"