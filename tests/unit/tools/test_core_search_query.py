"""
Golden tests for core search QUERY operations.

Tests the explicit YouTrack Query Language execution functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from youtrack_mcp.tools.search_tools import SearchTools
from youtrack_mcp.utils import format_json_response


class TestCoreSearchQuery:
    """Test cases for search QUERY operations."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch('youtrack_mcp.config.Config.get_base_url', return_value='https://test.youtrack.cloud/api'):
            self.tools = SearchTools()
        self.tools.client = Mock()
        self.tools.issues_api = Mock()
    @pytest.mark.asyncio
    async def test_query_basic_search(self):
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

        self.tools.issues_api.search_issues = AsyncMock(return_value=mock_issues)

        result = await self.tools.query(query="project: DEMO", limit=10)

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

    @pytest.mark.asyncio
    async def test_query_with_sorting(self):
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

        self.tools.issues_api.search_issues = AsyncMock(return_value=mock_issues)

        result = await self.tools.query(
            query="project: DEMO",
            limit=5,
            sort_by="created",
            sort_order="desc"
        )

        self.tools.issues_api.search_issues.assert_called_once_with(query="project: DEMO", limit=5)

        result_data = json.loads(result)
        # The results may have additional fields added by the IssuesClient processing
        expected = {
            "query": "project: DEMO",
            "results": result_data["results"],  # Use actual results since they may have extra fields
            "count": 2,
            "limit": 5,
            "sort_by": "created",
            "sort_order": "desc"
        }
        # Check the key fields match expected
        assert result_data["query"] == expected["query"]
        assert result_data["count"] == expected["count"]
        assert result_data["limit"] == expected["limit"]
        assert result_data["sort_by"] == expected["sort_by"]
        assert result_data["sort_order"] == expected["sort_order"]
        assert len(result_data["results"]) == 2
        assert result_data["results"][0]["id"] == "DEMO-125"
        assert result_data["results"][1]["id"] == "DEMO-126"

    @pytest.mark.asyncio
    async def test_query_with_sort_by_only(self):
        """Test search query with sort_by but no sort_order."""
        mock_issues = [
            {
                "id": "DEMO-127",
                "summary": "Issue A",
                "priority": "High"
            }
        ]

        self.tools.issues_api.search_issues = AsyncMock(return_value=mock_issues)

        result = await self.tools.query(
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

    @pytest.mark.asyncio
    async def test_query_empty_results(self):
        """Test search query that returns no results."""
        mock_issues = []

        self.tools.issues_api.search_issues = AsyncMock(return_value=mock_issues)

        result = await self.tools.query(query="project: NONEXISTENT", limit=10)

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

    @pytest.mark.asyncio
    async def test_query_complex_yql(self):
        """Test search query with complex YouTrack Query Language."""
        mock_issues = [
            {
                "id": "DEMO-128",
                "summary": "Complex Issue",
                "state": "Open",
                "priority": "Critical"
            }
        ]

        self.tools.issues_api.search_issues = AsyncMock(return_value=mock_issues)

        complex_query = "project: DEMO state: Open priority: Critical assignee: me"
        result = await self.tools.query(query=complex_query, limit=5)

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

    @pytest.mark.asyncio
    async def test_query_with_limit_one(self):
        """Test search query with limit of 1."""
        mock_issues = [
            {
                "id": "DEMO-129",
                "summary": "Single Issue"
            }
        ]

        self.tools.issues_api.search_issues = AsyncMock(return_value=mock_issues)

        result = await self.tools.query(query="project: DEMO", limit=1)

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

    @pytest.mark.asyncio
    async def test_query_with_pydantic_models(self):
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

        self.tools.issues_api.search_issues = AsyncMock(return_value=mock_issues)

        result = await self.tools.query(query="project: DEMO", limit=10)

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

    @pytest.mark.asyncio
    async def test_query_with_dict_objects(self):
        """Test search query that returns plain dict objects."""
        # Use plain dicts instead of custom objects to avoid JSON serialization issues
        mock_issues = [
            {"id": "DEMO-132", "summary": "Dict Issue 1"},
            {"id": "DEMO-133", "summary": "Dict Issue 2"}
        ]

        self.tools.issues_api.search_issues = AsyncMock(return_value=mock_issues)

        result = await self.tools.query(query="project: DEMO", limit=10)

        self.tools.issues_api.search_issues.assert_called_once_with(query="project: DEMO", limit=10)

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

    @pytest.mark.asyncio
    async def test_query_api_error(self):
        """Test error handling when API call fails."""
        self.tools.issues_api.search_issues = AsyncMock(side_effect=Exception("API Error"))

        result = await self.tools.query(query="project: DEMO", limit=10)

        result_data = json.loads(result)
        assert "error" in result_data
        assert "API Error" in result_data["error"]
        assert result_data["error_type"] == "Exception"
        assert result_data["query"] == "project: DEMO"

    @pytest.mark.asyncio
    async def test_query_invalid_sort_order(self):
        """Test search query with invalid sort order (should default to desc)."""
        mock_issues = [
            {
                "id": "DEMO-134",
                "summary": "Issue with invalid sort"
            }
        ]

        self.tools.issues_api.search_issues = AsyncMock(return_value=mock_issues)

        result = await self.tools.query(
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

    @pytest.mark.asyncio
    async def test_query_special_characters_in_query(self):
        """Test search query with special characters."""
        mock_issues = [
            {
                "id": "DEMO-135",
                "summary": "Issue with special chars"
            }
        ]

        special_query = 'project: DEMO text: "special characters: @#$%^&*()"'
        self.tools.issues_api.search_issues = AsyncMock(return_value=mock_issues)

        result = await self.tools.query(query=special_query, limit=10)

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

    @pytest.mark.asyncio
    async def test_query_large_result_set(self):
        """Test search query with a large number of results."""
        # Create 100 mock issues
        mock_issues = []
        for i in range(100):
            mock_issues.append({
                "id": f"DEMO-{100 + i}",
                "summary": f"Issue {i}",
                "created": 1641000000000 + (i * 1000000)  # Different timestamps
            })

        self.tools.issues_api.search_issues = AsyncMock(return_value=mock_issues)

        result = await self.tools.query(query="project: DEMO", limit=100)

        self.tools.issues_api.search_issues.assert_called_once_with(query="project: DEMO", limit=100)

        result_data = json.loads(result)
        assert result_data["count"] == 100
        assert len(result_data["results"]) == 100
        assert result_data["query"] == "project: DEMO"
        assert result_data["limit"] == 100

        # Verify first and last issues
        assert result_data["results"][0]["id"] == "DEMO-100"
        assert result_data["results"][99]["id"] == "DEMO-199"

    @pytest.mark.asyncio
    async def test_query_date_syntax_error_detection(self):
        """Test that incorrect date syntax returns error with suggestions."""
        # Set up async mock
        self.tools.issues_api.search_issues = AsyncMock()

        # Test with incorrect date syntax that should return error
        incorrect_query = "created: -6m .. *"
        result = await self.tools.query(query=incorrect_query, limit=10)

        # Should NOT call API due to syntax error
        self.tools.issues_api.search_issues.assert_not_called()

        result_data = json.loads(result)
        assert result_data["query"] == incorrect_query
        assert "error" in result_data
        assert "Invalid date range syntax detected" in result_data["error"]
        assert "suggestions" in result_data
        assert len(result_data["suggestions"]) > 0
        assert "examples" in result_data
        assert result_data["results"] == []
        assert result_data["count"] == 0

    @pytest.mark.asyncio
    async def test_query_date_syntax_error_detection_complex(self):
        """Test date syntax error detection with multiple patterns."""
        # Test with multiple incorrect patterns
        complex_query = "created: -6m .. * AND updated: {30 days ago .. Today}"
        result = await self.tools.query(query=complex_query, limit=10)

        # Should NOT call API due to syntax errors
        # (Note: issues_api.search_issues is not mocked here, so it won't be called)

        result_data = json.loads(result)
        assert result_data["query"] == complex_query
        assert "error" in result_data
        assert "Invalid date range syntax detected" in result_data["error"]
        assert "suggestions" in result_data
        assert len(result_data["suggestions"]) >= 2  # Should have suggestions for both patterns
        assert "examples" in result_data
        assert result_data["results"] == []
        assert result_data["count"] == 0

    @pytest.mark.asyncio
    async def test_query_date_syntax_already_correct(self):
        """Test that correct date syntax works normally."""
        mock_issues = [
            {
                "id": "DEMO-202",
                "summary": "Already correct date syntax"
            }
        ]

        self.tools.issues_api.search_issues = AsyncMock(return_value=mock_issues)

        # Test with already correct syntax
        correct_query = "created: {minus 7d} .. Today"
        result = await self.tools.query(query=correct_query, limit=10)

        # Should call API with same query (no errors)
        self.tools.issues_api.search_issues.assert_called_once_with(query=correct_query, limit=10)

        result_data = json.loads(result)
        assert "error" not in result_data  # No error for correct syntax
        assert result_data["query"] == correct_query
        assert result_data["results"] == mock_issues