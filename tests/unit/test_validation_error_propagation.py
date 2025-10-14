"""
Test that validation errors from YouTrack API properly propagate as MCP errors.

This test verifies the fix for the issue where ValidationError exceptions
were being caught and returned as JSON, causing MCP to report is_error=False
instead of is_error=True.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from youtrack_mcp.tools.search_tools import SearchTools
from youtrack_mcp.api.client import ValidationError


@pytest.mark.asyncio
async def test_validation_error_propagates_as_exception():
    """Test that ValidationError is raised, not returned as JSON dict."""
    search_tools = SearchTools()

    # Mock the issues_api.search_issues to raise ValidationError
    with patch.object(
        search_tools.issues_api,
        'search_issues',
        side_effect=ValidationError("API request failed with status 400: invalid_query", 400, MagicMock())
    ):
        # The tool should raise ValidationError, not return a dict with error field
        with pytest.raises(ValidationError) as exc_info:
            await search_tools.query("project: SP created: -1w .. Today #Unresolved")

        # Verify the error message
        assert "invalid_query" in str(exc_info.value)
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_validation_error_not_returned_as_json():
    """Test that validation errors are NOT returned as JSON objects."""
    search_tools = SearchTools()

    # Mock the issues_api.search_issues to raise ValidationError
    with patch.object(
        search_tools.issues_api,
        'search_issues',
        side_effect=ValidationError("API request failed with status 400: invalid_query", 400, MagicMock())
    ):
        # Try to call the tool
        try:
            result = await search_tools.query("invalid query")
            # If we got here, the tool returned a result instead of raising
            # Check if it's an error dict (this is the OLD broken behavior)
            if isinstance(result, dict) and "error" in result:
                pytest.fail(
                    "ValidationError was caught and returned as JSON dict instead of being raised. "
                    "This causes MCP to report is_error=False. "
                    f"Result: {result}"
                )
            else:
                pytest.fail(
                    "Tool returned a result without raising ValidationError: {result}"
                )
        except ValidationError:
            # This is the CORRECT behavior - validation errors should propagate
            pass


@pytest.mark.asyncio
async def test_other_exceptions_also_propagate():
    """Test that all exceptions propagate for proper MCP error handling."""
    search_tools = SearchTools()

    # Mock the issues_api.search_issues to raise a different exception
    with patch.object(
        search_tools.issues_api,
        'search_issues',
        side_effect=RuntimeError("Unexpected error")
    ):
        # All exceptions should propagate so MCP can handle them properly
        with pytest.raises(RuntimeError) as exc_info:
            await search_tools.query("some query")

        assert "Unexpected error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_successful_query_returns_dict():
    """Test that successful queries still return normal result dicts."""
    search_tools = SearchTools()

    # Mock successful response
    mock_issues = [
        {"id": "1", "idReadable": "SP-1", "summary": "Test issue"}
    ]

    with patch.object(
        search_tools.issues_api,
        'search_issues',
        return_value=mock_issues
    ):
        result = await search_tools.query("project: SP")

        # Should return a dict with results
        assert isinstance(result, dict)
        assert "results" in result
        assert "query" in result
        assert "error" not in result
        assert len(result["results"]) == 1
