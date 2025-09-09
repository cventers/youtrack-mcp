"""
Golden tests for core search QUERY operations.

Tests the explicit YouTrack Query Language execution functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch
from youtrack_mcp.tools.core_search import CoreSearchTools
from youtrack_mcp.utils import format_json_response


class TestCoreSearchQuery:
    """Test cases for search QUERY operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = CoreSearchTools()
        self.tools.client = Mock()
        self.tools.issues_api = Mock()

    def test_query_basic_search(self):
        """Test basic search query without sorting."""
        mock_issues = [
            {
                "id": "DEMO-123",
                "summary": "Test Issue 1",
                "project": {"shortName": "DEMO"},
                "assignee": {"login": "user1"}
            },
            {
                "id": "DEMO-124",
                "summary": "Test Issue 2",
                "project": {"shortName": "DEMO"},
                "assignee": {"login": "user2"}
            }
        ]

        self.tools.issues_api.search_issues = Mock(return_value=mock_issues)

        result = self.tools.query(query="project: DEMO", limit=10)

        self.tools.issues_api.search_issues.assert_called_once_with(query="project: DEMO", limit=10)

        # Parse the JSON result
        result_data = json.loads(result)
        expected = {
            "query": "project: DEMO",
            "results": mock_issues,
            "count": 2,
            "limit": 10,
            "sort_by": None,
            "sort_order": None
        }
        assert result_data == expected

    def test_query_with_sorting(self):
        """Test search query with sorting parameters."""
        mock_issues = [
            {
                "id": "DEMO-125",
                "summary": "Newer Issue",
                "created": 1642000000000
            },
            {
                "id": "DEMO-126",
                "summary": "Older Issue",
                "created": 1641000000000
            }
        ]

        self.tools.issues_api.search_issues = Mock(return_value=mock_issues)

        result = self.tools.query(
            query="project: DEMO",
            limit=5,
            sort_by="created",
            sort_order="desc"
        )

        self.tools.issues_api.search_issues.assert_called_once_with(query="project: DEMO", limit=5)

        result_data = json.loads(result)
        expected = {
            "query": "project: DEMO",
            "results": mock_issues,
            "count": 2,
            "limit": 5,
            "sort_by": "created",
            "sort_order": "desc"
        }
        assert result_data == expected

    def test_query_with_sort_by_only(self):
        """Test search query with sort_by but no sort_order."""
        mock_issues = [
            {
                "id": "DEMO-127",
                "summary": "Issue A",
                "priority": "High"
            }
        ]

        self.tools.issues_api.search_issues = Mock(return_value=mock_issues)

        result = self.tools.query(
            query="project: DEMO",
            limit=10,
            sort_by="priority"
        )

        self.tools.issues_api.search_issues.assert_called_once_with(query="project: DEMO", limit=10)

        result_data = json.loads(result)
        expected = {
            "query": "project: DEMO",
            "results": mock_issues,
            "count": 1,
            "limit": 10,
            "sort_by": "priority",
            "sort_order": None
        }
        assert result_data == expected

    def test_query_empty_results(self):
        """Test search query that returns no results."""
        mock_issues = []

        self.tools.issues_api.search_issues = Mock(return_value=mock_issues)

        result = self.tools.query(query="project: NONEXISTENT", limit=10)

        self.tools.issues_api.search_issues.assert_called_once_with(query="project: NONEXISTENT", limit=10)

        result_data = json.loads(result)
        expected = {
            "query": "project: NONEXISTENT",
            "results": [],
            "count": 0,
            "limit": 10,
            "sort_by": None,
            "sort_order": None
        }
        assert result_data == expected

    def test_query_complex_yql(self):
        """Test search query with complex YouTrack Query Language."""
        mock_issues = [
            {
                "id": "DEMO-128",
                "summary": "Complex Issue",
                "state": "Open",
                "priority": "Critical"
            }
        ]

        self.tools.issues_api.search_issues = Mock(return_value=mock_issues)

        complex_query = "project: DEMO state: Open priority: Critical assignee: me"
        result = self.tools.query(query=complex_query, limit=5)

        self.tools.issues_api.search_issues.assert_called_once_with(query=complex_query, limit=5)

        result_data = json.loads(result)
        expected = {
            "query": complex_query,
            "results": mock_issues,
            "count": 1,
            "limit": 5,
            "sort_by": None,
            "sort_order": None
        }
        assert result_data == expected

    def test_query_with_limit_one(self):
        """Test search query with limit of 1."""
        mock_issues = [
            {
                "id": "DEMO-129",
                "summary": "Single Issue"
            }
        ]

        self.tools.issues_api.search_issues = Mock(return_value=mock_issues)

        result = self.tools.query(query="project: DEMO", limit=1)

        self.tools.issues_api.search_issues.assert_called_once_with(query="project: DEMO", limit=1)

        result_data = json.loads(result)
        expected = {
            "query": "project: DEMO",
            "results": mock_issues,
            "count": 1,
            "limit": 1,
            "sort_by": None,
            "sort_order": None
        }
        assert result_data == expected

    def test_query_with_pydantic_models(self):
        """Test search query that returns Pydantic models."""
        class MockIssue:
            def __init__(self, id, summary):
                self.id = id
                self.summary = summary

            def model_dump(self):
                return {
                    "id": self.id,
                    "summary": self.summary
                }

        mock_issues = [
            MockIssue("DEMO-130", "Pydantic Issue 1"),
            MockIssue("DEMO-131", "Pydantic Issue 2")
        ]

        self.tools.issues_api.search_issues = Mock(return_value=mock_issues)

        result = self.tools.query(query="project: DEMO", limit=10)

        self.tools.issues_api.search_issues.assert_called_once_with(query="project: DEMO", limit=10)

        result_data = json.loads(result)
        expected_issues = [
            {"id": "DEMO-130", "summary": "Pydantic Issue 1"},
            {"id": "DEMO-131", "summary": "Pydantic Issue 2"}
        ]
        expected = {
            "query": "project: DEMO",
            "results": expected_issues,
            "count": 2,
            "limit": 10,
            "sort_by": None,
            "sort_order": None
        }
        assert result_data == expected

    def test_query_with_dict_objects(self):
        """Test search query that returns plain dict objects."""
        class MockIssue:
            def __init__(self, id, summary):
                self.__dict__ = {
                    "id": id,
                    "summary": summary
                }

        mock_issues = [
            MockIssue("DEMO-132", "Dict Issue 1"),
            MockIssue("DEMO-133", "Dict Issue 2")
        ]

        self.tools.issues_api.search_issues = Mock(return_value=mock_issues)

        result = self.tools.query(query="project: DEMO", limit=10)

        self.tools.issues_api.search_issues.assert_called_once_with(query="project: DEMO", limit=10)

        result_data = json.loads(result)
        expected_issues = [
            {"id": "DEMO-132", "summary": "Dict Issue 1"},
            {"id": "DEMO-133", "summary": "Dict Issue 2"}
        ]
        expected = {
            "query": "project: DEMO",
            "results": expected_issues,
            "count": 2,
            "limit": 10,
            "sort_by": None,
            "sort_order": None
        }
        assert result_data == expected

    def test_query_api_error(self):
        """Test error handling when API call fails."""
        self.tools.issues_api.search_issues = Mock(side_effect=Exception("API Error"))

        result = self.tools.query(query="project: DEMO", limit=10)

        result_data = json.loads(result)
        assert "error" in result_data
        assert "API Error" in result_data["error"]
        assert result_data["error_type"] == "Exception"
        assert result_data["query"] == "project: DEMO"

    def test_query_invalid_sort_order(self):
        """Test search query with invalid sort order (should default to desc)."""
        mock_issues = [
            {
                "id": "DEMO-134",
                "summary": "Issue with invalid sort"
            }
        ]

        self.tools.issues_api.search_issues = Mock(return_value=mock_issues)

        result = self.tools.query(
            query="project: DEMO",
            limit=10,
            sort_by="created",
            sort_order="invalid"
        )

        self.tools.issues_api.search_issues.assert_called_once_with(query="project: DEMO", limit=10)

        result_data = json.loads(result)
        expected = {
            "query": "project: DEMO",
            "results": mock_issues,
            "count": 1,
            "limit": 10,
            "sort_by": "created",
            "sort_order": "invalid"  # Should still be passed through
        }
        assert result_data == expected

    def test_query_special_characters_in_query(self):
        """Test search query with special characters."""
        mock_issues = [
            {
                "id": "DEMO-135",
                "summary": "Issue with special chars"
            }
        ]

        special_query = 'project: DEMO text: "special characters: @#$%^&*()"'
        self.tools.issues_api.search_issues = Mock(return_value=mock_issues)

        result = self.tools.query(query=special_query, limit=10)

        self.tools.issues_api.search_issues.assert_called_once_with(query=special_query, limit=10)

        result_data = json.loads(result)
        expected = {
            "query": special_query,
            "results": mock_issues,
            "count": 1,
            "limit": 10,
            "sort_by": None,
            "sort_order": None
        }
        assert result_data == expected

    def test_query_large_result_set(self):
        """Test search query with a large number of results."""
        # Create 100 mock issues
        mock_issues = []
        for i in range(100):
            mock_issues.append({
                "id": f"DEMO-{100 + i}",
                "summary": f"Issue {i}",
                "created": 1641000000000 + (i * 1000000)  # Different timestamps
            })

        self.tools.issues_api.search_issues = Mock(return_value=mock_issues)

        result = self.tools.query(query="project: DEMO", limit=100)

        self.tools.issues_api.search_issues.assert_called_once_with(query="project: DEMO", limit=100)

        result_data = json.loads(result)
        assert result_data["count"] == 100
        assert len(result_data["results"]) == 100
        assert result_data["query"] == "project: DEMO"
        assert result_data["limit"] == 100

        # Verify first and last issues
        assert result_data["results"][0]["id"] == "DEMO-100"
        assert result_data["results"][99]["id"] == "DEMO-199"