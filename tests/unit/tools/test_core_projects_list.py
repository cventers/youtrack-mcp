"""
Golden tests for core projects LIST operations.

Tests the project discovery functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch
from youtrack_mcp.tools.core_projects import CoreProjectsTools
from youtrack_mcp.utils import format_json_response


class TestCoreProjectsList:
    """Test cases for project LIST operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = CoreProjectsTools()
        self.tools.client = Mock()
        self.tools.projects_api = Mock()

    def test_list_projects_basic(self):
        """Test listing projects without archived projects."""
        mock_projects = [
            {
                "id": "0-0",
                "shortName": "DEMO",
                "name": "Demo Project",
                "description": "A demo project",
                "archived": False
            },
            {
                "id": "0-1",
                "shortName": "TEST",
                "name": "Test Project",
                "description": "A test project",
                "archived": False
            }
        ]

        self.tools.projects_api.get_projects = Mock(return_value=mock_projects)

        result = self.tools.list(include_archived=False)

        self.tools.projects_api.get_projects.assert_called_once_with(include_archived=False)

        # Parse the JSON result
        result_data = json.loads(result)
        expected = {
            "projects": mock_projects,
            "count": 2,
            "include_archived": False
        }
        assert result_data == expected

    def test_list_projects_with_archived(self):
        """Test listing projects including archived projects."""
        mock_projects = [
            {
                "id": "0-0",
                "shortName": "DEMO",
                "name": "Demo Project",
                "archived": False
            },
            {
                "id": "0-1",
                "shortName": "ARCHIVED",
                "name": "Archived Project",
                "archived": True
            }
        ]

        self.tools.projects_api.get_projects = Mock(return_value=mock_projects)

        result = self.tools.list(include_archived=True)

        self.tools.projects_api.get_projects.assert_called_once_with(include_archived=True)

        result_data = json.loads(result)
        expected = {
            "projects": mock_projects,
            "count": 2,
            "include_archived": True
        }
        assert result_data == expected

    def test_list_projects_empty(self):
        """Test listing projects when no projects are available."""
        mock_projects = []

        self.tools.projects_api.get_projects = Mock(return_value=mock_projects)

        result = self.tools.list(include_archived=False)

        self.tools.projects_api.get_projects.assert_called_once_with(include_archived=False)

        result_data = json.loads(result)
        expected = {
            "projects": [],
            "count": 0,
            "include_archived": False
        }
        assert result_data == expected

    def test_list_projects_single_project(self):
        """Test listing projects with only one project."""
        mock_projects = [
            {
                "id": "0-0",
                "shortName": "SINGLE",
                "name": "Single Project",
                "description": "The only project",
                "archived": False
            }
        ]

        self.tools.projects_api.get_projects = Mock(return_value=mock_projects)

        result = self.tools.list(include_archived=False)

        self.tools.projects_api.get_projects.assert_called_once_with(include_archived=False)

        result_data = json.loads(result)
        expected = {
            "projects": mock_projects,
            "count": 1,
            "include_archived": False
        }
        assert result_data == expected

    def test_list_projects_with_pydantic_models(self):
        """Test listing projects that return Pydantic models."""
        class MockProject:
            def __init__(self, id, short_name, name, archived=False):
                self.id = id
                self.shortName = short_name
                self.name = name
                self.archived = archived

            def model_dump(self):
                return {
                    "id": self.id,
                    "shortName": self.shortName,
                    "name": self.name,
                    "archived": self.archived
                }

        mock_projects = [
            MockProject("0-0", "DEMO", "Demo Project", False),
            MockProject("0-1", "TEST", "Test Project", False)
        ]

        self.tools.projects_api.get_projects = Mock(return_value=mock_projects)

        result = self.tools.list(include_archived=False)

        self.tools.projects_api.get_projects.assert_called_once_with(include_archived=False)

        result_data = json.loads(result)
        expected_projects = [
            {"id": "0-0", "shortName": "DEMO", "name": "Demo Project", "archived": False},
            {"id": "0-1", "shortName": "TEST", "name": "Test Project", "archived": False}
        ]
        expected = {
            "projects": expected_projects,
            "count": 2,
            "include_archived": False
        }
        assert result_data == expected

    def test_list_projects_with_dict_objects(self):
        """Test listing projects that return plain dict objects."""
        class MockProject:
            def __init__(self, id, short_name, name, archived=False):
                self.__dict__ = {
                    "id": id,
                    "shortName": short_name,
                    "name": name,
                    "archived": archived
                }

        mock_projects = [
            MockProject("0-0", "DEMO", "Demo Project", False),
            MockProject("0-1", "TEST", "Test Project", False)
        ]

        self.tools.projects_api.get_projects = Mock(return_value=mock_projects)

        result = self.tools.list(include_archived=False)

        self.tools.projects_api.get_projects.assert_called_once_with(include_archived=False)

        result_data = json.loads(result)
        expected_projects = [
            {"id": "0-0", "shortName": "DEMO", "name": "Demo Project", "archived": False},
            {"id": "0-1", "shortName": "TEST", "name": "Test Project", "archived": False}
        ]
        expected = {
            "projects": expected_projects,
            "count": 2,
            "include_archived": False
        }
        assert result_data == expected

    def test_list_projects_api_error(self):
        """Test error handling when API call fails."""
        self.tools.projects_api.get_projects = Mock(side_effect=Exception("API Error"))

        result = self.tools.list(include_archived=False)

        result_data = json.loads(result)
        assert "error" in result_data
        assert "API Error" in result_data["error"]
        assert result_data["error_type"] == "Exception"
        assert result_data["include_archived"] is False

    def test_list_projects_mixed_archived_status(self):
        """Test listing projects with mixed archived status."""
        mock_projects = [
            {
                "id": "0-0",
                "shortName": "ACTIVE",
                "name": "Active Project",
                "archived": False
            },
            {
                "id": "0-1",
                "shortName": "ARCHIVED1",
                "name": "First Archived Project",
                "archived": True
            },
            {
                "id": "0-2",
                "shortName": "ACTIVE2",
                "name": "Second Active Project",
                "archived": False
            },
            {
                "id": "0-3",
                "shortName": "ARCHIVED2",
                "name": "Second Archived Project",
                "archived": True
            }
        ]

        self.tools.projects_api.get_projects = Mock(return_value=mock_projects)

        # Test without archived
        result = self.tools.list(include_archived=False)
        result_data = json.loads(result)
        assert result_data["count"] == 4  # All projects returned, filtering happens in API
        assert result_data["include_archived"] is False

        # Test with archived
        result = self.tools.list(include_archived=True)
        result_data = json.loads(result)
        assert result_data["count"] == 4
        assert result_data["include_archived"] is True

    def test_list_projects_large_dataset(self):
        """Test listing projects with a large number of projects."""
        # Create 50 mock projects
        mock_projects = []
        for i in range(50):
            mock_projects.append({
                "id": f"0-{i}",
                "shortName": f"PROJ{i}",
                "name": f"Project {i}",
                "archived": i % 5 == 0  # Every 5th project is archived
            })

        self.tools.projects_api.get_projects = Mock(return_value=mock_projects)

        result = self.tools.list(include_archived=True)

        result_data = json.loads(result)
        assert result_data["count"] == 50
        assert len(result_data["projects"]) == 50
        assert result_data["include_archived"] is True

        # Verify the first few projects
        assert result_data["projects"][0]["shortName"] == "PROJ0"
        assert result_data["projects"][1]["shortName"] == "PROJ1"
        assert result_data["projects"][4]["archived"] is True  # Every 5th should be archived