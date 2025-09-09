"""
Golden tests for core issues GET operations.

Tests the rich read functionality with expansions for issue retrieval.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock
from youtrack_mcp.tools.core_issues import CoreIssuesTools


class TestCoreIssuesGet:
    """Test cases for issue GET operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = CoreIssuesTools()
        self.tools.client = Mock()
        self.tools.issues_api = Mock()

    @pytest.mark.asyncio
    async def test_get_basic_issue(self):
        """Test getting a basic issue without expansions."""
        mock_issue_data = {
            "id": "DEMO-123",
            "idReadable": "DEMO-123",
            "summary": "Test Issue",
            "description": "Test description",
            "project": {"id": "0-0", "shortName": "DEMO"},
            "reporter": {"id": "user-1", "login": "testuser"},
            "created": 1640995200000,
            "updated": 1640995200000
        }

        # Create a mock issue with model_dump method
        mock_issue = Mock()
        mock_issue.model_dump.return_value = mock_issue_data

        # Mock the async get_issue method
        self.tools.issues_api.get_issue = AsyncMock(return_value=mock_issue)

        result = await self.tools.get(issue_id="DEMO-123")

        self.tools.issues_api.get_issue.assert_called_once_with("DEMO-123")

        # Parse the JSON result
        result_data = json.loads(result)
        expected_issue = mock_issue_data.copy()
        expected_issue["created_iso8601"] = "2022-01-01T00:00:00+00:00"
        expected_issue["updated_iso8601"] = "2022-01-01T00:00:00+00:00"
        expected = {
            "issue": expected_issue,
            "expansions": [],
            "fields_requested": "id,idReadable,summary,description,created,updated,project,reporter,assignee"
        }
        assert result_data == expected

    @pytest.mark.asyncio
    async def test_get_issue_with_custom_fields_expansion(self):
        """Test getting an issue with custom fields expansion."""
        mock_issue_data = {
            "id": "DEMO-123",
            "summary": "Test Issue",
            "customFields": [
                {"name": "Priority", "value": {"name": "High"}},
                {"name": "Severity", "value": {"name": "Critical"}}
            ]
        }

        mock_issue = Mock()
        mock_issue.model_dump.return_value = mock_issue_data

        self.tools.issues_api.get_issue = AsyncMock(return_value=mock_issue)

        result = await self.tools.get(issue_id="DEMO-123", include=["customFields"])

        result_data = json.loads(result)
        expected = {
            "issue": mock_issue_data,
            "expansions": ["customFields"],
            "fields_requested": "id,idReadable,summary,description,created,updated,project,reporter,assignee,customFields"
        }
        assert result_data == expected

    @pytest.mark.asyncio
    async def test_get_issue_with_comments_expansion(self):
        """Test getting an issue with comments expansion."""
        mock_issue_data = {
            "id": "DEMO-123",
            "summary": "Test Issue",
            "comments": [
                {"id": "comment-1", "text": "First comment", "author": {"login": "user1"}},
                {"id": "comment-2", "text": "Second comment", "author": {"login": "user2"}}
            ]
        }

        mock_issue = Mock()
        mock_issue.model_dump.return_value = mock_issue_data

        self.tools.issues_api.get_issue = AsyncMock(return_value=mock_issue)

        result = await self.tools.get(issue_id="DEMO-123", include=["comments"])

        result_data = json.loads(result)
        expected = {
            "issue": mock_issue_data,
            "expansions": ["comments"],
            "fields_requested": "id,idReadable,summary,description,created,updated,project,reporter,assignee,comments"
        }
        assert result_data == expected

    @pytest.mark.asyncio
    async def test_get_issue_api_error(self):
        """Test error handling when API call fails."""
        self.tools.issues_api.get_issue = AsyncMock(side_effect=Exception("API Error"))

        result = await self.tools.get(issue_id="DEMO-123")

        result_data = json.loads(result)
        assert "error" in result_data
        assert "API Error" in result_data["error"]
        assert result_data["error_type"] == "Exception"
        assert result_data["issue_id"] == "DEMO-123"