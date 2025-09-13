"""
Golden tests for core resources READ operations.

Tests the secured URI proxy functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch
from youtrack_mcp.tools.resources_tools import ResourcesTools
from youtrack_mcp.utils import format_json_response


class TestCoreResourcesRead:
    """Test cases for resources READ operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = ResourcesTools()
        # Mock the client directly
        self.mock_client = Mock()
        self.tools._client = self.mock_client

    def test_read_issue_uri(self):
        """Test reading an issue via youtrack:// URI."""
        mock_issue_data = {
            "id": "DEMO-123",
            "summary": "Test Issue",
            "description": "Test description",
            "project": {"shortName": "DEMO"}
        }

        self.mock_client.get = Mock(return_value=mock_issue_data)

        result = self.tools.read(uri="youtrack://issues/DEMO-123")

        self.mock_client.get.assert_called_once_with("issues/DEMO-123")

        # Parse the JSON result
        result_data = json.loads(result)
        expected = {
            "uri": "youtrack://issues/DEMO-123",
            "resource_type": "issue",
            "content": mock_issue_data
        }
        assert result_data == expected

    def test_read_project_uri(self):
        """Test reading a project via youtrack:// URI."""
        mock_project_data = {
            "id": "0-0",
            "shortName": "DEMO",
            "name": "Demo Project",
            "description": "A demo project"
        }

        self.mock_client.get = Mock(return_value=mock_project_data)

        result = self.tools.read(uri="youtrack://projects/0-0")

        self.mock_client.get.assert_called_once_with("admin/projects/0-0")

        result_data = json.loads(result)
        expected = {
            "uri": "youtrack://projects/0-0",
            "resource_type": "project",
            "content": mock_project_data
        }
        assert result_data == expected

    def test_read_user_uri(self):
        """Test reading a user via youtrack:// URI."""
        mock_user_data = {
            "id": "user-1",
            "login": "testuser",
            "fullName": "Test User",
            "email": "test@example.com"
        }

        self.mock_client.get = Mock(return_value=mock_user_data)

        result = self.tools.read(uri="youtrack://users/user-1")

        self.mock_client.get.assert_called_once_with("users/user-1")

        result_data = json.loads(result)
        expected = {
            "uri": "youtrack://users/user-1",
            "resource_type": "user",
            "content": mock_user_data
        }
        assert result_data == expected

    def test_read_projects_list_uri(self):
        """Test reading projects list via youtrack:// URI."""
        mock_projects_data = [
            {"id": "0-0", "shortName": "DEMO", "name": "Demo Project"},
            {"id": "0-1", "shortName": "TEST", "name": "Test Project"}
        ]

        self.mock_client.get = Mock(return_value=mock_projects_data)

        result = self.tools.read(uri="youtrack://projects")

        self.mock_client.get.assert_called_once_with("admin/projects")

        result_data = json.loads(result)
        expected = {
            "uri": "youtrack://projects",
            "resource_type": "projects_list",
            "content": mock_projects_data
        }
        assert result_data == expected

    def test_read_issues_list_uri(self):
        """Test reading issues list via youtrack:// URI."""
        mock_issues_data = [
            {"id": "DEMO-123", "summary": "Issue 1"},
            {"id": "DEMO-124", "summary": "Issue 2"}
        ]

        self.mock_client.get = Mock(return_value=mock_issues_data)

        result = self.tools.read(uri="youtrack://issues")

        self.mock_client.get.assert_called_once_with("issues", params={"$top": 50})

        result_data = json.loads(result)
        expected = {
            "uri": "youtrack://issues",
            "resource_type": "issues_list",
            "content": mock_issues_data
        }
        assert result_data == expected

    def test_read_users_list_uri(self):
        """Test reading users list via youtrack:// URI."""
        mock_users_data = [
            {"id": "user-1", "login": "user1", "fullName": "User 1"},
            {"id": "user-2", "login": "user2", "fullName": "User 2"}
        ]

        self.mock_client.get = Mock(return_value=mock_users_data)

        result = self.tools.read(uri="youtrack://users")

        self.mock_client.get.assert_called_once_with("users")

        result_data = json.loads(result)
        expected = {
            "uri": "youtrack://users",
            "resource_type": "users_list",
            "content": mock_users_data
        }
        assert result_data == expected

    def test_read_help_uri(self):
        """Test reading help resource via help:// URI."""
        mock_help_content = {
            "description": "Help for issues.get",
            "parameters": ["issue_id", "include"],
            "examples": ["issues.get(issue_id='DEMO-123')"]
        }

        with patch('youtrack_mcp.tools.core_resources.get_help_resource') as mock_get_help:
            mock_get_help.return_value = mock_help_content

            result = self.tools.read(uri="help://issues.get")

            mock_get_help.assert_called_once_with("help://issues.get")

            result_data = json.loads(result)
            expected = {
                "uri": "help://issues.get",
                "resource_type": "help",
                "content": mock_help_content
            }
            assert result_data == expected

    def test_read_help_uri_not_found(self):
        """Test reading help resource that doesn't exist."""
        with patch('youtrack_mcp.tools.core_resources.get_help_resource') as mock_get_help:
            mock_get_help.return_value = None

            result = self.tools.read(uri="help://nonexistent.tool")

            result_data = json.loads(result)
            expected = {
                "error": "Help resource not found: help://nonexistent.tool"
            }
            assert result_data == expected

    def test_read_invalid_scheme(self):
        """Test reading URI with invalid scheme."""
        result = self.tools.read(uri="http://example.com")

        result_data = json.loads(result)
        expected = {
            "error": "Invalid URI scheme: http. Expected: youtrack or help"
        }
        assert result_data == expected

    def test_read_unsupported_uri_pattern(self):
        """Test reading unsupported URI pattern."""
        result = self.tools.read(uri="youtrack://unknown/resource")

        result_data = json.loads(result)
        expected = {
            "error": "Unsupported URI pattern: youtrack://unknown/resource"
        }
        assert result_data == expected

    def test_read_uri_with_query_params(self):
        """Test reading URI that includes query parameters."""
        mock_issue_data = {
            "id": "DEMO-123",
            "summary": "Test Issue"
        }

        self.mock_client.get = Mock(return_value=mock_issue_data)

        result = self.tools.read(uri="youtrack://issues/DEMO-123?fields=id,summary")

        # Should still work with query params (they get ignored)
        self.mock_client.get.assert_called_once_with("issues/DEMO-123")

        result_data = json.loads(result)
        assert "uri" in result_data
        assert "resource_type" in result_data
        assert "content" in result_data

    def test_read_uri_with_special_characters(self):
        """Test reading URI with special characters."""
        mock_issue_data = {
            "id": "DEMO-123_special",
            "summary": "Issue with special chars: @#$%^&*()"
        }

        self.mock_client.get = Mock(return_value=mock_issue_data)

        result = self.tools.read(uri="youtrack://issues/DEMO-123_special")

        self.mock_client.get.assert_called_once_with("issues/DEMO-123_special")

        result_data = json.loads(result)
        expected = {
            "uri": "youtrack://issues/DEMO-123_special",
            "resource_type": "issue",
            "content": mock_issue_data
        }
        assert result_data == expected

    def test_read_api_error(self):
        """Test error handling when API call fails."""
        self.mock_client.get = Mock(side_effect=Exception("API Error"))

        result = self.tools.read(uri="youtrack://issues/DEMO-123")

        result_data = json.loads(result)
        assert "error" in result_data
        assert "API Error" in result_data["error"]
        assert result_data["error_type"] == "Exception"
        assert result_data["uri"] == "youtrack://issues/DEMO-123"

    def test_read_empty_uri(self):
        """Test reading empty URI."""
        result = self.tools.read(uri="")

        result_data = json.loads(result)
        assert "error" in result_data
        assert "Invalid URI scheme" in result_data["error"]

    def test_read_uri_without_scheme(self):
        """Test reading URI without scheme."""
        result = self.tools.read(uri="issues/DEMO-123")

        result_data = json.loads(result)
        assert "error" in result_data
        assert "Invalid URI scheme" in result_data["error"]

    def test_read_uri_with_only_scheme(self):
        """Test reading URI with only scheme."""
        result = self.tools.read(uri="youtrack://")

        result_data = json.loads(result)
        assert "error" in result_data
        assert "Unsupported URI pattern" in result_data["error"]

    def test_read_case_sensitive_scheme(self):
        """Test reading URI with case-sensitive scheme."""
        result = self.tools.read(uri="YOUTRACK://issues/DEMO-123")

        result_data = json.loads(result)
        assert "error" in result_data
        assert "Invalid URI scheme" in result_data["error"]

    def test_read_help_case_sensitive_scheme(self):
        """Test reading help URI with case-sensitive scheme."""
        result = self.tools.read(uri="HELP://issues.get")

        result_data = json.loads(result)
        assert "error" in result_data
        assert "Invalid URI scheme" in result_data["error"]