"""
Test that detailed error information is returned to MCP clients.

This test verifies that when ValidationError and other API errors are raised,
they include comprehensive details like status codes, suggestions, and educational content.
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from youtrack_mcp.tools.search_tools import SearchTools
from youtrack_mcp.api.client import ValidationError


@pytest.mark.asyncio
async def test_validation_error_includes_detailed_info():
    """Test that ValidationError includes query, suggestions, and educational content."""
    search_tools = SearchTools()

    # Create a ValidationError with minimal info (as raised by API client)
    api_error = ValidationError(
        message="API request failed with status 400: invalid_query",
        status_code=400,
        response=MagicMock()
    )

    # Mock the issues_api.search_issues to raise ValidationError
    with patch.object(
        search_tools.issues_api,
        'search_issues',
        side_effect=api_error
    ):
        # The tool should enrich and re-raise with detailed info
        with pytest.raises(ValidationError) as exc_info:
            await search_tools.query("project: SP created: -1w .. Today")

        error = exc_info.value

        # Verify error has detailed information
        error_dict = error.to_dict()

        # Check core error info
        assert error_dict["error_type"] == "ValidationError"
        assert error_dict["status_code"] == 400
        assert "invalid_query" in error_dict["error"]

        # Check enriched query info
        assert error_dict["query"] == "project: SP created: -1w .. Today"

        # Check suggestions are present
        assert "suggestions" in error_dict
        assert len(error_dict["suggestions"]) > 0

        # Check educational content
        assert "learn_from_this" in error_dict
        assert len(error_dict["learn_from_this"]) > 0  # Should have some educational content

        # Check documentation link
        assert "documentation" in error_dict


@pytest.mark.asyncio
async def test_validation_error_json_serialization():
    """Test that ValidationError can be serialized to JSON for MCP client."""
    search_tools = SearchTools()

    api_error = ValidationError(
        message="API request failed with status 400: invalid_query",
        status_code=400,
        response=MagicMock()
    )

    with patch.object(
        search_tools.issues_api,
        'search_issues',
        side_effect=api_error
    ):
        with pytest.raises(ValidationError) as exc_info:
            await search_tools.query("project: INVALID")

        error = exc_info.value

        # Verify __str__ returns valid JSON
        error_json_str = str(error)
        error_data = json.loads(error_json_str)

        # Verify JSON contains all expected fields
        assert "error" in error_data
        assert "error_type" in error_data
        assert "status_code" in error_data
        assert "query" in error_data
        assert "suggestions" in error_data
        assert "learn_from_this" in error_data


@pytest.mark.asyncio
async def test_validation_error_with_date_syntax_detection():
    """Test that date syntax errors are detected and included in suggestions."""
    search_tools = SearchTools()

    # Create error for query with known date syntax issue
    api_error = ValidationError(
        message="API request failed with status 400: invalid_query",
        status_code=400,
        response=MagicMock()
    )

    with patch.object(
        search_tools.issues_api,
        'search_issues',
        side_effect=api_error
    ):
        with pytest.raises(ValidationError) as exc_info:
            # This query has incorrect date syntax (-1w should be {minus 1w})
            await search_tools.query("project: SP created: -1w .. Today")

        error = exc_info.value
        error_dict = error.to_dict()

        # Should have detected the date syntax issue
        assert "suggestions" in error_dict
        suggestions = error_dict["suggestions"]

        # Should mention the correct syntax
        assert any("minus" in str(s) for s in suggestions)


@pytest.mark.asyncio
async def test_other_api_errors_also_include_details():
    """Test that other API errors also propagate with details."""
    search_tools = SearchTools()

    from youtrack_mcp.api.client import AuthenticationError

    # Create an authentication error
    auth_error = AuthenticationError(
        message="API request failed with status 401: Unauthorized",
        status_code=401,
        response=MagicMock()
    )

    with patch.object(
        search_tools.issues_api,
        'search_issues',
        side_effect=auth_error
    ):
        with pytest.raises(AuthenticationError) as exc_info:
            await search_tools.query("project: SP")

        error = exc_info.value
        error_dict = error.to_dict()

        # Verify error includes status code
        assert error_dict["error_type"] == "AuthenticationError"
        assert error_dict["status_code"] == 401


@pytest.mark.asyncio
async def test_validation_error_preserves_response_data():
    """Test that ValidationError preserves response data from API."""
    search_tools = SearchTools()

    # Create a mock response with JSON error data
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "error": "invalid_query",
        "error_description": "Syntax error at position 23",
        "error_details": {"column": 23, "line": 1}
    }

    api_error = ValidationError(
        message="API request failed with status 400: invalid_query",
        status_code=400,
        response=mock_response
    )

    with patch.object(
        search_tools.issues_api,
        'search_issues',
        side_effect=api_error
    ):
        with pytest.raises(ValidationError) as exc_info:
            await search_tools.query("bad query")

        error = exc_info.value
        error_dict = error.to_dict()

        # Should include response data
        assert "response_data" in error_dict
        assert error_dict["response_data"]["error"] == "invalid_query"
        assert "error_details" in error_dict["response_data"]
